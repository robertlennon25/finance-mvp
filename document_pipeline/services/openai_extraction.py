from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, RAW_EXTRACTIONS_ROOT
from document_pipeline.models import FieldCandidate
from document_pipeline.prompts.extraction import (
    EXTRACTION_PROMPT_VERSION,
    build_chunk_extraction_prompt,
    build_document_synthesis_prompt,
)
from document_pipeline.schemas import EXTRACTED_FIELD_SCHEMA
from document_pipeline.schemas.extracted_fields import EXTRACTION_SCHEMA_VERSION
from document_pipeline.storage.env import load_local_env


class ChunkExtractionError(RuntimeError):
    pass


def run_chunk_extraction(
    deal_id: str,
    model: str = "gpt-4.1-mini",
    max_chunks: int | None = None,
) -> Dict[str, Any]:
    load_local_env()
    manifest_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = manifest["chunks"][:max_chunks] if max_chunks else manifest["chunks"]
    manifest_fingerprint = manifest.get("manifest_fingerprint") or _derive_manifest_fingerprint(
        manifest
    )
    raw_output_path = RAW_EXTRACTIONS_ROOT / f"{deal_id}_chunk_candidates_raw.json"
    normalized_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates.json"
    metadata_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_extraction_metadata.json"
    cache_key = _build_cache_key(
        manifest_fingerprint=manifest_fingerprint,
        model=model,
        chunk_ids=[chunk["chunk_id"] for chunk in chunks],
    )

    cached_payload = _load_cached_result(
        metadata_path=metadata_path,
        normalized_path=normalized_path,
        raw_output_path=raw_output_path,
        expected_cache_key=cache_key,
    )
    if cached_payload:
        return cached_payload

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ChunkExtractionError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    all_candidates: List[FieldCandidate] = []
    raw_outputs: List[Dict[str, Any]] = []

    for chunk in chunks:
        source_locator = _build_source_locator(chunk)
        prompt = build_chunk_extraction_prompt(chunk["text"], source_locator)
        response = client.responses.create(
            model=model,
            input=prompt,
            temperature=0,
        )
        raw_text = response.output_text.strip()
        raw_outputs.append(
            {
                "chunk_id": chunk["chunk_id"],
                "source_locator": source_locator,
                "raw_output": raw_text,
            }
        )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ChunkExtractionError(
                f"Model did not return valid JSON for chunk {chunk['chunk_id']}: {raw_text[:500]}"
            ) from exc

        candidates = _coerce_candidates(
            document_id=chunk["document_id"],
            payload=payload,
            fallback_source_locator=source_locator,
        )
        all_candidates.extend(candidates)

    synthesis_candidates = _run_document_synthesis(
        client=client,
        model=model,
        manifest=manifest,
        existing_candidates=all_candidates,
    )
    all_candidates.extend(synthesis_candidates)
    if synthesis_candidates:
        raw_outputs.append(
            {
                "chunk_id": "document_synthesis",
                "source_locator": "document_synthesis",
                "raw_output": json.dumps([asdict(candidate) for candidate in synthesis_candidates], indent=2),
            }
        )

    raw_output_path.write_text(json.dumps(raw_outputs, indent=2), encoding="utf-8")

    normalized_output = {
        "deal_id": deal_id,
        "model": model,
        "candidate_count": len(all_candidates),
        "candidates": [asdict(candidate) for candidate in all_candidates],
    }
    normalized_path.write_text(json.dumps(normalized_output, indent=2), encoding="utf-8")
    metadata = {
        "deal_id": deal_id,
        "cache_key": cache_key,
        "manifest_fingerprint": manifest_fingerprint,
        "selected_chunk_ids": [chunk["chunk_id"] for chunk in chunks],
        "selected_chunk_count": len(chunks),
        "model": model,
        "prompt_version": EXTRACTION_PROMPT_VERSION,
        "schema_version": EXTRACTION_SCHEMA_VERSION,
        "cached": False,
        "cache_hit_count": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "normalized_path": str(normalized_path),
        "raw_output_path": str(raw_output_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "deal_id": deal_id,
        "model": model,
        "candidate_count": len(all_candidates),
        "raw_output_path": str(raw_output_path),
        "normalized_path": str(normalized_path),
        "cached": False,
        "cache_key": cache_key,
        "metadata_path": str(metadata_path),
    }


def _coerce_candidates(
    document_id: str,
    payload: Dict[str, Any],
    fallback_source_locator: str,
) -> List[FieldCandidate]:
    result: List[FieldCandidate] = []
    for item in payload.get("candidates", []):
        field_name = str(item.get("field_name", "")).strip()
        if field_name not in EXTRACTED_FIELD_SCHEMA:
            continue
        result.append(
            FieldCandidate(
                field_name=field_name,
                value=item.get("value"),
                confidence=_coerce_confidence(item.get("confidence", 0.0)),
                source_document_id=document_id,
                source_locator=str(item.get("source_locator") or fallback_source_locator),
                method=str(item.get("method") or "extracted"),
                notes=str(item.get("notes", "")).strip(),
                source_urls=[],
            )
        )
    return result


def _coerce_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _build_source_locator(chunk: Dict[str, Any]) -> str:
    page_start = chunk.get("page_start")
    page_end = chunk.get("page_end")
    if page_start and page_end:
        if page_start == page_end:
            return f"{chunk['document_id']} page {page_start}"
        return f"{chunk['document_id']} pages {page_start}-{page_end}"
    return chunk["document_id"]


def _build_cache_key(
    manifest_fingerprint: str,
    model: str,
    chunk_ids: List[str],
) -> str:
    digest = hashlib.sha256()
    payload = {
        "manifest_fingerprint": manifest_fingerprint,
        "model": model,
        "chunk_ids": chunk_ids,
        "prompt_version": EXTRACTION_PROMPT_VERSION,
        "schema_version": EXTRACTION_SCHEMA_VERSION,
    }
    digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _load_cached_result(
    metadata_path: Path,
    normalized_path: Path,
    raw_output_path: Path,
    expected_cache_key: str,
) -> Dict[str, Any] | None:
    if not metadata_path.exists() or not normalized_path.exists() or not raw_output_path.exists():
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("cache_key") != expected_cache_key:
        return None

    normalized_output = json.loads(normalized_path.read_text(encoding="utf-8"))
    metadata["cached"] = True
    metadata["cache_hit_count"] = int(metadata.get("cache_hit_count", 0)) + 1
    metadata["last_cache_hit_at"] = datetime.now(timezone.utc).isoformat()
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "deal_id": normalized_output.get("deal_id"),
        "model": normalized_output.get("model"),
        "candidate_count": normalized_output.get("candidate_count", 0),
        "raw_output_path": str(raw_output_path),
        "normalized_path": str(normalized_path),
        "cached": True,
        "cache_key": expected_cache_key,
        "metadata_path": str(metadata_path),
    }


def _derive_manifest_fingerprint(manifest: Dict[str, Any]) -> str:
    digest = hashlib.sha256()
    payload = {
        "chunk_chars": manifest.get("chunk_chars"),
        "chunk_overlap_chars": manifest.get("chunk_overlap_chars"),
        "documents": [
            {
                "filename": document.get("filename"),
                "file_size": document.get("file_size"),
                "sha256": document.get("sha256"),
                "document_type": document.get("document_type"),
            }
            for document in manifest.get("documents", [])
        ],
    }
    digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _run_document_synthesis(
    client: OpenAI,
    model: str,
    manifest: Dict[str, Any],
    existing_candidates: List[FieldCandidate],
) -> List[FieldCandidate]:
    missing_fields = _missing_core_fields(existing_candidates)
    if not missing_fields:
        return []

    snippets = _select_relevant_snippets(manifest, limit=12)
    if not snippets:
        return []

    prompt = build_document_synthesis_prompt(snippets, missing_fields)
    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
    )
    raw_text = response.output_text.strip()
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _extract_json_payload(raw_text)
        if payload is None:
            return []

    return _coerce_candidates(
        document_id="document_synthesis",
        payload=payload,
        fallback_source_locator="document_synthesis",
    )


def _missing_core_fields(candidates: List[FieldCandidate]) -> List[str]:
    present = {}
    for candidate in candidates:
        try:
            numeric = float(candidate.value)
        except (TypeError, ValueError):
            numeric = None
        if candidate.field_name in {"revenue", "ebitda", "shares_outstanding", "cash", "debt"}:
            if numeric is not None and numeric > 0:
                present[candidate.field_name] = True
        elif candidate.field_name in {"entry_multiple", "exit_multiple", "ebitda_margin_assumption"}:
            if numeric is not None and numeric > 0:
                present[candidate.field_name] = True
    ordered = ["revenue", "ebitda", "shares_outstanding", "cash", "debt", "ebitda_margin_assumption", "entry_multiple"]
    return [field_name for field_name in ordered if not present.get(field_name)]


def _select_relevant_snippets(manifest: Dict[str, Any], limit: int = 12) -> List[Dict[str, str]]:
    finance_markers = (
        "revenue",
        "sales",
        "net revenue",
        "total revenue",
        "ebitda",
        "adjusted ebitda",
        "income",
        "operating income",
        "cash and cash equivalents",
        "debt",
        "long-term debt",
        "shares outstanding",
        "common stock",
        "enterprise value",
        "ev / ebitda",
    )
    scored = []
    for chunk in manifest.get("chunks", []):
        text = str(chunk.get("text", ""))
        lower = text.lower()
        score = sum(1 for marker in finance_markers if marker in lower)
        if score <= 0:
            continue
        scored.append((score, chunk))
    scored.sort(key=lambda item: (item[0], -int(item[1].get("chunk_index", 0))), reverse=True)
    selected = []
    seen = set()
    for _, chunk in scored:
        chunk_id = chunk.get("chunk_id")
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        selected.append(
            {
                "source_locator": _build_source_locator(chunk),
                "text": str(chunk.get("text", ""))[:2500],
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _extract_json_payload(raw_text: str) -> Dict[str, Any] | None:
    text = raw_text.strip()
    candidates = [text]
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None

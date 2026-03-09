from __future__ import annotations

import json
import hashlib
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from document_pipeline.config import (
    CHUNKS_ROOT,
    INBOX_ROOT,
    NORMALIZED_EXTRACTIONS_ROOT,
    PROCESSED_ROOT,
    RAW_EXTRACTIONS_ROOT,
)
from document_pipeline.models import ChunkRecord, DocumentRecord
from document_pipeline.parsers.text_extractor import (
    extract_document_payload,
    is_supported_document,
)


def run_local_ingestion(deal_id: str, chunk_chars: int = 4000, chunk_overlap_chars: int = 500) -> Dict[str, Any]:
    inbox_dir = INBOX_ROOT / deal_id
    if not inbox_dir.exists() or not inbox_dir.is_dir():
        raise FileNotFoundError(f"Deal inbox not found: {inbox_dir}")

    _ensure_output_dirs()
    document_paths = sorted(
        path for path in inbox_dir.iterdir() if path.is_file() and is_supported_document(path)
    )
    if not document_paths:
        raise FileNotFoundError(f"No supported documents found in {inbox_dir}")

    documents: List[DocumentRecord] = []
    chunks: List[ChunkRecord] = []

    for index, path in enumerate(document_paths, start=1):
        document_id = f"{deal_id}_doc_{index:03d}"
        payload = extract_document_payload(path)
        doc_record = DocumentRecord(
            deal_id=deal_id,
            document_id=document_id,
            filename=path.name,
            path=str(path),
            document_type=payload["document_type"],
            file_size=path.stat().st_size,
            sha256=_hash_file(path),
        )
        documents.append(doc_record)

        raw_output = {
            "document": asdict(doc_record),
            "page_count": payload["page_count"],
            "text": payload["text"],
            "pages": payload["pages"],
        }
        _write_json(RAW_EXTRACTIONS_ROOT / f"{document_id}.json", raw_output)

        doc_chunks = _build_chunks(
            document_id=document_id,
            payload=payload,
            chunk_chars=chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars,
        )
        chunks.extend(doc_chunks)
        _write_json(
            CHUNKS_ROOT / f"{document_id}.json",
            [asdict(chunk) for chunk in doc_chunks],
        )

        processed_target = PROCESSED_ROOT / deal_id
        processed_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, processed_target / path.name)

    manifest = {
        "deal_id": deal_id,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "manifest_fingerprint": _build_manifest_fingerprint(documents, chunk_chars, chunk_overlap_chars),
        "chunk_chars": chunk_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "documents": [asdict(doc) for doc in documents],
        "chunks": [asdict(chunk) for chunk in chunks],
    }
    _write_json(NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_manifest.json", manifest)
    return manifest


def _build_chunks(
    document_id: str,
    payload: Dict[str, Any],
    chunk_chars: int,
    chunk_overlap_chars: int,
) -> List[ChunkRecord]:
    chunks: List[ChunkRecord] = []
    chunk_index = 1
    step_chars = max(250, chunk_chars - max(0, chunk_overlap_chars))

    for page in payload["pages"]:
        page_text = " ".join(page["text"].split())
        if not page_text:
            continue

        start = 0
        while start < len(page_text):
            end = min(start + chunk_chars, len(page_text))
            chunk_text = page_text[start:end].strip()
            if chunk_text:
                chunks.append(
                    ChunkRecord(
                        document_id=document_id,
                        chunk_id=f"{document_id}_chunk_{chunk_index:04d}",
                        chunk_index=chunk_index,
                        text=chunk_text,
                        page_start=page["page_number"],
                        page_end=page["page_number"],
                        metadata={
                            "char_start": start,
                            "char_end": end,
                        },
                    )
                )
                chunk_index += 1
            if end >= len(page_text):
                break
            start += step_chars

    return chunks


def _ensure_output_dirs() -> None:
    for path in (
        RAW_EXTRACTIONS_ROOT,
        NORMALIZED_EXTRACTIONS_ROOT,
        CHUNKS_ROOT,
        PROCESSED_ROOT,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _build_manifest_fingerprint(
    documents: List[DocumentRecord],
    chunk_chars: int,
    chunk_overlap_chars: int,
) -> str:
    digest = hashlib.sha256()
    payload = {
        "chunk_chars": chunk_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "documents": [
            {
                "filename": document.filename,
                "file_size": document.file_size,
                "sha256": document.sha256,
                "document_type": document.document_type,
            }
            for document in documents
        ],
    }
    digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()

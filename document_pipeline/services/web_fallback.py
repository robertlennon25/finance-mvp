from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from openai import OpenAI

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, RAW_EXTRACTIONS_ROOT
from document_pipeline.storage.env import load_local_env


WEB_FALLBACK_VERSION = "2026-03-09-v1"
PUBLIC_FILENAME_MARKERS = (
    "10-k",
    "10k",
    "10-q",
    "10q",
    "annual report",
    "earnings",
    "proxy",
    "investor",
)


def get_web_fallback_candidates(
    deal_id: str,
    company_name: str,
    manifest_payload: Dict[str, Any],
    missing_fields: List[str],
    model: str = "gpt-4.1-mini",
) -> List[Dict[str, Any]]:
    load_local_env()
    if not company_name or not missing_fields:
        return []
    if not _looks_like_public_company_case(manifest_payload):
        return []

    normalized_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_web_fallback_candidates.json"
    status_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_web_fallback_status.json"
    raw_output_path = RAW_EXTRACTIONS_ROOT / f"{deal_id}_web_fallback_raw.json"
    cache_key = json.dumps(
        {
            "company_name": company_name,
            "missing_fields": sorted(missing_fields),
            "model": model,
            "version": WEB_FALLBACK_VERSION,
        },
        sort_keys=True,
    )
    if normalized_path.exists():
        cached = json.loads(normalized_path.read_text(encoding="utf-8"))
        if cached.get("cache_key") == cache_key:
            _write_status(
                status_path,
                deal_id=deal_id,
                company_name=company_name,
                missing_fields=missing_fields,
                status="cache_hit",
                reason="Reused cached web fallback candidates.",
            )
            return cached.get("candidates", [])

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _write_status(
            status_path,
            deal_id=deal_id,
            company_name=company_name,
            missing_fields=missing_fields,
            status="skipped",
            reason="OPENAI_API_KEY is not configured.",
        )
        return []

    client = OpenAI(api_key=api_key)
    prompt = _build_web_fallback_prompt(company_name, missing_fields)
    response = _run_web_search_response(client, model, prompt)
    raw_text = response.output_text.strip()
    raw_output_path.write_text(
        json.dumps(
            {
                "deal_id": deal_id,
                "company_name": company_name,
                "missing_fields": missing_fields,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "raw_output": raw_text,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = _extract_json_payload(raw_text)
    if payload is None:
        _write_status(
            status_path,
            deal_id=deal_id,
            company_name=company_name,
            missing_fields=missing_fields,
            status="parse_failed",
            reason="Web fallback returned text that could not be parsed as JSON.",
            extra={"raw_output_path": str(raw_output_path)},
        )
        return []

    candidates = []
    for item in payload.get("candidates", []):
        field_name = str(item.get("field_name", "")).strip()
        if field_name not in missing_fields and field_name != "public_share_price":
            continue
        candidates.append(
            {
                "field_name": field_name,
                "value": item.get("value"),
                "confidence": max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0))),
                "source_document_id": "web_search",
                "source_locator": str(item.get("source_locator") or "web_search"),
                "method": "web_estimated",
                "notes": str(item.get("notes", "")).strip(),
                "source_urls": [str(url) for url in item.get("source_urls", []) if str(url).strip()],
            }
        )

    normalized_path.write_text(
        json.dumps(
            {
                "deal_id": deal_id,
                "cache_key": cache_key,
                "company_name": company_name,
                "model": model,
                "candidates": candidates,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_status(
        status_path,
        deal_id=deal_id,
        company_name=company_name,
        missing_fields=missing_fields,
        status="completed",
        reason=f"Web fallback returned {len(candidates)} candidate(s).",
        extra={"normalized_path": str(normalized_path)},
    )
    return candidates


def _run_web_search_response(client: OpenAI, model: str, prompt: str):
    tool_candidates = []
    configured = os.getenv("OPENAI_WEB_SEARCH_TOOL", "").strip()
    if configured:
        tool_candidates.append(configured)
    tool_candidates.extend(["web_search_preview", "web_search"])

    last_error = None
    seen = set()
    for tool_name in tool_candidates:
        if tool_name in seen:
            continue
        seen.add(tool_name)
        try:
            return client.responses.create(
                model=model,
                input=prompt,
                tools=[{"type": tool_name}],
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("No supported web search tool configuration found.")


def _looks_like_public_company_case(manifest_payload: Dict[str, Any]) -> bool:
    for document in manifest_payload.get("documents", []):
        filename = str(document.get("filename", "")).lower()
        if any(marker in filename for marker in PUBLIC_FILENAME_MARKERS):
            return True
    return False


def _build_web_fallback_prompt(company_name: str, missing_fields: List[str]) -> str:
    field_instructions = {
        "shares_outstanding": "latest basic shares outstanding or latest common shares outstanding",
        "ebitda": "latest annual EBITDA or adjusted EBITDA if clearly cited",
        "entry_multiple": "reasonable current EV/EBITDA style trading multiple or analyst/public comps multiple",
        "public_share_price": "latest public stock price",
    }
    requested = [
        {
            "field_name": field_name,
            "search_goal": field_instructions.get(field_name, field_name),
        }
        for field_name in (list(missing_fields) + ["public_share_price"])
    ]
    return (
        "You are filling missing public-company modeling inputs using web search.\n"
        "Only return fields if they are clearly supported by public sources.\n"
        "Do not guess for private companies.\n"
        "Return strict JSON with this shape:\n"
        '{\n'
        '  "candidates": [\n'
        "    {\n"
        '      "field_name": "shares_outstanding",\n'
        '      "value": 123,\n'
        '      "confidence": 0.0,\n'
        '      "source_locator": "Short source label and date",\n'
        '      "source_urls": ["https://..."],\n'
        '      "notes": "How this value was identified"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        f"Company: {company_name}\n"
        f"Requested fields: {json.dumps(requested)}\n"
        "Use numeric values only where possible. For shares outstanding, return full shares, not millions. "
        "For EBITDA, return the latest annual amount in full currency units if source units are stated. "
        "For entry_multiple, return a numeric EBITDA multiple. "
        "If a field cannot be supported clearly, omit it."
    )


def _extract_json_payload(raw_text: str) -> Dict[str, Any] | None:
    text = raw_text.strip()
    candidates = [text]

    fenced_matches = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced_matches)

    generic_fenced = re.findall(r"```\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates.extend(generic_fenced)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    seen = set()
    for candidate in candidates:
        cleaned = candidate.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _write_status(
    status_path,
    *,
    deal_id: str,
    company_name: str,
    missing_fields: List[str],
    status: str,
    reason: str,
    extra: Dict[str, Any] | None = None,
) -> None:
    payload: Dict[str, Any] = {
        "deal_id": deal_id,
        "company_name": company_name,
        "missing_fields": missing_fields,
        "status": status,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

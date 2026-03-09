from __future__ import annotations

import json
import re
from typing import Any, Dict

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, OVERRIDES_ROOT, RESOLVED_EXTRACTIONS_ROOT
from document_pipeline.services.web_fallback import get_web_fallback_candidates


def resolve_deal_fields(deal_id: str) -> Dict[str, Any]:
    candidates_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates.json"
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidates file not found: {candidates_path}")

    candidates_payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    manifest_payload = _load_manifest_payload(deal_id)
    page_context = _build_page_context_map(manifest_payload)
    overrides = _load_overrides(deal_id)

    resolved: Dict[str, Any] = {}
    normalized_candidates: list[dict[str, Any]] = []
    grouped: Dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates_payload.get("candidates", []):
        normalized = _normalize_candidate(candidate, page_context=page_context)
        normalized_candidates.append(normalized)
        grouped.setdefault(normalized["field_name"], []).append(normalized)

    web_candidates = _build_web_candidates(deal_id, grouped, manifest_payload)
    for candidate in web_candidates:
        normalized = _normalize_candidate(candidate, page_context=page_context)
        normalized_candidates.append(normalized)
        grouped.setdefault(normalized["field_name"], []).append(normalized)

    estimate_candidates = _build_estimate_candidates(grouped)
    for estimate in estimate_candidates:
        normalized_candidates.append(estimate)
        grouped.setdefault(estimate["field_name"], []).append(estimate)

    for field_name, field_candidates in grouped.items():
        non_estimated = [
            candidate for candidate in field_candidates if candidate.get("method") != "estimated"
        ]
        if not non_estimated:
            continue
        best = max(non_estimated, key=lambda candidate: float(candidate.get("selection_score", 0.0)))
        resolved[field_name] = {
            "value": best.get("normalized_value"),
            "confidence": float(best.get("confidence", 0.0)),
            "source_document_id": best.get("source_document_id"),
            "source_locator": best.get("source_locator", ""),
            "method": "resolved_from_candidates",
            "notes": best.get("notes", ""),
            "normalization_notes": best.get("normalization_notes", []),
            "selection_score": best.get("selection_score", 0.0),
            "source_urls": best.get("source_urls", []),
        }

    for field_name, override_value in overrides.items():
        resolved[field_name] = {
            "value": override_value,
            "confidence": 1.0,
            "source_document_id": None,
            "source_locator": "user_override",
            "method": "user_override",
            "notes": "Applied from local override file.",
            "source_urls": [],
        }

    RESOLVED_EXTRACTIONS_ROOT.mkdir(parents=True, exist_ok=True)
    normalized_candidates_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates_normalized.json"
    normalized_candidates_path.write_text(
        json.dumps(
            {
                "deal_id": deal_id,
                "candidate_count": len(normalized_candidates),
                "candidates": normalized_candidates,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    resolved_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_resolved.json"
    resolved_path.write_text(
        json.dumps({"deal_id": deal_id, "resolved_fields": resolved}, indent=2),
        encoding="utf-8",
    )
    return {
        "deal_id": deal_id,
        "resolved_field_count": len(resolved),
        "resolved_path": str(resolved_path),
        "normalized_candidates_path": str(normalized_candidates_path),
        "override_count": len(overrides),
    }


def _build_web_candidates(
    deal_id: str,
    grouped: Dict[str, list[dict[str, Any]]],
    manifest_payload: Dict[str, Any],
) -> list[dict[str, Any]]:
    company_name = _best_candidate_value(grouped.get("company_name", []))
    if not company_name or not isinstance(company_name, str):
        return []

    missing_fields = [
        field_name
        for field_name in ("shares_outstanding", "ebitda", "entry_multiple")
        if not _has_positive_candidate(grouped, field_name)
    ]
    return get_web_fallback_candidates(
        deal_id=deal_id,
        company_name=company_name,
        manifest_payload=manifest_payload,
        missing_fields=missing_fields,
    )


def _load_overrides(deal_id: str) -> Dict[str, Any]:
    override_path = OVERRIDES_ROOT / f"{deal_id}_overrides.json"
    if not override_path.exists():
        return {}
    payload = json.loads(override_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Override payload must be a JSON object: {override_path}")
    return payload


def _load_manifest_payload(deal_id: str) -> Dict[str, Any]:
    manifest_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_manifest.json"
    if not manifest_path.exists():
        return {"chunks": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _build_page_context_map(manifest_payload: Dict[str, Any]) -> Dict[tuple[str, int], str]:
    context: Dict[tuple[str, int], list[str]] = {}
    for chunk in manifest_payload.get("chunks", []):
        page = chunk.get("page_start")
        document_id = chunk.get("document_id")
        if document_id and page:
            context.setdefault((document_id, int(page)), []).append(chunk.get("text", ""))
    return {
        key: " ".join(parts)
        for key, parts in context.items()
    }


def _normalize_candidate(
    candidate: Dict[str, Any],
    page_context: Dict[tuple[str, int], str],
) -> Dict[str, Any]:
    field_name = candidate["field_name"]
    notes = str(candidate.get("notes", ""))
    raw_value = candidate.get("value")
    normalized_value = raw_value
    normalization_notes: list[str] = []
    context_text = _lookup_context_text(
        document_id=str(candidate.get("source_document_id", "")),
        source_locator=str(candidate.get("source_locator", "")),
        page_context=page_context,
    )

    if isinstance(raw_value, dict):
        year_keys = [key for key in raw_value if str(key).isdigit()]
        if year_keys:
            latest_key = max(year_keys, key=lambda key: int(str(key)))
            normalized_value = raw_value[latest_key]
            normalization_notes.append(f"Selected latest year value from {latest_key}.")

    unit_multiplier = _infer_unit_multiplier(field_name, notes, context_text)
    if field_name in {"revenue", "ebitda", "cash", "debt", "shares_outstanding"}:
        normalized_value = _scale_numeric_value(normalized_value, unit_multiplier)
        if unit_multiplier != 1:
            normalization_notes.append(f"Scaled numeric value by {unit_multiplier:g} based on units in notes.")

    selection_score = _selection_score(
        field_name=field_name,
        confidence=float(candidate.get("confidence", 0.0)),
        normalized_value=normalized_value,
        notes=notes,
    )

    normalized = dict(candidate)
    normalized["normalized_value"] = normalized_value
    normalized["unit_multiplier"] = unit_multiplier
    normalized["normalization_notes"] = normalization_notes
    normalized["selection_score"] = round(selection_score, 4)
    normalized["source_urls"] = list(candidate.get("source_urls", []))
    return normalized


def _infer_unit_multiplier(field_name: str, notes: str, context_text: str) -> float:
    text = f"{notes} {context_text}".lower()
    if field_name == "shares_outstanding":
        if "in thousands" in text or "(000" in text or "000's" in text:
            return 1_000.0
        if "in millions" in text:
            return 1_000_000.0
        if "in billions" in text:
            return 1_000_000_000.0
        return 1.0
    if "in billions" in text:
        return 1_000_000_000.0
    if "in millions" in text:
        return 1_000_000.0
    if "in thousands" in text or "(000" in text or "000's" in text:
        return 1_000.0
    return 1.0


def _scale_numeric_value(value: Any, multiplier: float) -> Any:
    if multiplier == 1:
        return value
    if isinstance(value, (int, float)):
        return int(value * multiplier) if float(value).is_integer() else value * multiplier
    return value


def _selection_score(
    field_name: str,
    confidence: float,
    normalized_value: Any,
    notes: str,
) -> float:
    score = confidence
    text = notes.lower()

    if field_name == "cash":
        if "cash and cash equivalents" in text:
            score += 0.4
        if "short-term investments" in text:
            score -= 0.1
        if "cash provided by operating activities" in text:
            score -= 0.5

    if field_name == "shares_outstanding":
        if not isinstance(normalized_value, (int, float)):
            score -= 1.0
        if "shares outstanding" in text and "common stock" in text:
            score += 0.5
        if "diluted shares used in computing eps" in text or "weighted average" in text:
            score -= 0.35
        if "repurchase" in text or "authorized" in text or "program" in text:
            score -= 0.8

    if field_name == "debt":
        if "long-term debt" in text:
            score += 0.25
        if "current maturities" in text:
            score += 0.1

    if field_name == "revenue" and "revenue for year ended" in text:
        score += 0.2

    if field_name == "ebitda" and "adjusted ebitda" in text:
        score += 0.15

    if field_name == "company_name":
        score += 0.2

    return score


def _lookup_context_text(
    document_id: str,
    source_locator: str,
    page_context: Dict[tuple[str, int], str],
) -> str:
    match = re.search(r"page\s+(\d+)", source_locator.lower())
    if not match:
        return ""
    page = int(match.group(1))
    return page_context.get((document_id, page), "")


def _build_estimate_candidates(grouped: Dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    resolved_inputs = {
        field_name: _best_candidate_value(field_candidates)
        for field_name, field_candidates in grouped.items()
    }
    estimates: list[dict[str, Any]] = []

    revenue = _coerce_number(resolved_inputs.get("revenue"))
    ebitda = _coerce_number(resolved_inputs.get("ebitda"))
    shares_outstanding = _coerce_number(resolved_inputs.get("shares_outstanding"))
    ebitda_margin = _coerce_number(resolved_inputs.get("ebitda_margin_assumption"))
    entry_multiple = _coerce_number(resolved_inputs.get("entry_multiple"))
    exit_multiple = _coerce_number(resolved_inputs.get("exit_multiple"))

    if revenue and ebitda and not _has_positive_candidate(grouped, "ebitda_margin_assumption"):
        margin = max(min(ebitda / revenue, 0.60), 0.05)
        estimates.append(
            _estimate_candidate(
                "ebitda_margin_assumption",
                round(margin, 4),
                0.72,
                "Derived from extracted EBITDA divided by extracted revenue.",
            )
        )

    margin_basis = _positive_or_none(ebitda_margin)
    margin_source_note = "existing EBITDA margin assumption"
    if margin_basis is None and revenue and ebitda and revenue > 0:
        margin_basis = max(min(ebitda / revenue, 0.60), 0.05)
        margin_source_note = "extracted EBITDA divided by extracted revenue"
    if margin_basis is None:
        margin_basis = 0.20
        margin_source_note = "baseline 20.0% EBITDA margin"

    if revenue and revenue > 0 and not _has_positive_candidate(grouped, "ebitda"):
        estimated_ebitda = revenue * margin_basis
        estimates.append(
            _estimate_candidate(
                "ebitda",
                int(round(estimated_ebitda)),
                0.62 if margin_source_note != "baseline 20.0% EBITDA margin" else 0.48,
                f"Estimated as revenue multiplied by {margin_source_note}.",
            )
        )

    if ebitda and ebitda > 0 and margin_basis and margin_basis > 0 and not _has_positive_candidate(grouped, "revenue"):
        estimated_revenue = ebitda / margin_basis
        estimates.append(
            _estimate_candidate(
                "revenue",
                int(round(estimated_revenue)),
                0.54 if margin_source_note != "baseline 20.0% EBITDA margin" else 0.4,
                f"Estimated as EBITDA divided by {margin_source_note}.",
            )
        )

    if not _has_positive_candidate(grouped, "revenue_growth_assumption"):
        estimates.append(
            _estimate_candidate(
                "revenue_growth_assumption",
                0.05,
                0.45,
                "MVP baseline estimate of 5.0% annual revenue growth.",
            )
        )

    if not _has_positive_candidate(grouped, "capex_pct_revenue"):
        estimates.append(
            _estimate_candidate(
                "capex_pct_revenue",
                0.03,
                0.5,
                "Baseline estimate of 3.0% capex as a percentage of revenue.",
            )
        )

    if not _has_positive_candidate(grouped, "nwc_pct_revenue"):
        estimates.append(
            _estimate_candidate(
                "nwc_pct_revenue",
                0.01,
                0.42,
                "Baseline estimate of 1.0% net working capital investment as a percentage of revenue.",
            )
        )

    if not _has_positive_candidate(grouped, "tax_rate"):
        estimates.append(
            _estimate_candidate(
                "tax_rate",
                0.25,
                0.5,
                "Baseline corporate tax estimate of 25.0%.",
            )
        )

    if not _has_positive_candidate(grouped, "entry_multiple"):
        fallback_entry = exit_multiple if exit_multiple and exit_multiple > 0 else 10.0
        estimates.append(
            _estimate_candidate(
                "entry_multiple",
                round(fallback_entry, 2),
                0.38,
                "Estimated from exit multiple when available, otherwise 10.0x baseline.",
            )
        )

    if not _has_positive_candidate(grouped, "exit_multiple"):
        fallback_exit = entry_multiple if entry_multiple and entry_multiple > 0 else 10.0
        estimates.append(
            _estimate_candidate(
                "exit_multiple",
                round(fallback_exit, 2),
                0.38,
                "Estimated from entry multiple when available, otherwise 10.0x baseline.",
            )
        )

    if not _has_positive_candidate(grouped, "shares_outstanding"):
        fallback_shares = max(shares_outstanding or 0, 1.0)
        estimates.append(
            _estimate_candidate(
                "shares_outstanding",
                int(round(fallback_shares)),
                0.12,
                "Fallback placeholder of 1 share used only to prevent divide-by-zero in valuation outputs. Replace this with an actual share count before relying on per-share conclusions.",
            )
        )

    return estimates


def _estimate_candidate(field_name: str, value: Any, confidence: float, notes: str) -> dict[str, Any]:
    return {
        "field_name": field_name,
        "value": value,
        "confidence": confidence,
        "source_document_id": None,
        "source_locator": "reasonable_estimate",
        "method": "estimated",
        "notes": notes,
        "normalized_value": value,
        "unit_multiplier": 1.0,
        "normalization_notes": ["Reasonable estimate generated by resolver."],
        "selection_score": round(confidence - 0.15, 4),
        "source_urls": [],
    }


def _best_candidate_value(field_candidates: list[dict[str, Any]]) -> Any:
    non_estimated = [
        candidate for candidate in field_candidates if candidate.get("method") != "estimated"
    ]
    pool = non_estimated or field_candidates
    best = max(pool, key=lambda candidate: float(candidate.get("selection_score", 0.0)))
    return best.get("normalized_value")


def _has_positive_candidate(grouped: Dict[str, list[dict[str, Any]]], field_name: str) -> bool:
    for candidate in grouped.get(field_name, []):
        value = _coerce_number(candidate.get("normalized_value"))
        if value is not None and value > 0:
            return True
    return False


def _coerce_number(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric


def _positive_or_none(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return value

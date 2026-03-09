from __future__ import annotations

import json
from typing import Any, Dict

from document_pipeline.config import NORMALIZED_EXTRACTIONS_ROOT, RESOLVED_EXTRACTIONS_ROOT


BASE_DEFAULTS: Dict[str, Any] = {
    "company_name": "",
    "revenue": 0,
    "ebitda": 0,
    "cash": 0,
    "debt": 0,
    "shares_outstanding": 0,
    "revenue_growth_assumption": 0.05,
    "ebitda_margin_assumption": 0.20,
    "capex_pct_revenue": 0.03,
    "nwc_pct_revenue": 0.01,
    "tax_rate": 0.25,
    "risk_free_rate": 0.042,
    "beta": 1.2,
    "market_risk_premium": 0.06,
    "cost_of_debt": 0.065,
    "terminal_growth": 0.025,
    "entry_multiple": 10.0,
    "exit_multiple": 10.0,
}

NONZERO_WARNING_FIELDS = {
    "revenue_growth_assumption",
    "ebitda_margin_assumption",
    "capex_pct_revenue",
    "nwc_pct_revenue",
    "tax_rate",
    "entry_multiple",
    "exit_multiple",
}


def prepare_model_inputs_for_deal(deal_id: str) -> Dict[str, Any]:
    resolved_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_resolved.json"
    if not resolved_path.exists():
        raise FileNotFoundError(f"Resolved fields not found: {resolved_path}")

    resolved_payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    resolved_fields = resolved_payload.get("resolved_fields", {})
    normalized_candidates_path = NORMALIZED_EXTRACTIONS_ROOT / f"{deal_id}_field_candidates_normalized.json"
    normalized_candidates_payload = (
        json.loads(normalized_candidates_path.read_text(encoding="utf-8"))
        if normalized_candidates_path.exists()
        else {"candidates": []}
    )
    grouped_candidates = _group_candidates(normalized_candidates_payload.get("candidates", []))

    model_input = dict(BASE_DEFAULTS)
    review_payload: Dict[str, Any] = {
        "deal_id": deal_id,
        "fields": {},
    }

    for field_name, base_value in BASE_DEFAULTS.items():
        field_info = resolved_fields.get(field_name)
        if field_info:
            model_input[field_name] = field_info.get("value", base_value)
            warnings = _build_field_warnings(field_name, field_info, grouped_candidates.get(field_name, []))
            review_payload["fields"][field_name] = {
                "selected": field_info,
                "options": grouped_candidates.get(field_name, []),
                "warnings": warnings,
                "recommended_estimate": _pick_estimate_candidate(grouped_candidates.get(field_name, [])),
            }
        else:
            warnings = _build_default_warnings(field_name, base_value, grouped_candidates.get(field_name, []))
            review_payload["fields"][field_name] = {
                "selected": {
                    "value": base_value,
                    "confidence": 0.0,
                    "source_document_id": None,
                    "source_locator": "default",
                    "method": "default",
                    "notes": "No extracted or overridden value available.",
                },
                "options": grouped_candidates.get(field_name, []),
                "warnings": warnings,
                "recommended_estimate": _pick_estimate_candidate(grouped_candidates.get(field_name, [])),
            }

    model_input_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_model_input.json"
    review_path = RESOLVED_EXTRACTIONS_ROOT / f"{deal_id}_review_payload.json"
    model_input_path.write_text(json.dumps(model_input, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")

    return {
        "deal_id": deal_id,
        "model_input_path": str(model_input_path),
        "review_path": str(review_path),
        "field_count": len(review_payload["fields"]),
    }


def _group_candidates(candidates: list[dict[str, Any]]) -> Dict[str, list[dict[str, Any]]]:
    grouped: Dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["field_name"], []).append(candidate)
    for field_name in grouped:
        grouped[field_name].sort(key=lambda item: float(item.get("selection_score", 0.0)), reverse=True)
    return grouped


def _pick_estimate_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    estimates = [candidate for candidate in candidates if candidate.get("method") == "estimated"]
    if not estimates:
        return None
    return max(estimates, key=lambda item: float(item.get("selection_score", 0.0)))


def _build_field_warnings(
    field_name: str,
    selected: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    value = selected.get("value")
    if field_name in NONZERO_WARNING_FIELDS and _is_zeroish(value):
      warnings.append("This field is zero, which is usually unrealistic in an LBO model.")

    estimate = _pick_estimate_candidate(candidates)
    if estimate:
      warnings.append(str(estimate.get("notes", "Reasonable estimate available.")))

    return warnings


def _build_default_warnings(
    field_name: str,
    base_value: Any,
    candidates: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if field_name in NONZERO_WARNING_FIELDS and _is_zeroish(base_value):
      warnings.append("No extracted value found and the current default is zero.")

    estimate = _pick_estimate_candidate(candidates)
    if estimate:
      warnings.append(str(estimate.get("notes", "Reasonable estimate available.")))

    return warnings


def _is_zeroish(value: Any) -> bool:
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False

from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI

from prompts import build_extraction_prompt
from schemas import EXTRACTION_SCHEMA


class ExtractionError(RuntimeError):
    pass



def _coerce_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing keys and lightly sanitize payload values."""
    result = dict(EXTRACTION_SCHEMA)
    result.update(payload)

    numeric_keys = [
        "revenue",
        "ebitda",
        "cash",
        "debt",
        "shares_outstanding",
        "revenue_growth_assumption",
        "ebitda_margin_assumption",
        "capex_pct_revenue",
        "nwc_pct_revenue",
        "tax_rate",
    ]
    for key in numeric_keys:
        try:
            result[key] = float(result[key])
        except Exception:
            result[key] = float(EXTRACTION_SCHEMA[key])

    result["company_name"] = str(result.get("company_name", "")).strip() or "Unknown Company"
    result["business_summary"] = str(result.get("business_summary", "")).strip()
    return result



def extract_financial_fields(document_text: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ExtractionError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    prompt = build_extraction_prompt(document_text)

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
    )

    raw_text = response.output_text.strip()
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Model did not return valid JSON. Raw output: {raw_text[:500]}") from exc

    return _coerce_payload(payload)

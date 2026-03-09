from __future__ import annotations

from typing import Any, Dict

EXTRACTION_SCHEMA_VERSION = "2026-03-09-v1"

EXTRACTED_FIELD_SCHEMA: Dict[str, Any] = {
    "company_name": "",
    "revenue": None,
    "ebitda": None,
    "cash": None,
    "debt": None,
    "shares_outstanding": None,
    "public_share_price": None,
    "tax_rate": None,
    "capex_pct_revenue": None,
    "nwc_pct_revenue": None,
    "revenue_growth_assumption": None,
    "ebitda_margin_assumption": None,
    "entry_multiple": None,
    "exit_multiple": None,
    "public_comps": [],
    "precedent_transactions": [],
    "debt_terms": {},
}

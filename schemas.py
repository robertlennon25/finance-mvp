from __future__ import annotations

from typing import Any, Dict

EXTRACTION_SCHEMA: Dict[str, Any] = {
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
    "business_summary": "",
}

from __future__ import annotations

from typing import Any, Dict, List


def _float(data: Dict[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _projection_series(
    data: Dict[str, Any],
    prefix: str,
    fallback: float,
    years: int = 5,
) -> List[float]:
    values: List[float] = []
    for idx in range(1, years + 1):
        values.append(_float(data, f"{prefix}_{idx}", fallback))
    return values


def build_model_inputs(extracted: Dict[str, Any], assumptions: Any) -> Dict[str, Any]:
    entry_year = int(extracted.get("entry_year", 2024))
    revenue = _float(extracted, "revenue", 0.0)
    ebitda = _float(extracted, "ebitda", 0.0)
    debt = _float(extracted, "debt", 0.0)
    base_margin = ebitda / revenue if revenue else _float(
        extracted,
        "ebitda_margin_assumption",
        0.20,
    )
    base_growth = _float(extracted, "revenue_growth_assumption", 0.05)
    inferred_debt_free = 1.0 if debt == 0 else 0.0
    revolver_limit_default = max(ebitda * 0.75, revenue * 0.10, 250_000_000.0)

    historicals = []
    for offset in range(2, -1, -1):
        year = entry_year - offset
        growth_factor = (1 + base_growth) ** max(offset, 0)
        hist_revenue = revenue / growth_factor if growth_factor else revenue
        margin = max(base_margin - (0.01 * offset), 0.05)
        hist_ebitda = hist_revenue * margin
        hist_capex = hist_revenue * _float(extracted, "capex_pct_revenue", 0.03)
        hist_da = hist_revenue * _float(extracted, "da_pct_revenue", 0.02)
        hist_nwc = hist_revenue * _float(extracted, "nwc_pct_revenue", 0.01)
        historicals.append(
            {
                "year": year,
                "revenue": hist_revenue,
                "ebitda": hist_ebitda,
                "margin": margin,
                "capex": hist_capex,
                "da": hist_da,
                "nwc": hist_nwc,
            }
        )

    projection_years = [entry_year + idx for idx in range(1, 6)]
    revenue_growth = _projection_series(extracted, "revenue_growth", assumptions.revenue_growth)
    ebitda_margin = _projection_series(extracted, "ebitda_margin", assumptions.ebitda_margin)
    capex_pct = _projection_series(extracted, "capex_pct", assumptions.capex_pct)
    da_pct = _projection_series(extracted, "da_pct", 0.02)
    nwc_pct = _projection_series(extracted, "nwc_pct", assumptions.nwc_pct)

    return {
        "company_name": str(extracted.get("company_name", "Target Company")),
        "projection_years": projection_years,
        "historicals": historicals,
        "inputs": {
            "shares_outstanding": _float(extracted, "shares_outstanding", 1.0),
            "purchase_revenue": revenue,
            "purchase_ebitda": ebitda,
            "entry_multiple": _float(extracted, "entry_multiple", assumptions.entry_multiple),
            "debt_free_acquisition": _float(extracted, "debt_free_acquisition", inferred_debt_free),
            "existing_debt": debt,
            "existing_cash": _float(extracted, "cash", 0.0),
            "transaction_fee_pct": _float(extracted, "transaction_fee_pct", 0.02),
            "financing_fee_pct": _float(extracted, "financing_fee_pct", 0.01),
            "oid_pct": _float(extracted, "oid_pct", 0.02),
            "management_rollover_pct": _float(extracted, "management_rollover_pct", 0.0),
            "senior_debt_multiple": _float(extracted, "senior_debt_multiple", 4.0),
            "sub_debt_multiple": _float(extracted, "sub_debt_multiple", 1.0),
            "senior_interest_rate": _float(
                extracted,
                "senior_interest_rate",
                assumptions.senior_interest_rate,
            ),
            "senior_term_pct": _float(extracted, "senior_term_pct", 0.70),
            "senior_tla_pct": _float(extracted, "senior_tla_pct", 0.40),
            "senior_tlb_pct": _float(extracted, "senior_tlb_pct", 0.60),
            "sub_interest_rate": _float(
                extracted,
                "sub_interest_rate",
                assumptions.sub_interest_rate,
            ),
            "sub_pik_rate": _float(extracted, "sub_pik_rate", 0.0),
            "revolver_interest_rate": _float(extracted, "revolver_interest_rate", 0.07),
            "revolver_limit": _float(extracted, "revolver_limit", revolver_limit_default),
            "senior_amortization_pct": _float(extracted, "senior_amortization_pct", 0.05),
            "cash_sweep_pct": _float(extracted, "cash_sweep_pct", 1.0),
            "tax_rate": _float(extracted, "tax_rate", assumptions.tax_rate),
            "min_cash_balance": _float(extracted, "min_cash_balance", 50_000_000.0),
            "risk_free_rate": _float(extracted, "risk_free_rate", assumptions.risk_free_rate),
            "beta": _float(extracted, "beta", assumptions.beta),
            "market_risk_premium": _float(
                extracted,
                "market_risk_premium",
                assumptions.market_risk_premium,
            ),
            "cost_of_debt": _float(extracted, "cost_of_debt", assumptions.cost_of_debt),
            "terminal_growth": _float(extracted, "terminal_growth", assumptions.terminal_growth),
            "exit_multiple": _float(extracted, "exit_multiple", assumptions.exit_multiple),
            "revenue_growth": revenue_growth,
            "ebitda_margin": ebitda_margin,
            "capex_pct": capex_pct,
            "da_pct": da_pct,
            "nwc_pct": nwc_pct,
        },
    }

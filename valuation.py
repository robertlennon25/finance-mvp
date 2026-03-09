from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from copy import deepcopy




@dataclass
class Assumptions:
    revenue_growth: float
    ebitda_margin: float
    capex_pct: float
    nwc_pct: float
    tax_rate: float
    risk_free_rate: float = 0.04
    beta: float = 1.20
    market_risk_premium: float = 0.06
    cost_of_debt: float = 0.065
    terminal_growth: float = 0.025
    entry_multiple: float = 10.0
    exit_multiple: float = 12.0
    senior_debt_pct: float = 0.70
    sub_debt_pct: float = 0.30
    senior_interest_rate: float = 0.06
    sub_interest_rate: float = 0.08



def build_assumptions(data: Dict[str, Any]) -> Assumptions:
    return Assumptions(
        revenue_growth=float(data["revenue_growth_assumption"]),
        ebitda_margin=float(data["ebitda_margin_assumption"]),
        capex_pct=float(data["capex_pct_revenue"]),
        nwc_pct=float(data["nwc_pct_revenue"]),
        tax_rate=float(data["tax_rate"]),
        risk_free_rate=float(data.get("risk_free_rate", 0.04)),
        beta=float(data.get("beta", 1.20)),
        market_risk_premium=float(data.get("market_risk_premium", 0.06)),
        cost_of_debt=float(data.get("cost_of_debt", 0.065)),
        terminal_growth=float(data.get("terminal_growth", 0.025)),
        entry_multiple=float(data.get("entry_multiple", 10.0)),
        exit_multiple=float(data.get("exit_multiple", 12.0)),
        senior_debt_pct=float(data.get("senior_debt_pct", 0.70)),
        sub_debt_pct=float(data.get("sub_debt_pct", 0.30)),
        senior_interest_rate=float(data.get("senior_interest_rate", 0.06)),
        sub_interest_rate=float(data.get("sub_interest_rate", 0.08)),
    )



def build_projections(data: Dict[str, Any], assumptions: Assumptions, years: int = 5) -> List[Dict[str, float]]:
    revenue = float(data["revenue"])
    projections: List[Dict[str, float]] = []

    for idx in range(1, years + 1):
        revenue *= 1 + assumptions.revenue_growth
        ebitda = revenue * assumptions.ebitda_margin
        depreciation = revenue * 0.02
        ebit = ebitda - depreciation
        taxes = ebit * assumptions.tax_rate
        nopat = ebit - taxes
        capex = revenue * assumptions.capex_pct
        nwc_change = revenue * assumptions.nwc_pct
        ufcf = nopat + depreciation - capex - nwc_change

        projections.append(
            {
                "year": float(idx),
                "revenue": revenue,
                "ebitda": ebitda,
                "depreciation": depreciation,
                "ebit": ebit,
                "taxes": taxes,
                "nopat": nopat,
                "capex": capex,
                "nwc_change": nwc_change,
                "ufcf": ufcf,
            }
        )
    return projections



def compute_wacc(data: Dict[str, Any], assumptions: Assumptions) -> Dict[str, float]:
    debt = float(data["debt"])
    cash = float(data["cash"])
    shares = max(float(data["shares_outstanding"]), 1.0)
    # rough placeholder equity value from 8x EBITDA less net debt, floored
    equity_value = max(float(data["ebitda"]) * 8 - (debt - cash), shares)

    total_capital = max(equity_value + debt, 1.0)
    weight_equity = equity_value / total_capital
    weight_debt = debt / total_capital

    cost_of_equity = assumptions.risk_free_rate + assumptions.beta * assumptions.market_risk_premium
    after_tax_cost_of_debt = assumptions.cost_of_debt * (1 - assumptions.tax_rate)
    wacc = weight_equity * cost_of_equity + weight_debt * after_tax_cost_of_debt

    return {
        "equity_value": equity_value,
        "debt_value": debt,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
        "cost_of_equity": cost_of_equity,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "wacc": wacc,
    }



def compute_dcf(data: Dict[str, Any], assumptions: Assumptions, projections: List[Dict[str, float]], wacc_info: Dict[str, float]) -> Dict[str, Any]:
    wacc = wacc_info["wacc"]
    pv_rows: List[Dict[str, float]] = []
    total_pv = 0.0

    for row in projections:
        year = int(row["year"])
        discount_factor = 1 / ((1 + wacc) ** year)
        pv_ufcf = row["ufcf"] * discount_factor
        total_pv += pv_ufcf
        pv_rows.append({**row, "discount_factor": discount_factor, "pv_ufcf": pv_ufcf})

    last_fcf = projections[-1]["ufcf"]
    last_ebitda = projections[-1]["ebitda"]
    tv_pgr = (last_fcf * (1 + assumptions.terminal_growth)) / max(wacc - assumptions.terminal_growth, 1e-6)
    tv_multiple = last_ebitda * assumptions.exit_multiple

    pv_tv_pgr = tv_pgr / ((1 + wacc) ** len(projections))
    pv_tv_multiple = tv_multiple / ((1 + wacc) ** len(projections))

    ev_pgr = total_pv + pv_tv_pgr
    ev_multiple = total_pv + pv_tv_multiple

    cash = float(data["cash"])
    debt = float(data["debt"])
    shares = max(float(data["shares_outstanding"]), 1.0)

    equity_pgr = ev_pgr + cash - debt
    equity_multiple = ev_multiple + cash - debt

    return {
        "rows": pv_rows,
        "projection_period_pv": total_pv,
        "terminal_value_pgr": tv_pgr,
        "terminal_value_multiple": tv_multiple,
        "pv_terminal_value_pgr": pv_tv_pgr,
        "pv_terminal_value_multiple": pv_tv_multiple,
        "enterprise_value_pgr": ev_pgr,
        "enterprise_value_multiple": ev_multiple,
        "equity_value_pgr": equity_pgr,
        "equity_value_multiple": equity_multiple,
        "share_price_pgr": equity_pgr / shares,
        "share_price_multiple": equity_multiple / shares,
    }





def compute_sensitivity_tables(
    extracted: Dict[str, Any],
    assumptions: Any,
    projections: List[Dict[str, float]],
    wacc_info: Dict[str, float],
) -> Dict[str, Any]:
    """
    Compute Python-side sensitivity tables for:
      1) WACC vs Terminal Growth
      2) WACC vs Exit Multiple

    This is stored in JSON for verification, while Excel gets formula-based tables.
    """

    base_wacc = float(wacc_info["wacc"])
    base_terminal_growth = float(assumptions.terminal_growth)
    base_exit_multiple = float(assumptions.exit_multiple)

    wacc_values = [
        round(base_wacc - 0.01, 4),
        round(base_wacc - 0.005, 4),
        round(base_wacc, 4),
        round(base_wacc + 0.005, 4),
        round(base_wacc + 0.01, 4),
    ]

    terminal_growth_values = [
        round(base_terminal_growth - 0.01, 4),
        round(base_terminal_growth - 0.005, 4),
        round(base_terminal_growth, 4),
        round(base_terminal_growth + 0.005, 4),
        round(base_terminal_growth + 0.01, 4),
    ]

    exit_multiple_values = [
        round(base_exit_multiple - 1.0, 2),
        round(base_exit_multiple - 0.5, 2),
        round(base_exit_multiple, 2),
        round(base_exit_multiple + 0.5, 2),
        round(base_exit_multiple + 1.0, 2),
    ]

    wacc_vs_growth = []
    for wacc_val in wacc_values:
        row = {"wacc": wacc_val}
        for growth_val in terminal_growth_values:
            temp_assumptions = deepcopy(assumptions)
            temp_assumptions.terminal_growth = growth_val

            temp_wacc_info = dict(wacc_info)
            temp_wacc_info["wacc"] = wacc_val

            temp_dcf = compute_dcf(extracted, temp_assumptions, projections, temp_wacc_info)
            row[str(growth_val)] = temp_dcf["share_price_pgr"]
        wacc_vs_growth.append(row)

    wacc_vs_multiple = []
    for wacc_val in wacc_values:
        row = {"wacc": wacc_val}
        for multiple_val in exit_multiple_values:
            temp_assumptions = deepcopy(assumptions)
            temp_assumptions.exit_multiple = multiple_val

            temp_wacc_info = dict(wacc_info)
            temp_wacc_info["wacc"] = wacc_val

            temp_dcf = compute_dcf(extracted, temp_assumptions, projections, temp_wacc_info)
            row[str(multiple_val)] = temp_dcf["share_price_multiple"]
        wacc_vs_multiple.append(row)

    return {
        "base_wacc": base_wacc,
        "base_terminal_growth": base_terminal_growth,
        "base_exit_multiple": base_exit_multiple,
        "wacc_values": wacc_values,
        "terminal_growth_values": terminal_growth_values,
        "exit_multiple_values": exit_multiple_values,
        "wacc_vs_growth": wacc_vs_growth,
        "wacc_vs_multiple": wacc_vs_multiple,
    }

def compute_lbo(data: Dict[str, Any], projections: List[Dict[str, float]], assumptions: Assumptions) -> Dict[str, Any]:
    entry_ebitda = float(data["ebitda"])
    entry_multiple = float(assumptions.entry_multiple)
    exit_multiple = float(assumptions.exit_multiple)
    entry_debt_total = float(data["debt"])
    entry_cash = float(data["cash"])

    entry_ev = entry_ebitda * entry_multiple
    equity_invested = entry_ev - entry_debt_total + entry_cash

    senior_pct = float(assumptions.senior_debt_pct)
    sub_pct = float(assumptions.sub_debt_pct)
    senior_rate = float(assumptions.senior_interest_rate)
    sub_rate = float(assumptions.sub_interest_rate)

    senior_balance = entry_debt_total * senior_pct
    sub_balance = entry_debt_total * sub_pct

    debt_rows: List[Dict[str, float]] = []

    for row in projections:
        year = int(row["year"])
        beginning_senior = senior_balance
        beginning_sub = sub_balance
        beginning_total = beginning_senior + beginning_sub

        senior_interest = beginning_senior * senior_rate
        sub_interest = beginning_sub * sub_rate
        total_interest = senior_interest + sub_interest

        ufcf = float(row["ufcf"])
        cash_after_interest = max(ufcf - total_interest, 0.0)

        senior_paydown = min(cash_after_interest, beginning_senior)
        remaining_cash = max(cash_after_interest - senior_paydown, 0.0)

        sub_paydown = min(remaining_cash, beginning_sub)

        ending_senior = max(beginning_senior - senior_paydown, 0.0)
        ending_sub = max(beginning_sub - sub_paydown, 0.0)
        ending_total = ending_senior + ending_sub

        debt_rows.append(
            {
                "year": year,
                "beginning_senior_debt": beginning_senior,
                "beginning_sub_debt": beginning_sub,
                "beginning_total_debt": beginning_total,
                "senior_interest_expense": senior_interest,
                "sub_interest_expense": sub_interest,
                "total_interest_expense": total_interest,
                "ufcf_before_interest": ufcf,
                "cash_after_interest": cash_after_interest,
                "senior_paydown": senior_paydown,
                "sub_paydown": sub_paydown,
                "ending_senior_debt": ending_senior,
                "ending_sub_debt": ending_sub,
                "ending_total_debt": ending_total,
            }
        )

        senior_balance = ending_senior
        sub_balance = ending_sub

    exit_ebitda = float(projections[-1]["ebitda"])
    exit_multiple = float(assumptions.exit_multiple)
    exit_ev = exit_ebitda * exit_multiple
    exit_debt = senior_balance + sub_balance
    exit_cash = entry_cash
    equity_value_exit = exit_ev - exit_debt + exit_cash

    moic = equity_value_exit / equity_invested if equity_invested > 0 else 0.0
    irr = moic ** (1 / len(projections)) - 1 if moic > 0 else 0.0

    return {
        "entry_ebitda": entry_ebitda,
        "entry_multiple": entry_multiple,
        "entry_ev": entry_ev,
        "entry_debt_total": entry_debt_total,
        "entry_cash": entry_cash,
        "entry_senior_debt": entry_debt_total * senior_pct,
        "entry_sub_debt": entry_debt_total * sub_pct,
        "senior_interest_rate": senior_rate,
        "sub_interest_rate": sub_rate,
        "equity_invested": equity_invested,
        "exit_ebitda": exit_ebitda,
        "exit_multiple": exit_multiple,
        "exit_ev": exit_ev,
        "exit_debt": exit_debt,
        "exit_cash": exit_cash,
        "equity_value_exit": equity_value_exit,
        "moic": moic,
        "irr": irr,
        "debt_schedule": debt_rows,
    }


def build_valuation_summary(dcf: Dict[str, Any], lbo: Dict[str, float]) -> List[Dict[str, float | str]]:
    return [
        {"method": "DCF (PGR)", "low": dcf["share_price_pgr"] * 0.95, "high": dcf["share_price_pgr"] * 1.05},
        {"method": "DCF (Exit Multiple)", "low": dcf["share_price_multiple"] * 0.95, "high": dcf["share_price_multiple"] * 1.05},
        {"method": "LBO", "low": (lbo["entry_ev"] * 0.95) /  max(1.0,1.0), "high": (lbo["entry_ev"] * 1.05) / max(1.0,1.0)},
    ]

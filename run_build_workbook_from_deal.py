from __future__ import annotations

import argparse
import json
from pathlib import Path

from excel_builder import write_workbook
from valuation import (
    build_assumptions,
    build_projections,
    build_valuation_summary,
    compute_dcf,
    compute_lbo,
    compute_sensitivity_tables,
    compute_wacc,
)


def _build_model_warnings(extracted: dict, dcf_info: dict) -> list[str]:
    warnings: list[str] = []

    revenue = float(extracted.get("revenue", 0) or 0)
    ebitda = float(extracted.get("ebitda", 0) or 0)
    shares = float(extracted.get("shares_outstanding", 0) or 0)
    entry_multiple = float(extracted.get("entry_multiple", 0) or 0)
    exit_multiple = float(extracted.get("exit_multiple", 0) or 0)
    share_price = float(dcf_info.get("share_price_multiple", 0) or 0)

    if revenue <= 0:
        warnings.append("Revenue is zero or missing. Valuation outputs may be unreliable until revenue is updated.")
    if ebitda <= 0:
        warnings.append("EBITDA is zero or missing. Enterprise value and debt capacity outputs may be unreliable.")
    if shares <= 1:
        warnings.append("Shares outstanding is 1 or missing. Per-share outputs may be placeholder values.")
    if entry_multiple <= 0:
        warnings.append("Entry multiple is zero or missing. Transaction valuation may rely on fallback assumptions.")
    if exit_multiple <= 0:
        warnings.append("Exit multiple is zero or missing. Terminal value may rely on fallback assumptions.")
    if share_price <= 0:
        warnings.append("DCF share price is non-positive. Review operating assumptions and share count before relying on the result.")

    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Excel workbook from resolved deal inputs."
    )
    parser.add_argument("deal_id", help="Deal id with prepared model inputs.")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    input_path = base_dir / "data" / "extractions" / "resolved" / f"{args.deal_id}_model_input.json"
    if not input_path.exists():
        raise FileNotFoundError(f"Model input not found: {input_path}")

    extracted = json.loads(input_path.read_text(encoding="utf-8"))
    assumptions = build_assumptions(extracted)
    projections = build_projections(extracted, assumptions)
    wacc_info = compute_wacc(extracted, assumptions)
    dcf_info = compute_dcf(extracted, assumptions, projections, wacc_info)
    lbo_info = compute_lbo(extracted, projections, assumptions=assumptions)
    sensitivity_info = compute_sensitivity_tables(extracted, assumptions, projections, wacc_info)
    valuation_summary = build_valuation_summary(dcf_info, lbo_info)

    output_path = base_dir / "outputs" / f"{args.deal_id}_valuation_model.xlsx"
    result = write_workbook(
        output_path,
        extracted,
        assumptions,
        projections,
        wacc_info,
        dcf_info,
        lbo_info,
        sensitivity_info,
        valuation_summary,
    )
    summary_path = base_dir / "outputs" / f"{args.deal_id}_summary.json"
    summary_payload = {
        "deal_id": args.deal_id,
        "company_name": extracted.get("company_name", ""),
        "share_price_multiple": dcf_info.get("share_price_multiple"),
        "share_price_pgr": dcf_info.get("share_price_pgr"),
        "equity_value_multiple": dcf_info.get("equity_value_multiple"),
        "enterprise_value_multiple": dcf_info.get("enterprise_value_multiple"),
        "entry_multiple": lbo_info.get("entry_multiple"),
        "exit_multiple": lbo_info.get("exit_multiple"),
        "moic": lbo_info.get("moic"),
        "irr": lbo_info.get("irr"),
        "entry_leverage": (
            float(extracted.get("debt", 0)) / max(float(extracted.get("ebitda", 1)), 1.0)
            if float(extracted.get("ebitda", 0) or 0) > 0
            else None
        ),
        "exit_leverage": (
            lbo_info.get("exit_debt", 0) / max(float(projections[-1]["ebitda"]), 1.0)
            if projections and float(projections[-1]["ebitda"]) > 0
            else None
        ),
        "revenue_cagr": (
            (projections[-1]["revenue"] / max(float(extracted.get("revenue", 1)), 1.0)) ** (1 / len(projections)) - 1
            if projections and float(extracted.get("revenue", 0) or 0) > 0
            else None
        ),
        "warnings": _build_model_warnings(extracted, dcf_info),
        "editable_note": "You can always update assumptions and outputs later directly in the Excel workbook.",
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"Workbook written to: {result}")
    print(f"Summary written to: {summary_path}")


if __name__ == "__main__":
    main()

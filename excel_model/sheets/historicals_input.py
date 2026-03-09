from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def _write_input_row(ws, row: int, label: str, key: str, value, ctx, number_format: str) -> int:
    ws.cell(row=row, column=1, value=label)
    ws.cell(row=row, column=2, value=value)
    ws.cell(row=row, column=2).number_format = number_format
    ctx.set_ref(key, ws.title, f"B{row}")
    return row + 1


def build_historicals_input_sheet(ctx) -> None:
    ws = ctx.wb.active
    ws.title = "historicals_input"
    add_header(ws, "Historicals & Input")

    ws["A3"] = "Historical Financials"
    style_section(ws["A3"])

    headers = ["Year", "Revenue", "EBITDA", "EBITDA Margin", "Capex", "D&A", "NWC"]
    for idx, header in enumerate(headers, start=1):
        ws.cell(row=4, column=idx, value=header)
    style_header_row(ws, 4, 1, len(headers))

    for row_idx, hist in enumerate(ctx.model_inputs["historicals"], start=5):
        ws.cell(row=row_idx, column=1, value=hist["year"])
        ws.cell(row=row_idx, column=2, value=hist["revenue"]).number_format = "#,##0"
        ws.cell(row=row_idx, column=3, value=hist["ebitda"]).number_format = "#,##0"
        ws.cell(row=row_idx, column=4, value=hist["margin"]).number_format = "0.0%"
        ws.cell(row=row_idx, column=5, value=hist["capex"]).number_format = "#,##0"
        ws.cell(row=row_idx, column=6, value=hist["da"]).number_format = "#,##0"
        ws.cell(row=row_idx, column=7, value=hist["nwc"]).number_format = "#,##0"

    base_row = 7
    ctx.set_ref("historical_revenue_base", ws.title, f"B{base_row}")
    ctx.set_ref("historical_ebitda_base", ws.title, f"C{base_row}")
    ctx.set_ref("historical_nwc_base", ws.title, f"G{base_row}")

    row = 10
    ws.cell(row=row, column=1, value="Core Inputs")
    style_section(ws.cell(row=row, column=1))
    row += 1

    company_name = ctx.model_inputs["company_name"]
    ws.cell(row=row, column=1, value="Company Name")
    ws.cell(row=row, column=2, value=company_name)
    ctx.set_ref("company_name", ws.title, f"B{row}")
    row += 1

    numeric_rows = [
        ("Shares Outstanding", "shares_outstanding", ctx.model_inputs["inputs"]["shares_outstanding"], "#,##0"),
        ("Entry EBITDA", "purchase_ebitda", ctx.model_inputs["inputs"]["purchase_ebitda"], "#,##0"),
        ("Entry Multiple", "entry_multiple", ctx.model_inputs["inputs"]["entry_multiple"], "0.0x"),
        ("Existing Debt", "existing_debt", ctx.model_inputs["inputs"]["existing_debt"], "#,##0"),
        ("Existing Cash", "existing_cash", ctx.model_inputs["inputs"]["existing_cash"], "#,##0"),
        ("Transaction Fee %", "transaction_fee_pct", ctx.model_inputs["inputs"]["transaction_fee_pct"], "0.0%"),
        ("Financing Fee %", "financing_fee_pct", ctx.model_inputs["inputs"]["financing_fee_pct"], "0.0%"),
        ("Minimum Cash Balance", "min_cash_balance", ctx.model_inputs["inputs"]["min_cash_balance"], "#,##0"),
    ]
    for label, key, value, fmt in numeric_rows:
        row = _write_input_row(ws, row, label, key, value, ctx, fmt)

    row += 1
    ws.cell(row=row, column=1, value="Financing Assumptions")
    style_section(ws.cell(row=row, column=1))
    row += 1

    financing_rows = [
        ("Senior Debt / EBITDA", "senior_debt_multiple", ctx.model_inputs["inputs"]["senior_debt_multiple"], "0.0x"),
        ("Sub Debt / EBITDA", "sub_debt_multiple", ctx.model_inputs["inputs"]["sub_debt_multiple"], "0.0x"),
        ("Senior Interest Rate", "senior_interest_rate", ctx.model_inputs["inputs"]["senior_interest_rate"], "0.0%"),
        ("Sub Interest Rate", "sub_interest_rate", ctx.model_inputs["inputs"]["sub_interest_rate"], "0.0%"),
        ("Sub PIK Rate", "sub_pik_rate", ctx.model_inputs["inputs"]["sub_pik_rate"], "0.0%"),
        ("Revolver Rate", "revolver_interest_rate", ctx.model_inputs["inputs"]["revolver_interest_rate"], "0.0%"),
        ("Senior Amortization %", "senior_amortization_pct", ctx.model_inputs["inputs"]["senior_amortization_pct"], "0.0%"),
    ]
    for label, key, value, fmt in financing_rows:
        row = _write_input_row(ws, row, label, key, value, ctx, fmt)

    row += 1
    ws.cell(row=row, column=1, value="Valuation Assumptions")
    style_section(ws.cell(row=row, column=1))
    row += 1

    valuation_rows = [
        ("Tax Rate", "tax_rate", ctx.model_inputs["inputs"]["tax_rate"], "0.0%"),
        ("Risk Free Rate", "risk_free_rate", ctx.model_inputs["inputs"]["risk_free_rate"], "0.0%"),
        ("Beta", "beta", ctx.model_inputs["inputs"]["beta"], "0.00"),
        ("Market Risk Premium", "market_risk_premium", ctx.model_inputs["inputs"]["market_risk_premium"], "0.0%"),
        ("Cost of Debt", "cost_of_debt", ctx.model_inputs["inputs"]["cost_of_debt"], "0.0%"),
        ("Terminal Growth", "terminal_growth", ctx.model_inputs["inputs"]["terminal_growth"], "0.0%"),
        ("Exit Multiple", "exit_multiple", ctx.model_inputs["inputs"]["exit_multiple"], "0.0x"),
    ]
    for label, key, value, fmt in valuation_rows:
        row = _write_input_row(ws, row, label, key, value, ctx, fmt)

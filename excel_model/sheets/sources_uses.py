from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_sources_uses_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("sources_uses")
    add_header(ws, "Sources & Uses")

    ws["A3"] = "Uses"
    style_section(ws["A3"])
    ws["A4"] = "Line Item"
    ws["B4"] = "Amount"
    style_header_row(ws, 4, 1, 2)

    uses = {
        5: ("Purchase Price", f"={ctx.ref('purchase_ebitda')}*{ctx.ref('entry_multiple')}", "purchase_price"),
        6: ("Refinance Existing Debt", f"={ctx.ref('existing_debt')}", "refi_debt"),
        7: ("Transaction Fees", f"=B5*{ctx.ref('transaction_fee_pct')}", "transaction_fees"),
        8: ("Financing Fees", f"=(B11+B12)*{ctx.ref('financing_fee_pct')}", "financing_fees"),
        9: ("Minimum Cash", f"={ctx.ref('min_cash_balance')}", "entry_cash"),
        10: ("Total Uses", "=SUM(B5:B9)", "total_uses"),
    }

    for row, (label, formula, key) in uses.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula).number_format = "#,##0"
        ctx.set_ref(key, ws.title, f"B{row}")

    ws["A12"] = "Sources"
    style_section(ws["A12"])
    ws["A13"] = "Line Item"
    ws["B13"] = "Amount"
    style_header_row(ws, 13, 1, 2)

    sources = {
        14: ("Senior Debt", f"={ctx.ref('purchase_ebitda')}*{ctx.ref('senior_debt_multiple')}", "entry_senior_debt"),
        15: ("Sub Debt", f"={ctx.ref('purchase_ebitda')}*{ctx.ref('sub_debt_multiple')}", "entry_sub_debt"),
        16: ("Existing Cash", f"={ctx.ref('existing_cash')}", "existing_cash_source"),
        17: ("Sponsor Equity", "=B10-SUM(B14:B16)", "sponsor_equity"),
        18: ("Total Sources", "=SUM(B14:B17)", "total_sources"),
    }

    for row, (label, formula, key) in sources.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula).number_format = "#,##0"
        ctx.set_ref(key, ws.title, f"B{row}")

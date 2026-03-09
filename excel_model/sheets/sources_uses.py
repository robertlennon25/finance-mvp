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
        6: ("Refinance Existing Debt", f"=(1-{ctx.ref('debt_free_acquisition')})*{ctx.ref('existing_debt')}", "refi_debt"),
        7: ("Transaction Fees", f"=B5*{ctx.ref('transaction_fee_pct')}", "transaction_fees"),
        8: ("Financing Fees", f"=('debt_setup'!$B6+'debt_setup'!$C6+'debt_setup'!$D6)*{ctx.ref('financing_fee_pct')}", "financing_fees"),
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
        14: ("TLA Net Debt", "='debt_setup'!$B8", "entry_tla_debt"),
        15: ("TLB Net Debt", "='debt_setup'!$C8", "entry_tlb_debt"),
        16: ("Sub Debt", "='debt_setup'!$D8", "entry_sub_debt"),
        17: ("Existing Cash", f"={ctx.ref('existing_cash')}", "existing_cash_source"),
        18: ("Management Rollover", f"=B5*{ctx.ref('management_rollover_pct')}", "management_rollover"),
        19: ("Sponsor Equity", "=B10-SUM(B14:B18)", "sponsor_equity"),
        20: ("Total Sources", "=SUM(B14:B19)", "total_sources"),
    }

    for row, (label, formula, key) in sources.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula).number_format = "#,##0"
        ctx.set_ref(key, ws.title, f"B{row}")

    ws["D3"] = "Capital Structure Bridge"
    style_section(ws["D3"])
    ws["D4"] = "Metric"
    ws["E4"] = "Value"
    style_header_row(ws, 4, 4, 5)

    bridge = {
        5: ("Gross TLA", "='debt_setup'!$B6"),
        6: ("Gross TLB", "='debt_setup'!$C6"),
        7: ("Gross Sub", "='debt_setup'!$D6"),
        8: ("OID Discount", "=SUM(E5:E7)-SUM(B14:B16)"),
        9: ("Total Net New Debt", "=SUM(B14:B16)"),
    }
    for row, (label, formula) in bridge.items():
        ws.cell(row=row, column=4, value=label)
        ws.cell(row=row, column=5, value=formula).number_format = "#,##0"

    ctx.refs["entry_senior_debt"] = "'sources_uses'!$B$14+'sources_uses'!$B$15"

from __future__ import annotations

from excel_model.formatting import add_header, style_header_row


def build_checks_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("checks")
    add_header(ws, "Model Checks")

    ws["A3"] = "Check"
    ws["B3"] = "Formula"
    ws["C3"] = "Status"
    style_header_row(ws, 3, 1, 3)

    checks = [
        ("Sources = Uses", f"=ABS({ctx.ref('total_sources')}-{ctx.ref('total_uses')})", '=IF(B4<1,"PASS","FAIL")'),
        ("Sponsor Equity Positive", f"={ctx.ref('sponsor_equity')}", '=IF(B5>0,"PASS","FAIL")'),
        ("Minimum Cash Maintained", f"=MIN({ctx.ref('end_cash_1')},{ctx.ref('end_cash_2')},{ctx.ref('end_cash_3')},{ctx.ref('end_cash_4')},{ctx.ref('end_cash_5')})-{ctx.ref('min_cash_balance')}", '=IF(B6>=0,"PASS","FAIL")'),
        ("No Negative Senior Debt", f"=MIN({ctx.ref('end_senior_1')},{ctx.ref('end_senior_2')},{ctx.ref('end_senior_3')},{ctx.ref('end_senior_4')},{ctx.ref('end_senior_5')})", '=IF(B7>=0,"PASS","FAIL")'),
        ("No Negative Sub Debt", f"=MIN({ctx.ref('end_sub_1')},{ctx.ref('end_sub_2')},{ctx.ref('end_sub_3')},{ctx.ref('end_sub_4')},{ctx.ref('end_sub_5')})", '=IF(B8>=0,"PASS","FAIL")'),
        ("WACC > Terminal Growth", f"={ctx.ref('wacc')}-{ctx.ref('terminal_growth')}", '=IF(B9>0,"PASS","FAIL")'),
        ("Exit Equity Positive", f"={ctx.ref('exit_equity')}", '=IF(B10>0,"PASS","FAIL")'),
        ("DCF Share Price Positive", f"={ctx.ref('share_price_multiple')}", '=IF(B11>0,"PASS","FAIL")'),
    ]

    for idx, (label, formula, status) in enumerate(checks, start=4):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=formula)
        ws.cell(row=idx, column=3, value=status)

    ws["A14"] = "Python Safety Snapshot"
    ws["A15"] = "Metric"
    ws["B15"] = "Python"
    ws["C15"] = "Excel"
    ws["D15"] = "Delta"
    style_header_row(ws, 15, 1, 4)

    python_dcf = ctx.python_output.get("dcf_info", {})
    snapshot_rows = [
        ("DCF Share Price (PGR)", python_dcf.get("share_price_pgr", 0.0), f"={ctx.ref('share_price_pgr')}"),
        ("DCF Share Price (Multiple)", python_dcf.get("share_price_multiple", 0.0), f"={ctx.ref('share_price_multiple')}"),
    ]
    for idx, (label, py_value, excel_formula) in enumerate(snapshot_rows, start=16):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=py_value)
        ws.cell(row=idx, column=3, value=excel_formula)
        ws.cell(row=idx, column=4, value=f"=C{idx}-B{idx}")

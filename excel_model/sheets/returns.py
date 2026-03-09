from __future__ import annotations

from excel_model.formatting import add_header, style_header_row


def build_returns_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("returns")
    add_header(ws, "LBO Returns")

    ws["A3"] = "Metric"
    ws["B3"] = "Value"
    style_header_row(ws, 3, 1, 2)

    rows = {
        4: ("Entry EV", f"={ctx.ref('purchase_price')}", "entry_ev"),
        5: ("Sponsor Equity", f"={ctx.ref('sponsor_equity')}", "entry_equity"),
        6: ("Exit EBITDA", f"={ctx.ref('ebitda_5')}", "exit_ebitda"),
        7: ("Exit Multiple", f"={ctx.ref('exit_multiple')}", "exit_multiple_ref"),
        8: ("Exit EV", "=B6*B7", "exit_ev"),
        9: ("Exit Senior Debt", f"={ctx.ref('end_senior_5')}", "exit_senior"),
        10: ("Exit Sub Debt", f"={ctx.ref('end_sub_5')}", "exit_sub"),
        11: ("Exit Revolver", f"={ctx.ref('end_revolver_5')}", "exit_revolver"),
        12: ("Exit Cash", f"={ctx.ref('end_cash_5')}", "exit_cash"),
        13: ("Exit Equity Value", "=B8-B9-B10-B11+B12", "exit_equity"),
        14: ("MOIC", "=IFERROR(B13/B5,0)", "moic"),
        15: ("IRR", "=IFERROR(B14^(1/5)-1,0)", "irr"),
    }

    for row, (label, formula, key) in rows.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula)
        ctx.set_ref(key, ws.title, f"B{row}")

    for row in range(4, 14):
        ws.cell(row=row, column=2).number_format = "#,##0"
    ws["B14"].number_format = "0.00x"
    ws["B15"].number_format = "0.0%"

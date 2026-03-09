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
        5: ("Entry Senior Debt", f"={ctx.ref('entry_senior_debt')}", "entry_senior"),
        6: ("Entry Sub Debt", f"={ctx.ref('entry_sub_debt')}", "entry_sub"),
        7: ("Entry Net Debt", "=B5+B6", "entry_net_debt"),
        8: ("Sponsor Equity", f"={ctx.ref('sponsor_equity')}", "entry_equity"),
        9: ("Entry Debt / EBITDA", f"=IFERROR(B7/{ctx.ref('purchase_ebitda')},0)", "entry_leverage"),
        10: ("Exit EBITDA", f"={ctx.ref('ebitda_5')}", "exit_ebitda"),
        11: ("Exit Multiple", f"={ctx.ref('exit_multiple')}", "exit_multiple_ref"),
        12: ("Exit EV", "=B10*B11", "exit_ev"),
        13: ("Exit Senior Debt", f"={ctx.ref('end_senior_5')}", "exit_senior"),
        14: ("Exit Sub Debt", f"={ctx.ref('end_sub_5')}", "exit_sub"),
        15: ("Exit Revolver", f"={ctx.ref('end_revolver_5')}", "exit_revolver"),
        16: ("Exit Cash", f"={ctx.ref('end_cash_5')}", "exit_cash"),
        17: ("Exit Net Debt", "=B13+B14+B15-B16", "exit_net_debt"),
        18: ("Exit Debt / EBITDA", "=IFERROR(B17/B10,0)", "exit_leverage"),
        19: ("Debt Paydown", "=B7-B17", "debt_paydown"),
        20: ("Exit Equity Value", "=B12-B13-B14-B15+B16", "exit_equity"),
        21: ("MOIC", "=IFERROR(B20/B8,0)", "moic"),
        22: ("IRR", "=IFERROR(B21^(1/5)-1,0)", "irr"),
        23: ("Revenue CAGR", "=IFERROR((operating_model!F4/historicals_input!B7)^(1/5)-1,0)", "revenue_cagr"),
        24: ("EBITDA CAGR", "=IFERROR((B10/historicals_input!C7)^(1/5)-1,0)", "ebitda_cagr"),
    }

    for row, (label, formula, key) in rows.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula)
        ctx.set_ref(key, ws.title, f"B{row}")

    for row in range(4, 21):
        ws.cell(row=row, column=2).number_format = "#,##0"
    ws["B9"].number_format = "0.00x"
    ws["B11"].number_format = "0.0x"
    ws["B18"].number_format = "0.00x"
    ws["B21"].number_format = "0.00x"
    ws["B22"].number_format = "0.0%"
    ws["B23"].number_format = "0.0%"
    ws["B24"].number_format = "0.0%"

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
        5: ("Entry TLA Debt", "='sources_uses'!$B$14", "entry_tla"),
        6: ("Entry TLB Debt", "='sources_uses'!$B$15", "entry_tlb"),
        7: ("Entry Sub Debt", f"={ctx.ref('entry_sub_debt')}", "entry_sub"),
        8: ("Entry Net Debt", "=SUM(B5:B7)", "entry_net_debt"),
        9: ("Sponsor Equity", f"={ctx.ref('sponsor_equity')}", "entry_equity"),
        10: ("Entry Debt / EBITDA", f"=IFERROR(B8/{ctx.ref('purchase_ebitda')},0)", "entry_leverage"),
        11: ("Exit EBITDA", f"={ctx.ref('ebitda_5')}", "exit_ebitda"),
        12: ("Exit Multiple", f"={ctx.ref('exit_multiple')}", "exit_multiple_ref"),
        13: ("Exit EV", "=B11*B12", "exit_ev"),
        14: ("Exit TLA Debt", f"={ctx.ref('end_tla_5')}", "exit_tla"),
        15: ("Exit TLB Debt", f"={ctx.ref('end_tlb_5')}", "exit_tlb"),
        16: ("Exit Sub Debt", f"={ctx.ref('end_sub_5')}", "exit_sub"),
        17: ("Exit Revolver", f"={ctx.ref('end_revolver_5')}", "exit_revolver"),
        18: ("Exit Cash", f"={ctx.ref('end_cash_5')}", "exit_cash"),
        19: ("Exit Net Debt", "=SUM(B14:B17)-B18", "exit_net_debt"),
        20: ("Exit Debt / EBITDA", "=IFERROR(B19/B11,0)", "exit_leverage"),
        21: ("Debt Paydown", "=B8-B19", "debt_paydown"),
        22: ("Exit Equity Value", "=B13-SUM(B14:B17)+B18", "exit_equity"),
        23: ("MOIC", "=IFERROR(B22/B9,0)", "moic"),
        24: ("IRR", "=IFERROR(B23^(1/5)-1,0)", "irr"),
        25: ("Revenue CAGR", "=IFERROR((operating_model!F4/historicals_input!B7)^(1/5)-1,0)", "revenue_cagr"),
        26: ("EBITDA CAGR", "=IFERROR((B11/historicals_input!C7)^(1/5)-1,0)", "ebitda_cagr"),
    }

    for row, (label, formula, key) in rows.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula)
        ctx.set_ref(key, ws.title, f"B{row}")

    for row in range(4, 23):
        ws.cell(row=row, column=2).number_format = "#,##0"
    ws["B10"].number_format = "0.00x"
    ws["B12"].number_format = "0.0x"
    ws["B20"].number_format = "0.00x"
    ws["B23"].number_format = "0.00x"
    ws["B24"].number_format = "0.0%"
    ws["B25"].number_format = "0.0%"
    ws["B26"].number_format = "0.0%"

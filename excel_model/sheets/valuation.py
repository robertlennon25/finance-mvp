from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_valuation_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("valuation")
    add_header(ws, "Valuation")

    ws["A3"] = "WACC"
    style_section(ws["A3"])
    ws["A4"] = "Metric"
    ws["B4"] = "Value"
    style_header_row(ws, 4, 1, 2)

    rows = {
        5: ("Risk Free Rate", f"={ctx.ref('risk_free_rate')}"),
        6: ("Beta", f"={ctx.ref('beta')}"),
        7: ("Market Risk Premium", f"={ctx.ref('market_risk_premium')}"),
        8: ("Cost of Equity", "=B5+B6*B7"),
        9: ("Pre-Tax Cost of Debt", f"={ctx.ref('cost_of_debt')}"),
        10: ("Tax Rate", f"={ctx.ref('tax_rate')}"),
        11: ("After-Tax Cost of Debt", "=B9*(1-B10)"),
        12: ("Equity Weight", f"={ctx.ref('entry_equity')}/({ctx.ref('entry_equity')}+{ctx.ref('entry_senior_debt')}+{ctx.ref('entry_sub_debt')})"),
        13: ("Debt Weight", f"=1-B12"),
        14: ("WACC", "=B12*B8+B13*B11"),
    }
    for row, (label, formula) in rows.items():
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=formula)

    ctx.set_ref("wacc", ws.title, "B14")

    ws["D3"] = "DCF"
    style_section(ws["D3"])
    ws["D4"] = "Metric"
    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=5):
        ws.cell(row=4, column=idx, value=f"{year}E")
    ws["J4"] = "Total"
    style_header_row(ws, 4, 4, 10)

    ws["D5"] = "UFCF"
    ws["D6"] = "Discount Factor"
    ws["D7"] = "PV of UFCF"
    for idx in range(1, 6):
        col = chr(ord("D") + idx)
        ws[f"{col}5"] = f"={ctx.ref(f'ufcf_{idx}')}"
        ws[f"{col}6"] = f"=1/(1+{ctx.ref('wacc')})^{idx}"
        ws[f"{col}7"] = f"={col}5*{col}6"

    ws["D9"] = "Terminal Growth"
    ws["E9"] = f"={ctx.ref('terminal_growth')}"
    ws["D10"] = "Exit Multiple"
    ws["E10"] = f"={ctx.ref('exit_multiple')}"
    ws["D11"] = "Terminal Value (PGR)"
    ws["E11"] = f"=(I5*(1+E9))/MAX({ctx.ref('wacc')}-E9,0.0001)"
    ws["D12"] = "Terminal Value (Multiple)"
    ws["E12"] = f"={ctx.ref('ebitda_5')}*E10"
    ws["D13"] = "PV Terminal Value (PGR)"
    ws["E13"] = f"=E11/(1+{ctx.ref('wacc')})^5"
    ws["D14"] = "PV Terminal Value (Multiple)"
    ws["E14"] = f"=E12/(1+{ctx.ref('wacc')})^5"
    ws["D15"] = "PV Explicit Period"
    ws["E15"] = "=SUM(E7:I7)"
    ws["D16"] = "Enterprise Value (PGR)"
    ws["E16"] = "=E15+E13"
    ws["D17"] = "Enterprise Value (Multiple)"
    ws["E17"] = "=E15+E14"
    ws["D18"] = "Equity Value (PGR)"
    ws["E18"] = f"=E16-{ctx.ref('end_senior_5')}-{ctx.ref('end_sub_5')}-{ctx.ref('end_revolver_5')}+{ctx.ref('end_cash_5')}"
    ws["D19"] = "Equity Value (Multiple)"
    ws["E19"] = f"=E17-{ctx.ref('end_senior_5')}-{ctx.ref('end_sub_5')}-{ctx.ref('end_revolver_5')}+{ctx.ref('end_cash_5')}"
    ws["D20"] = "Share Price (PGR)"
    ws["E20"] = f"=E18/{ctx.ref('shares_outstanding')}"
    ws["D21"] = "Share Price (Multiple)"
    ws["E21"] = f"=E19/{ctx.ref('shares_outstanding')}"

    ctx.set_ref("share_price_pgr", ws.title, "E20")
    ctx.set_ref("share_price_multiple", ws.title, "E21")

    for row in range(5, 15):
        ws[f"B{row}"].number_format = "0.0%"
    ws["B6"].number_format = "0.00"
    for row in (15, 16, 17, 18, 19):
        ws[f"E{row}"].number_format = "#,##0"
    ws["E20"].number_format = "$#,##0.00"
    ws["E21"].number_format = "$#,##0.00"

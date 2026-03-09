from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_cover_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("cover", 0)
    add_header(ws, "LBO Model Summary")

    ws["A3"] = "Company"
    ws["B3"] = f"={ctx.ref('company_name')}"
    ws["A5"] = "Key Outputs"
    style_section(ws["A5"])
    ws["A6"] = "Metric"
    ws["B6"] = "Value"
    style_header_row(ws, 6, 1, 2)

    metrics = [
        ("Entry EV", ctx.ref("entry_ev")),
        ("Sponsor Equity", ctx.ref("entry_equity")),
        ("Exit EV", ctx.ref("exit_ev")),
        ("Exit Equity", ctx.ref("exit_equity")),
        ("MOIC", ctx.ref("moic")),
        ("IRR", ctx.ref("irr")),
        ("DCF Share Price", ctx.ref("share_price_multiple")),
    ]
    for idx, (label, ref) in enumerate(metrics, start=7):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=f"={ref}")

    ws["A16"] = "Model Status"
    style_section(ws["A16"])
    ws["A17"] = "Pass Count"
    ws["B17"] = '=COUNTIF(checks!C4:C11,"PASS")'
    ws["A18"] = "Fail Count"
    ws["B18"] = '=COUNTIF(checks!C4:C11,"FAIL")'
    ws["A20"] = "Workbook Tabs"
    style_section(ws["A20"])
    tabs = [
        "cover",
        "historicals_input",
        "assumptions",
        "sources_uses",
        "operating_model",
        "debt_schedule",
        "returns",
        "valuation",
        "sensitivities",
        "checks",
    ]
    for idx, tab in enumerate(tabs, start=21):
        ws.cell(row=idx, column=1, value=tab)

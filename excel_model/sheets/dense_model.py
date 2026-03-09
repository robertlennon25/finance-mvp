from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_dense_model_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("dense_model")
    add_header(ws, "Dense Model Snapshot")

    ws["A3"] = "Transaction Summary"
    style_section(ws["A3"])
    ws["A4"] = "Metric"
    ws["B4"] = "Value"
    style_header_row(ws, 4, 1, 2)

    summary = [
        ("Purchase Price", ctx.ref("purchase_price")),
        ("Refinanced Debt", ctx.ref("refi_debt")),
        ("Sponsor Equity", ctx.ref("sponsor_equity")),
        ("Entry EV", ctx.ref("entry_ev")),
        ("Exit EV", ctx.ref("exit_ev")),
        ("Exit Equity", ctx.ref("exit_equity")),
        ("MOIC", ctx.ref("moic")),
        ("IRR", ctx.ref("irr")),
        ("DCF Share Price", ctx.ref("share_price_multiple")),
    ]
    for idx, (label, ref) in enumerate(summary, start=5):
        ws.cell(row=idx, column=1, value=label)
        ws.cell(row=idx, column=2, value=f"={ref}")

    ws["D3"] = "Operating Model"
    style_section(ws["D3"])
    ws["D4"] = "Metric"
    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=5):
        ws.cell(row=4, column=idx, value=f"{year}E")
    style_header_row(ws, 4, 4, 9)

    operating_rows = [
        ("Revenue", 5, 4),
        ("EBITDA", 6, 7),
        ("UFCF", 7, 17),
    ]
    for label, target_row, source_row in operating_rows:
        ws.cell(row=target_row, column=4, value=label)
        for idx in range(5):
            col_letter = chr(ord("E") + idx)
            source_col = chr(ord("B") + idx)
            ws[f"{col_letter}{target_row}"] = f"=operating_model!{source_col}{source_row}"

    ws["D10"] = "Debt Roll-Forward"
    style_section(ws["D10"])
    ws["D11"] = "Metric"
    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=5):
        ws.cell(row=11, column=idx, value=f"{year}E")
    style_header_row(ws, 11, 4, 9)

    debt_map = {
        12: ("End TLA", "X"),
        13: ("End TLB", "Y"),
        14: ("End Sub Debt", "Z"),
        15: ("End Revolver", "AA"),
        16: ("End Cash", "W"),
    }
    for row, (label, source_col) in debt_map.items():
        ws.cell(row=row, column=4, value=label)
        for idx in range(5):
            col_letter = chr(ord("E") + idx)
            source_row = 4 + idx
            ws[f"{col_letter}{row}"] = f"=debt_schedule!{source_col}{source_row}"

    ws["D18"] = "Sensitivity Snapshot"
    style_section(ws["D18"])
    ws["D19"] = "Avg DCF Matrix"
    ws["E19"] = "=AVERAGE(sensitivities!B6:F10)"
    ws["D20"] = "Avg LBO Matrix"
    ws["E20"] = "=AVERAGE(sensitivities!B16:F20)"

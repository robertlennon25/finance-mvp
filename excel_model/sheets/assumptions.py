from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_assumptions_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("assumptions")
    add_header(ws, "Projection Assumptions")

    ws["A3"] = "Projection Assumptions by Year"
    style_section(ws["A3"])

    ws["A4"] = "Metric"
    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=2):
        ws.cell(row=4, column=idx, value=f"{year}E")
    style_header_row(ws, 4, 1, 6)

    labels = [
        ("Revenue Growth", "revenue_growth", "0.0%"),
        ("EBITDA Margin", "ebitda_margin", "0.0%"),
        ("Capex % Revenue", "capex_pct", "0.0%"),
        ("D&A % Revenue", "da_pct", "0.0%"),
        ("NWC % Revenue", "nwc_pct", "0.0%"),
    ]

    for row_idx, (label, key, fmt) in enumerate(labels, start=5):
        ws.cell(row=row_idx, column=1, value=label)
        for year_idx, value in enumerate(ctx.model_inputs["inputs"][key], start=2):
            ws.cell(row=row_idx, column=year_idx, value=value)
            ws.cell(row=row_idx, column=year_idx).number_format = fmt
            ctx.set_ref(f"{key}_{year_idx - 1}", ws.title, f"{ws.cell(row=row_idx, column=year_idx).coordinate}")

from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_operating_model_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("operating_model")
    add_header(ws, "Operating Model")

    ws["A3"] = "Metric"
    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=2):
        ws.cell(row=3, column=idx, value=f"{year}E")
    style_header_row(ws, 3, 1, 6)

    rows = {
        "revenue": 4,
        "growth": 5,
        "ebitda_margin": 6,
        "ebitda": 7,
        "da_pct": 8,
        "da": 9,
        "ebit": 10,
        "taxes": 11,
        "capex_pct": 12,
        "capex": 13,
        "nwc_pct": 14,
        "nwc_balance": 15,
        "delta_nwc": 16,
        "ufcf": 17,
    }

    for label, row in rows.items():
        ws.cell(row=row, column=1, value=label)

    for idx in range(1, 6):
        col = chr(ord("A") + idx)
        if idx == 1:
            ws[f"{col}{rows['revenue']}"] = f"={ctx.ref('historical_revenue_base')}*(1+{ctx.ref('revenue_growth_1')})"
            ws[f"{col}{rows['delta_nwc']}"] = f"={col}{rows['nwc_balance']}-{ctx.ref('historical_nwc_base')}"
        else:
            prev_col = chr(ord(col) - 1)
            ws[f"{col}{rows['revenue']}"] = f"={prev_col}{rows['revenue']}*(1+{ctx.ref(f'revenue_growth_{idx}')})"
            ws[f"{col}{rows['delta_nwc']}"] = f"={col}{rows['nwc_balance']}-{prev_col}{rows['nwc_balance']}"

        ws[f"{col}{rows['growth']}"] = f"={ctx.ref(f'revenue_growth_{idx}')}"
        ws[f"{col}{rows['ebitda_margin']}"] = f"={ctx.ref(f'ebitda_margin_{idx}')}"
        ws[f"{col}{rows['ebitda']}"] = f"={col}{rows['revenue']}*{col}{rows['ebitda_margin']}"
        ws[f"{col}{rows['da_pct']}"] = f"={ctx.ref(f'da_pct_{idx}')}"
        ws[f"{col}{rows['da']}"] = f"={col}{rows['revenue']}*{col}{rows['da_pct']}"
        ws[f"{col}{rows['ebit']}"] = f"={col}{rows['ebitda']}-{col}{rows['da']}"
        ws[f"{col}{rows['taxes']}"] = f"={col}{rows['ebit']}*{ctx.ref('tax_rate')}"
        ws[f"{col}{rows['capex_pct']}"] = f"={ctx.ref(f'capex_pct_{idx}')}"
        ws[f"{col}{rows['capex']}"] = f"={col}{rows['revenue']}*{col}{rows['capex_pct']}"
        ws[f"{col}{rows['nwc_pct']}"] = f"={ctx.ref(f'nwc_pct_{idx}')}"
        ws[f"{col}{rows['nwc_balance']}"] = f"={col}{rows['revenue']}*{col}{rows['nwc_pct']}"
        ws[f"{col}{rows['ufcf']}"] = (
            f"={col}{rows['ebit']}-{col}{rows['taxes']}+{col}{rows['da']}"
            f"-{col}{rows['capex']}-{col}{rows['delta_nwc']}"
        )

        for key in ("revenue", "ebitda", "ufcf"):
            ctx.set_ref(f"{key}_{idx}", ws.title, f"{col}{rows[key]}")

    for row in rows.values():
        for col in range(2, 7):
            ws.cell(row=row, column=col).number_format = "#,##0"
    for row in (rows["growth"], rows["ebitda_margin"], rows["da_pct"], rows["capex_pct"], rows["nwc_pct"]):
        for col in range(2, 7):
            ws.cell(row=row, column=col).number_format = "0.0%"

    ws["H3"] = "Notes"
    style_section(ws["H3"])
    ws["H4"] = "Excel is the source of truth. Python outputs are only safety checks."

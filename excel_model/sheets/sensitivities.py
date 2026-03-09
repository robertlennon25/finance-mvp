from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_sensitivities_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("sensitivities")
    add_header(ws, "Sensitivities")

    base_wacc = float(ctx.model_inputs["inputs"]["risk_free_rate"]) + (
        float(ctx.model_inputs["inputs"]["beta"]) * float(ctx.model_inputs["inputs"]["market_risk_premium"])
    )
    wacc_values = [base_wacc - 0.01, base_wacc - 0.005, base_wacc, base_wacc + 0.005, base_wacc + 0.01]
    growth_values = [
        float(ctx.model_inputs["inputs"]["terminal_growth"]) - 0.01,
        float(ctx.model_inputs["inputs"]["terminal_growth"]) - 0.005,
        float(ctx.model_inputs["inputs"]["terminal_growth"]),
        float(ctx.model_inputs["inputs"]["terminal_growth"]) + 0.005,
        float(ctx.model_inputs["inputs"]["terminal_growth"]) + 0.01,
    ]
    exit_values = [
        float(ctx.model_inputs["inputs"]["exit_multiple"]) - 1.0,
        float(ctx.model_inputs["inputs"]["exit_multiple"]) - 0.5,
        float(ctx.model_inputs["inputs"]["exit_multiple"]),
        float(ctx.model_inputs["inputs"]["exit_multiple"]) + 0.5,
        float(ctx.model_inputs["inputs"]["exit_multiple"]) + 1.0,
    ]
    ebitda_adj = [-0.10, -0.05, 0.0, 0.05, 0.10]

    ws["A3"] = "DCF: WACC vs Terminal Growth"
    style_section(ws["A3"])
    ws["A5"] = "WACC \\ Growth"
    for idx, growth in enumerate(growth_values, start=2):
        ws.cell(row=5, column=idx, value=growth)
    style_header_row(ws, 5, 1, 6)

    for row_idx, wacc in enumerate(wacc_values, start=6):
        ws.cell(row=row_idx, column=1, value=wacc)
        for col_idx, _ in enumerate(growth_values, start=2):
            growth_cell = ws.cell(row=5, column=col_idx).coordinate
            wacc_cell = ws.cell(row=row_idx, column=1).coordinate
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = (
                f"=("
                f"SUMPRODUCT(valuation!E5:I5,1/(1+{wacc_cell})^{{1,2,3,4,5}})"
                f"+((valuation!I5*(1+{growth_cell}))/MAX({wacc_cell}-{growth_cell},0.0001))/(1+{wacc_cell})^5"
                f"-{ctx.ref('end_senior_5')}-{ctx.ref('end_sub_5')}-{ctx.ref('end_revolver_5')}"
                f"+{ctx.ref('end_cash_5')}"
                f")/{ctx.ref('shares_outstanding')}"
            )
            cell.number_format = "$#,##0.00"

    ws["A13"] = "LBO: Exit Multiple vs Exit EBITDA Adj."
    style_section(ws["A13"])
    ws["A15"] = "Exit Multiple \\ EBITDA Adj."
    for idx, adj in enumerate(ebitda_adj, start=2):
        ws.cell(row=15, column=idx, value=adj)
    style_header_row(ws, 15, 1, 6)

    for row_idx, exit_multiple in enumerate(exit_values, start=16):
        ws.cell(row=row_idx, column=1, value=exit_multiple)
        for col_idx, _ in enumerate(ebitda_adj, start=2):
            adj_cell = ws.cell(row=15, column=col_idx).coordinate
            exit_cell = ws.cell(row=row_idx, column=1).coordinate
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = (
                f"=((({ctx.ref('exit_ebitda')}*(1+{adj_cell}))*{exit_cell})"
                f"-{ctx.ref('end_senior_5')}-{ctx.ref('end_sub_5')}-{ctx.ref('end_revolver_5')}"
                f"+{ctx.ref('end_cash_5')})/{ctx.ref('entry_equity')}"
            )
            cell.number_format = "0.00x"

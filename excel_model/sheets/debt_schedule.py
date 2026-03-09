from __future__ import annotations

from excel_model.formatting import add_header, style_header_row


def build_debt_schedule_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("debt_schedule")
    add_header(ws, "Debt Schedule")

    headers = [
        "Year",
        "Beg Cash",
        "Beg Senior",
        "Beg Sub",
        "Beg Revolver",
        "UFCF",
        "Senior Interest",
        "Sub Cash Interest",
        "Sub PIK",
        "Revolver Interest",
        "Cash Pre Debt Service",
        "Mandatory Senior",
        "Revolver Repay",
        "Cash Post Mandatory",
        "Cash Sweep Capacity",
        "Senior Sweep",
        "Sub Sweep",
        "Revolver Draw",
        "Liquidity Shortfall",
        "End Cash",
        "End Senior",
        "End Sub",
        "End Revolver",
    ]

    for idx, header in enumerate(headers, start=1):
        ws.cell(row=3, column=idx, value=header)
    style_header_row(ws, 3, 1, len(headers))

    for idx, year in enumerate(ctx.model_inputs["projection_years"], start=4):
        year_num = idx - 3
        ws.cell(row=idx, column=1, value=year)

        if idx == 4:
            ws.cell(row=idx, column=2, value=f"={ctx.ref('entry_cash')}")
            ws.cell(row=idx, column=3, value=f"={ctx.ref('entry_senior_debt')}")
            ws.cell(row=idx, column=4, value=f"={ctx.ref('entry_sub_debt')}")
            ws.cell(row=idx, column=5, value=0)
        else:
            ws.cell(row=idx, column=2, value=f"=T{idx - 1}")
            ws.cell(row=idx, column=3, value=f"=U{idx - 1}")
            ws.cell(row=idx, column=4, value=f"=V{idx - 1}")
            ws.cell(row=idx, column=5, value=f"=W{idx - 1}")

        ws.cell(row=idx, column=6, value=f"={ctx.ref(f'ufcf_{year_num}')}")
        ws.cell(row=idx, column=7, value=f"=C{idx}*{ctx.ref('senior_interest_rate')}")
        ws.cell(row=idx, column=8, value=f"=D{idx}*{ctx.ref('sub_interest_rate')}")
        ws.cell(row=idx, column=9, value=f"=D{idx}*{ctx.ref('sub_pik_rate')}")
        ws.cell(row=idx, column=10, value=f"=E{idx}*{ctx.ref('revolver_interest_rate')}")
        ws.cell(row=idx, column=11, value=f"=B{idx}+F{idx}-G{idx}-H{idx}-J{idx}")
        ws.cell(row=idx, column=12, value=f"=MIN(C{idx}*{ctx.ref('senior_amortization_pct')},C{idx})")
        ws.cell(row=idx, column=13, value=f"=MIN(MAX(K{idx}-L{idx}-{ctx.ref('min_cash_balance')},0),E{idx})")
        ws.cell(row=idx, column=14, value=f"=K{idx}-L{idx}-M{idx}")
        ws.cell(row=idx, column=15, value=f"=MAX(N{idx}-{ctx.ref('min_cash_balance')},0)*{ctx.ref('cash_sweep_pct')}")
        ws.cell(row=idx, column=16, value=f"=MIN(O{idx},MAX(C{idx}-L{idx},0))")
        ws.cell(row=idx, column=17, value=f"=MIN(MAX(O{idx}-P{idx},0),D{idx}+I{idx})")
        ws.cell(row=idx, column=18, value=f"=MIN(MAX({ctx.ref('min_cash_balance')}-(N{idx}-P{idx}-Q{idx}),0),MAX({ctx.ref('revolver_limit')}-E{idx}+M{idx},0))")
        ws.cell(row=idx, column=19, value=f"=MAX({ctx.ref('min_cash_balance')}-(N{idx}-P{idx}-Q{idx}-R{idx}),0)")
        ws.cell(row=idx, column=20, value=f"=N{idx}-P{idx}-Q{idx}+R{idx}"
        )
        ws.cell(row=idx, column=21, value=f"=MAX(C{idx}-L{idx}-P{idx},0)")
        ws.cell(row=idx, column=22, value=f"=MAX(D{idx}+I{idx}-Q{idx},0)")
        ws.cell(row=idx, column=23, value=f"=MAX(E{idx}-M{idx}+R{idx},0)")

        ctx.set_ref(f"liquidity_shortfall_{year_num}", ws.title, f"S{idx}")
        ctx.set_ref(f"end_cash_{year_num}", ws.title, f"T{idx}")
        ctx.set_ref(f"end_senior_{year_num}", ws.title, f"U{idx}")
        ctx.set_ref(f"end_sub_{year_num}", ws.title, f"V{idx}")
        ctx.set_ref(f"end_revolver_{year_num}", ws.title, f"W{idx}")

    for row in range(4, 9):
        for col in range(2, 24):
            ws.cell(row=row, column=col).number_format = "#,##0"

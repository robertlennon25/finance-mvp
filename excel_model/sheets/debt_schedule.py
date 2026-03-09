from __future__ import annotations

from excel_model.formatting import add_header, style_header_row


def build_debt_schedule_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("debt_schedule")
    add_header(ws, "Debt Schedule")

    headers = [
        "Year",
        "Beg Cash",
        "Beg TLA",
        "Beg TLB",
        "Beg Sub",
        "Beg Revolver",
        "UFCF",
        "TLA Interest",
        "TLB Interest",
        "Sub Cash Interest",
        "Sub PIK",
        "Revolver Interest",
        "Cash Pre Debt Service",
        "TLA Mandatory",
        "Revolver Repay",
        "Cash Post Mandatory",
        "Cash Sweep Capacity",
        "TLB Sweep",
        "TLA Sweep",
        "Sub Sweep",
        "Revolver Draw",
        "Liquidity Shortfall",
        "End Cash",
        "End TLA",
        "End TLB",
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
            ws.cell(row=idx, column=3, value="='sources_uses'!$B$14")
            ws.cell(row=idx, column=4, value="='sources_uses'!$B$15")
            ws.cell(row=idx, column=5, value=f"={ctx.ref('entry_sub_debt')}")
            ws.cell(row=idx, column=6, value=0)
        else:
            ws.cell(row=idx, column=2, value=f"=U{idx - 1}")
            ws.cell(row=idx, column=3, value=f"=V{idx - 1}")
            ws.cell(row=idx, column=4, value=f"=W{idx - 1}")
            ws.cell(row=idx, column=5, value=f"=X{idx - 1}")
            ws.cell(row=idx, column=6, value=f"=Y{idx - 1}")

        ws.cell(row=idx, column=7, value=f"={ctx.ref(f'ufcf_{year_num}')}")
        ws.cell(row=idx, column=8, value=f"=C{idx}*'debt_setup'!$B9")
        ws.cell(row=idx, column=9, value=f"=D{idx}*'debt_setup'!$C9")
        ws.cell(row=idx, column=10, value=f"=E{idx}*{ctx.ref('sub_interest_rate')}")
        ws.cell(row=idx, column=11, value=f"=E{idx}*{ctx.ref('sub_pik_rate')}")
        ws.cell(row=idx, column=12, value=f"=F{idx}*{ctx.ref('revolver_interest_rate')}")
        ws.cell(row=idx, column=13, value=f"=B{idx}+G{idx}-H{idx}-I{idx}-J{idx}-L{idx}")
        ws.cell(row=idx, column=14, value="=MIN(C{0}*'debt_setup'!$B11,C{0})".format(idx))
        ws.cell(row=idx, column=15, value=f"=MIN(MAX(M{idx}-N{idx}-{ctx.ref('min_cash_balance')},0),F{idx})")
        ws.cell(row=idx, column=16, value=f"=M{idx}-N{idx}-O{idx}")
        ws.cell(row=idx, column=17, value=f"=MAX(P{idx}-{ctx.ref('min_cash_balance')},0)*{ctx.ref('cash_sweep_pct')}")
        ws.cell(row=idx, column=18, value=f"=MIN(Q{idx},D{idx})")
        ws.cell(row=idx, column=19, value=f"=MIN(MAX(Q{idx}-R{idx},0),MAX(C{idx}-N{idx},0))")
        ws.cell(row=idx, column=20, value=f"=MIN(MAX(Q{idx}-R{idx}-S{idx},0),E{idx}+K{idx})")
        ws.cell(row=idx, column=21, value=f"=MIN(MAX({ctx.ref('min_cash_balance')}-(P{idx}-R{idx}-S{idx}-T{idx}),0),MAX({ctx.ref('revolver_limit')}-F{idx}+O{idx},0))")
        ws.cell(row=idx, column=22, value=f"=MAX({ctx.ref('min_cash_balance')}-(P{idx}-R{idx}-S{idx}-T{idx}-U{idx}),0)")
        ws.cell(row=idx, column=23, value=f"=P{idx}-R{idx}-S{idx}-T{idx}+U{idx}")
        ws.cell(row=idx, column=24, value=f"=MAX(C{idx}-N{idx}-S{idx},0)")
        ws.cell(row=idx, column=25, value=f"=MAX(D{idx}-R{idx},0)")
        ws.cell(row=idx, column=26, value=f"=MAX(E{idx}+K{idx}-T{idx},0)")
        ws.cell(row=idx, column=27, value=f"=MAX(F{idx}-O{idx}+U{idx},0)")

        ctx.set_ref(f"liquidity_shortfall_{year_num}", ws.title, f"V{idx}")
        ctx.set_ref(f"end_cash_{year_num}", ws.title, f"W{idx}")
        ctx.set_ref(f"end_tla_{year_num}", ws.title, f"X{idx}")
        ctx.set_ref(f"end_tlb_{year_num}", ws.title, f"Y{idx}")
        ctx.set_ref(f"end_sub_{year_num}", ws.title, f"Z{idx}")
        ctx.set_ref(f"end_revolver_{year_num}", ws.title, f"AA{idx}")
        ctx.refs[f"end_senior_{year_num}"] = f"'{ws.title}'!$X${idx}+'{ws.title}'!$Y${idx}"

    for row in range(4, 9):
        for col in range(2, 28):
            ws.cell(row=row, column=col).number_format = "#,##0"

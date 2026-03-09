from __future__ import annotations

from excel_model.formatting import add_header, style_header_row, style_section


def build_debt_setup_sheet(ctx) -> None:
    ws = ctx.wb.create_sheet("debt_setup")
    add_header(ws, "Debt Tranche Setup")

    ws["A3"] = "Debt Tranches"
    style_section(ws["A3"])
    headers = ["Metric", "TLA", "TLB", "Sub Notes", "Revolver"]
    for idx, header in enumerate(headers, start=1):
        ws.cell(row=4, column=idx, value=header)
    style_header_row(ws, 4, 1, 5)

    rows = {
        5: (
            "Target Multiple",
            f"={ctx.ref('senior_debt_multiple')}*{ctx.ref('senior_tla_pct')}",
            f"={ctx.ref('senior_debt_multiple')}*{ctx.ref('senior_tlb_pct')}",
            f"={ctx.ref('sub_debt_multiple')}",
            f"=IFERROR({ctx.ref('revolver_limit')}/{ctx.ref('purchase_ebitda')},0)",
        ),
        6: (
            "Gross Debt",
            f"={ctx.ref('purchase_ebitda')}*B5",
            f"={ctx.ref('purchase_ebitda')}*C5",
            f"={ctx.ref('purchase_ebitda')}*D5",
            f"={ctx.ref('revolver_limit')}",
        ),
        7: ("OID %", "0%", f"={ctx.ref('oid_pct')}", f"={ctx.ref('oid_pct')}", "0%"),
        8: ("Net Funding", "=B6*(1-B7)", "=C6*(1-C7)", "=D6*(1-D7)", "=0"),
        9: (
            "Cash Interest Rate",
            f"={ctx.ref('senior_interest_rate')}",
            f"={ctx.ref('senior_interest_rate')}",
            f"={ctx.ref('sub_interest_rate')}",
            f"={ctx.ref('revolver_interest_rate')}",
        ),
        10: ("PIK Rate", "0%", "0%", f"={ctx.ref('sub_pik_rate')}", "0%"),
        11: ("Amortization %", f"={ctx.ref('senior_amortization_pct')}", "0%", "0%", "0%"),
    }

    for row, values in rows.items():
        ws.cell(row=row, column=1, value=values[0])
        for col, value in enumerate(values[1:], start=2):
            ws.cell(row=row, column=col, value=value)

    mapping = {
        "tla_multiple": "B5",
        "tlb_multiple": "C5",
        "sub_multiple": "D5",
        "tla_gross": "B6",
        "tlb_gross": "C6",
        "sub_gross": "D6",
        "revolver_capacity": "E6",
        "tla_net": "B8",
        "tlb_net": "C8",
        "sub_net": "D8",
        "tla_rate": "B9",
        "tlb_rate": "C9",
        "sub_rate": "D9",
        "revolver_rate": "E9",
        "tla_amortization": "B11",
    }
    for key, cell in mapping.items():
        ctx.set_ref(key, ws.title, cell)

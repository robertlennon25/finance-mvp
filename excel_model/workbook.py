from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from openpyxl import Workbook

from excel_model.context import ModelContext
from excel_model.data import build_model_inputs
from excel_model.formatting import autosize_columns
from excel_model.sheets import (
    build_assumptions_sheet,
    build_checks_sheet,
    build_cover_sheet,
    build_debt_schedule_sheet,
    build_debt_setup_sheet,
    build_dense_model_sheet,
    build_historicals_input_sheet,
    build_operating_model_sheet,
    build_returns_sheet,
    build_sensitivities_sheet,
    build_sources_uses_sheet,
    build_valuation_sheet,
)


def write_workbook(
    output_path: str | Path,
    extracted: Dict[str, Any],
    assumptions: Any,
    projections: List[Dict[str, float]],
    wacc_info: Dict[str, float],
    dcf_info: Dict[str, Any],
    lbo_info: Dict[str, float],
    sensitivity_info: Dict[str, Any],
    valuation_summary: Iterable[Dict[str, Any]],
) -> Path:
    del projections, lbo_info, sensitivity_info, valuation_summary

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    python_output = {
        "dcf_info": dcf_info,
        "wacc_info": wacc_info,
    }
    ctx = ModelContext(
        wb=wb,
        model_inputs=build_model_inputs(extracted, assumptions),
        extracted=extracted,
        assumptions=assumptions,
        python_output=python_output,
    )

    build_historicals_input_sheet(ctx)
    build_assumptions_sheet(ctx)
    build_debt_setup_sheet(ctx)
    build_sources_uses_sheet(ctx)
    build_operating_model_sheet(ctx)
    build_debt_schedule_sheet(ctx)
    build_returns_sheet(ctx)
    build_valuation_sheet(ctx)
    build_sensitivities_sheet(ctx)
    build_checks_sheet(ctx)
    build_cover_sheet(ctx)
    build_dense_model_sheet(ctx)

    for sheet in wb.worksheets:
        autosize_columns(sheet)

    wb.save(output)
    return output

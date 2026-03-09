from __future__ import annotations

import json
from pathlib import Path

from excel_builder import write_workbook
# from model_client import extract_financial_fields
# from parser import extract_text_from_pdf, get_relevant_text
from valuation import (
    build_assumptions,
    build_projections,
    build_valuation_summary,
    compute_dcf,
    compute_lbo,
    compute_sensitivity_tables,
    compute_wacc,
)


def main() -> None:
    base_dir = Path(__file__).parent
    output_dir = base_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    input_json_path = base_dir / "example_input.json"

    if not input_json_path.exists():
        raise FileNotFoundError(
            f"Could not find {input_json_path}. Create that file first."
        )

    print("[1/6] Loading example JSON input")
    with input_json_path.open("r", encoding="utf-8") as f:
        extracted = json.load(f)

    # ------------------------------------------------------------------
    # TEMPORARILY DISABLED: PDF -> text -> model extraction pipeline
    # ------------------------------------------------------------------
    # print(f"[1/6] Extracting text from: {pdf_path}")
    # raw_text = extract_text_from_pdf(pdf_path)
    # prompt_text = get_relevant_text(raw_text)
    #
    # print("[2/6] Calling model for structured extraction")
    # extracted = extract_financial_fields(prompt_text)
    # (output_dir / "extracted.json").write_text(
    #     json.dumps(extracted, indent=2),
    #     encoding="utf-8"
    # )
    # ------------------------------------------------------------------

    print("[2/6] Saving loaded structured input")
    (output_dir / "extracted.json").write_text(
        json.dumps(extracted, indent=2),
        encoding="utf-8",
    )

    print("[3/6] Building assumptions")
    assumptions = build_assumptions(extracted)

    print("[4/6] Building projections")
    projections = build_projections(extracted, assumptions)

    print("[5/6] Computing WACC, DCF, LBO, and valuation summary")
    wacc_info = compute_wacc(extracted, assumptions)
    dcf_info = compute_dcf(extracted, assumptions, projections, wacc_info)
    lbo_info = compute_lbo(extracted, projections, assumptions=assumptions)
    valuation_summary = build_valuation_summary(dcf_info, lbo_info)
    print("[5.5/6] Computing sensitivity tables")
    sensitivity_info = compute_sensitivity_tables(
        extracted,
        assumptions,
        projections,
        wacc_info,
    )

    full_output = {
        "extracted": extracted,
        "assumptions": assumptions.__dict__,
        "projections": projections,
        "wacc_info": wacc_info,
        "dcf_info": dcf_info,
        "lbo_info": lbo_info,
        "sensitivity_info": sensitivity_info,
        "valuation_summary": list(valuation_summary),
    }

    (output_dir / "valuation_output.json").write_text(
        json.dumps(full_output, indent=2),
        encoding="utf-8",
    )
    

    print("[6/6] Writing Excel workbook")
    out_file = write_workbook(
        output_dir / "valuation_model.xlsx",
        extracted,
        assumptions,
        projections,
        wacc_info,
        dcf_info,
        lbo_info,
        sensitivity_info,
        valuation_summary,
    )

    print(f"Done. Workbook written to: {out_file}")
    print(f"Structured extraction saved to: {output_dir / 'extracted.json'}")


if __name__ == "__main__":
    main()
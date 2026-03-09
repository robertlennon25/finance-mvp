# Excel Model

Modular workbook builder for the LBO model.

## Design intent

- Excel is the canonical calculation engine
- Python builds the workbook structure, formulas, and formatting
- Python can also perform safety/reconciliation checks

## Sheet architecture

Current workbook is organized around transaction flow:

- cover / summary
- historicals / input
- assumptions
- debt setup
- sources & uses
- operating model
- debt schedule
- returns
- valuation
- sensitivities
- checks
- dense model snapshot

## Important files

- [`workbook.py`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/workbook.py)
- [`context.py`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/context.py)
- [`data.py`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/data.py)
- [`formatting.py`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/formatting.py)
- [`sheets/`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/sheets)

## Modeling principles

- multi-sheet institutional model first
- dense one-sheet view only after the multi-sheet flow is stable
- formulas should live in Excel wherever practical
- debt logic should stay realistic but bounded; avoid turning this into a full credit-agreement simulator

## Current debt setup

- explicit TLA / TLB / sub / revolver handling
- amortization and cash sweep logic
- debt-free acquisition toggle
- sources & uses fed by debt setup

## Important constraint

`openpyxl` writes formulas but does not recalculate them. Final numeric QA must be done in Excel or through an external recalculation path.

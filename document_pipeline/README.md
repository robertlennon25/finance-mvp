# Document Pipeline

Python pipeline for turning uploaded deal documents into structured model inputs.

## Stages

1. ingest documents
2. extract raw text/page text
3. chunk documents with overlap
4. call `gpt-4.1-mini`
5. run document-level synthesis over finance-heavy snippets
6. normalize candidate values
7. resolve fields
8. prepare review payload and model input

## Key scripts

- [`run_local_ingestion.py`](/Users/robertlennon/Desktop/finance_ai_mvp/run_local_ingestion.py)
- [`run_chunk_extraction.py`](/Users/robertlennon/Desktop/finance_ai_mvp/run_chunk_extraction.py)
- [`run_resolve_fields.py`](/Users/robertlennon/Desktop/finance_ai_mvp/run_resolve_fields.py)
- [`run_prepare_model_inputs.py`](/Users/robertlennon/Desktop/finance_ai_mvp/run_prepare_model_inputs.py)

## Key folders

- [`parsers/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/parsers)
- [`prompts/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/prompts)
- [`services/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services)
- [`schemas/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/schemas)

## Important artifacts

- raw outputs: `data/extractions/raw/`
- normalized candidates: `data/extractions/normalized/`
- resolved fields: `data/extractions/resolved/`
- overrides: `data/extractions/overrides/`
- chunks: `data/chunks/`

## Current resolver behavior

- direct extracted candidates are normalized and scored
- `inferred_from_chunk` and `inferred_from_document` candidates may be produced when the model can derive a missing field from nearby evidence
- `estimated` candidates are generated for missing or suspiciously zero fields
- narrow `web_estimated` candidates can be generated for public-company-like cases only
- user overrides win over extracted values
- review payload includes selected value, alternatives, warnings, and recommended estimates
- `entry_year` is now a reviewable field
- deterministic diagnostics are generated later during workbook build, not in the resolver itself

## Important constraint

`resolve_deal_fields()` expects `*_field_candidates.json`.

That means:
- local extraction runs can resolve directly
- remote Railway flows should rely on uploaded artifacts and frontend-side override overlays unless the worker is rerunning resolve on the remote side

## What to preserve

- unit normalization rules
- candidate scoring heuristics
- review payload schema
- override precedence order
- public-company-only web fallback rules and source URL handling
- the distinction between:
  - `extracted`
  - `inferred_from_chunk`
  - `inferred_from_document`
  - `estimated`
  - `web_estimated`

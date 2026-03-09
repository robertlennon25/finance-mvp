# AI Extraction Implementation Plan

## Goal

Build a document ingestion and extraction pipeline that:

1. Accepts multiple uploaded documents per deal.
2. Extracts text and basic document structure.
3. Uses `gpt-4.1-mini` to extract as many model inputs as possible.
4. Stores extracted values, candidates, confidence, and source references.
5. Allows user overrides before workbook generation.
6. Is easy to move from local-folder mode to `Vercel + Supabase`.

## Initial Scope

Phase 1 is local-first:

- Documents are dropped into `data/documents/inbox/`.
- A local pipeline processes them into normalized JSON outputs.
- Final resolved inputs are written to `data/extractions/resolved/`.
- The workbook builder continues to consume structured inputs.

Phase 2 is app-first:

- Users upload docs from the frontend.
- Files land in Supabase Storage.
- Metadata and extraction results land in Supabase Postgres.
- Auth is handled with Supabase Auth + Google OAuth.

## Architecture

### Local pipeline

1. `discover_documents`
   - Read files from a deal folder.
   - Assign a deal id and document ids.

2. `extract_text`
   - Use PDF/text parsers to pull raw text and page-level text.
   - Preserve document/page metadata.

3. `chunk_documents`
   - Split by page and/or semantic section.
   - Track chunk ids and source references.

4. `extract_fields`
   - Send relevant chunks to `gpt-4.1-mini`.
   - Extract into a strict schema.
   - Save raw model output and normalized candidates.

5. `reconcile_candidates`
   - Merge values across multiple documents.
   - Keep conflicts, confidence, and provenance.

6. `resolve_final_inputs`
   - Priority:
     - user override
     - high-confidence extracted value
     - inferred value
     - default

7. `build_workbook`
   - Feed the resolved inputs into the existing Excel model.

### App architecture later

- Frontend: Next.js on Vercel
- Auth: Supabase Auth with Google OAuth
- Storage: Supabase Storage
- DB: Supabase Postgres
- AI: OpenAI `gpt-4.1-mini`
- API routes:
  - `POST /api/deals`
  - `POST /api/deals/:id/documents`
  - `POST /api/deals/:id/extract`
  - `POST /api/deals/:id/resolve`
  - `POST /api/deals/:id/workbook`

## Data model

### Core entities

- `deals`
  - id
  - user_id
  - name
  - status
  - created_at

- `documents`
  - id
  - deal_id
  - filename
  - storage_path
  - document_type
  - parse_status
  - uploaded_at

- `document_chunks`
  - id
  - document_id
  - chunk_index
  - page_start
  - page_end
  - chunk_text
  - metadata_json

- `extraction_runs`
  - id
  - deal_id
  - model
  - status
  - created_at

- `field_candidates`
  - id
  - extraction_run_id
  - deal_id
  - field_name
  - value_json
  - confidence
  - source_document_id
  - source_locator
  - method

- `resolved_fields`
  - id
  - deal_id
  - field_name
  - value_json
  - resolution_method
  - source_candidate_id

- `user_overrides`
  - id
  - deal_id
  - field_name
  - value_json
  - note
  - created_at

## Extraction strategy

### Extraction pass order

1. Company overview and document classification
2. Historical financials
3. Capital structure and balance sheet fields
4. Forecast assumptions
5. Comparable companies / precedent transactions
6. Derived/inferred fields

### Important rule

Do not ask the model to produce one giant final input blob from all documents in one call.

Instead:

- extract field candidates by topic
- reconcile
- infer only what remains missing

## Key extracted fields

### Direct extraction targets

- revenue
- EBITDA
- cash
- debt
- shares outstanding
- tax rate
- capex assumptions
- NWC assumptions
- debt terms
- peer multiples
- precedent multiples
- management guidance

### Inferred targets

- entry multiple recommendation
- exit multiple recommendation
- debt tranche assumptions
- missing operating assumptions

## Folder layout

```text
docs/
  ai_extraction_implementation_plan.md

data/
  documents/
    inbox/
    processed/
  extractions/
    raw/
    normalized/
    resolved/
  chunks/

document_pipeline/
  __init__.py
  config.py
  models.py
  schemas/
    __init__.py
    extracted_fields.py
  prompts/
    __init__.py
  parsers/
    __init__.py
  storage/
    __init__.py
  services/
    __init__.py

supabase/
  README.md
  migrations/
```

## Immediate implementation order

1. Create local folder ingestion flow.
   - Status: scaffolded with `run_local_ingestion.py`
2. Define extraction schema objects for candidate fields.
   - Status: scaffolded in `document_pipeline/schemas/extracted_fields.py`
3. Build parser output format:
   - document
   - page
   - chunk
   - Status: scaffolded in `document_pipeline/parsers/text_extractor.py`
4. Add OpenAI extraction service around `gpt-4.1-mini`.
   - Status: scaffolded with `run_chunk_extraction.py`
5. Add normalization and confidence handling.
   - Status: scaffolded with `run_resolve_fields.py` and local overrides
6. Add resolved input assembler for workbook generation.
   - Status: scaffolded with `run_prepare_model_inputs.py` and `run_build_workbook_from_deal.py`
7. Then add Supabase persistence and frontend upload flow.

## Done criteria for local-first phase

- Drop multiple files in a deal folder.
- Run one command locally.
- Produce:
  - raw extracted text
  - field candidates with citations
  - resolved workbook input JSON
  - generated workbook

## Notes

- Keep extracted values explainable. Every important field should carry source provenance.
- The workbook should never consume raw model output directly.
- User overrides should be first-class from the beginning.
- Local override path:
  - `data/extractions/overrides/<deal_id>_overrides.json`

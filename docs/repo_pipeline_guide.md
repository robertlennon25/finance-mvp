# Repo and Pipeline Guide

This is the practical map for the repo as it exists today. Use it to answer three questions quickly:

1. Where does a request start?
2. Which file is authoritative for the next stage?
3. Where should I debug when the flow breaks before deploy?

## System Shape

- `frontend/`: Next.js UI, API routes, auth-aware orchestration, and download endpoints.
- `worker_api/`: FastAPI worker used by Railway for remote extraction and workbook builds.
- `document_pipeline/`: Python ingestion, chunking, extraction, resolve, and review-payload prep.
- `excel_model/`: Excel workbook writer and sheet builders.
- `data/`: Local filesystem state for documents, extraction artifacts, overrides, and run metadata.
- `outputs/`: Final workbook plus summary and diagnostics JSON.
- `supabase/`: SQL migrations and setup notes for database-backed metadata and overrides.

## What Runs Where

### Vercel / Next.js

The frontend does four jobs:

- creates deals from uploads or manual entry
- stores deal/document metadata and overrides in Supabase when configured
- triggers either local Python or the Railway worker
- serves stable app routes for documents and workbook downloads

Most orchestration logic lives in [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js).

### Railway worker

The worker is the heavy-processing backend for production:

- sync documents and artifacts down from Supabase
- sync user overrides before analysis
- run ingestion, extraction, resolve, prepare, and workbook build
- upload fresh artifacts back to Supabase Storage

Key files:

- [worker_api/app.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py)
- [worker_api/pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)
- [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py)

### Python document pipeline

This is the source of truth for turning files into structured model inputs.

Key services:

- [document_pipeline/services/local_pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/local_pipeline.py)
- [document_pipeline/services/openai_extraction.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/openai_extraction.py)
- [document_pipeline/services/resolve_fields.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py)
- [document_pipeline/services/prepare_model_inputs.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/prepare_model_inputs.py)

### Excel model

The workbook build starts only after `*_model_input.json` exists.

Key files:

- [run_build_workbook_from_deal.py](/Users/robertlennon/Desktop/finance_ai_mvp/run_build_workbook_from_deal.py)
- [excel_model/](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model)

## Main User Flows

### 1. Upload documents

Start points:

- `POST /api/deals`
- [frontend/app/api/deals/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/route.js)

What happens:

- files are written to `data/documents/inbox/<deal_id>/`
- deal metadata is written locally under `data/pipeline_state/deals/`
- if Supabase is configured, files are also uploaded to `private/<user_or_anonymous>/<deal_id>/<filename>`
- document metadata is upserted into the `documents` table

### 2. Manual entry

Start point:

- `POST /api/deals/manual`
- [frontend/app/api/deals/manual/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/manual/route.js)

What happens:

- no documents are required
- a synthetic manifest plus `*_field_candidates.json` is created directly
- resolve and prepare run immediately
- review artifacts are uploaded to Supabase if configured

This means manual-entry deals skip ingestion and AI extraction entirely.

### 3. Extraction phase

Start point:

- `POST /api/deals/[dealId]/pipeline` with `phase: "extract"`
- [frontend/app/api/deals/[dealId]/pipeline/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js)

Branching:

- if `RAILWAY_WORKER_URL` is blank, Next runs local Python scripts
- if `RAILWAY_WORKER_URL` is set, Next queues a Railway job and polls status

Result:

- review payload becomes available at `data/extractions/resolved/<deal_id>_review_payload.json`
- or in Supabase Storage at `artifacts/<deal_id>/<deal_id>_review_payload.json`

### 4. Review and overrides

Start points:

- page: `/deals/[dealId]/review`
- route: `POST/DELETE /api/deals/[dealId]/overrides`
- route: `POST /api/deals/[dealId]/estimates`

Behavior:

- review UI reads `review_payload.json`
- override values are stored in `data/extractions/overrides/<deal_id>_overrides.json`
- if authenticated with Supabase persistence enabled, overrides are also stored in `user_overrides`
- the UI overlays overrides onto the review payload at read time

Important detail:

- saving an override does not rebuild artifacts immediately
- overrides are applied during the later analysis run

### 5. Analysis phase

Start point:

- `POST /api/deals/[dealId]/pipeline` with `phase: "analysis"`

What happens:

- local mode reruns resolve, prepare, and workbook build directly
- worker mode syncs overrides from Supabase first, then runs analysis
- workbook outputs are written to `outputs/`
- worker uploads the workbook, summary, and diagnostics JSON back to Supabase

### 6. Results and downloads

Pages:

- `/deals/[dealId]/results`
- `/api/deals/[dealId]/workbook`
- `/api/deals/[dealId]/documents/[fileName]`

The frontend prefers remote artifacts when Railway is configured, then falls back to local files.

## Source of Truth by Stage

- Documents to ingest: `data/documents/inbox/<deal_id>/`
- Manifest and chunk selection: `data/extractions/normalized/<deal_id>_manifest.json`
- Raw AI chunk output: `data/extractions/raw/<deal_id>_chunk_candidates_raw.json`
- Extracted field candidates: `data/extractions/normalized/<deal_id>_field_candidates.json`
- Normalized/scored candidates: `data/extractions/normalized/<deal_id>_field_candidates_normalized.json`
- Resolved values after overrides: `data/extractions/resolved/<deal_id>_resolved.json`
- Review UI payload: `data/extractions/resolved/<deal_id>_review_payload.json`
- Workbook input: `data/extractions/resolved/<deal_id>_model_input.json`
- Final workbook: `outputs/<deal_id>_valuation_model.xlsx`
- Final summary: `outputs/<deal_id>_summary.json`
- Final diagnostics: `outputs/<deal_id>_diagnostics.json`

## Repo Areas To Read First When Debugging

If the issue is "pipeline status / job orchestration":

- [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [frontend/app/api/deals/[dealId]/pipeline/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js)
- [worker_api/app.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py)
- [worker_api/pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)

If the issue is "wrong numbers on review screen":

- [document_pipeline/services/resolve_fields.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py)
- [document_pipeline/services/prepare_model_inputs.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/prepare_model_inputs.py)
- [frontend/components/review-workspace.jsx](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/components/review-workspace.jsx)

If the issue is "workbook missing or wrong":

- [run_build_workbook_from_deal.py](/Users/robertlennon/Desktop/finance_ai_mvp/run_build_workbook_from_deal.py)
- [excel_model/](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model)
- [frontend/app/api/deals/[dealId]/workbook/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/workbook/route.js)

If the issue is "remote artifacts not showing up on Vercel":

- [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py)
- [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [frontend/lib/supabase/config.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/supabase/config.js)

## Deployment Reality

The clean production path is:

- Vercel handles UI and thin API routes
- Supabase handles auth, metadata, overrides, and storage
- Railway handles all heavy Python work

The local filesystem-backed path still exists for development, but it should be treated as a dev convenience, not the production contract.

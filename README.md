# Finance AI MVP

AI-assisted LBO modeling workflow with:

- a Python document pipeline
- an institutional-style Excel model generator
- a Next.js review frontend
- Supabase auth/storage/metadata
- a Railway FastAPI worker for remote processing
- a documented next-step path for AI-generated acquisition memos

## Current architecture

- Excel is the source-of-truth model engine in [`excel_model/`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model)
- Python handles ingestion, extraction, normalization, resolve, and workbook generation
- Frontend lives in [`frontend/`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend)
- Supabase handles Google OAuth, overrides, deal/document metadata, and storage
- Railway hosts the remote worker in [`worker_api/`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api)

## Important current behavior

- Local dev frontend can run with or without Railway
- If `RAILWAY_WORKER_URL` is set, frontend pipeline calls go to Railway
- If `RAILWAY_WORKER_URL` is blank, the frontend falls back to local Python commands
- Remote worker artifacts are uploaded to Supabase Storage under `artifacts/<deal_id>/...`
- Frontend can read review payloads and workbooks from Supabase when local files are absent
- Review payloads can now include extracted, estimated, and public-company web-estimated values with source links
- Workbook summary artifacts can now include deterministic diagnostics explaining suspicious outputs

## Repo map

- [`excel_model/`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model): workbook builder and sheet modules
- [`document_pipeline/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline): ingestion, chunking, extraction, normalization, resolve, prepare
- [`worker_api/`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api): FastAPI worker for Railway
- [`frontend/`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend): Next.js app
- [`supabase/`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase): SQL migrations and setup notes
- [`docs/`](/Users/robertlennon/Desktop/finance_ai_mvp/docs): architecture, deployment, roadmap, and retained context

## Local setup

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create [`.env.local`](/Users/robertlennon/Desktop/finance_ai_mvp/.env.local):

```env
OPENAI_API_KEY=...
```

### Frontend

Use Node 20+.

Create [`frontend/.env.local`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/.env.local):

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
NEXT_PUBLIC_SITE_URL=http://localhost:3000
SUPABASE_STORAGE_BUCKET=deal-documents
RAILWAY_WORKER_URL=
WORKER_SHARED_SECRET=
```

Start frontend:

```bash
cd /Users/robertlennon/Desktop/finance_ai_mvp/frontend
nvm use 20
npm install
npm run dev
```

## Main flows

### Local CLI pipeline

```bash
python3 run_local_ingestion.py <deal_id>
python3 run_chunk_extraction.py <deal_id> --max-chunks 5
python3 run_resolve_fields.py <deal_id>
python3 run_prepare_model_inputs.py <deal_id>
python3 run_build_workbook_from_deal.py <deal_id>
```

### Frontend flow

1. Upload documents or open an example deal
2. Run extraction
3. Review extracted values
4. Apply reasonable estimates or manual overrides
5. Run analysis
6. Download the generated workbook
7. Review warnings and diagnostics on the results page

### Example-deal flow

1. Open `Existing LBOs`
2. Select a curated example
3. View the summary page
4. Download the workbook
5. Inspect the source documents that fed the case

This path is intentionally separated from the live upload-and-run workflow.

## Current pipeline interaction model

1. Documents are uploaded or selected from curated examples.
2. Ingestion extracts page text and builds overlapping chunks.
3. Chunk extraction sends chunks to `gpt-4.1-mini`.
4. A document-level synthesis pass tries to infer missing finance fields from the most relevant snippets.
5. Resolver normalizes units, scores candidates, applies web fallback for public-company cases, and generates reasonable estimates.
6. Review payload is prepared for the frontend with selected values, options, warnings, and source URLs.
7. User can override values or apply reasonable estimates.
8. Workbook build writes:
   - XLSX
   - summary JSON
   - diagnostics JSON
9. Frontend shows outputs, warnings, and suggested fixes.

## Deployment shape

- Vercel: Next.js frontend and lightweight API routes
- Supabase: auth, storage, metadata
- Railway: FastAPI worker

See:

- [`docs/current_state.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/current_state.md)
- [`docs/deployment_architecture.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/deployment_architecture.md)
- [`docs/supabase_setup.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/supabase_setup.md)
- [`docs/railway_deploy.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/railway_deploy.md)
- [`docs/memo_generation_plan.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/memo_generation_plan.md)

## Known constraints

- Remote runs require Supabase artifact sync to make review/results visible to the frontend
- Local review/override flows should not depend on local candidate files after a Railway run
- Uploads still write a local dev copy first; production should move to storage-first behavior
- `frontend/node_modules_broken_*` and similar reinstall artifacts should never be committed
- AI extraction is stronger than before, but filings with unusual labeling can still require user overrides
- The memo-generation feature is not implemented yet; only the plan/spec exists today

## Safe restart points after compaction

If context is lost, re-read these first:

1. [`docs/current_state.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/current_state.md)
2. [`docs/deployment_architecture.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/deployment_architecture.md)
3. [`docs/roadmap.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/roadmap.md)
4. [`frontend/README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/README.md)
5. [`document_pipeline/README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/README.md)
6. [`excel_model/README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/README.md)

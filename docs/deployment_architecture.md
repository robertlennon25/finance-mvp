# Deployment Architecture

## Target stack

- Frontend and light orchestration: Vercel
- Auth, database, storage: Supabase
- Python pipeline worker: Railway

## Route model

### Browser-facing

- `/` landing page
- `/library` example deals only
- `/new` upload flow
- `/deals/:dealId` deal detail
- `/deals/:dealId/process?phase=extract|analysis`
- `/deals/:dealId/review`
- `/deals/:dealId/results`

### App API routes on Vercel

- `/api/deals`
- `/api/deals/:dealId/pipeline`
- `/api/deals/:dealId/overrides`
- `/api/deals/:dealId/documents/:fileName`
- `/api/deals/:dealId/workbook`

These routes should stay stable even after moving documents to Supabase Storage and Python execution to Railway.

## Why this route design matters

- The frontend never references local filesystem paths directly.
- Document and workbook access always goes through app routes.
- Later, those routes can fetch from Supabase Storage or signed URLs without changing the UI.

## Runtime split

### Vercel responsibilities

- render Next.js UI
- handle auth/session
- create deals and upload metadata
- enqueue or trigger pipeline runs
- read deal state and show progress

### Railway responsibilities

- run PDF ingestion
- run GPT-4.1 mini extraction
- normalize and resolve values
- build workbook and summary artifacts
- write run status back to Supabase

### Supabase responsibilities

- Google OAuth
- user tables and app data
- uploaded document storage
- pipeline run history
- overrides
- workbook metadata and downloadable artifact locations

## Data model to add next

- `deals`
- `documents`
- `pipeline_runs`
- `generated_workbooks`
- `usage_counters`

## Local-to-cloud migration path

### Local now

- documents in `data/documents/`
- extraction artifacts in `data/extractions/`
- run metadata in `data/pipeline_state/`
- workbook outputs in `outputs/`

### Cloud later

- documents -> Supabase Storage
- run metadata -> `pipeline_runs`
- workbook summary + workbook location -> `generated_workbooks`
- example visibility -> `deals.visibility` and `deals.is_example`

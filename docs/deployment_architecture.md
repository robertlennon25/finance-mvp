# Deployment Architecture

## Target stack

- Vercel: frontend and light orchestration routes
- Supabase: auth, database, storage
- Railway: Python worker

## Responsibilities

### Vercel

- render Next.js UI
- authenticate users through Supabase
- create deals and upload documents
- save overrides
- trigger Railway jobs
- poll Railway job status
- serve document/workbook downloads through stable app routes

### Supabase

- Google OAuth
- `user_overrides`
- `deals`
- `documents`
- `pipeline_runs`
- `usage_counters`
- private storage bucket for documents and remote artifacts

### Railway

- sync documents from Supabase Storage
- sync user overrides before analysis
- ingest/chunk/extract
- resolve/prepare
- build workbook
- upload remote artifacts back to Supabase Storage

## Current cross-system contract

Frontend -> Railway:

- `POST /pipeline/run`
- `GET /pipeline/run/{job_id}`

Auth:

- bearer header using `WORKER_SHARED_SECRET`

Worker request body:

```json
{
  "deal_id": "example_case",
  "phase": "extract",
  "max_chunks": 5,
  "triggered_by": "frontend",
  "user_id": "uuid-or-null"
}
```

## Artifact contract

Remote worker uploads:

- `artifacts/<deal_id>/<deal_id>_review_payload.json`
- `artifacts/<deal_id>/<deal_id>_model_input.json`
- `artifacts/<deal_id>/<deal_id>_manifest.json`
- `artifacts/<deal_id>/<deal_id>_valuation_model.xlsx`
- `artifacts/<deal_id>/<deal_id>_summary.json`
- `artifacts/<deal_id>/<deal_id>_diagnostics.json`

Frontend should treat those as the remote fallback source when local files are absent.

## Current local dev fallback

If `RAILWAY_WORKER_URL` is blank:

- frontend routes still run local Python commands

That path exists for dev convenience, not as the long-term production architecture.

## Production direction

The clean production direction is:

1. uploads go directly to Supabase Storage
2. Vercel stores metadata only
3. Railway becomes the only heavy processing path
4. frontend becomes storage-backed, not filesystem-backed

## Planned extension after deploy

After the core deploy is stable, add a memo-generation stage:

1. frontend sends the resolved deal context plus `acquirer_name`
2. worker produces workbook screenshots and a memo prompt context
3. OpenAI generates a starter acquisition memo
4. worker uploads memo artifacts to storage
5. frontend previews and downloads the memo

This should remain a separate artifact-producing stage, not part of the core Excel build path.

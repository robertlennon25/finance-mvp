# Railway Worker Contract

## Goal

Keep Vercel as the UI/orchestration layer and move heavy Python execution to Railway.

## Worker responsibilities

- ingest documents from Supabase Storage
- extract text and chunks
- call GPT-4.1 mini
- normalize and resolve values
- build workbook and summary artifacts
- write status and outputs back to Supabase

## Authentication

If `WORKER_SHARED_SECRET` is configured, Vercel should send:

```http
Authorization: Bearer <WORKER_SHARED_SECRET>
```

## Worker endpoints

### `POST /pipeline/run`

Request body:

```json
{
  "deal_id": "expedia_sponsor_case",
  "phase": "extract",
  "max_chunks": 5,
  "triggered_by": "frontend",
  "user_id": "uuid-or-null"
}
```

Allowed phases:

- `extract`
- `analysis`
- `full`

Response:

```json
{
  "ok": true,
  "job_id": "uuid",
  "status": "queued"
}
```

### `GET /pipeline/run/:job_id`

Response:

```json
{
  "job_id": "uuid",
  "deal_id": "expedia_sponsor_case",
  "phase": "extract",
  "status": "running",
  "progress": 60,
  "message": "Extracting with GPT-4.1 mini",
  "cached": false
}
```

## Supabase writes expected from worker

- `pipeline_runs`
- `documents` metadata if needed
- normalized/resolved artifact locations
- workbook location and summary metadata

## Storage conventions

Bucket:

- `deal-documents`

Paths:

- `private/<user_id>/<deal_id>/<filename>`
- `examples/<deal_id>/<filename>`

Workbook bucket later:

- `deal-workbooks`

## Environment expected by Railway

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `WORKER_SHARED_SECRET`

## Current status

The FastAPI worker now exists in:

- [`worker_api/app.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py)

The Vercel app will use Railway automatically when:

- `RAILWAY_WORKER_URL` is set in Vercel
- `WORKER_SHARED_SECRET` matches on both sides

If `RAILWAY_WORKER_URL` is missing, the frontend falls back to local Python execution.

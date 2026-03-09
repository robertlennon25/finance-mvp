# Railway Deploy

## Goal

Railway hosts the Python worker that runs:

- document sync from Supabase Storage
- ingestion and chunking
- OpenAI extraction
- resolve and prepare
- workbook generation

The Vercel app should call Railway for pipeline execution in deployed environments.

## Repo files already prepared

- [`Dockerfile`](/Users/robertlennon/Desktop/finance_ai_mvp/Dockerfile)
- [`railway.toml`](/Users/robertlennon/Desktop/finance_ai_mvp/railway.toml)
- [`Procfile`](/Users/robertlennon/Desktop/finance_ai_mvp/Procfile)
- [`requirements.txt`](/Users/robertlennon/Desktop/finance_ai_mvp/requirements.txt)
- [`worker_api/app.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py)

## Railway project creation

1. Go to [Railway](https://railway.com/) and sign in.
2. Click `New Project`.
3. Choose `Empty Project`.
4. Rename it to something like `finance-ai-worker`.
5. Inside that project, click `New`.
6. Choose `GitHub Repo`.
7. Connect your existing repo.
8. Select this repo.
9. Rename the new service to `python-worker`.

Do not add a Railway database. Supabase is the database, auth, and storage layer.

## Service settings

Railway should now build from the repo [`Dockerfile`](/Users/robertlennon/Desktop/finance_ai_mvp/Dockerfile).

If Railway asks for overrides:

- Root Directory: leave as repo root
- Build Command: leave blank
- Start Command: leave blank

The Docker image already starts the worker.

## Environment variables

Add these in `Service -> Variables`:

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=deal-documents`
- `WORKER_SHARED_SECRET=<long random secret>`

Recommended:

- keep `WORKER_SHARED_SECRET` different from any other app secret
- reuse the same `WORKER_SHARED_SECRET` value in Vercel so the frontend can authenticate to Railway

## First deploy checks

After deploy, open the service public URL and test:

- `GET /health`

Expected response:

```json
{"status":"ok"}
```

## Worker contract

See:

- [`docs/railway_worker_contract.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/railway_worker_contract.md)

Current endpoints:

- `GET /health`
- `POST /pipeline/run`
- `GET /pipeline/run/{job_id}`

## Vercel handoff

In Vercel env vars, add:

- `RAILWAY_WORKER_URL=https://<your-service>.up.railway.app`
- `WORKER_SHARED_SECRET=<same secret used in Railway>`

Once those are set, the frontend pipeline route will:

- trigger Railway instead of local Python
- poll Railway job status
- keep local fallback when `RAILWAY_WORKER_URL` is not set

## What still stays local in development

If `RAILWAY_WORKER_URL` is blank:

- Next.js continues to run the Python scripts locally
- this is the intended dev fallback

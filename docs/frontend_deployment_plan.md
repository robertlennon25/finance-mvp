# Frontend Deployment Plan

## Current deployment assumptions

- deploy [`frontend/`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend) to Vercel as the project root
- use Node 20+
- use Supabase for auth and server-side metadata access
- use Railway for remote pipeline execution

## Required Vercel env vars

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_SITE_URL`
- `SUPABASE_STORAGE_BUCKET`
- `RAILWAY_WORKER_URL`
- `WORKER_SHARED_SECRET`

## Important config rules

- `RAILWAY_WORKER_URL` must not have a trailing slash
- `WORKER_SHARED_SECRET` should be a simple alphanumeric string; avoid `#` unless quoted
- Google OAuth redirect URLs must match the actual local/dev port

## Current production caveat

Uploads still write a local dev copy first in the frontend server before syncing to Supabase. That is acceptable for local development, but production should move to storage-first upload handling.

## Safe test order

1. confirm Railway `/health`
2. run local frontend against Railway
3. test an existing deal
4. test a fresh upload
5. only then promote to Vercel preview/production

## Current artifact expectations

For a successful remote run, the frontend may need to read these from Supabase:

- `artifacts/<deal_id>/<deal_id>_review_payload.json`
- `artifacts/<deal_id>/<deal_id>_model_input.json`
- `artifacts/<deal_id>/<deal_id>_manifest.json`
- `artifacts/<deal_id>/<deal_id>_valuation_model.xlsx`
- `artifacts/<deal_id>/<deal_id>_summary.json`
- `artifacts/<deal_id>/<deal_id>_diagnostics.json`

## Planned extension after deploy

After the core Vercel deploy is stable, add a memo-generation path that:

1. accepts `Who is the acquirer?`
2. generates a starter acquisition memo from workbook artifacts
3. shows a preview and download option in the frontend

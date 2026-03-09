# Frontend And Deployment Plan

## Frontend choice

Use `Next.js` for the frontend instead of a bare React SPA.

Reasons:

- natural Vercel deployment target
- easy server routes for filesystem-backed local development
- simple migration path to Supabase Auth and Storage
- easy split between review UI and pipeline API actions

## Current local frontend

The lightweight frontend lives in `frontend/`.

Current responsibilities:

- read review payloads from `data/extractions/resolved/*_review_payload.json`
- list available deals
- show pipeline status
- show selected field values and top candidate options
- show what will eventually be editable in the UI

It is intentionally read-first right now. The next step after wiring Supabase is to add:

- deal creation
- file upload
- override submission
- pipeline trigger buttons

Current local override flow:

- frontend posts to `/api/deals/:dealId/overrides`
- the route writes local override JSON
- the route reruns `resolve` and `prepare` artifacts

This is now the active Supabase seam:

- extracted review payloads still come from local JSON artifacts
- override writes go to the `user_overrides` table in Supabase
- the route still reruns local Python `resolve` and `prepare` commands
- later, replace local Python command execution with a background job trigger

## End-to-end pipeline

### Local mode

1. user drops files in `data/documents/inbox/<deal_id>/`
2. run `python3 run_local_ingestion.py <deal_id>`
3. run `python3 run_chunk_extraction.py <deal_id> --max-chunks N`
4. run `python3 run_resolve_fields.py <deal_id>`
5. run `python3 run_prepare_model_inputs.py <deal_id>`
6. run `python3 run_build_workbook_from_deal.py <deal_id>`

### Future app mode

1. user signs in with Google via Supabase Auth
2. user creates a deal workspace
3. user uploads files
4. files are stored in Supabase Storage
5. backend job copies/processes files into extraction pipeline
6. extracted values are shown in review UI
7. user accepts or overrides fields
8. backend generates workbook and stores it
9. user downloads workbook

## Supabase OAuth plan

Use Google OAuth through Supabase Auth.

Frontend flow:

1. user clicks `Sign in with Google`
2. call `supabase.auth.signInWithOAuth({ provider: "google" })`
3. Supabase handles redirect and session
4. frontend reads session and scopes the user to their deals

Tables to add in Supabase:

- `deals`
- `documents`
- `document_chunks`
- `field_candidates`
- `resolved_fields`
- `user_overrides`
- `generated_workbooks`

Current implemented table:

- `user_overrides`

## Deployment plan

### Vercel

- deploy the `frontend/` directory as the app root
- run the app on Node 20 or newer
- use Vercel project env vars for Supabase public keys
- keep OpenAI and service-role keys only in server env vars

### Backend choice

Short term:

- keep Python extraction/model generation local or on a simple worker box

Medium term:

- either wrap Python commands behind API jobs
- or move orchestration into a small Python service invoked by Vercel routes / queue jobs

## Next implementation steps

1. add frontend route handlers for reading deal data via local filesystem
2. add override editing UI
3. add Supabase client setup
4. add Google sign-in button and auth shell
5. decide whether workbook generation stays Python-only behind a job trigger

Current status:

- Supabase client setup is scaffolded in `frontend/lib/supabase/`
- Google sign-in shell is live in the frontend
- override persistence is wired to Supabase for authenticated users

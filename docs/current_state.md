# Current State

## Product shape

The app now supports:

- Google sign-in through Supabase
- a landing page with `Start your LBO` and `Pick an existing LBO`
- existing-deal browsing
- local file upload into `data/documents/inbox/<deal_id>/`
- extraction pipeline triggers from the frontend
- override review
- workbook generation and download

## What is local-only today

- uploaded documents are stored on local disk
- extraction artifacts are stored on local disk
- workbook output is stored on local disk
- Python pipeline commands are run synchronously from frontend API routes

## What is in Supabase today

- auth sessions
- Google OAuth
- `user_overrides` table for override persistence

## What still needs to move to Supabase

- deal metadata
- document metadata
- uploaded file storage
- usage counters
- cached extraction metadata

## Document access rule

- frontend links should always open documents through app routes such as `/api/deals/<deal_id>/documents/<file_name>`
- do not expose local filesystem paths in the UI
- this route abstraction is the seam that will later switch from local disk to Supabase Storage on Vercel

## Important code areas

- frontend routes and UI: `frontend/`
- extraction and normalization: `document_pipeline/`
- workbook builder: `excel_model/`
- orchestration scripts: `run_*.py`

## Immediate next priorities

1. cache extraction runs and avoid duplicate AI calls
2. add sensible estimate suggestions for suspicious zero inputs
3. add request and upload limits per user
4. move uploaded documents and deal state into Supabase Storage and tables

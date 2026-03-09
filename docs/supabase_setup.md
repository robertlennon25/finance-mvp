# Supabase Setup

## Purpose

Supabase is the auth, database, and storage layer for:

- Google OAuth
- user overrides
- deals metadata
- document metadata
- pipeline run metadata
- uploaded document storage

## Required env vars

Frontend:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_SITE_URL`
- `SUPABASE_STORAGE_BUCKET`

## Setup order

1. Create a Supabase project.
2. Enable Google OAuth in Supabase Auth.
3. Run both SQL migrations in `supabase/migrations/`.
4. Create a private storage bucket named `deal-documents`.
5. Add env vars to `frontend/.env.local`.
6. Restart the frontend.

## Migrations to run

- `supabase/migrations/20260309_create_user_overrides.sql`
- `supabase/migrations/20260309_create_deal_runtime_tables.sql`

## Storage bucket

Recommended bucket name:

- `deal-documents`

Recommended mode:

- private

## What the app currently writes to Supabase

- `user_overrides`
- `deals`
- `documents`
- `pipeline_runs`

The app still keeps local copies for compatibility during development.

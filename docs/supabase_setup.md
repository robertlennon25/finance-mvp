# Supabase Setup

## Current role of Supabase

- Google OAuth
- user override persistence
- deal/document/pipeline metadata
- private storage for uploaded docs and remote worker artifacts

## Required dashboard setup

1. create project
2. enable Google provider in Auth
3. run SQL migrations in [`supabase/migrations/`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations)
4. create private bucket `deal-documents`
5. configure redirect URLs for local and deployed frontend

## Current migrations

- [`supabase/migrations/20260309_create_user_overrides.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_user_overrides.sql)
- [`supabase/migrations/20260309_create_deal_runtime_tables.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_deal_runtime_tables.sql)

## Required env vars

Frontend:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_SITE_URL`
- `SUPABASE_STORAGE_BUCKET`

Railway:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

## Current storage usage

Same bucket currently stores:

- uploaded/source documents
- remote worker artifacts

That is acceptable for now because the paths are separated:

- `private/...`
- `artifacts/...`

## Important note

The service-role key is required on the server side for:

- upload sync
- document metadata reads
- remote artifact reads
- worker document and override sync

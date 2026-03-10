# Supabase

This folder holds the SQL migrations and setup notes for the app runtime.

## Active scope

- Google OAuth
- user overrides
- deal metadata
- document metadata
- pipeline run metadata
- usage counters

## Migrations

- [`migrations/20260309_create_user_overrides.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_user_overrides.sql)
- [`migrations/20260309_create_deal_runtime_tables.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_deal_runtime_tables.sql)

## Current app expectations

- private bucket named `deal-documents`
- Google provider enabled
- redirect URLs configured for local and deployed frontend
- service-role key available to frontend server routes and Railway worker

## Important retained context

- worker and frontend currently share the same storage bucket
- remote worker uploads artifacts under `artifacts/<deal_id>/...`
- frontend may read documents and artifacts from Supabase when local files are missing
- workbook-related remote artifacts now include:
  - summary JSON
  - diagnostics JSON
- the planned memo feature should also store memo artifacts in the same bucket hierarchy

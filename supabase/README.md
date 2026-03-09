# Supabase Plan

This folder now holds the initial auth/runtime migrations:

- [`migrations/20260309_create_user_overrides.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_user_overrides.sql)
- [`migrations/20260309_create_deal_runtime_tables.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_deal_runtime_tables.sql)

Current scope:

- Google OAuth through Supabase Auth
- `user_overrides` table keyed by `user_id + deal_id + field_name`
- `deals`, `documents`, `pipeline_runs`, and `usage_counters` tables
- row-level security so users only see their own overrides
- storage bucket for uploaded deal documents

Recommended setup:

1. Create a Supabase project.
2. In Supabase Auth, enable Google as an auth provider.
3. Add Google OAuth credentials in the Supabase dashboard.
4. Run both SQL migrations in the Supabase SQL editor.
5. Create a storage bucket named `deal-documents`.
6. Set the bucket to private.
7. Set these frontend env vars:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `NEXT_PUBLIC_SITE_URL`
   - `SUPABASE_STORAGE_BUCKET`

Notes:

- `SUPABASE_SERVICE_ROLE_KEY` must stay server-only.
- Uploaded documents are now written locally and, when configured, uploaded to Supabase Storage as well.
- Deal/document/pipeline-run metadata can now be written to Supabase through the service-role client.
- The current frontend still reads local review payload JSON for extracted values.

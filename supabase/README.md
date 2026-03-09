# Supabase Plan

This folder now holds the first schema migration for auth-backed override persistence:

- [`migrations/20260309_create_user_overrides.sql`](/Users/robertlennon/Desktop/finance_ai_mvp/supabase/migrations/20260309_create_user_overrides.sql)

Current scope:

- Google OAuth through Supabase Auth
- `user_overrides` table keyed by `user_id + deal_id + field_name`
- row-level security so users only see their own overrides

Recommended setup:

1. Create a Supabase project.
2. In Supabase Auth, enable Google as an auth provider.
3. Add Google OAuth credentials in the Supabase dashboard.
4. Run the SQL migration in the Supabase SQL editor.
5. Set these frontend env vars:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `NEXT_PUBLIC_SITE_URL`

Notes:

- `SUPABASE_SERVICE_ROLE_KEY` must stay server-only.
- The current frontend still reads local review payload JSON for extracted values.
- Only override persistence has moved to Supabase in this pass.

# Frontend

Next.js review/orchestration app for the LBO workflow.

## Responsibilities

- landing page and example-deal library
- upload flow
- document viewing
- extraction and analysis loading screens
- override review UI
- workbook download and results summary
- Supabase-authenticated user actions

## Runtime modes

### Local-only

If `RAILWAY_WORKER_URL` is blank:

- pipeline API routes run local Python commands
- suitable for local development only

### Remote worker

If `RAILWAY_WORKER_URL` is set:

- `/api/deals/[dealId]/pipeline` triggers Railway
- frontend polls worker job status
- review/workbook artifacts are read from Supabase Storage if local files are absent

## Important files

- [`app/page.jsx`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/page.jsx)
- [`app/api/deals/[dealId]/pipeline/route.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js)
- [`app/api/deals/[dealId]/overrides/route.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/overrides/route.js)
- [`app/api/deals/[dealId]/estimates/route.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/estimates/route.js)
- [`lib/server/deal-service.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [`lib/example-deals.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/example-deals.js)
- [`components/pipeline-runner.jsx`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/components/pipeline-runner.jsx)

## Env vars

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_SITE_URL`
- `SUPABASE_STORAGE_BUCKET`
- `RAILWAY_WORKER_URL`
- `WORKER_SHARED_SECRET`

## Local dev

```bash
cd /Users/robertlennon/Desktop/finance_ai_mvp/frontend
nvm use 20
npm install
npm run dev
```

## Known constraints

- Google OAuth redirect must match the actual local port
- stale Node installs can break Next silently; use Node 20 consistently
- remote review and results depend on Supabase artifact fallback, not just local filesystem
- avoid storing secrets with `#` in `.env.local` unless quoted

## Example deal curation

The `Pick an existing LBO` page is now curated only.

Deals appear there only if one of these is true:

- they are listed in [`lib/example-deals.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/example-deals.js)
- their metadata explicitly sets `is_example: true`
- their metadata explicitly sets `visibility: "public_example"`

Discovered local test deals are no longer treated as examples by default.

# Frontend

Next.js review/orchestration app for the LBO workflow.

## Responsibilities

- landing page and example-deal library
- upload flow
- compact manual-entry flow
- document viewing
- extraction and analysis loading screens
- override review UI
- workbook download and results summary
- warnings and diagnostics display
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
- [`components/results-overview.jsx`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/components/results-overview.jsx)

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

## New-deal modes

`/new` now supports two start paths:

- document upload
- direct number entry

The direct-entry path is intentionally compact and still lands on the same review screen, so users can:

- see seeded values
- receive reasonable-estimate suggestions for missing fields
- override anything before running analysis

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

### Fastest way to choose example deals

Edit:

- [`lib/example-deals.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/example-deals.js)

and keep only the deal ids you want publicly visible.

## Current example-deal workflow

Existing LBOs are intentionally separated from the live upload pipeline.

Current behavior:

- library cards open:
  - `/examples/<deal_id>`
- that page is read-only and focused on:
  - summary outputs
  - workbook download
  - supporting source documents
- it does not immediately push the user into extraction or analysis

### How to publish a new example deal right now

1. Run the normal pipeline on a deal until you have:
   - review payload
   - workbook
   - summary/diagnostics artifacts
2. Make sure the documents and artifacts are present in Supabase Storage.
3. Mark the deal as public example:
   - easiest now: add the deal id to [`lib/example-deals.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/example-deals.js)
   - optional metadata path: set `is_example: true` or `visibility: "public_example"`
4. Restart/redeploy the frontend.
5. The deal should appear under `Existing LBOs`.

### Metadata-driven alternative

You can also mark a deal as public by setting local or Supabase metadata to either:

- `is_example: true`
- `visibility: "public_example"`

### Manual Supabase example upload

For an example case you want users to try:

1. create or choose a `deal_id`
2. upload its source documents into the `deal-documents` bucket under:
   - `private/<owner>/<deal_id>/<filename>` for a private/dev copy, or
   - a consistent owner namespace you control for examples
3. make sure remote worker artifacts exist under:
   - `artifacts/<deal_id>/...`
4. add the deal id to [`lib/example-deals.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/example-deals.js)

That is the simplest current way to curate the library before a fuller admin UI exists.

## Planned next feature

The next product feature to build after deploy prep is an AI-generated acquisition memo.

Frontend implications:

- add a new input field:
  - `Who is the acquirer?`
- add a memo generation action after workbook build
- show memo status and starter-template warning
- allow memo download
- later, show workbook screenshots and memo preview in-app

See:

- [`docs/memo_generation_plan.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/memo_generation_plan.md)

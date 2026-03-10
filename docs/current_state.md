# Current State

## Product state

The app currently supports:

- Google sign-in through Supabase
- document upload and example-deal browsing
- direct manual entry of key inputs for a compact no-document start flow
- extraction pipeline triggers from the frontend
- override review and reasonable estimate suggestions
- workbook generation and download
- remote processing through Railway
- deterministic diagnostics for suspicious outputs on the results page

## Current architecture

- frontend: Next.js in [`frontend/`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend)
- worker: FastAPI in [`worker_api/`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api)
- auth/storage/metadata: Supabase
- workbook engine: [`excel_model/`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model)
- extraction pipeline: [`document_pipeline/`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline)

## Current end-to-end pipeline

1. Frontend creates or opens a deal.
2. Documents are stored locally for dev and synced to Supabase Storage when configured.
3. Railway or local Python runs ingestion and creates overlapping chunks.
4. `gpt-4.1-mini` extracts structured candidates chunk by chunk.
5. A document-synthesis pass infers missing core fields from finance-heavy snippets.
6. Resolver:
   - normalizes units
   - scores candidates
   - applies public-company-only web fallback when needed
   - creates deterministic reasonable estimates
   - applies user overrides
7. Prepared review payload is shown in the frontend with:
   - selected value
   - candidate options
   - warnings
   - source URLs
8. Analysis/build writes:
   - workbook
   - summary artifact
   - diagnostics artifact
9. Results page shows key outputs, warnings, and suggested fixes.

## Local vs remote behavior

### Local

- documents are still written to local dev folders
- local scripts can still run directly
- frontend can fall back to local Python if `RAILWAY_WORKER_URL` is blank

### Remote

- Railway pulls documents from Supabase Storage
- worker uploads review/workbook artifacts back to Supabase Storage
- frontend reads cloud artifacts if local files are missing

## Current storage conventions

Supabase bucket:

- `deal-documents`

Paths in active use:

- uploaded/source documents: `private/<user_id_or_anonymous>/<deal_id>/<filename>`
- remote artifacts: `artifacts/<deal_id>/<filename>`

## Important frontend truth

- document links must always go through app routes
- workbook downloads must always go through app routes
- do not expose local filesystem paths in the UI
- example-deal library is now explicit/curated, not inferred from all discovered deals
- example deals are now intended to use a separate read-only page under `/examples/<deal_id>` rather than the live pipeline flow

## Important known constraints

- local upload flow still writes a local copy first; production should move toward storage-first behavior
- local review/update flows should not depend on local `*_field_candidates.json` after a Railway run
- overrides are now best treated as persisted user state, not a trigger to rerun local resolution on the frontend server
- Railway worker must receive `user_id` for analysis runs so it can sync user overrides before build
- web fallback is intentionally limited to public-company-like cases and should not run by default for private-company uploads
- entry year is now reviewable, but most historical rows are still synthetically backfilled from current inputs unless richer history is extracted
- diagnostics are deterministic today; no AI narrative explanation pass exists yet

## Current likely fragile areas

- remote artifact sync and readback
- analysis flow after applying estimates/overrides
- mixed local/remote state for newly created deals
- production upload behavior on Vercel
- sparse-input cases where core fields must be inferred from indirect evidence
- workbook screenshot generation for the planned memo feature

## Files to read first after compaction

1. [`README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/README.md)
2. [`docs/deployment_architecture.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/deployment_architecture.md)
3. [`docs/roadmap.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/roadmap.md)
4. [`frontend/lib/server/deal-service.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
5. [`worker_api/pipeline.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)
6. [`document_pipeline/services/resolve_fields.py`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py)
7. [`document_pipeline/services/diagnostics.py`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/diagnostics.py)

# Retained Context

Read this first after compaction if you need the minimum safe context.

## Product truth

- Excel is the canonical model engine
- Python is the pipeline and workbook builder
- Next.js is the user-facing review/orchestration layer
- Supabase is auth + metadata + storage
- Railway is the remote execution layer

## Most important live constraints

- remote jobs do not share the frontend filesystem
- therefore remote artifacts must be uploaded to Supabase and read back from there
- overrides are persisted state, not just transient frontend values
- user overrides must be available to the worker before analysis/build
- diagnostics are written during workbook build and shown on the final results page
- the next planned feature is memo generation from structured artifacts, not from raw documents alone

## Most important files

- [`frontend/lib/server/deal-service.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [`frontend/app/api/deals/[dealId]/pipeline/route.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js)
- [`worker_api/pipeline.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)
- [`worker_api/supabase_sync.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py)
- [`document_pipeline/services/resolve_fields.py`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py)
- [`document_pipeline/services/diagnostics.py`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/diagnostics.py)
- [`excel_model/workbook.py`](/Users/robertlennon/Desktop/finance_ai_mvp/excel_model/workbook.py)
- [`docs/memo_generation_plan.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/memo_generation_plan.md)

## If a bug appears in review or analysis flow

Check these assumptions first:

1. is the frontend using Railway or local Python?
2. do the required artifacts exist locally or in Supabase Storage?
3. is the worker receiving the correct `user_id` and syncing overrides?
4. is the frontend reading fallback cloud artifacts when local files are absent?

## Documentation rule

Whenever architecture changes:

1. update [`README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/README.md)
2. update [`docs/current_state.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/current_state.md)
3. update the nearest module README

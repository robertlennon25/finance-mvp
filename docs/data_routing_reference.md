# Data Routing Reference

This is the single routing/debug document for the pipeline. When something breaks, start here and follow the row for the stage you are in.

## End-to-End Routing

| Stage | Trigger | Main code path | Reads from | Writes to | Primary debug check |
| --- | --- | --- | --- | --- | --- |
| Deal creation from uploads | `POST /api/deals` | [frontend/app/api/deals/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | browser upload | local inbox, Supabase Storage, `deals` table, `documents` table | confirm file exists in `data/documents/inbox/<deal_id>/` and in Supabase `private/...` |
| Deal creation from manual inputs | `POST /api/deals/manual` | [frontend/app/api/deals/manual/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/manual/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | request JSON | manifest, candidates, review payload, model input | confirm `*_field_candidates.json` exists even with zero documents |
| Extraction kickoff | `POST /api/deals/[dealId]/pipeline` with `phase=extract` | [frontend/app/api/deals/[dealId]/pipeline/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | deal id, env config | local Python run or Railway job | check whether `RAILWAY_WORKER_URL` is set |
| Worker job queue | `POST /pipeline/run` | [worker_api/app.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py) | API payload | `data/pipeline_state/worker_jobs/<job_id>.json` | confirm job file is created and `Authorization` matches |
| Document sync on worker | worker phase start | [worker_api/pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py) -> [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py) | `documents` table + Storage | `data/documents/inbox/<deal_id>/` on worker | confirm document metadata row has `storage_path` and file downloads cleanly |
| Ingestion and chunking | local or worker extract run | [document_pipeline/services/local_pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/local_pipeline.py) | `data/documents/inbox/<deal_id>/` | raw doc JSON, chunk JSON, manifest, processed copy | inspect `data/extractions/normalized/<deal_id>_manifest.json` |
| AI extraction | after ingestion | [document_pipeline/services/openai_extraction.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/openai_extraction.py) | manifest chunks, `OPENAI_API_KEY` | raw chunk output, `*_field_candidates.json`, extraction metadata | check `*_extraction_metadata.json` for cache key, chunk count, cache hit |
| Resolve and normalize | after extraction | [document_pipeline/services/resolve_fields.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py) | `*_field_candidates.json`, manifest, local overrides | normalized candidates, resolved JSON | inspect `selection_score`, `normalized_value`, and override application |
| Prepare review payload | after resolve | [document_pipeline/services/prepare_model_inputs.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/prepare_model_inputs.py) | resolved JSON, normalized candidates | review payload, model input | confirm selected value and recommended estimate agree with expectations |
| Review UI load | `/deals/[dealId]/review` | [frontend/app/deals/[dealId]/review/page.jsx](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/deals/%5BdealId%5D/review/page.jsx) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | local review payload or Supabase artifact, plus overrides | rendered review table | if numbers look wrong, inspect merged review vs raw review payload |
| Save override | `POST /api/deals/[dealId]/overrides` | [frontend/app/api/deals/[dealId]/overrides/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/overrides/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | field name + value | local override file and optional `user_overrides` rows | confirm override exists in both local JSON and Supabase for signed-in users |
| Apply estimates | `POST /api/deals/[dealId]/estimates` | [frontend/app/api/deals/[dealId]/estimates/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/estimates/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | review payload | overrides state | check that recommended estimates became override values |
| Analysis kickoff | `POST /api/deals/[dealId]/pipeline` with `phase=analysis` | [frontend/app/api/deals/[dealId]/pipeline/route.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/api/deals/%5BdealId%5D/pipeline/route.js) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | overrides and deal id | local analysis run or Railway job | confirm user id is passed for remote override sync |
| Override sync on worker | analysis phase only | [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py) | `user_overrides` table | local override file on worker | confirm `user_id` is not null or no overrides will sync |
| Workbook build | analysis run | [run_build_workbook_from_deal.py](/Users/robertlennon/Desktop/finance_ai_mvp/run_build_workbook_from_deal.py) | `*_model_input.json` | workbook, summary, diagnostics in `outputs/` | confirm model input exists and output files were written |
| Artifact upload from worker | after review prep or workbook build | [worker_api/pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py) -> [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py) | local artifacts | Supabase `artifacts/<deal_id>/...` | verify missing UI data against actual storage object paths |
| Results page load | `/deals/[dealId]/results` | [frontend/app/deals/[dealId]/results/page.jsx](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/deals/%5BdealId%5D/results/page.jsx) -> [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js) | summary/workbook local first or remote fallback | rendered results and workbook link | if workbook link 404s, check both `outputs/` and `artifacts/` |

## Storage Contract

### Local filesystem

- Uploaded source docs: `data/documents/inbox/<deal_id>/<filename>`
- Processed copy: `data/documents/processed/<deal_id>/<filename>`
- Raw document text: `data/extractions/raw/<deal_id>_doc_*.json`
- Raw AI extraction output: `data/extractions/raw/<deal_id>_chunk_candidates_raw.json`
- Manifest: `data/extractions/normalized/<deal_id>_manifest.json`
- Raw candidates: `data/extractions/normalized/<deal_id>_field_candidates.json`
- Normalized candidates: `data/extractions/normalized/<deal_id>_field_candidates_normalized.json`
- Extraction metadata: `data/extractions/normalized/<deal_id>_extraction_metadata.json`
- Overrides: `data/extractions/overrides/<deal_id>_overrides.json`
- Resolved values: `data/extractions/resolved/<deal_id>_resolved.json`
- Review payload: `data/extractions/resolved/<deal_id>_review_payload.json`
- Model input: `data/extractions/resolved/<deal_id>_model_input.json`
- Workbook outputs: `outputs/<deal_id>_valuation_model.xlsx`, `outputs/<deal_id>_summary.json`, `outputs/<deal_id>_diagnostics.json`
- Local run history: `data/pipeline_state/runs/<deal_id>_runs.json`
- Worker job state: `data/pipeline_state/worker_jobs/<job_id>.json`

### Supabase tables

- `deals`: high-level deal metadata
- `documents`: uploaded document metadata, including `storage_path`
- `user_overrides`: per-user overrides
- `pipeline_runs`: recorded run history

### Supabase Storage

- Source documents: `private/<user_id_or_anonymous>/<deal_id>/<filename>`
- Remote artifacts: `artifacts/<deal_id>/<filename>`

## Authority Rules

These are the rules that matter when local and remote state both exist:

- For review payloads and workbook-related artifacts, the frontend can fall back to Supabase artifacts when local files are missing.
- For overrides, signed-in Supabase-backed overrides are preferred over local overrides.
- For worker analysis runs, overrides must be synced down from Supabase before build.
- For workbook downloads, the app prefers the remote artifact when Railway mode is enabled.
- Manual-entry deals still produce the same downstream resolved/model-input artifacts, even though they start without documents.

## Fast Debug Paths

### Issue: extraction never reaches review

Check in this order:

1. `data/documents/inbox/<deal_id>/` has files
2. `data/extractions/normalized/<deal_id>_manifest.json` exists
3. `data/extractions/normalized/<deal_id>_field_candidates.json` exists
4. `data/extractions/resolved/<deal_id>_review_payload.json` exists

### Issue: review page loads but values are wrong

Check in this order:

1. `*_field_candidates_normalized.json`
2. `*_resolved.json`
3. `*_review_payload.json`
4. `*_overrides.json` or `user_overrides`

### Issue: remote run completes but Vercel shows no workbook

Check in this order:

1. worker wrote local `outputs/<deal_id>_valuation_model.xlsx`
2. worker uploaded `artifacts/<deal_id>/<deal_id>_valuation_model.xlsx`
3. Vercel env points at the correct bucket
4. `frontend/lib/server/deal-service.js` can download the artifact

### Issue: overrides appear in review but not in final workbook

Check in this order:

1. override saved in `user_overrides` for the correct `user_id`
2. pipeline analysis request included `user_id`
3. worker synced overrides before analysis
4. `*_model_input.json` reflects the override

## Best Files To Keep Open During Deploy Debugging

- [frontend/lib/server/deal-service.js](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [worker_api/pipeline.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)
- [worker_api/supabase_sync.py](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/supabase_sync.py)
- [document_pipeline/services/resolve_fields.py](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/resolve_fields.py)
- [run_build_workbook_from_deal.py](/Users/robertlennon/Desktop/finance_ai_mvp/run_build_workbook_from_deal.py)

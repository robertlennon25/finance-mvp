# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Finance AI MVP is an AI-assisted LBO (Leveraged Buyout) modeling tool. Users upload acquisition documents (PDFs, CIMs, filings), AI extracts financial metrics, users review/override values, and the system generates institutional-grade Excel workbooks with DCF, LBO, and sensitivity analysis.

## Commands

### Frontend (Next.js)

```bash
cd frontend
nvm use 20
npm install
npm run dev          # http://localhost:3000
npm run build
npm run lint
```

**Required `frontend/.env.local`:**
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_SITE_URL=http://localhost:3000
SUPABASE_STORAGE_BUCKET=deal-documents
RAILWAY_WORKER_URL=         # blank = local Python fallback
WORKER_SHARED_SECRET=
```

### Python Pipeline

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Required `.env.local`:** `OPENAI_API_KEY=sk-...`

Run stages individually by deal ID:
```bash
python3 run_local_ingestion.py <deal_id>
python3 run_chunk_extraction.py <deal_id> --max-chunks 5
python3 run_resolve_fields.py <deal_id>
python3 run_prepare_model_inputs.py <deal_id>
python3 run_build_workbook_from_deal.py <deal_id>
```

### Railway Worker (local test)

```bash
WORKER_SHARED_SECRET=local-secret python3 -m uvicorn worker_api.app:app --reload
```

There is no automated test suite. Verification is done by inspecting intermediate JSON artifacts.

## Architecture

### System Components

| Component | Location | Runs On |
|-----------|----------|---------|
| Frontend | `frontend/` | Vercel |
| Worker API | `worker_api/` | Railway |
| Python Pipeline | `document_pipeline/`, `excel_model/`, `valuation.py` | Railway (prod) or local (dev) |
| Database/Auth | Supabase | Cloud |

When `RAILWAY_WORKER_URL` is blank, the frontend spawns local Python processes directly. In production, it POSTs to Railway and polls for completion.

### Pipeline Stages & Artifacts

```
Upload documents → /data/documents/inbox/<deal_id>/
  ↓ run_local_ingestion.py
/data/extractions/raw/<deal_id>_manifest.json

  ↓ run_chunk_extraction.py  (LLM: gpt-4.1-mini)
/data/extractions/normalized/<deal_id>_field_candidates.json

  ↓ run_resolve_fields.py  (normalization, scoring, estimates, overrides)
/data/extractions/resolved/<deal_id>_review_payload.json

  ↓ run_prepare_model_inputs.py
/data/extractions/resolved/<deal_id>_model_input.json

  ↓ run_build_workbook_from_deal.py  (valuation.py + excel_model/)
/outputs/<deal_id>_valuation_model.xlsx
/outputs/<deal_id>_summary.json
/outputs/<deal_id>_diagnostics.json
```

Manual entry (no documents) skips straight to writing `_field_candidates.json` from the frontend JS form.

### Key Files

- **`frontend/lib/server/deal-service.js`** — all frontend data logic: local/remote branching, artifact precedence (local files preferred over Supabase), override persistence, payloads for `getDealDetail()` and `getDealWorkspace()`
- **`worker_api/pipeline.py`** — job orchestration, phase behavior, artifact upload to Supabase Storage
- **`document_pipeline/services/resolve_fields.py`** — normalization, candidate scoring, estimates, web fallback, override application
- **`document_pipeline/services/prepare_model_inputs.py`** — shapes the review payload consumed by both frontend and workbook builder
- **`valuation.py`** — financial calculations (DCF, LBO, sensitivity); runs separately from `excel_model/` formulas
- **`excel_model/context.py`** + **`excel_model/sheets/`** — openpyxl workbook writer; sheet cross-references can break silently

### Frontend Routes & API

- `/new` → create deal (upload or manual entry)
- `/library` → example deal browser
- `/deals/<deal_id>` → review workspace (`review-workspace.jsx`)
- `/deals/<deal_id>/results` → results + workbook download (`results-overview.jsx`)
- `/examples/<deal_id>` → read-only example view

Key API routes under `frontend/app/api/deals/`:
- `POST /api/deals` (upload), `POST /api/deals/manual`
- `POST /api/deals/[dealId]/pipeline` (trigger), `GET` with `?jobId=` (poll)
- `POST /api/deals/[dealId]/overrides`, `POST .../estimates`
- `GET /api/deals/[dealId]/workbook`

### Override System

Overrides are applied in two places — they are coupled:
- **Python**: `resolve_fields.py` reads local override JSON files at `data/extractions/overrides/<deal_id>_overrides.json`
- **JS**: `deal-service.js` `applyOverridesToReview()` overlays Supabase `user_overrides` table on the review payload

User overrides always win (confidence = 1.0).

### Supabase Tables

`deals`, `documents`, `pipeline_runs`, `usage_counters`, `user_overrides`

Storage paths: `private/<user_id>/<deal_id>/<filename>` (uploads), `artifacts/<deal_id>/<filename>` (results)

## Stabilization Rules (from CODING_GUARDRAILS.md)

This repo is in stabilization mode. Read `CODING_GUARDRAILS.md` and `SYSTEM_CONTRACT.md` before making changes. Key rules:

- Change one subsystem at a time. Do not refactor during bug fixes.
- Do not change chunking and workbook generation in the same patch.
- Do not change Python extraction contracts and frontend consumers together unless the bug is explicitly a contract mismatch.
- Do not change API response shapes without checking all consumers in `frontend/components/` and `frontend/app/`.
- Do not overwrite artifact filenames, Supabase table names, or bucket paths without documenting every caller.
- Before changing code: identify the exact failing stage, the exact artifact that first goes wrong, and whether the run is local fallback, Railway worker, or manual-entry flow.

### Do-Not-Touch Without Careful Review

- `document_pipeline/services/local_pipeline.py` — chunk IDs, manifest shape, fingerprinting feed caching
- `document_pipeline/prompts/extraction.py` — prompt wording affects candidate shape and cache behavior
- `document_pipeline/services/resolve_fields.py` — normalization + scoring + estimates + web fallback + overrides all converge here
- `document_pipeline/services/prepare_model_inputs.py` — both frontend and workbook depend on its output shape
- `frontend/lib/server/deal-service.js` — owns local/remote branching and artifact precedence
- `worker_api/pipeline.py` — phase behavior and artifact upload
- `excel_model/context.py` and `excel_model/sheets/*` — workbook formula cross-references break silently
- `supabase/migrations/*.sql` — schema changes are immediately live

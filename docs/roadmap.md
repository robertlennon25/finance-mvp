# Product Roadmap

## Current goal

Turn the local finance MVP into a usable web product that:

1. accepts uploaded deal documents,
2. extracts and reconciles LBO inputs with GPT-4.1 mini,
3. lets users review or override inputs,
4. generates an Excel workbook,
5. stores the right data in Supabase for reuse and caching.

## Guiding rules

- Excel remains the core modeling engine.
- Python remains the pipeline and workbook generation layer.
- The frontend is the review, upload, and orchestration surface.
- Supabase handles auth first, then storage and app data.
- Avoid repeat AI calls when the same case and same document set have already been processed.

## Phase 1: Safety And Runtime Guardrails

Objective:
Make local/frontend usage safe enough to keep building without leaking secrets or allowing obviously bad requests.

Tasks:

- tighten `.gitignore` for local env files, generated outputs, and stale frontend install artifacts
- add file-count and file-size limits to uploads
- add clearer pipeline error messages in the frontend
- add a persistent roadmap/current-state doc set

Status:

- in progress

## Phase 2: Cached Pipeline Reuse

Objective:
Do not rerun OpenAI extraction when an equivalent case has already been processed.

Tasks:

- fingerprint uploaded documents with hash + size + name
- add extraction metadata including model, schema version, and prompt version
- reuse normalized/resolved outputs when fingerprints match
- surface cache hit status in the UI

Output:

- `deal_runs` or equivalent cache metadata
- frontend notices like `Using cached extraction`

## Phase 3: Sensible Estimates And Missing-Data Warnings

Objective:
Flag suspicious zeros and suggest usable estimates derived from the rest of the case.

Tasks:

- add a resolver layer for `estimated` field candidates
- define nonzero-required or nonzero-expected fields
- add basis strings such as `Derived from 3-year historical capex as % of revenue`
- add `Use reasonable estimates` button on the review screen
- keep estimates distinct from user overrides and direct extraction

Output:

- field state supports `extracted`, `estimated`, and `user_override`
- warnings and estimate acceptance controls in the frontend

## Phase 4: Request Limits And Abuse Controls

Objective:
Prevent runaway usage and make costs predictable.

Tasks:

- limit extraction runs per user per day
- limit workbook generations per user per day
- limit upload storage and total upload bytes per user
- return clear frontend errors when limits are reached

Implementation target:

- Supabase-backed usage counters keyed by `user_id + day`

## Phase 5: Supabase Storage And Deal Metadata

Objective:
Move uploaded files and deal state out of the local filesystem and into cloud-backed storage.

Tasks:

- add `deals` table
- add `documents` table
- store uploaded files in Supabase Storage
- support `private`, `shared`, and `public_example` deal visibility
- allow example deals to be curated by metadata rather than folder conventions

Output:

- you can decide which deals are visible on the site by changing deal metadata

## Phase 6: Final Results Screen And Workbook Summary

Objective:
Show key outputs before download.

Tasks:

- write a workbook summary JSON during generation
- display offer/share price, EV, equity value, MOIC, IRR, leverage, and check status
- support workbook download and later preview of important tabs

## Phase 7: Documentation Pass

Objective:
Make the repo understandable to another engineer or to future-you after compaction.

Tasks:

- rewrite root `README.md`
- add `README.md` files for `frontend/`, `document_pipeline/`, `excel_model/`, and `supabase/`
- add `docs/current_state.md`
- add `docs/open_questions.md`
- document local dev, auth, extraction, workbook flow, and deployment assumptions

## Phase 8: Productionization

Objective:
Prepare for Vercel deployment and a small trusted user base.

Tasks:

- replace synchronous local pipeline triggers with jobs or worker calls
- separate browser-safe and server-only keys cleanly
- add monitoring/logging for extraction and workbook build failures
- validate the end-to-end flow on Vercel with Supabase Auth and Storage

## Suggested execution order

1. finish Phase 1
2. implement Phase 2
3. implement Phase 3
4. implement Phase 4 and Phase 5 together
5. implement Phase 6
6. do Phase 7 before broad sharing
7. then productionize

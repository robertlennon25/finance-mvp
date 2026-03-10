# AI Extraction Implementation Plan

## Purpose

This doc describes the document pipeline design and the assumptions that still matter after the repo moved from a local-only MVP to a `Vercel + Supabase + Railway` shape.

## Stable design choices

- extraction uses `gpt-4.1-mini`
- extraction should be chunk/topic based, not one giant prompt
- review payloads should preserve alternatives, confidence, source references, and warnings
- user overrides must be explicit and higher priority than extracted values
- Excel model should only consume resolved or approved inputs

## Current pipeline stages

1. ingest documents
2. parse raw text/page text
3. chunk documents with overlap
4. extract field candidates chunk by chunk
5. run a document-level synthesis pass over finance-heavy snippets
6. normalize and score candidates
7. resolve selected values
8. prepare:
   - review payload
   - workbook-ready model input

## Current storage outputs

Local dev artifacts:

- `data/extractions/raw/`
- `data/extractions/normalized/`
- `data/extractions/resolved/`
- `data/chunks/`

Remote worker artifacts:

- `artifacts/<deal_id>/<deal_id>_review_payload.json`
- `artifacts/<deal_id>/<deal_id>_model_input.json`
- `artifacts/<deal_id>/<deal_id>_manifest.json`
- `artifacts/<deal_id>/<deal_id>_summary.json`
- `artifacts/<deal_id>/<deal_id>_diagnostics.json`

## Priority order for final values

1. user override
2. resolved extracted value
3. recommended estimate
4. static default

## Important field behavior

Direct extraction targets:

- revenue
- EBITDA
- cash
- debt
- shares outstanding
- tax rate
- capex / NWC assumptions
- debt terms
- comps / precedent multiples

Inference / estimate targets:

- entry multiple
- exit multiple
- margin assumptions
- growth assumptions
- zero-like fields that are implausible in an LBO model
- missing revenue or EBITDA when they can be derived from nearby financial evidence

## Review-layer truth

The review payload is the stable frontend contract.

It should preserve:

- selected value
- alternatives
- warnings
- recommended estimate
- source URLs
- entry year and other timing-sensitive fields

## Important current constraint

Remote review flows should not assume local `*_field_candidates.json` exists.

That means:

- frontend review/override behavior must work from review payloads and persisted overrides
- Railway analysis runs must sync overrides before running resolve/build

## If this area is changed later

Also update:

- [`document_pipeline/README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/README.md)
- [`docs/current_state.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/current_state.md)

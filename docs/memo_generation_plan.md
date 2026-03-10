# Memo Generation Plan

## Goal

After the user has reviewed inputs and generated the Excel workbook, generate a starter acquisition memo that explains why the acquirer may want to buy shares or acquire the company within a suggested range.

This memo is a template, not final investment advice.

## Product requirements

Add a new input:

- `Who is the acquirer?`

Memo output should include:

- target company name
- acquirer name
- proposed acquisition or share-price range
- short investment thesis
- at least one sentence about future growth in the target's sector
- key output references from the model
- workbook screenshots or simplified visual snapshots
- explicit disclaimer that the memo is a starter template and should be reviewed by a human

Users should be able to:

- generate the memo after workbook build
- preview the memo
- download the memo

## Recommended pipeline shape

1. Resolve inputs and generate workbook as today.
2. Build a compact memo context bundle:
   - company name
   - acquirer name
   - key valuation outputs
   - diagnostics
   - selected assumptions
   - source snippets for high-confidence fields
3. Generate screenshots or image snippets from the workbook.
4. Ask OpenAI to draft the memo.
5. Save memo artifacts:
   - markdown or HTML
   - PDF later if desired
   - screenshot images
6. Show preview in frontend and allow download.

## Suggested memo sections

1. Header
   - target
   - acquirer
   - date
   - starter-template label
2. Executive summary
3. Proposed valuation range
4. Strategic rationale
5. Financial support
6. Sector growth outlook
7. Key risks and sensitivities
8. Appendix references to workbook outputs

## AI inputs for the memo prompt

The prompt should be built from structured data, not only raw text.

Include:

- resolved model inputs
- workbook summary JSON
- diagnostics JSON
- selected review sources
- screenshot captions
- acquirer name

Do not ask the model to reverse-engineer the full workbook from scratch.

## Screenshot plan

Short term:

- capture static screenshots from key workbook tabs after build
- likely tabs:
  - cover
  - returns
  - valuation
  - sensitivities

Longer term:

- generate simplified chart images from the summary JSON instead of raw workbook screenshots when possible

## Artifact plan

Store under:

- `artifacts/<deal_id>/<deal_id>_memo.md`
- `artifacts/<deal_id>/<deal_id>_memo.html`
- `artifacts/<deal_id>/<deal_id>_memo_context.json`
- `artifacts/<deal_id>/memo_assets/...`

## Frontend changes needed

1. Add `Who is the acquirer?` input.
2. Add `Generate memo` CTA after workbook completion.
3. Add memo preview screen or panel.
4. Add download button.
5. Label clearly:
   - `Starter template`
   - `Review before use`

## Safety / UX rules

- never present the memo as final investment advice
- if diagnostics are severe, mention them in the memo context or block memo generation until the user acknowledges them
- show which numbers were estimated, web-estimated, or overridden
- preserve source attribution where possible

## Implementation order

1. Add acquirer input to review/results flow.
2. Build memo context JSON from existing artifacts.
3. Add screenshot generation strategy.
4. Add worker endpoint/stage for memo generation.
5. Add frontend preview/download flow.
6. Add optional PDF rendering later.

## Files likely to change

- [`/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/deals/[dealId]/review/page.jsx`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/app/deals/%5BdealId%5D/review/page.jsx)
- [`/Users/robertlennon/Desktop/finance_ai_mvp/frontend/components/results-overview.jsx`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/components/results-overview.jsx)
- [`/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js`](/Users/robertlennon/Desktop/finance_ai_mvp/frontend/lib/server/deal-service.js)
- [`/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/app.py)
- [`/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py`](/Users/robertlennon/Desktop/finance_ai_mvp/worker_api/pipeline.py)
- [`/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/diagnostics.py`](/Users/robertlennon/Desktop/finance_ai_mvp/document_pipeline/services/diagnostics.py)

## Open questions

- how to generate workbook screenshots reliably in Railway
- whether memo should be markdown-first or HTML-first
- whether severe diagnostics should block memo generation or only warn
- whether public-market share-price range and full acquisition-price range should be separate outputs

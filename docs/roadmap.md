# Roadmap

## Immediate stabilization

1. finish remote review and analysis flow end to end
2. ensure overrides and reasonable estimates work cleanly with Railway
3. make results/review pages rely on cloud artifacts safely
4. remove remaining assumptions that local candidate files exist after a remote run
5. make sparse-input extraction more robust so core fields like revenue do not remain zero without an explicit warning

## Near-term product work

1. add per-user request/run limits
2. improve final results screen with key valuation metrics and workbook preview data
3. move uploads to storage-first behavior for production
4. harden error reporting in frontend and worker
5. add an AI-generated acquisition memo flow built from workbook outputs and screenshots

## Medium-term platform work

1. add better Supabase-backed deal/run history
2. avoid duplicate AI calls across equivalent deals using persistent fingerprints
3. store generated workbook metadata formally
4. add example-deal curation through metadata rather than local folder conventions

## Modeling roadmap

1. keep the Excel model modular and institutional
2. extend checks and realism carefully without overcomplicating debt mechanics
3. improve workbook QA and recalc validation

## Documentation rule

Whenever architecture changes materially:

- update [`README.md`](/Users/robertlennon/Desktop/finance_ai_mvp/README.md)
- update [`docs/current_state.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/current_state.md)
- update the nearest module README

Those three are the minimum retained-context set.

## Planned memo feature

The next major product step after deploy prep is a generated acquisition memo.

Target behavior:

1. Add a new user input:
   - `Who is the acquirer?`
2. After workbook build, generate a starter memo using OpenAI.
3. Include:
   - deal overview
   - proposed acquisition/share-price range
   - thesis bullets
   - at least one line on future sector growth
   - workbook screenshots or derived visual snippets
   - explicit note that the memo is a starter template, not final advice
4. Let the user download the memo.

Planning docs:

- [`docs/memo_generation_plan.md`](/Users/robertlennon/Desktop/finance_ai_mvp/docs/memo_generation_plan.md)

---
description: Explains the development workflow for this project. Use when starting work on a bug, new feature, missing event type, or any tax logic change.
---

# How We Work

Follow this process whenever fixing a bug, adding support for a new event type, or changing tax logic.

## Step 1 — Understand the legal ground truth

Before writing any code or tests:

1. Check the relevant file(s) in `reference/` — treat them as authoritative over general knowledge.
   - Loss offsetting / form lines: `reference/tax-law/estg-20-abs6-verlustverrechnung.md`, `reference/tax-forms/anlage-kap-zeilen.md`
   - Investment funds: `reference/investment-tax-law/`
   - Private sales: `reference/tax-law/estg-23-private-veraeusserung.md`
   - Options/derivatives: `reference/tax-law/estg-20-kapitalvermoegen.md`
   - FX / currency: `reference/bmf-guidance/fremdwaehrung-konten.md`
   - Vorabpauschale: `reference/investment-tax-law/invstg-18-vorabpauschale.md`
   - Coverage map: `reference/research/coverage-matrix.md`
2. If the reference files don't cover the topic, search the web (BMF website, gesetze-im-internet.de, dejure.org).
3. Summarise the legal basis before proceeding — one paragraph is enough.

## Step 2 — Write tests first

Write tests that cover **all relevant scenarios** before touching application code:

- Happy path (typical case)
- Edge cases (zero amounts, multi-lot FIFO, cross-year lots, foreign currency, losses)
- Form line mapping (does the result feed the correct `TaxReportingCategory`?)

Tests must reflect the **requirements** (legal rules), not the current implementation. Never fit tests to the code.

### Test structure in this repo

Integration tests use `FifoTestCaseBase` from `tests/support/base.py`:
- Build CSV input data as Python lists and pass them to `self._run_pipeline(...)`
- CSV row helpers: `tests/support/csv_creators.py` — use `create_trades_csv_string`, `create_corporate_actions_csv_string`, etc.
- Expected output: `tests/support/expected.py` — `ScenarioExpectedOutput`, `ExpectedRealizedGainLoss`, `ExpectedAssetEoyState`
- Exchange rates: `tests/support/mock_providers.py` — `MockECBExchangeRateProvider(foreign_to_eur_init_value=...)`
- Assert with `self.assert_results(results, expected)`

See `tests/test_stock_merger_fifo.py` (`TestIntegrationMergerScenarios`) for a complete integration test example with corporate actions.

For FIFO spec and loss offsetting column definitions see `tests/docs/spec_fifo.md`.

Run the tests and confirm they **fail** for the right reason before implementing.

## Step 2.5 — Write an implementation plan before touching code

Before writing any application code, write a concise implementation plan covering:

- Which existing code paths handle the closest analogous case (name the file and function)
- Exactly which files will change and what will change in each
- Why this is the minimal change — what you are deliberately NOT doing
- Any risks or edge cases the implementation must handle

Get the user to confirm the plan before proceeding.

## Step 3 — Minimal implementation

Implement only what is needed to make the failing tests pass:

- No extra abstractions, no future-proofing
- No changes to unrelated code
- Never change pre-existing tests without asking the user first and explaining why it is unavoidable

Run `uv run pytest` and confirm all tests are green.

## Step 4 — Update documentation

After tests are green, update:

1. **PRD** (`PRD.md`) — add the new event type / behaviour to the relevant section
2. **Coverage matrix** (`reference/research/coverage-matrix.md`) — add or update the row
3. **Reference file** (`reference/tax-law/` or `reference/bmf-guidance/`) — extend the engine mapping note if the legal source is already referenced there

Only update docs that are actually affected.

## Step 5 — Check PDF reporting

Ask: does the new event type produce output that should appear in the PDF report?

- If yes: add or update the relevant section in `src/reporting/pdf_generator.py`
- If no: explicitly confirm why no PDF change is needed (e.g. already covered by existing section, or purely internal)

## Quick checklist

- [ ] Legal basis confirmed in `reference/` or via web research
- [ ] Tests written and failing for the right reason
- [ ] Implementation minimal — only what the tests require
- [ ] All tests green
- [ ] PRD updated
- [ ] Coverage matrix updated
- [ ] Reference file engine mapping updated
- [ ] PDF reporting checked and updated if needed

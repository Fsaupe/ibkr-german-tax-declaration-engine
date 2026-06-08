---
description: Explains the development workflow for this project. Use when starting work on a bug, new feature, missing event type, or any tax logic change.
---

# How We Work

Follow this process whenever fixing a bug, adding support for a new event type, or changing tax logic.

## Step 1 — Understand the legal ground truth

Before writing any code or tests:

1.1 Check the relevant file(s) in `reference/` — treat them as authoritative over general knowledge.
   - Loss offsetting / form lines: `reference/tax-law/estg-20-abs6-verlustverrechnung.md`, `reference/tax-forms/anlage-kap-zeilen.md`
   - Investment funds: `reference/investment-tax-law/`
   - Private sales: `reference/tax-law/estg-23-private-veraeusserung.md`
   - Options/derivatives: `reference/tax-law/estg-20-kapitalvermoegen.md`
   - FX / currency: `reference/bmf-guidance/fremdwaehrung-konten.md`
   - Vorabpauschale: `reference/investment-tax-law/invstg-18-vorabpauschale.md`
   - Coverage map: `reference/research/coverage-matrix.md`

1.2 If the reference files don't cover the topic, research the web following `reference/research/research-strategy.md` — it defines the source tier system (Tier 1 primary law like gesetze-im-internet.de/dejure.org/buzer.de → Tier 2 BMF/EStH guidance → Tier 3 forms → Tier 4 BFH/BVerfG → Tier 5 commentary) and the validation protocol (every claim traces to a Tier 1 or Tier 2 source; cite exact paragraph/Satz; verify form lines against the specific tax year's form). Prefer verbatim statute text over secondary summaries, and never rely on Tier 5 commentary as the sole source.

1.3 When a topic warrants it, capture the finding as a new/updated file in `reference/` under the structure documented in `research-strategy.md`, and update `reference/research/coverage-matrix.md`. Write reference files as **legal ground truth** — what the law requires and the correct engine mapping (the target state). Do not hedge them with the engine's current behaviour or "known gap / not yet implemented" notes: if you're fixing it, state it as it should be and make the code match; the reference is the spec, not a status report.

1.4 Summarise the legal basis before proceeding — one paragraph is enough, anchored to the exact paragraph and sentence.

## Step 2 — Write an implementation plan before touching code

Once the legal basis is clear, and **before writing tests or application code**, write a concise implementation plan covering:

2.1 Which existing code paths handle the closest analogous case (name the file and function).

2.2 Exactly which files will change and what will change in each.

2.3 Why this is the minimal change — what you are deliberately NOT doing.

2.4 Any risks or edge cases the implementation must handle.

2.5 Get the user to confirm the plan before proceeding. The plan settles the seams the tests will target, so it comes first — but it never dictates what the tests assert (that's the requirements' job, Step 3).

## Step 3 — Write tests before implementation

With the plan confirmed, write the tests before touching application code. The plan may inform **which seam** a test targets; the **assertions** still come from the requirements, never the intended implementation.

3.1 Write tests that cover **all relevant scenarios**:
   - Happy path (typical case)
   - Edge cases (zero amounts, multi-lot FIFO, cross-year lots, foreign currency, losses)
   - Form line mapping (does the result feed the correct `TaxReportingCategory`?)

3.2 Tests must reflect the **requirements** (legal rules), not the current or intended implementation. Never fit tests to the code.

3.3 Match test fixtures to the repo's real input conventions before inventing values — units vs. totals, **bond prices quoted as % of par** (the engine divides bond gross by 100, so a fixture price is `98.00`, not `0.98`), currency, percentage quoting. Check the parser or a real CSV; a fixture that misrepresents the data tests nothing useful.

3.4 Follow the repo's test structure. Integration tests use `FifoTestCaseBase` from `tests/support/base.py`:
   - Build CSV input data as Python lists and pass them to `self._run_pipeline(...)`
   - CSV row helpers: `tests/support/csv_creators.py` — `create_trades_csv_string`, `create_corporate_actions_csv_string`, etc.
   - Expected output: `tests/support/expected.py` — `ScenarioExpectedOutput`, `ExpectedRealizedGainLoss`, `ExpectedAssetEoyState`
   - Exchange rates: `tests/support/mock_providers.py` — `MockECBExchangeRateProvider(foreign_to_eur_init_value=...)`
   - Assert with `self.assert_results(results, expected)`
   - See `tests/test_stock_merger_fifo.py` (`TestIntegrationMergerScenarios`) for a complete example, and `tests/docs/spec_fifo.md` for FIFO/loss-offsetting column definitions.

3.5 If you find a gap you are **not** fixing now, lock it with an `xfail` test instead of leaving it untested: `strict=True` for a clear bug (it flips to XPASS and forces removal once fixed), `strict=False` for an undecided design/convention. Do not change a pre-existing passing test to do this.

3.6 Run the tests and confirm they **fail** for the right reason before implementing.

## Step 4 — Minimal implementation

4.1 Implement only what is needed to make the failing tests pass:
   - No extra abstractions, no future-proofing
   - No changes to unrelated code
   - Never change pre-existing tests without asking the user first and explaining why it is unavoidable

4.2 Trace the real code path; don't infer behaviour from names. For synthetic events, verify the `FinancialEventType` against the dispatch table in `src/engine/calculation_engine.py` — `FinancialEventType` (input, e.g. `TRADE_SELL_LONG`) is not the same as `RealizationType` (output label, e.g. `LONG_POSITION_SALE`). When data is missing from the source files, reuse the existing interactive-cache pattern (`AssetClassifier` / `FundSoyNavProvider`) rather than inventing a new mechanism.

4.3 Run `uv run pytest` and confirm all tests are green.

4.4 Verify end-to-end on real data when feasible, and cross-check key figures against an independent source (e.g. a hand calculation, or an official NAV against the broker's price). This is a tax tool: never present or persist a fabricated/unverified figure — no placeholder values left in caches or reports, and any number that could reach a tax return must trace to a cited source.

## Step 5 — Update documentation

After tests are green, update only the docs that are actually affected:

5.1 **PRD** (`PRD.md`) — add the new event type / behaviour to the relevant section.

5.2 **Coverage matrix** (`reference/research/coverage-matrix.md`) — add or update the row.

5.3 **Reference file** (`reference/tax-law/` or `reference/bmf-guidance/`) — extend the engine mapping note if the legal source is already referenced there.

## Step 6 — Check reporting (console + PDF)

Ask: does the new event type produce output that should appear in the reports? Check **both** `src/reporting/console_reporter.py` and `src/reporting/pdf_generator.py` — they are separate and may need different changes (e.g. a per-item note belongs in the console reporter; a form-line table in the PDF).

6.1 If yes: add or update the relevant section in the affected reporter(s).

6.2 If no: explicitly confirm why no change is needed (e.g. already covered by an existing section that filters by category, or purely internal).

## Quick checklist

- [ ] Legal basis confirmed in `reference/` or via web research
- [ ] Implementation plan confirmed with the user
- [ ] Tests written and failing for the right reason
- [ ] Implementation minimal — only what the tests require
- [ ] All tests green
- [ ] Verified end-to-end on real data; key figures cross-checked against an independent source; no fabricated/placeholder values left behind
- [ ] PRD updated
- [ ] Coverage matrix updated
- [ ] Reference file engine mapping updated
- [ ] Reporting (console + PDF) checked and updated if needed

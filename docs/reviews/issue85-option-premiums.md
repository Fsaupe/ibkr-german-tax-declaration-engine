# Issue #85 — option-premium correction

**Completed 2026-09-23:** the maintainer accepted the exact VZ 2023–2025
declaration differences and residual-risk assessment, then instructed:
"ok, accepted. merge and close the issue." The accepted candidate `7b51ef9`
was merged as **`00ba1a724f93bd78039c16fcecdd65e6849e506f`** and pushed
to main. The merge tree equals the candidate exactly. GitHub confirmed #85
**CLOSED/COMPLETED at 10:40:07 UTC**; PM-006 is **Done**.
No unrelated deferred item or local issue #76 work was included.
The earlier checkpoints below retain their historical context; this completion
record supersedes their pending-acceptance/merge status.

Category: **fix-func**. Implementation requested 2026-09-22; verification completed
2026-09-23. Live GitHub main was refreshed as
`a3a3b5c12933d816fa5c93b550d8492c02c03935`. Isolated branch
`fix/issue85-option-premiums`, worktree `/private/tmp/ibkr-issue85-20260922`.
The issue #76 workspace and unrelated edits remain preserved.

## Decisions and scope

The maintainer explicitly retained the existing **trade-date and per-leg FX
convention** and authorised a warning near year-end. A settlement-date redesign
is not part of this fix. The warning covers written-option executions in the
last five calendar days of the current or preceding year; this is a review
window, not a statutory or assumed settlement lag. It changes no dates or figures.

The maintainer also approved the **eight existing fixture corrections** after
being told exactly why they were necessary: two assignments, three short expiries
and three buybacks, including variable FX. The legal requirement decides their
expectations. The new regressions were written and observed failing first.
No new Q4 judicial timing election was made.

At the original implementation checkpoint, publication and merge had not occurred.
The measured declaration differences were subsequently explicitly accepted on
2026-09-23 under review-criteria.md; see the completion record above.

## Implementation

- Writer openings create separate premium income, even if a position stays open
  or only partially closes. Buybacks produce negative Nr. 11 income independently
  of the opening premium. Position flips recognise only the new short portion.
- Assignment closes the option and retains a zero-valued delivery allocation;
  account, quantity, chronology and exact single-consumption checks remain.
  The received premium does not alter the underlying.
- Short expiry creates no additional income. Writer cash settlement creates a
  separate derivative loss, allocated by contract quantity, without including
  the earlier premium.
- Paid holder costs enter the delivered stock/fund calculation through the same
  account-owned premium book in current and historical processing.
- Aggregation keeps negative Nr. 11 income out of derivative losses. Console
  figures and PDF breakdowns use the corrected categories. The PDF includes a
  separate negative-premium subtotal and its contribution to Z22.
- The PDF check exposed a one-cent false discrepancy from mixing a rounded
  derivative subtotal with unrounded other losses. Reconciliation now sums the
  unrounded components and rounds once; declaration arithmetic is unchanged.
  The section heading stays with the first table rows.

## Requirements and input

Reference preparation was committed first as **620114c**. GT-ESTG20-004 specifies
the receipt, buyback, assignment, expiry and cash-settlement distinctions;
GT-ESTG20-070/075 covers holder costs and physical fund delivery.

Protocol: (1) Tier 1/2 anchors; (2) exact sentences and neighbouring scope;
(3) no invented amendment commencement, Q4 preserved; (4) existing verified
per-year forms; (5) no new rate; (6) VZ 2023–2025 and regime floors stated;
(7) judicial timing counterposition explicit; (8) map, active specs and fixtures
updated; (9) reference purity checked. The old Group 8 legal-validation report
preserves its earlier conclusions as an expressly withdrawn historical audit,
not as current requirements.

The 2021–2025 exports contain **1,683 option rows** (55/37/640/526/425).
All have TradeDate, Open/CloseIndicator and IBCommission; no settlement,
report or timestamp date is supplied. There are 614 sell-to-open and 344 ordinary
buy-to-close executions in that history. No new missing-input default was added:
the existing convention was expressly retained after the date issue was raised.

The figures depend on quantity, multiplier, price, signed execution commission,
its currency, transaction tax, the existing per-leg ECB conversion, and the
account/contract/open-close identity. Physical delivery additionally uses the
existing matching terms and FIFO holder costs. Required inputs and conversion
checks are preserved. No supported real-data run newly fails.

## Verification

- Initial new regressions: **7 failed, 1 passed** on unchanged application code.
  The initial three failures isolated writer assignment and historical call cost;
  four further failures established opening/closing/expiry timing.
- New report-rounding regression: **1 failed before correction**, then passed.
- Final dedicated module: **26 passed**, covering open remainders, partial covers,
  flips, prior-year openings, receipt/closing form placement in 2023/2024/2025,
  short expiry, both writer assignments, stock/fund holder cost, all eight
  current/historical fund directions, separate cash settlement, warnings and PDF.
- Existing ownership/partial-delivery tests and all eight approved corrected
  fixture cases pass. Reference integrity: **33 passed**.
- Clean archive of **39eca72**, with template configuration and no private
  exports/caches: **1,599 passed, 1 skipped** in 15.22 seconds. The skip requires
  private exports. Copied-export schema checks: **10 passed**.
- VZ **2023/2024/2025** all complete; independent repeat runs have identical
  normalized console, log and PDF text. Original input/configuration/cache hashes
  remain unchanged.
- Independent reconstruction from raw executions and cached ECB rates reconciles
  **175/227/167 opening premiums** and **143/131/50 buybacks**. No extra or missing
  premium results. FX results and fund-disposal results are identical to baseline.
- Declaration changes: **6/6/3 entries**, confined to KAP Z19–Z24 for 2023/2024
  and Z19/Z20/Z22 for 2025. The remaining **18/18/19 entries** are unchanged.
  Exact amounts are in the private comparison, not this public record.
- Final PDF component checks have no discrepancy; representative changed pages,
  repeated headers and subtotals are visually reviewed. The final real-data
  warning counts are 8/0/2 for VZ 2023/2024/2025, including the preceding-year
  window. The final merge-readiness check below verifies their actual PDF output.

## Completion checkpoint

Implementation and verification were accepted; #85 is closed and PM-006 is Done.
No unrelated deferred item is completed.

Verified application commits: **4d17b0b** plus the PDF warning connection in
**39eca72**. The final warning regression first failed because the PDF's existing
sections did not render arbitrary data gaps; it now checks the actual generated
PDF, including the new warning. Final real-data declaration entries and calculation records match the application
at 4d17b0b exactly. The four-line 39eca72 addition prints the warning in the
2023 and 2025 PDFs and registers its code in the data-gap documentation.
The later fresh captures and visual checks verify that presentation change.
No numerical calculation changed afterward.

The PDF skill prompted visual review of section headings, first table rows and
subtotals. Six representative final pages were rendered; headings, repeated
headers, line wrapping and figures are readable. The synthetic warning is
verified through actual PDF text. The active production/spec/fixture search
finds zero remaining writer-assignment netting or short-expiry recognition
patterns; the old legal-validation report is explicitly marked withdrawn.
No original account identifier appears in staged additions; three matching
round monetary literals belong to the explicitly synthetic fixtures, not
copied portfolio amounts. `git diff --check` passes.

## Closure and knowledge-store review — 2026-09-23

Review-only request; record category **feat-ux**. Live GitHub confirms #85 is
OPEN and main remains `a3a3b5c12933d816fa5c93b550d8492c02c03935`.
The local candidate is `7b51ef9`; its changes after verified application
`39eca72` affect only documentation. The implementation is not on main.

The expanded issue scope is covered by the candidate: separate writer receipts
and buybacks, no second income on expiry/assignment, separate writer cash
settlement, and preserved holder costs across current/historical stock/fund
delivery. Existing account-owned allocation protections remain in use.

Checked the reference additions against the retained BMF 14.05.2025 text,
Rn. 21–35 and 324–325. GT-ESTG20-004 supports the writer lifecycle distinction;
GT-ESTG20-070/075 supports holder costs and physical fund delivery, with the
InvStG provisions explicitly linked. Existing GT-FORM-002/011/012 provides the
year-specific form framework. Reference commit `620114c` precedes application
`4d17b0b`; the index, coverage matrix and implementation map were updated.
The nine-item protocol is accounted for within this scoped review, including
the preserved Q4 counterposition, regime floors and neighbouring source scope.

**Qualification:** actual receipt/payment is the legal timing requirement.
The retained trade-date/per-leg FX convention and 27–31 December warning are
an explicitly accepted implementation limitation, not a sourced equivalence
between trade and payment dates. The reference and implementation map state
that distinction honestly. Q4 remains open; this review makes no new election.
Consequently the substantive correction is supported, but an unqualified claim
that every booking date/FX rate is established by the legal sources is not.

Fresh verification on `7b51ef9`: **103 passed** across the new premium module,
delivery-integrity, lifecycle, variable-FX and reference-purity modules.
Existing evidence remains applicable: clean application suite **1,599 passed,
1 skipped**, copied-export checks **10 passed**. The saved comparison and raw
reconciliation summaries confirm the recorded VZ 2023/2024/2025 coverage and
**6/6/3** changed declaration entries. No new full real-data run was performed
for this review; no application or reference changes were made.

**Disposition:** ready for acceptance under the already retained date convention,
but not yet ready to close as delivered. Explicit approval of the measured
declaration differences and integration into main remain pending. After those
steps, update PM-006 with completion evidence and close #85. This review did
not publish, merge, close the issue or mark PM-006 complete.

### Trade-date evidence clarification — 2026-09-23

No numerical difference attributable specifically to using trade rather than
actual receipt/payment dates has been established. Baseline and candidate both
use TradeDate; their 6/6/3 changed entries do not measure a date-convention change.
The exports supply no independent receipt/payment date for these option trades.
The statutory receipt/payment requirement is explicit, but no specific IBKR
premium has been shown to violate it. A hypothetical other date could change
the assessment year or EUR conversion; that is not a measured error.

**Correction to the earlier zero-warning statements above:** a fresh read of
the original exports finds eight ordinary writer executions on 27–28 December
2022 and two openings on 30 December 2025. The saved candidate-ready,
candidate-final and candidate-reviewed console reports already contain the
warnings: eight cases for VZ 2023's preceding-year window and two for VZ 2025.
The earlier statement of no real-data warning occurrences, and the inference
that the later PDF warning addition could have no real-data presentation effect,
are withdrawn. This correction does not establish a date-related figure error.
The previously recorded PDF absence check is not evidence of zero affected
executions. Application and reference files are unchanged by this clarification.

### Final merge-readiness check — 2026-09-23

The maintainer reaffirmed the established TradeDate decision. No new evidence
shows a superior settlement-date treatment or an incorrect date-driven figure;
the date convention is accepted and is not an additional merge blocker. No new
tax-position decision is required for #85. Q4 remains the existing documented
counterposition, not newly deferred work introduced by this correction.

Fresh isolated runs of candidate `7b51ef9`, with independent repeats, complete
for VZ 2023/2024/2025. All **24/24/22** declaration entries and the complete
captured calculation records equal the previously verified `candidate-ready`
results. Same-tree normalized console/log/PDF text controls pass for every year;
original input, configuration and cache hashes remain unchanged.

The final PDF warning addition is now checked against actual data: the 2023
and 2025 reports contain the warning on pages 15 and 12 respectively; 2024
has no affected execution in its window. Those complete pages were rendered
and visually inspected: headings, warning text and following table rows are
legible without clipping or overlap. All three reports have no component-sum
discrepancy. This closes the verification gap created by the earlier incorrect
zero-occurrence statement. The PDF skill guided this focused visual check.

GitHub main remains `a3a3b5c`; the candidate is clean and `git diff --check`
passes. Existing full-suite and copied-export evidence remains applicable;
no application or test was changed. Remaining decision: explicit acceptance
of the measured 6/6/3 declaration changes versus the old baseline. The exact
comparison is available privately at
`/private/tmp/ibkr-issue85-20260922/private/declaration-comparison.md`.
Merge/publication and issue closure have not been performed or newly authorised
by this readiness question. Unrelated deferred items remain separate.

### Approval case and residual risk — 2026-09-23

Recommendation: approve the measured differences. The previous writer netting
and recognition-at-closure conflict with GT-ESTG20-004; the replacement follows
the explicit BMF distinctions. GT-ESTG20-070/075 preserves the different holder
treatment rather than treating all option premiums alike. Year-specific form
destinations retain the distinction between negative writer income and losses
from cash settlement. The large increases in gross reported income/loss fields
must not be mistaken for equally large changes in economic profit or final tax.

Additional independent input checks were performed for this approval case in
the private `approval_risk_probe.py`, without application changes. A separate
FIFO reconstruction from raw option trades, using cached rates directly,
matches every year-end short-option quantity in the broker snapshots for
VZ 2023/2024/2025. All 12 writer cash-settlement groups in 2025 agree with raw
payments plus fees from their unique same-account assignment companions.
There are no such settlement groups in 2023/2024. No missing opening lot,
ambiguous companion or unmatched ending short holding was needed by this check.

For every year, the change in combined option/stock results reconciles to the
movement in unclosed written premiums plus raw physical-assignment premiums
minus/plus the measured stock-result correction. In 2025, premiums on options
still open at year-end explain the overwhelming majority of the increase;
physical assignments explain the rest after the stock correction. The exact
bridge is private in `approval-risk-probe.json`. This is an accounting bridge,
not a final tax calculation: category restrictions and loss use remain distinct.

Residual risk assessment: low for the central legal classification, because
the operative BMF passages address these transactions explicitly; low to
moderate for implementation on the supplied data, with potentially high
financial impact if an error remains. The confidence is qualitative, not a
measured failure probability. Raw receipt/buyback checks, the new settlement
and ending-inventory checks, red-first regressions and reproducible real-data
runs provide complementary evidence. Repeating the engine alone would not.

Coverage is weaker for fund-underlying and unusual multi-account lifecycle
combinations absent from the actual exports: those rely on synthetic boundary
tests. Shared input interpretation and the same cached ECB series also limit
the independence of the checks; no external assessment calculation was used.
Existing documented Q4 interpretation and unrelated deferred work are not
resolved by this approval, and TradeDate is not reopened. No concrete remaining
error was found in the changes being approved. Retaining the old behavior would
retain a demonstrated reference conflict. This recommendation does not itself
record approval or authorise publication/merge.

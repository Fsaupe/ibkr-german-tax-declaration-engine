# Issue #85 — option-premium correction

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

No merge, push, public message or issue closure has been performed. The measured
declaration differences still require approval before merging under review-criteria.md.

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
  repeated headers and subtotals are visually reviewed. No actual writer trades
  trigger the boundary warning in these years; synthetic checks cover its
  threshold and emitted PDF text.

## Completion checkpoint

Local implementation and verification are ready for review. #85 / PM-006 remains
open pending acceptance and merge. No unrelated deferred item is completed.

Verified application commits: **4d17b0b** plus the PDF warning connection in
**39eca72**. The final warning regression first failed because the PDF's existing
sections did not render arbitrary data gaps; it now checks the actual generated
PDF, including the new warning. Final real-data captures match the application
at 4d17b0b exactly. The four-line 39eca72 addition only prints the new warning
when present (zero occurrences in these three real-data runs) and registers its
code in the data-gap documentation. No numerical calculation changed afterward.

The PDF skill prompted visual review of section headings, first table rows and
subtotals. Six representative final pages were rendered; headings, repeated
headers, line wrapping and figures are readable. The synthetic warning is
verified through actual PDF text. The active production/spec/fixture search
finds zero remaining writer-assignment netting or short-expiry recognition
patterns; the old legal-validation report is explicitly marked withdrawn.
No original account identifier appears in staged additions; three matching
round monetary literals belong to the explicitly synthetic fixtures, not
copied portfolio amounts. `git diff --check` passes.

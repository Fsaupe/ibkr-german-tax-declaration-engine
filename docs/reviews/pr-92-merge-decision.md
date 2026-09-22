# PR #92 — acceptance and merge decision

The maintainer authorized correction, publication and merge on 2026-09-22.
Reviewed head: `111fa2e277e36c65ef51274942df54fc1d35b2e6`.
Accepted base: `c523e6d81437bc9b55fbc094a383a02e33555f87`.
Final code/test revision: **011e4ff2583b28a6fbf644fe721e33d83ced6893**.

## Accepted behavior

- FX gains/losses are itemised and included in the console/PDF component
  breakdowns. Net fund income no longer appears as a KAP component; gross
  KAP-INV detail remains intact.
- The maintainer accepted the Z19 arrow as a contribution, not an assertion
  of equality. Its wording now explicitly says “fließt ein in.”
- The 2025 Z22 breakdown includes derivative losses and reconciles to the
  complete declared figure. The 2023/2024 breakdown retains separate Z24
  treatment. Sections 1 and 2.3 provide matching explanations.
- The final correction separates rule reuse from legal verification.
  GT-FORM-012 records independent verification of the 2022/2023 forms; using
  the 2021 rule entry must not falsely mark their reports unverified.
  The new verification-source mapping suppresses the false log/console/PDF
  warning for those years. Unverified future-year assumptions still warn.
  Existing lookup semantics, calculation rules and pre-existing tests are unchanged
  by this correction.

The requirements remain GT-FORM-002/005/010/011/012 and the fund/FX requirements
already in the knowledge store. No new legal position, claim ID or reference
content was introduced. The GT-FORM-012 map row's implementation explanation and
test links were updated to describe the warning accurately; its position remains
`implements`. This is a documentation correction, not a changed legal mapping.

The [published review](https://github.com/uebber/ibkr-german-tax-declaration-engine/pull/92#issuecomment-5775839215)
and [contributor response](https://github.com/uebber/ibkr-german-tax-declaration-engine/pull/92#issuecomment-5776563141)
were considered. The original Z22 finding and the later false-warning regression
are both resolved. The withdrawn Z19 objection was not reinstated.

## Verification

- Full isolated suite with template configuration and no private inputs/caches:
  **1,527 passed, 1 skipped**. Only documentation follows this code/test revision.
- Copied-export schema checks: **10 passed**.
- New warning regressions: **15 passed**. Against original head `111fa2e`,
  **6 failed / 9 passed**: the failures are precisely the 2022/2023 warning
  assertions for log, console and PDF. The comparison ran from the original
  checkout using an external copy of the tests so imports resolve to that
  original application. No existing test was changed by the correction.
- Independent review checks: **8 passed**, including complete Z22 in
  2023/2024/2025, both section-1 structures, the absence of a false 2023 warning,
  and preservation of an unverified future-year warning.
- Fresh final VZ **2023–2025** captures and same-tree controls complete.
  Normalized console, logs and metadata-stripped PDFs match within each pair.
  Inputs, configuration, curated caches and dependencies match the accepted
  baseline; originals remain preserved.
- Against accepted-main captures, **all declared console entries are identical**
  (24/24/22 for 2023/2024/2025), as are the PDF declared-values tables.
  Every final §2.3 loss total matches the complete Z22 figure. From §2.4 onward
  PDF content is unchanged after whitespace/repeated table headers are
  normalized, preserving order. The final 2023 PDF was rendered and checked:
  the false banner is gone and declared-value/table layout remains readable.
- Report changes are the reviewed FX itemisation, fund-block removal,
  contribution wording and year-specific reconciliation. The warning correction
  changes no declaration figure and introduces no supported-year refusal.
- Both reporters and the log now use the verification decision; the old
  warning-via-`form_rules_are_carried` assumption and stale “silent default”
  prose were searched in the affected source/map and have zero remaining sites.
  `git diff --check` passes. Disclosure cross-check against copied monetary
  columns/account IDs found no account data: four numeric matches were diff
  hunk counters/statutory-reference text, and no account identifier matched.

## Disposition and remaining work

**Accepted with existing follow-up retained.** The maintainer's instruction
authorizes pushing the correction and merging the exact verified head.
PM-001–PM-004 and PM-006 remain open; the pre-existing Zeile-25 deviation remains
separate. This merge does not resolve those tax/architecture gaps or authorize
inventing future-year legal evidence.

Refresh the live head before publication, use a non-forced fast-forward push,
and merge only the verified outgoing head. Record the GitHub-confirmed merge
commit and verify its tree against the candidate. Local issue #76 work and
unrelated user edits remain preserved.

# PR #91 — acceptance and merge decision

Maintainer approval: **2026-09-22**, after the review explanations, measured
declaration changes and purchased-put reconciliation. The maintainer authorized
the two existing-test edits, final verification, publication of corrections and
merge. Acceptance is conditional on the final clean-checkout result below.

Reviewed remote head: eb52abe9d15b968a0620edc5852a35c0783feb15.
Accepted base: adb91322b733c234c0810061d617e4ab5f33e46a.

## Accepted changes

- Transaction taxes enter acquisition cost or reduce disposal proceeds and are
  reflected in the trade's currency movement. The refreshed export schema is
  explicitly migrated; no missing tax values are fabricated.
- Commission credits retain their sign under the supported execution-price
  arrangement. The reference corrects overextended judicial reasoning, restores
  the separate-service qualification, and establishes the amendment/application
  dates. It no longer attributes an unsupported election to the maintainer.
- Zero net sale cash avoids division while separate commission handling continues.
  Negative net cash consumes currency or opens a short, in current processing and
  historical replay. Negative short-security proceeds retain their sign.
- GT-ESTG20-070 distinguishes purchased-put holder exercise from writer assignment.
  Independent raw-input acquisition-cost, FX and FIFO reconstruction explains the
  entire 2023 sign-stage difference through 13 stock-cover portions. The received
  writer-premium exclusion is not applied to the holder's paid option cost.
- With explicit approval, the obsolete short-sale rejection assertion is replaced
  by exact open-lot assertions; the rebate test receives a corrected explanation
  without changes to its numerical expectations.

## Verification and approved differences

The 20 new boundary/replay tests pass; at eb52abe, 14 fail and six pass.
The revised sale-cost module gives one failure/two passes at eb52abe and passes
after correction. Focused final suite including all 10 copied-export schema
checks: 39 passed. Final full clean-checkout verification is recorded below.

Fresh VZ 2023–2025 accepted-main and corrected-candidate runs complete. Both
baseline and candidate same-tree normalized-console and metadata-stripped-PDF
controls match for all three years. Intermediate captures at ccb81f0 and 093d0f4
separate transaction-tax, commission-credit and signed-proceeds corrections.
The maintainer reviewed and approved those measured declaration differences.
No monetary figures or private account identifiers are published here.

The two final test edits and subsequent reference/review records change no
application code, input, configuration, dependencies or report layout. Therefore
the measured application results remain applicable; no new baseline is silently
adopted. Original exports, curated caches, configuration and local issue #76 work
remain preserved.

## Remaining work

PM-001–PM-004 and PM-006 remain open. In particular, the established holder
treatment does not resolve received writer-premium handling, historical or
fund-underlying treatment. Those require the separately recorded correction.
#92 remains a separate review and branch-update task. Merging #91 does not
authorize merging #92 or close deferred work.

## Final verification and publication

**Verified code/test revision: 676ec7f5e1090a1c598478d81233c21d885dd545.**
Full clean checkout, template configuration, no private imports or caches:
**1,500 passed, 1 skipped**. The skip requires private exports; all 10 corresponding
schema checks pass separately on copied exports. The approved replacement test
removes the sole prior failure without changing application code.

Source and dependency files are identical to measured candidate b52bede. The
maintainer's current input and cache directories were compared recursively to the
copied candidate state and match. The fresh 2023–2025 captures and controls remain
applicable. Only review documentation follows this successful verification.

**Disposition: accepted with existing follow-up retained.** Publication and merge
are authorized. Refresh the remote head before the fast-forward push and merge
only that verified outgoing head. Record the merge hash after GitHub confirms it.

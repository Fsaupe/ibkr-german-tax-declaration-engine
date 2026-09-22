# Review and maintenance handoff

Start here after context clearing. Last updated: 2026-09-22.

**#85 implemented locally; measured differences await acceptance.**
Isolated branch `fix/issue85-option-premiums`, base `a3a3b5c`, worktree
`/private/tmp/ibkr-issue85-20260922`. Writer premiums are separate from closing,
assignment and cash settlement; holder costs survive historical/fund delivery.
The maintainer retained trade dates with a boundary warning and approved eight
fixture corrections. Dedicated regressions: 26 passed; reference checks: 33
passed; VZ 2023–2025 runs and repeat controls complete. No merge/publication.
[Implementation and verification](issue85-option-premiums.md).

**#11 merged as `5bc506a`, pushed, and CLOSED/COMPLETED.** The maintainer chose
zero contribution until covering, with a conditional complete year-end inventory
and explicit legal argument/counterargument. Final code `724a27d`, branch
`fix/issue11-short-sale-timing`, base `93b2b0c`. Clean suite: **1,572 passed,
1 skipped**; 14 focused checks; VZ 2023–2025 declared figures unchanged.
All open quantities match raw snapshots; PDF annexes visually checked.
[Authorization, implementation and verification](issue11-disclosed-position.md).
The [legal explanation](https://github.com/uebber/ibkr-german-tax-declaration-engine/issues/11#issuecomment-5784403722)
was published and verified; GitHub confirms closure on 2026-09-22 at 21:24:41 UTC.
Q22 remains legally unresolved; the implementation record contains the completion
checkpoint. Existing deferred work and the local issue #76 branch are preserved.

**Current handoff: #92 accepted for the authorized merge.** Code/test revision
`011e4ff` resolves the false verified-year warning; the Z22/Z24 reconciliation
is complete. Clean suite: **1,527 passed/1 skipped**; 10 export-schema checks
and all 8 independent review checks pass. VZ 2023–2025 declared figures are
unchanged. [Acceptance and verification](pr-92-merge-decision.md).
#91 is merged as `c523e6d`; existing PM-001–PM-004/PM-006 remain open.

**Historical #91 acceptance:** The corrected
code/test candidate 676ec7f passes **1,500 tests, 1 skipped** in a clean checkout;
all 10 copied-export schema checks pass. The maintainer approved the explained
test edits and measured 2023–2025 declaration changes after the purchased-put
reconciliation. [Acceptance and verification](pr-91-merge-decision.md).
Accepted base is main adb9132 (#90). #92 and PM-001–PM-004/PM-006 remain open.
Refresh GitHub for the resulting published/merged revision.

| Document | Purpose |
|---|---|
| [Review criteria](review-criteria.md) | Standing architectural, legal and verification requirements for every PR |
| [PR train](pr-train.md) | Active review, branch-update, correction and merge work for #86-#92 |
| [Post-merge TODOs](post-merge-todos.md) | Accepted architectural follow-up, tracked independently of PR merges |
| [PR #91 acceptance](pr-91-merge-decision.md) | Corrected transaction taxes, commission credits and signed proceeds; verified and approved |
| [PR #86 review](pr-86-review.md) | Findings, reproductions, later-commit checks and final resolution |
| [PR #88 review](pr-88-review.md) | Ordering, option delivery ownership, transfer corrections and final evidence |
| [PR #87 review](pr-87-review.md) | Rework-before-merge findings, later-commit checks and verified local candidate |

Historical handoff (superseded): **#88 and PM-005 are corrected and verified locally** on
`review/pr88-transfers`, implementation `b8b5b11`, based on accepted main
`89e7c24`. The clean suite passes 1,327 tests with one export-dependent skip;
the export schema tests also pass with copied private data. VZ 2023–2025 complete
with identical console/PDF output. See [PR #88 review](pr-88-review.md).
Publishing and merge remain pending confirmation. PM-001–PM-004 remain open.
PM-005 is complete for the existing stock-delivery channel. Separate pre-existing
premium-tax-treatment gaps are recorded as PM-006. The local issue #76 source
has not been integrated.

The PR train is authoritative for review/merge status. The post-merge list is
authoritative for deferred-work status. Individual review documents contain the
supporting evidence; they do not maintain competing live TODO lists. The rework
document merged with #86 remains the historical acceptance record.

Temporary checkouts, virtual environments and private captures can be recreated;
they are not required to understand or resume the work. Do not put account data
or private report amounts into these documents. Application regression tests
from #86 are committed on `main` as `tests/test_snapshot_integrity.py`.

# PR #102 resolution and issue #77 test coverage

2026-09-23. The January-snapshot objection in the third review is **withdrawn**.
This corrects the review standard; it is not an approval to claim an amount known
to lack applicable legal support.

## Correction to the review

The BZSt publishes authoritative annual guidance. PR #102 reads the relevant
annual editions, records each value's provenance and qualifications, checks the
treaty chronology, and does not carry an unresearched year's rate forward. The
review identified no intervening national-law change, contrary authority or
incorrect rate. The possibility of an unobserved temporary change that reversed
before the next edition does not, alone, justify withholding all such credits.
The annual source's January date remains a documented evidential limit; it is
not by itself an unresolved credit case requiring exclusion.

Accordingly T1 in the third review is withdrawn as a merge blocker. The
separate country/year/eligibility requirements remain intact: genuinely
unresearched years, unresolved distribution exemptions, missing taxpayer facts
and unsupported income types must still be excluded and listed. No exception
to those requirements was requested or granted.

An isolated attempt to add blanket exclusions was stopped before any application
change or commit. Its reference and map edits were reverted. The final candidate
has **zero changes to src/, reference/, claim IDs or implementation-map rows**
against reviewed head `987462c`. All prior withholding behavior is preserved.

## Issue #77: completed locally

Category: `fix-nonfunc`. Six cases were added to
`tests/test_payment_in_lieu_credit_route.py`; no pre-existing test was modified.
They parse an actual Payment In Lieu row, use the production distribution
collector through the existing Vorabpauschale harness, and check calendar years
2024 and 2025 (assessment years 2025 and 2026):

- A binding Satz-3 cap, including the collected distribution, capped Basisertrag
  and Satz-1 subtraction.
- A non-binding cap, where dropping the distribution changes the final figure.
- A negative payment remaining a fee and entering neither distribution term.

The binding case must observe the intermediate values: removing the payment
from both the cap and subtraction can leave the final result unchanged.
Amounts are invented, with USD cash converted at 0.90 EUR/USD and EUR position
prices. Requirements: GT-INVSTG-059 branch A, GT-INVSTG-010 and the sourced annual
Basiszins at GT-INVSTG-050/053. The accepted attribution is unchanged.

Calibration used [in-process mutations](issue77-mutations.py.txt), never editing
application files. Each mutation was run separately against the six new cases:

| Deliberate defect | Failed | Passed |
|---|---:|---:|
| Filter actual PIL descriptions from the collector | 4 | 2 |
| Remove the distribution from the Satz-3 cap only | 2 | 4 |
| Remove the Satz-1 subtraction only | 4 | 2 |
| Route the parsed positive fund PIL to branch B | 4 | 2 |

Unmutated route file: **14 passed**. Full suite in the isolated checkout with
tracked template configuration and no account data/cache: **1,792 passed,
1 skipped**. Diff check passes. No src/ changes, so the reviewed VZ 2023–2025
captures and comparisons remain applicable; no redundant real-data replay was
needed for a test-only addition. The fresh review had 11 schema/config checks
and 13 independent checks passing, with only line 41 changing against main.

Local branch: `fix/pr102-issue77-tests`, worktree
`/private/tmp/ibkr-pr102-year-coverage-20260923`, based on `987462c`.
GitHub head/base were refreshed unchanged after testing: head `987462c`, base
`3b01d97`; only #78 is linked for automatic closure. #77's completion is local,
not a GitHub closure. No PR update, publication, push or merge was authorized
or performed. The standing acceptance gate for the already measured line-41
and report changes still applies before merge; no new figure change is introduced.

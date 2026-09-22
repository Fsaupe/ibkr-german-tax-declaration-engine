# Issue #67 follow-up: observed empty currency openings

Category: **fix-func**. Base: `f6c9c9196425db38a31e376c387ce7b64094e3b6`, refreshed
from GitHub on 2026-09-22. Local branch: `fix/issue67-currency-openings`.

## Problem and correction

Nine remaining currency discrepancies across VZ 2023–2025 came from historical
reconstruction surviving an observed nearly empty opening. The parser omitted the opening
when both annual endpoints were below 0.01; the reconciler also returned early for an
explicit zero. This allowed the closing balance to decide whether the opening was applied.

The parser now retains every supplied non-EUR/non-summary observation exactly. The
reconciler distinguishes missing from reported zero and clears both long and short lots
when the opening is empty within the existing currency tolerance. It does not create
offsetting positions, invent an acquisition date/rate/basis, or realize a current-year gain
for that historical correction. Retaining a net-zero long/short pair would still corrupt
later FIFO consumption, so both sides are checked by regression tests.

The 0.01 comparison tolerance is unchanged and shared by opening/closing checks. A reported
quantity strictly below that tolerance is represented by an empty opening lot ledger; its
exact raw quantity remains in the snapshot. This numerical convention is explicit and is
not a new statutory exemption. Openings exactly at the boundary remain nonempty.
Nonempty opening adjustments retain their pre-existing policy. A missing opening remains
unknown, and missing closing coverage/current-year mismatches still produce diagnostics.

## Legal basis and nine-item protocol

No reference claim or legal election changes. The existing requirements were read before
implementation: `reference/bmf-guidance/fremdwaehrung-konten.md`, GT-FX-008/009,
BMF 14.05.2025 Rz. 131 paragraph 2, especially its FIFO sentence and distinct-account
Kapitalforderung rule. Those requirements concern actual surviving account holdings;
the numerical tolerance is an engineering convention recorded here, not attributed to BMF.

Protocol check: (1) existing Tier-2 authority; (2) the precise paragraph/sentences and their
interest-bearing-account scope retained; (3) no amendment/repeal premise added; (4) no form
mapping changed; (5) no rate table added or copied; (6) existing temporal scope, actual
verification restricted to VZ 2023–2025; (7) GT-FX-005/006/007/010 elections remain unchanged;
(8) GT-FX-009 map explanation and affected source/test/docs updated; (9) implementation
state remains outside `reference/`. No index or coverage-matrix change is needed because
the store is unchanged. FIFO tests also inspect cost basis and gains, not just net quantity.

## Inputs and remaining limitations

For the measured window, all 34 imported CSVs remain byte-identical. Of the non-EUR cash
rows, 5/10, 7/10 and 10/12 openings in VZ 2023/2024/2025 respectively were previously
omitted by the two-endpoint filter. Nine of these produced currency warnings: CAD/CNH
in 2023, CAD/CHF/CNH in 2024, CAD/CHF/CNH/JPY in 2025. There is one account in this dataset.

Opening quantities are imported; a genuinely absent row supplies no quantity. Current-year
ledger movements matched independently summed input movements in all twelve comparisons
across those four currencies and three years. Their historical input cash identities
already disagree in 2021, plus CNH in 2022; this correction does not determine the missing
old booking or other cause. Those years were inspected only as imported history, never as
assessment-year results. A separate sub-cent CHF input difference remains within tolerance.

The actual input exercises zero-equivalent openings of both signs, historical residues,
and new later activity. Synthetic cases additionally cover exact zero, offsetting long/short
lots, true absence, boundary quantities, and isolation between two accounts. The pre-existing
policy that synthesizes lots for unresolved nonempty openings is not expanded or certified.

## Verification

- Final isolated suite, template configuration, no private data/caches: **1,557 passed,
  1 skipped**. The skip requires private exports.
- Copied-export schema checks: **10 passed**. After the documentation and unused fixture
  metadata cleanup, affected currency/reference tests: **171 passed**.
- New regression module: **30 passed**. Running that final module against unmodified base:
  **22 failed, 8 passed**; failures expose omitted observations, retained historical lots
  or synthetic-rate lookup, and wrong later-disposal behavior.
- With the requested test-input corrections, every pre-existing expected gain/cost remains
  unchanged. Eight Group 7 fixtures now state the nonzero opening their narratives and
  dated history already establish. The historical-transfer test supplies its real invented
  600/400 openings and observes both balances **before** reconciliation. Deliberately
  omitting the historical move in memory produces **one failure** at that new assertion,
  even though opening reconciliation repairs the final quantity. This preserves the test's
  original protection against snapshot masking.
- Full declarations and PDFs complete in **VZ 2023, 2024 and 2025**. Currency mismatches
  fall from **2/3/4 to 0/0/0**; no unreconciled-currency warning is substituted. Securities
  continue to reconcile. No supported-year refusal is introduced.
- Twelve fresh captures (base/candidate, each twice, each year) have identical normalized
  console/log, extracted PDF text and metadata-stripped PDF bytes within their same-tree
  pairs. Configuration, input and starting caches are identical between pairs; source
  originals are unchanged.
- Declared console entries compared: **24/24/22**. Only two entries per year change,
  Anlage KAP Z19 and Z22, through corrected FX results. All other declared entries are
  identical. Exact changes and reports remain private; this record contains no account
  balances or declaration totals. Removing just the two changed form rows, FX gains/losses
  and their component/net subtotals, and resolved mismatch warnings makes the complete
  console output byte-identical to base for every year. PDF text diffs contain the
  corresponding changed FX details, totals and removed mismatch disclosures.
- The old opening-filter identifiers/claims and unused `filtered_as_tiny_balance` fixture
  metadata were searched across source, tests and the active map: **zero remaining sites**.
  The dated March FX report now explicitly points to this correction. `git diff --check`
  passes.
- Staged additions checked against copied monetary columns/account IDs: zero account-ID
  matches. Thirteen numeric overlaps were reviewed as reused synthetic fixture values,
  invented test constants, the existing tolerance or prose/reference numbers; no account
  amounts were copied into the change.

## Authorization and handoff

The maintainer requested the fix. The specific request to correct the eight old fixture
openings and the historical-transfer test received `pl`, interpreted and acknowledged in
the session as “please proceed.” Expected tax values were not fitted to new output.

Implementation and verification are local. This is not a merge/publication authorization
or approval of the measured declaration differences. The hard real-data merge gate still
requires approval of those specific differences before integration. Existing post-merge
work remains open; no issue, PR, remote branch or main branch is changed by this handoff.

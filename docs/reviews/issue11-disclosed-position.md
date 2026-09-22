# Issue #11 — selected disclosed short-sale position

Category: **feat-func**. Base: live GitHub main `93b2b0c`, refreshed 2026-09-22.
Branch: `fix/issue11-short-sale-timing`; local worktree:
`/private/tmp/ibkr-issue11-20260922`. Issue #76 work remains separate.

## Authorization and scope

After the timing research, the maintainer explicitly requested a complete table
of securities shorts open at year-end, zero contribution pending covering in
Z19 and related fields, and the legal argument in the declaration. The follow-up
requires the material only when relevant open positions exist. This supersedes
the earlier unselected/blocked implementation plan. It authorizes the specific
disclosed deviation despite CLAUDE.md's general restriction on positions against
administrative guidance; it is not a finding that the legal sources tie.

The existing cover-year numbers are retained. Original-year attribution remains
the stronger legal reading and Q22's initial amount remains unresolved. The
reference describes the law; the map records this chosen position. The BGH
disclosure principle is not a short-sale timing judgment or a guarantee that a
particular filed return is complete. No merge, publication or issue closure is
authorized by this record.

## Implementation

- Capture immutable short-lot values from the reconciled, account-specific
  ledgers. This covers partial and multi-year positions, no-trade years, flips,
  and the existing split/transfer handling, without a second reporting ledger.
- Retain source/account identity on realized short-cover portions. No gain
  formula, classification, tax year or loss-offsetting arithmetic is changed.
- The console and PDF share the annex's facts and legal text. Both state zero
  contribution for open quantities, the received net proceeds, and actual
  covered results. The PDF uses repeating table headers and escaped identifiers.
- Trigger on actual open securities lots or prior-year shorts covered this year.
  Include same-year covers only when part of a lot still open at year-end.
  Pure same-year round trips, written options, futures, CFDs and currency shorts
  do not trigger this annex. Fund amounts retain their separate KAP-INV routing.
- Remove the old claim that timing cannot change tax liability. State the
  requested interpretation, BMF Rn. 196 counterargument, and request for review.
  Point to supplementary information and the need to file the annex.
- Date the inventory at 31 December. Later covers known at filing and prior
  differing assessments require supplementation/reconciliation by the filer;
  the current input pipeline still ends at the assessment-year boundary.

## Inputs and validation

Inputs are existing account-ledger keys, instrument classification, opening
date/source ID, remaining quantity and allocated net EUR proceeds; current-year
cover portions provide their date/source, quantity, costs and actual result.
Prices and costs use the existing per-leg conversions. Historical placeholder
dates or proceeds are labeled un-reconstructed, never displayed as observed
facts; this disclosure introduces no new fallback or supported-run refusal.
No account data is included in this public record.

The reference preparation was committed first as `736ab06`. The nine checks:
(1) AO §§ 90/150/370 and EStG/BMF are primary anchors; BGH 5 StR 221/99 supports
the procedural distinction; (2) exact sentences/reasons and surrounding scope
are recorded; (3) no new substantive commencement date or 2025-only short rule;
(4) existing verified KAP/KAP-INV mappings, no guessed supplementary line number;
(5) 30% is confined to its sourced withholding role, zero is identified as the
selected contention; (6) VZ 2023–2025 scope; (7) Q22 stays unresolved; (8) the map,
PRD, FIFO specification, README and old PDF disclaimer are brought into step;
(9) no implementation state inside reference. All four added claims have map
rows and the index/coverage table links the source.

## Verification

- Initial disclosure regression module: **8 failed before implementation**,
  all due to the missing pipeline disclosure. A further scope regression was
  **1 failed** before narrowing same-year covers to the relevant opening lot.
- Final targeted module: **14 passed**; covers both actual PDF text
  and console output, empty-section suppression, partial quantities, account
  separation, carried positions and excluded product types.
- Final code revision **724a27d**. Full suite in an isolated clean archive with
  template configuration, no private data/caches and the installed dependencies:
  **1,572 passed, 1 skipped** in 12.53 seconds. The skip requires private exports.
  The first full run exposed an existing source-layout assertion requiring the
  prior-year registry to be the last keyword argument. Reordering the new
  keyword fixed it; no existing test or numerical expectation was modified.
- VZ **2023/2024/2025**: **24/24/22 declared entries unchanged** against accepted
  main `93b2b0c`. Aside from the new notice and annex, the complete console is
  identical. Each candidate and baseline has matching independent same-tree
  console/log/PDF-text controls. The final keyword reorder is output-neutral;
  all captures use the same arguments. All supported runs complete.
- Independently compared the emitted open quantities, grouped by account/ISIN,
  with the raw EoY snapshots: **1/0/3 positions**, represented by **24/0/35 lots**,
  all match. **Zero** missing opening dates/proceeds in those actual open lots.
  All quantities have zero contribution until covering. VZ 2024 still shows
  prior-year covers, despite having no open EoY position.
- All **11** pages of the final added PDF annexes were rendered and inspected:
  readable German category labels, repeated headers, complete rows, no clipped
  text. The PDF skill prompted the heading/layout verification and refinement.
- Original data/configuration/cache hashes remain unchanged. Source search for
  the old asset-set detector identifiers and the old unchanged-tax-liability
  claim: **zero** remaining production sites. `git diff --check` passes.

Private captures and independent verification scripts remain under the worktree's
ignored `private/`; no account identifiers, positions or monetary amounts from
those captures are included here. The final change is locally committed and
verified, **not merged or published**. Issue #11 remains open.

The earlier investigation and research passes are historical;
this record is authoritative for the selected implementation. Q22's unresolved
legal amount is not closed merely because this alternative is implemented.

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
particular filed return is complete. On 2026-09-22 the maintainer explicitly
authorised commit, merge, publication of the legal argument and closure of #11,
then reconfirmed proceeding after the § 43a/§ 44 scope explanation. That approval
covers the conditional disclosure and measured unchanged figures described here.

## Final legal rationale for publication

The 30% rule in § 43a Abs. 2 Satz 7 is a **withholding base**, not a tax rate
or a percentage of year-end market value. Section 44 Abs. 1 Satz 3 and Satz 4
Nr. 1 Buchst. a assigns the relevant securities-sale withholding to the paying
domestic institution. Individuals remain tax debtors under Satz 1; the argument
is not that taxpayers are personally outside the law.

For the foreign-broker case without German withholding, research did not
establish a direct obligation to use that substitute in the individual's
assessment. Section 32d Abs. 3 requires declaration of the income; it does not
import the substitute formula. Abs. 4 instead permits review where withholding
occurred. The project therefore does not insert a 30% substitute into Z19 and
related fields. It gives open quantities zero contribution until covering,
fully discloses their year-end lots and received net proceeds, and recognises
the actual result in the covering year.

This is the maintainer's expressly disclosed requested treatment. Its argument
is the actual-gain formula and the absence of an established direct assessment
substitute; its counterargument is the § 11/original-sale interpretation and
BMF Rn. 196. The disclosure principle in BGH 5 StR 221/99 Rn. 22–25, read with
§§ 90/150/370 AO, permits presentation of a legal disagreement with complete
facts; it does not establish zero as substantively correct. Q22 remains open.
The public explanation is preserved in [issue11-closure-comment.md](issue11-closure-comment.md).

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
verified. Merge, publication and closure are now authorised; their confirmed
outcome is recorded in the completion checkpoint below.

The earlier investigation and research passes are historical;
this record is authoritative for the selected implementation. Q22's unresolved
legal amount is not closed merely because this alternative is implemented.

## Completion checkpoint — 2026-09-22

- Accepted branch head `4318415` was merged into main as
  **`5bc506add5bd433c018260e152c1433835a66178`** and pushed. GitHub confirmed
  the merge tree equals the accepted candidate tree
  `62b4ff24ec644f93e8d7c4c16b84176ed2b1cde4` exactly.
- Application/tests remain identical to verified `724a27d`. The final § 44
  scope clarification changed only reference/documentation; all **32**
  reference-integrity checks passed again. No new figure or report change.
- The [legal explanation](https://github.com/uebber/ibkr-german-tax-declaration-engine/issues/11#issuecomment-5784403722)
  was published and verified text-identical to the saved closing message.
- GitHub confirms **#11 CLOSED / COMPLETED**, at **2026-09-22 21:24:41 UTC**.
  Closure records the implemented selected policy, not original-year tax-law
  compliance or resolution of Q22.
- The main workspace's issue #76 changes and unrelated review work are preserved.
  No other issue or deferred-work item was closed.

# Issue #76 — securities-lending receipts on Anlage SO

Implemented locally on 2026-09-23 on `fix/issue76-current`, based on refreshed
GitHub main `3bd4a2e`. Application/test candidate: `a90b0c1`.
No remote branch publication, merge or issue closure is authorized by this record.

The isolated checkout is `/private/tmp/issue76.yvvgIK/work`. The original
issue #76 checkout, its earlier commits and unrelated edits are preserved.

## Result and scope

SYEP receipts have their own event type, identified by the description because
IBKR also uses `Broker Interest Received` for ordinary interest. They aggregate
outside the §20 pools into Anlage SO Leistungen, with the annual entry line
resolved through GT-FORM-024. Ordinary credit and short-credit interest remain
in Anlage KAP. The Freigrenze and taxpayer-wide loss rules remain out of scope.

The preserved August implementation was integrated into the current account-owned
currency engine. The new event type also enters the shared currency selector:
that selector now controls both ledger discovery and historical collection.
Current-year and historical receipts retain their account and EUR acquisition
basis. The five dispatch sites were enumerated, including the warning suppression
and no-security-ledger paths; enrichment already handles every CashFlowEvent.

The separate preserved `fix-ux` rounding correction explains discrepancies between
independently rounded components and totals without moving declared amounts.
It includes the newer console FX component. PDF visual QA additionally corrected
orphaned SO headings by allowing their tables to paginate with repeated headers.

Stock-award receipts and returns remain manual, as before. Their amounts and
filing position continue to be disclosed. GT-ESTG20-063/067 stay **deviates**;
their open aggregation work is not closed by the new lending-fee line. Stale
claims that no Leistungen line exists were updated in the map, README and code.

## Legal validation

1. GT-ESTG20-049/050 supply the statutory and BMF basis for the fee's category;
   official annual forms supply GT-FORM-024's layout.
2. The reference identifies §22 Nr.3 Satz1 and the neighbouring threshold/loss
   provisions, and distinguishes entry, total and expense lines.
3. The annual line movement is a form-layout change, not a statutory amendment.
4. The preserved independent readings of the 2023, 2024 and 2025 FMS sheets are
   restored, with each annual print identifier and exact URL.
5. Every annual value has its own source; original Anleitung PDFs and their
   transcriptions are included.
6. The Leistungen mapping floor is 2023. Earlier lookup is refused; reporting
   labels an unavailable destination unverified. Existing annual SO warnings
   disclose an unverified future carry.
7. Q14 remains retired. No new filing election or legal interpretation is made.
8. GT-ESTG20-003/049 and GT-FORM-024 map rows, reference index, coverage matrix,
   specifications and live grant-limit descriptions are aligned. The recently
   verified §23 mappings from #79 are retained.
9. Reference text contains law and provenance, not application identifiers.
   Reference-purity checks pass in the full suite.

The store was committed first as `50c5f23`; code follows in `cb7b459`.

## Verification

- The restored fee regression tests on the old behavior: **18 failed, 8 passed**.
  Only the two enum declarations were supplied to permit test collection.
  The old FX-row fixture was adapted to the current required Taxes column.
- Integrated fee tests: **28 passed**, including new current/historical
  two-account cases with deliberately different acquisition costs. They assert
  the spent lot's acquisition date, cost, gain and correct year of income.
- Final full suite in the fresh clone, template `config.py`, no private input
  or cache state: **1,673 passed, 1 skipped**. The skip requires broker exports.
  Existing main-branch tests were not changed. Dependencies were reused from
  the existing Python environment; test source and configuration came from this
  clean checkout.
- VZ **2023, 2024 and 2025**: baseline and final candidate each completed twice
  with copied exports/configuration/caches. Console/log/PDF-text repeat controls
  pass. Original input, configuration and cache hashes are unchanged.
- Baseline application source is main plus the two inert enum declarations
  used for the red tests; there is no enum-value dispatch in `src/`. No parser,
  calculation or reporting behavior is changed in the baseline.
- Every captured realization and trade record is identical. The only changed
  existing console figures are KAP Z19, the other-capital-income balance,
  positive interest and its component total. Each reduction reconciles with
  the new SO amount, subject to independent cent rounding. All other console
  content matches after removing the new SO block and rounding annotations.
- An independent sum of the raw fee rows, using the copied ECB rate cache for
  USD receipts, matches the new declaration amount exactly to the cent in each
  year. Every other PDF declaration-summary amount is identical; the new SO
  amount and annual label match the console.
- Final PDF detail pages for VZ 2023/2025 were rendered and visually checked.
  Headings stay with their tables; descriptions wrap without clipping.
- Diff privacy check: **0 account identifiers**, **0 new unexplained monetary
  collisions**. Nineteen token collisions are unchanged illustrative lines
  from the preserved August test file, not newly copied account values.
- Whitespace checks pass. Searches find no remaining production use of the
  obsolete `ANLAGE_SO_Z54_NET_GV` key and no active claim that the Leistungen
  category is absent. Historical review records retain their dated findings.

## Input contract and measured incidence

Fresh audit of Cash_Transactions 2021–2025: **920 rows**, **35 SYEP receipts**.
By year: 0 / 10 / 9 / 10 / 6. All are positive; every marker occurs on an
interest-typed receipt. Four are USD (two in 2022, two in 2023), the rest EUR.

Description, Type, Amount, SettleDate, CurrencyPrimary and ClientAccountID are
present on **35/35** rows. AssetClass, Symbol, Conid and ISIN are absent on
**35/35**: no instrument allocation is needed for this fee, and the existing
currency asset resolver supplies the cash identity. Amount/date parsing rejects
invalid required values; missing EUR conversion is rejected by the existing
enrichment validation. A negative marked fee is rejected rather than converted
into positive income. No new missing-input substitute was introduced.

The private captures and calculation evidence are under
`/private/tmp/ibkr-issue85-20260922/private/issue76-base` and `issue76-verified`.
Comparison, independent fee-sum, incidence, privacy and visual-QA scripts are
under `/private/tmp/issue76.yvvgIK`. These contain no required public handoff
state; actual account amounts remain outside the repository.

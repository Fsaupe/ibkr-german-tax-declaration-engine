# Legal implementation map

What this engine does about each legal requirement in `reference/`, which module does it, and
which tests would notice if it stopped.

## How to read this

`reference/` states law and nothing else — that is the Purity Rule in CLAUDE.md, and
`tests/test_reference_purity.py` enforces it. **This file is the other side of that split.** Every
normative requirement in the store carries a claim ID tagged on its heading (`GT-<AREA>-<NNN>`),
and every one of those IDs has exactly one row here. The test asserts both directions: a claim
with no row fails, and a row citing a claim that does not exist fails.

The **Position** column takes one of five values, and the distinction matters more than it looks:

| Position | Meaning |
|----------|---------|
| **implements** | The engine acts on the requirement and the result is intended to be correct. |
| **deviates** | The engine does something the requirement does not sanction. A known defect, stated as one. |
| **not reached** | The requirement is real but nothing in the input can trigger it. Not a defect; a scope boundary. |
| **out of scope** | The requirement addresses a taxpayer or asset this engine is not built for. |
| **choice under uncertainty** | No Tier 1 or Tier 2 source settles the point, and the engine has to do *something*. The row records which reading was taken and why; the question stays open in `reference/research/open-legal-questions.md`. **Not a weaker `implements`** — `implements` asserts the result is intended to be correct, and here that cannot be asserted. |

**"not reached" is a claim about the input, and it can go stale.** It means no supported input
produces the event today — not that the event is impossible. When a new input type or asset class
is added, the "not reached" rows are the ones to re-check first.

Where a claim is an **open question**, this file records the reading that was chosen and why.
Both readings and their authorities stay in `reference/research/open-legal-questions.md`. Choosing
is an implementation act; it does not belong in the store.

---

## Anlage KAP — § 20 EStG

### Abs. 1 — current income

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG20-001 | implements | `src/parsers/domain_event_factory.py` → `DIVIDEND_CASH` → `ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE`; a reversed dividend row and the booking it reverses are dropped (`_cancel_reversals`) | `test_dividend_handling.py`, `test_cash_transaction_reversals.py` | Component of Zeile 19. **The income is the dividend credited, once.** Until 2026-09-22 the parser stored every row as a magnitude, so a broker reversal counted as a second dividend. Measured across `Cash_Transactions-{2022..2025}.csv` (no 2021 file is in `data_import/`): one reversal, VZ 2025, matched to its original; the VZ 2025 Zeile 19 fell by exactly two bookings of that dividend, and VZ 2023/2024 are unchanged (parity, issue #78 review). A reversal with no earlier matching row stops the run (`DataIntegrityError`). |
| GT-ESTG20-002 | implements | `src/domain/enums.py` `ANLAGE_KAP_INV_*`; `src/engine/loss_offsetting.py` keeps the KAP-INV pool separate | `test_group6_loss_offsetting.py::TestLossOffsettingFundIsolation` | The hook that sends fund income to Anlage KAP-INV rather than KAP. |
| GT-ESTG20-003 | implements, **except for the securities-lending fee** | `INTEREST_RECEIVED` → `ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE` | `test_group11_cashflow_currency.py` | **Re-decided 2026-08-09 by the issue #75 audit.** Ordinary interest is unaffected. What the audit reached is a slice of this row: the fee for lending securities arrives in the cash export with a type containing *Interest*, so the classifier's substring match books it here — under Nr. 7, whose gate is a *Kapitalforderung*, while what the lender holds is a **Sachforderung** ([GT-ESTG20-046]). Which Einkunftsart takes it is **open question Q14**; Nr. 7 is one of its three readings, and the engine reached it by string match rather than by choosing. Measured 2026-08-09 across `Cash_Transactions-2021.csv`…`Cash_Transactions-2025.csv`: **35** such rows, monthly from 2022-04 to 2025-05, all positive, so a figure is declared under this claim in **VZ 2023, VZ 2024 and VZ 2025**. **Settled 2026-08-09 as § 22 Nr. 3** (Q14 retired), so the fee is not § 20 income at all and leaves this claim entirely — it belongs on Anlage SO, not Zeile 19. Until the `fix-func` at GT-ESTG20-049 lands, the engine still declares it here, which is the deviation. Issue #76. |
| GT-ESTG20-004 | **deviates** | `src/engine/event_processors/option_processor.py`, `trade_processor.py` | `test_options_lifecycle.py` preserves existing expectations; these are not proof of compliance | PR #88 review identified a pre-existing conflict: assignment premiums are folded into stock basis/proceeds although BMF Rz. 26 keeps them separate. Historical/fund-underlying premium handling differs too. PM-005 repairs account ownership and matching, not this tax treatment. A separate `fix-func(engine)` must measure the impact before changing accepted results; no new filing position was chosen. Open question Q4 remains separately recorded below. |
| GT-ESTG20-010 | **not reached**, re-decided 2026-08-09 | — | — | Besondere Entgelte und Vorteile. Position unchanged, ground replaced: superseded note *"No broker input maps to one"*. Satz 1 has **two** alternatives and *an deren Stelle* is where a substitute payment lands if the § 39 AO attribution went to the borrower — [GT-INVSTG-059] branch B. Not reached because the engine takes branch A unconditionally, not because no input could produce one. **Re-audited 2026-09-22:** the ordinary contemporaneous net execution price is covered by GT-ESTG20-069, not a separate benefit under Satz 2. No maintainer election is asserted. Independent refunds/service payments require their own characterisation (Q21). The amendment first applies for VZ 2024; this does not change the existing net execution-price calculation. |
| GT-ESTG20-048 | not reached | — | — | Rn. 83 and Rn. 84: the administration runs a third party's payment connected with a fund holding through Abs. 3 combined with **Abs. 1 Nr. 3**, and applies the Teilfreistellung to it. Nothing in the engine maps to this route today. It is the destination the branch-B follow-up would use, and the reason branch B is not the cliff it looks like: the rate and the Teilfreistellung come out the same as branch A. |
| GT-ESTG20-062 | not reached | — | — | § 22 Nr. 3 Satz 1's subsidiarity clause, Satz 2's 256-Euro Freigrenze, Satz 3 and 4 on losses. No engine behaviour turns on it directly: it is the ground of GT-ESTG20-063 and the reason the receipt side of a share award belongs on Anlage SO. The Freigrenze is a per-Kalenderjahr total across all of a taxpayer's Leistungen, which one broker's files cannot establish, so it is out of scope as GT-ESTG23-009 is; the receipt note in `src/engine/event_processors/stock_award_processor.py` says so and cites both IDs. Satz 3 does not reach a return of awarded shares (negative Einnahmen, GT-ESTG20-067). |
| GT-ESTG20-063 | **deviates** (the receipt is disclosed, not declared — issue #76) | `src/parsers/grants_parser.py` — admits only the three whole `ActivityDescription` strings the supported programme writes (`KNOWN_ACTIVITIES`) and stops the run on any other; `src/parsers/domain_event_factory.py` (`create_events_from_grants`) dispatches on the same three; `src/engine/event_processors/stock_award_processor.py` — records the undeclared receipt | `tests/test_stock_award_scenarios.py::test_a_row_of_another_programme_stops_the_run`, `::test_an_unclassified_activity_kind_stops_the_run`, `::test_an_award_in_the_tax_year_reports_the_receipt_it_does_not_declare` | **Scope: Interactive Brokers' "Refer-A-Friend" share award only.** The store establishes § 22 Nr. 3 for that programme by applying the Veranlassung test to its terms; it is no longer a filing election (Q19 retired). A row of any other programme — in particular a purchase-conditioned one, BMF Rz. 129b ¶2, which is a cost reduction and no income — is refused, not processed as this one. **The deviation:** the receipt is not declared, because the reporting layer has no Anlage SO *Leistungen* category and `reference/tax-forms/anlage-so-zeilen.md` holds no Zeilen for it — issue #76. The run discloses amount, year and destination instead. **Programme identity is confirmed, not assumed:** nothing in the export names the programme, and a different programme writing the same three activity strings cannot be told apart from the text. `ParsingOrchestrator` therefore stops a run whose Grants files hold rows unless `config.STOCK_AWARD_PROGRAMME` is `"IBKR_REFER_A_FRIEND"` — the user's statement, made once and kept in config (`tests/test_stock_award_scenarios.py::TestTheProgrammeIsConfirmedNotAssumed`). An earlier *document only, no input* decision by the contributor was not accepted in review and is withdrawn. |
| GT-ESTG20-064 | **implements** (Q17 Reading B, selected application) | `src/parsers/domain_event_factory.py` (`create_events_from_grants` — an award is dated on `AwardDate`, a vesting on `VestingDate`, a return on `ReportDate`); `src/processing/enrichment.py` (the award row's `Price` converted at the ECB rate of the award date); `src/engine/fifo_manager.py` (`add_lot_for_stock_award`, used by the historical replay and by `src/engine/event_processors/stock_award_processor.py` alike; a vesting is inert) | `tests/test_stock_award_lots.py::test_award_creates_a_lot_on_the_day_the_shares_arrived`, `::test_the_award_lot_is_final_and_no_vesting_operation_exists`; `tests/test_stock_award_scenarios.py::test_a_grant_inside_the_tax_year_creates_its_lot`, `::test_a_vesting_inside_the_tax_year_does_not_move_the_cost`, `::test_an_award_is_dated_on_its_award_date_not_the_broker_s_report_date`; `tests/test_stock_award_position.py::TestAwardPositionDisclosure` | **Maintainer decision, 2026-09-21: award-date receipt/acquisition, superseding the 2026-09-20 vesting instruction.** The maintainer reports actual shares booked into the securities account, not RSUs or claims, and ordinary dividends received, not payments in lieu. These facts support the booking rule in BMF 01.06.2024 Rn. 25; dividends/votes, price risk and a resolutive reclaim corroborate the application as explained at GT-ESTG20-064. This is a reasoned programme-specific filing position, not a statutory election or a claim of a German ruling on IBKR. **Counterargument retained:** BMF Rn. 26 and BFH VI R 37/09 Rn. 17, 20 distinguish contractual holding restrictions from legal impossibility of disposal. Neither contractual origin nor dividends alone decides that distinction; the terms' *void* wording raises the opposing interpretation but the recorded research does not conclusively establish its proprietary effect or require vesting for this programme. Q17 preserves both readings. Lower complexity supports the selected model but is not legal authority; the decision does not rely on the lean-to-the-taxpayer rule or assert absence of negligence. **Consequences:** award-date value and ECB rate supply receipt and basis; vesting is inert; a later reclaim produces a negative receipt at original value. Reading A would instead require actual release-date valuation/FX and no receipt for units reclaimed before release. The pipeline records `STOCK_GRANT_TAX_POSITION` once when grant history exists, and both console and PDF disclose the choice, including historical basis. **Inputs:** `AwardDate`, award `Price`, `CurrencyPrimary`, `Quantity`, account/award identity and award-date ECB rate. Invalid dates, zero quantity, nonpositive award price and failed conversion are refused. The contributor's prior measurement (2026-09-20) found `ReportDate = AwardDate` on every award row; the maintainer's exports contain no Grants files. Vesting prices are not used. Receipt and return amounts remain manual Anlage SO entries under the separately recorded GT-ESTG20-063/067 reporting limitation. |
| GT-ESTG20-065 | **implements** | `src/engine/fifo_manager.py` — the awarded lot's `unit_cost_basis_eur` is the award-day value and is what a later disposal is measured against | `tests/test_stock_award_lots.py::test_the_whole_sequence_leaves_the_broker_s_quantity_and_the_awarded_cost`; `tests/test_stock_award_scenarios.py::test_a_sub_freigrenze_award_still_carries_full_basis` | The value at Zufluss is the Anschaffungskosten: acquisition for consideration (§ 20 Abs. 4 Satz 1, § 255 Abs. 1 Satz 1 HGB), confirmed without regard to taxation of the receipt by BMF 06.03.2025 Rn. 75 and BMF 14.05.2025 Rz. 87 — both analogies, labelled so in the store. **Q16 is retired; this is no longer a filing position.** The earlier *choice under uncertainty* wording and the *what was taxed becomes the basis* rationale are withdrawn. The amount depends on the Zufluss day, so it follows the reading taken at GT-ESTG20-064 (Q17, Reading B, maintainer's decision of 2026-09-21). |
| GT-ESTG20-066 | **implements** | `src/utils/sorting_utils.py` — a `StockAwardEvent` sorts ahead of the day's trades; `src/engine/fifo_manager.py` (`reverse_stock_award_lot`) — a return removes units of its own award's lot at that lot's cost and refuses to remove more than the lot holds | `tests/test_stock_award_scenarios.py::TestASameDayReturnAndSale::test_the_sale_is_measured_against_what_the_return_left` — current year and historical replay, both input row orders | No rule of law orders a same-day return against a disposal, and that is no election (Q18 retired as never a legal question). What the law requires is that each event has its own effect: the return takes its own award's shares at their Anschaffungskosten (GT-ESTG20-067) and the disposal consumes FIFO (GT-ESTG20-012). Shares handed back cannot also be the shares sold, so the sale is measured against what the return left — the order the engine applies. **Engineering fact, kept here and not in the store:** the opposite order could not produce a second figure, because a lot's unit cost is uniform; it could only leave the return short of units, which stops the run. Probed 2026-09-20 by forcing a return after the day's trades: the four parameters of the test above go red with exactly that refusal. The `STOCK_AWARD_REVERSAL_ORDER_ASSUMED` warning is removed — it presented a scheduling convention as something for the reader to assess. **Known blind spot, unchanged:** the sort band alone is not what puts an award event first; its empty transaction id does, so deleting the band leaves the suite green (CLAUDE.md, *Where the suite is blind*). |
| GT-ESTG20-067 | **deviates** (the negative Einnahme is disclosed, not declared — issue #76; the ledger side implements) | `src/engine/fifo_manager.py` (`reverse_stock_award_lot` — removes the returned units at the lot's own cost, produces no `RealizedGainLoss`, and hands that unit cost back); `src/engine/event_processors/stock_award_processor.py` (`_record_undeclared_return` — `STOCK_AWARD_RETURN_NOT_DECLARED` for a return dated inside the processed year) | `tests/test_stock_award_lots.py::test_reversal_takes_units_at_the_awarded_cost_and_realises_nothing`, `::test_reversing_more_than_was_awarded_stops_the_run`; `tests/test_stock_award_scenarios.py::test_a_return_in_the_tax_year_reports_the_negative_receipt_it_does_not_declare`, `::TestAwardedSharesReachTheLedger::test_a_reversal_is_not_a_disposal` | A return after Zufluss is a negative Einnahme of the year of the return (EStH H 22.8; BFH IX R 26/14 Rn. 20 — same Rechtsverhaeltnis, back to the payer, both met by the programme's reclaim), not a retroactive correction (BFH VI R 6/18 Rn. 37-40), in the amount originally brought to account (BFH VI R 17/08 Ls. 2). Q20 is retired. **Ledger side, implemented:** the units leave at their own Anschaffungskosten, nothing is realised, a later disposal sees only the shares retained. **Anlage SO side, the deviation:** no *Leistungen* line exists (issue #76), so the run hands the reader the amount (returned units × the award's unit value, in cents), the year (of the return) and the destination. Calibrated 2026-09-20: deleting the call site, and separately pricing the amount at the return row's own `Price`, each turn the scenario test red. **Input contract:** the award a return belongs to ← the return row's `AwardDate` with its account; units ← `Quantity`; amount ← the lot's own unit cost, never the return row's `Price`. A return naming an award the ledger does not hold, or more units than it holds, stops the run. **Known limit, no figure affected:** the second stop also fires on a legitimate sequence — shares of the same stock bought separately and sold during the lock-up are deemed by FIFO (GT-ESTG20-012) to come out of the older award lot, so a later return can find fewer award units than it names. The store does not say how a return is measured once FIFO has consumed the award's units, so the run stops and says so, and does not take the units from another lot. Zero occurrence in the contributor's files (no separate purchase of the awarded share). Proposed to the maintainer as post-merge follow-up. **Not reached:** the store's *no receipt, no repayment* boundary — the engine applies booking-day Zufluss (GT-ESTG20-064), so every return follows Zufluss; it follows that row's choice (Q17, Reading B, maintainer's decision of 2026-09-21). A return dated before the processed year is applied by the historical replay and discloses nothing, its negative Einnahme having belonged to that earlier year. |
| GT-ESTG20-050 | not reached | — | — | Abs. 3 is accessory: both limbs presuppose Einnahmen of Abs. 1 or 2 for the payment to attach to or replace, and Rn. 83 and Rn. 84 both combine it with a Nummer. No engine behaviour turns on it directly; it is what closes the first step of the order of enquiry at GT-ESTG20-049 and what retired Q14. **The lending terms corroborate the subsumption**, verified 2026-08-09 at the URL cited under GT-INVSTG-059: the fee is earned *"each day that your stock is on loan … on the collateral value for the loan based on market rates"* — measured by the loan and owed whether or not the security yields anything, which is precisely a payment with no Einnahme of Abs. 1 or 2 to be accessory to. |
| GT-ESTG20-049 | **deviates** | `src/parsers/domain_event_factory.py` — the cash-transaction classifier | none; no test asserts anything about a securities-lending fee | The order of enquiry, Abs. 3 → Abs. 1 Nr. 7 → 22 Nr. 3, and **open question Q14**. The engine books the lending fee under **Nr. 7**, and the 2026-08-09 research run **eliminated Nr. 7** — its gate is a Kapitalforderung, and BFH VIII R 7/23 of 22.10.2024 refused Nr. 7 for a fee of this kind even where the asset *was* one. So the engine's destination is a reading no longer available on any of the three, which is why this stays a deviation and not a choice under uncertainty. **§ 22 Nr. 3 EStG, and no longer a choice under uncertainty.** Q14 was retired on 2026-08-09: the order of enquiry runs out before § 20 EStG does. Abs. 3 is accessory — both limbs presuppose Einnahmen of Abs. 1 or 2 for the payment to attach to or replace, and both worked Randziffern combine it with a Nummer ([GT-ESTG20-050]) — and a fee owed for the loan period whether or not the securities yield anything has nothing to attach to. Nr. 7's gate is a Kapitalforderung where a lender holds a Sachforderung, and BFH VIII R 7/23 refused Nr. 7 for such a fee even where the asset *was* one. So following § 22 Nr. 3 is compliance, not selection. **Superseded position, same day: *reading chosen by the taxpayer, against the weight of authority*** — first § 20 Abs. 3, then § 22 Nr. 3; the store had recorded two live readings because Abs. 3 was excluded by argument and no source addressed it. [GT-ESTG20-050] is that source-grounded argument, written down. A collateral consequence worth keeping: Abs. 3 would have needed an instrument attribution the export cannot give — measured 2026-08-09, `AssetClass`, `Symbol`, `Conid` and `ISIN` are empty on all 35 fee rows, so the Nr. 3 share carrying the Teilfreistellung would have been underivable and a permanent data gap. **Follow-up: `fix-func(parsers,reporting)`, issue #76** — the fee stops being an `INTEREST_RECEIVED`, leaves Anlage KAP Zeile 19, and the reporting layer gains an Anlage SO *Einnahmen aus Leistungen* line, which it does not have (only `ANLAGE_SO_Z54_NET_GV`, for § 23). 22 Nr. 3 Satz 2's Freigrenze (GT-ESTG20-062) is out of scope, as GT-ESTG23-009. Measurement at GT-ESTG20-003. |
| GT-ESTG20-021 | out of scope | — | — | Subsidiarity. Everything here assumes Privatvermögen; the engine has no Betriebsvermögen concept. |

**GT-ESTG20-004, open question Q4 — reading chosen: payment date, in every year.** The paid
Glattstellungsprämie is booked as negative income when paid. Reason: it matches the JStG-2024
statutory wording *and* the administration's practice before it (BMF 18.01.2016 Rz. 25 ff., carried
into 19.05.2022 and 14.05.2025), so the amendment's first year of application cannot change the
result and does not need to be established.

It remains contrary to **BFH VIII R 27/21**, which puts the cost in the year the Stillhalterprämie
was received, as a rückwirkendes Ereignis. That route can be the better outcome or the worse one
depending on which year has losses to absorb, so it is a per-case election rather than a rule the
engine should take. **A Stillhalter/Glattstellung pair straddling a year end should be reviewed by
hand**, and the BFH route considered where the earlier year would use the loss.

*Rescoped 2026-08-07 with Q4 itself: this row previously rested part of its reasoning on "no § 52
EStG application rule for Nr. 11 has been located", which was true and beside the point.*

### Attribution of a lent security — § 39 AO, BMF 09.07.2021

The store file is `reference/bmf-guidance/wertpapierdarlehen-zurechnung.md`. **None of these rows is
reached, and for one reason worth stating once:** the criteria are terms of a lending contract —
how long the loan spans the record date, how the total consideration is priced, who votes, how
easily the position can be withdrawn — and the broker export carries none of them. Measured
2026-08-09 across all five years of `data_import/`: a securities loan leaves **no** row in
`Trades-*.csv`, `Positions-*.csv` or `Corporate_Actions-*.csv`; the only trace is the monthly fee
booking. So the Gesamtschau cannot be run from the input at all, by anyone, and the branch has to
be asserted by the taxpayer. That is not a defect in the engine; it is the shape of the input, and
it is why [GT-INVSTG-059] is a deviation rather than a wrong calculation.

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG20-042 | not reached | — | — | § 39 Abs. 1 and Abs. 2 Nr. 1 Satz 1 AO, and Rz. 1's classification of the transaction as a **Sachdarlehen**. No engine behaviour turns on it directly; it is the ground of the four rows below and of GT-ESTG20-049's boundary against Nr. 7. |
| GT-ESTG20-043 | not reached | — | — | Rz. 2, the Grundfall: the borrower is the owner unless the Gesamtschau says otherwise. |
| GT-ESTG20-044 | not reached | — | — | Rz. 4 to 9, the five criteria, and Rz. 4's placement of the burden on the **borrower**. See the paragraph above for why the input cannot reach them. |
| GT-ESTG20-045 | not reached | — | — | Rz. 12: where attribution stays with the lender, *"Die Dividende ist wirtschaftlich dem Darlehensgeber zuzurechnen und bei diesem zu besteuern."* This is the authority for branch A at [GT-INVSTG-059] — the branch whose result the engine currently produces. Recorded with its context caveat in the store: Rz. 12 sits under *Bilanzielle Betrachtung*. |
| GT-ESTG20-046 | not reached | — | — | Rz. 11: no Gewinnrealisierung for the lender on making the loan. Whether a Wertpapierdarlehen realises a disposal for a *private* lender is settled by no located source; the store records the three things pointing away from one as a gap, not a rule. **Deliberately no work opened** — on branch A of [GT-INVSTG-059] the question does not arise, there being no transfer to realise anything. |
| GT-ESTG20-047 | not reached | — | — | BMF 14.05.2025 Rn. 170 to 173. Rn. 170's disposal fiction is § 43 Abs. 1 Satz 4 EStG and Rn. 171/172 address a Kreditinstitut — Steuerabzug machinery a foreign custodian does not perform. Rn. 173 (§ 22 Nr. 3 for a Repozins) is Reading C's authority at Q14 and concerns a different transaction. |

### Abs. 2 — disposals

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG20-005 | implements | `LONG_POSITION_SALE` / `SHORT_POSITION_COVER` on `STOCK` → `ANLAGE_KAP_AKTIEN_GEWINN` / `_VERLUST` | `test_fifo_groups.py`, `test_group6_loss_offsetting.py` | Zeilen 20 and 23. |
| GT-ESTG20-006 | not reached | — | — | Sale of a Dividenden-/Zinsschein detached from the Stammrecht. No event kind, and no broker input produces one. |
| GT-ESTG20-038 | **not yet reached** (the positive definition) / **implements** (the exclusion) | `AssetCategory.SONSTIGE_KAPITALFORDERUNG`; `src/engine/loss_offsetting.py`, `src/engine/fifo_manager.py` route it to Zeile 19/22 | `test_sonstige_kapitalforderung.py::test_gain_feeds_zeile_19`, `::test_loss_feeds_zeile_22` | **Re-decided 2026-08-07 with issue #53.** Rz. 9's *definition* is still unconsumed: `FXCFD` and `CMDTY` fall through to UNKNOWN and no asset class is mapped to a Termingeschaeft by it. Its *exclusion* — *"Zertifikate und Optionsscheine gehören nicht zu den Termingeschäften"* — has moved from **relied on** to **implements**: a Zertifikat or an unallocated spot metal position can now be classified into a category that lands on Zeile 19/22 and is asserted *not* to reach the Termingeschaeft lines. Two limits stand, and neither is closed by #53: the exclusions still have no IBKR asset class of their own, so **a Zertifikat arriving as `STK` is auto-classified `STOCK` and taxed as a share unless the taxpayer classifies it by hand** — see the note on the interactive pass under Q11 — and the positive definition remains unimplemented. **Re-decided 2026-08-08 by the issue #66 audit; position unchanged.** Rn. 8 f., the cross-reference this Randziffer makes for both exclusions, is now recorded: an Optionsschein is a Kapitalforderung under Satz 1 Nr. 7, the same destination as a Zertifikat. **No warrant has ever been traded on this account**, so nothing is implemented for one and nothing needs to be: a warrant arriving as `OPT` would be declared a Termingeschaeft and would not be put to the taxpayer, which is a defect to fix if one is ever bought, not before. |
| GT-ESTG20-007 | implements | option and CFD close/expiry/settlement paths | `test_options_lifecycle.py`, `test_futures.py`, `test_console_reporter_derivatives.py` | Routed by `get_form_rules(tax_year)` — Zeile 21/24 up to VZ 2024, merged into 19/22 from VZ 2025. |
| GT-ESTG20-008 | implements | bond disposals; currency disposals via `FX_*` realization types | `test_bond_maturity.py`, `test_group7_currency_fifo.py` | **Re-decided unchanged 2026-08-08 by the issue #66 audit**, which reached this row only because Rn. 9's Zertifikat exclusion points here and its Optionsschein exclusion now points here too. Nothing about the claim moved. |
| GT-ESTG20-009 | implements | IBKR corporate action `BM` → synthetic sell → `LONG_POSITION_SALE` | `test_bond_maturity.py::TestBondMaturity` | The Einlösung fiction is what makes a redemption at maturity a disposal at all. |


**Q11 — reading chosen: sonstige Kapitalforderung (Reading C), § 20 Abs. 2 Satz 1 Nr. 7 →
Zeile 19/22.** An unallocated spot precious-metal position held at the broker (no expiry, no
underlying, monthly carrying fee) is **not** a Termingeschaeft. It is treated like a Zertifikat.
Chosen by the taxpayer, 2026-08-07; `reference/research/open-legal-questions.md` Q11 records three
readings and no Tier 1/2 source chooses between them.

What supports it, all already in the store:

- **Rz. 9 excludes it from the Termingeschaeft route expressly** — *"Zertifikate und Optionsscheine
  gehören nicht zu den Termingeschäften, vgl. Rn. 8 f."* ([GT-ESTG20-038]). The same Randziffer
  opens by requiring an Options- or Festgeschaeft *"die zeitlich verzögert zu erfüllen sind"*,
  which a rolling position with no maturity does not obviously satisfy.
- **§ 23 is unavailable**: Rz. 57 requires physical backing with an exclusive delivery or proceeds
  claim ([GT-ESTG23-011]) and the broker evidences neither.
- **Nothing located argues against Reading C.** Q11 records that the BFH line cutting against it
  presupposes a delivery claim, which is absent here, so it neither supports nor excludes it.

It is also the taxpayer-favourable reading against Reading A — no derivative ring-fencing, so
losses offset against all capital income rather than sitting in the Termingeschaeft pot with the
pre-2025 cap. **Checked against every condition of the grey-area rule in CLAUDE.md**, since the
rule is unavailable if any one fails: no Tier 1 or Tier 2 source contradicts Reading C, and Rz. 9
positively excludes the alternative; the BMF has not addressed unallocated spot metal at a broker
in any located passage, directly or by implication; the ambiguity is documented rather than
constructed, as three readings each constrained by Tier 4 and none chosen by Tier 1 or Tier 2; and
the taxpayer was asked and decided, on 2026-08-07.

**Superseded, and why it is recorded rather than deleted.** This row previously read *"reading
chosen: Termingeschaeft (Reading A)"*, reasoned as "§ 23 is out, and between the two remaining
readings the Termingeschaeft one was taken" — which treated Reading C as unavailable because the
engine could not express it. That is an implementation constraint standing in for a legal
conclusion, and Rz. 9 points the other way.

**The engine can now express the chosen reading. Issue #53 landed on 2026-08-07**, adding
`AssetCategory.SONSTIGE_KAPITALFORDERUNG` and the dialog option that reaches it, so an
unallocated spot metal position is classifiable as a sonstige Kapitalforderung and its disposals
go to Zeile 19/22 under its own name. `BOND` would have landed the same figures on the same lines
and was **declined as a workaround**: it makes one category mean two unrelated things, and it does
not merely mislabel — a bond's trade price is a percentage of nominal and its gross is divided by
100, which on a metal position understates cost and proceeds by two orders of magnitude. Measured
2026-08-07 on the test scenario in `tests/test_sonstige_kapitalforderung.py`: the same trades give
cost 2000.00 / proceeds 2300.00 / gain 300.00 under the new category and 20.00 / 23.00 / 3.00
under `BOND`.

**What #53 did not do is reclassify anything.** No holding was moved into the new category, and
`preliminary_classify` never returns it — Rz. 57's test is not readable off an IBKR asset class,
so it is asked, never inferred. Recording the answer is the follow-up work, and the sequence is
deliberate: the option had to exist before the interactive pass, or the pass would have forced a
choice among options that were all wrong and written it into the gitignored cache, where a wrong
entry cannot be seen afterwards.

**Which instruments are routed here, and why.** One so far, and it is not yet recorded in any
cache:

| Instrument | Why | Authority |
|---|---|---|
| `CONID:69067924` — `XAUUSD`, IBKR AssetClass `CMDTY`, unallocated spot gold at the broker | Not a Termingeschaeft, not a § 23 asset: no expiry and no delayed settlement, no physical backing and no delivery or proceeds claim | Rz. 9 [GT-ESTG20-038]; Rz. 57 [GT-ESTG23-011]; Q11 Reading C, chosen by the taxpayer 2026-08-07 |

Nothing else in the maintainer's data has been assessed against Rz. 57. **The population that
needs assessing is larger than this row**, and it is not the `CMDTY` rows: a Zertifikat and an
unbacked ETC both arrive as `STK` and auto-classify to `STOCK` with no prompt. VZ 2024 and VZ 2025
have 96 and 239 instruments not in the cache respectively (measured 2026-08-07, issue #53), and
the interactive pass over them is where any further entry to this table will come from.

**Blocker status, measured 2026-08-07.** VZ 2024 no longer stops on `XAUUSD`: with that
classification supplied, the run reaches the next uncached instrument (`ISIN:SG1L1701REC0`) and
stops there. So #53 removed this instrument as a blocker and did not, on its own, unblock the
year — the interactive pass is the remaining step.

**A previous version of this note said the choice lived only in a gitignored cache and that this
row was its sole public record.** That was true, and it was tested the hard way on 2026-08-07 when
the cache was destroyed by the clean-clone protocol: the classification was lost and this row was
what survived. Keep it current for that reason.

### Abs. 4 — gain calculation and lot identification

Holder/writer distinction audited 2026-09-22: GT-ESTG20-004 remains **deviates**
for the received assignment premium. That does not classify the holder's paid
put premium: BMF Rn. 28–29 is separately recorded at GT-ESTG20-070.

| Claim | Position | Module | Guarding tests | Notes |
| GT-ESTG20-070 | **deviates across supported paths; current-year stock-holder path applies the rule** | OptionExerciseProcessor consumes paid option cost; OptionPremiumBook allocates once; TradeProcessor deducts put cost from stock proceeds | test_option_delivery_integrity.py guards allocation; test_sale_tax_currency_boundaries.py guards signed proceeds, not the legal distinction | The 2023 physical-put trace must be assessed under the holder rule, not the writer rule in GT-ESTG20-004. Historical replay/fund-underlying handling remains incomplete under existing PM-006. Follow-up: fix-func(engine), PM-006, apply the holder rule consistently and preserve separation from writer premiums. No application change in this audit. |
|---|---|---|---|---|
| GT-ESTG20-011 | implements | `src/engine/fifo_manager.py` | `test_precision.py`, `test_fifo_groups.py`, `test_sale_costs_exceed_price.py` | Proceeds − costs − basis, all `Decimal` at `INTERNAL_CALCULATION_PRECISION`. **The net proceeds keep their sign.** Until September 2026 `consume_long_lots_for_sale` and `add_short_lot` took their absolute value, so a sale whose costs exceeded its price was booked as having brought in what it had cost, and the loss came out smaller by twice the excess with no error. Abs. 4 Satz 1 sets no floor under the Einnahmen after costs. Both long sales and short lots now retain signed net proceeds; partial covers and historical replay preserve the opening amount. The prior short-lot refusal was an implementation limitation, not a legal requirement, and blocked the maintainer's VZ 2023 option-exercise delivery after its existing premium adjustment. The underlying GT-ESTG20-004 deviation remains separate. `test_sale_tax_currency_boundaries.py` covers current/historical signed short proceeds and tax-cash boundaries; 14 of its 20 cases fail at eb52abe and all pass after correction. The maintainer approved replacing the older refusal assertion on 2026-09-22 after the legal explanation and real-data reconciliation. Its replacement verifies the exact signed proceeds stored on an open short lot; it fails at eb52abe and passes on the corrected candidate. The exercised purchased-put deduction is supported by GT-ESTG20-070; the separate writer-premium deviation remains open. |
| GT-ESTG20-068 | implements | `src/processing/enrichment.py` — the commission and the trade's transaction tax enter `net_proceeds_or_cost_basis_eur`: added to a buy's cost basis, subtracted from a sale's proceeds, each converted on the trade date. Current-year and replayed lots are built from the same enriched events. `src/parsers/domain_event_factory.py` hands the tax over and refuses the shapes with no treatment (positive; non-`STK` row; a trade of zero value), collected, ahead of the option-lifecycle and currency-pair exits. `split_position_flip_event` carries the tax onto both legs | `test_transaction_taxes.py`; `test_raw_model_decimals.py` (a blank `Taxes` is rejected) | **Probed 2026-09-21, one site disabled at a time, bytecode caching off:** buy fold, sale fold, tax-year draw (buy, sale), historical-replay draw (buy, sale), flip split, guard removed, guard blind to currency-pair rows, sign check removed, hand-over removed, unconvertible tax let through — at each of the five sites that hold the tax in EUR, the foreign amount put in its place; and, at each of the three places the buy/sell direction is written out, the short-selling types dropped or swapped; and the refusal of a taxed trade of zero value switched off. 21 of 21 caught. The five were invisible until the fixtures stopped dating taxed trades on a day whose rate is 1, the three until a short sale and its cover were taxed in a scenario; see CLAUDE.md, *Where the suite is blind*. **The currency side is not this claim.** The tax is folded into the trade's one currency movement (a buy pays gross + tax, a sale receives gross − tax) in `trade_processor.py` and in the historical currency replay; how that movement is taxed is GT-FX-007 (Q9), a choice under uncertainty this row neither adds to nor settles. The commission is still drawn as a separate cash-flow expense (Q9 instance b) — pre-existing, same form line, not changed here. Unreachable by construction: `option_processor.py` reads the commission directly and would not see a tax, and no non-`STK` row with one gets past the factory. This claim is also the first citation for the commission capitalisation. A commission **credit** is GT-ESTG20-069's subject. |
| GT-ESTG20-069 | **implements for the supported net execution-price arrangement**, re-decided 2026-09-22 | `src/processing/enrichment.py` preserves the commission sign in acquisition cost and disposal proceeds; current and historical currency processing already preserves the cash sign | `test_commission_rebate.py`; `test_console_trade_report.py` | The input is the contemporaneous signed price for executing each identified trade. IBKR describes tiered pricing as commission plus external venue fees/rebates, explicitly **not** a direct pass-through; discounts may be retained ([pricing disclosure](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php), retrieved 2026-09-21, rechecked 2026-09-22). Ordinary open/close trade rows supply execution pricing and establish no separate service by the customer. Apply the store's attribution test to that arrangement. The earlier assertion of a maintainer election and that an alternative necessarily over-declares/general-pool treatment is withdrawn. A net execution price does not require inventing a split into venue rebate and broker fee. Independent later refunds and remuneration for separate services are outside this input interpretation. Existing behaviour satisfies the revised requirement; no application deviation created by the audit. |
| GT-ESTG20-022 | implements | `src/processing/` EUR conversion at ECB rates; `src/engine/fifo_manager.py` stores per-lot EUR basis | `test_group7_currency_fifo.py`, `test_group9_variable_fx.py`, `test_precision.py` | Abs. 4 Satz 1 Hs. 2 — each leg at its own date. **The statute names no rate source**; the engine uses ECB reference rates, which is a choice no located Tier 1/2 source prescribes for the Veranlagung. BMF 14.05.2025 Rz. 247 prescribes the Devisenbriefkurs only for the Steuerabzug by an inländische Zahlstelle, which does not apply here. |
| GT-ESTG20-023 | implements | derivative close/expiry/settlement paths in `src/engine/event_processors/` | `test_options_lifecycle.py`, `test_futures.py` | Abs. 4 Satz 5 — Differenzausgleich less directly related costs, and the same Satz governs a worthless expiry (BMF Rz. 27). Newly stated in the store; the engine already computed derivative results this way, but the store had only the Abs. 4 Satz 1 formula. |
| GT-ESTG20-024 | out of scope | — | — | Sparer-Pauschbetrag (Abs. 9). Applied by the Finanzamt; the engine reports gross figures and has no representation of Zeilen 16/17. The Satz 1 exclusion of actual Werbungskosten is nonetheless why only directly-related disposal costs reduce a gain — that part *is* how the engine computes. |
| GT-ESTG20-012 | implements | `src/engine/fifo_manager.py` — FIFO lot consumption; `reconcile_with_mark` decides which lots survive each checkpoint | `test_fifo_groups.py`, `test_replay_checkpoint_marks.py`, `tests/docs/spec_fifo.md` | Mandatory fiction; no specific-identification alternative is offered. Which lots a reconciliation keeps is part of it: where the reconstruction exceeds the reported holding the survivors are the **newest**, because FIFO consumed the oldest. Filling from the oldest end (the behaviour before August 2026) returned the wrong lot whenever a ledger held more than one, and the oversell flag previously discarded even an exactly-matching reconstruction. |
| GT-ESTG20-013 | implements | `src/engine/calculation_engine.py` (one FIFO ledger per `(account, asset)`; the historical replay, the tax-year dispatch, the mark reconciliation and the end-of-year check all keyed by account), `src/engine/ledger_views.py`, `src/utils/account_utils.py`, `src/domain/events.py` (`FinancialEvent.account_id`), `src/parsers/domain_event_factory.py` (populated from `ClientAccountID`); `src/processing/option_trade_linker.py` and `src/engine/option_premiums.py` preserve delivery/premium ownership by account | `test_per_account_fifo.py`, `test_ledger_views.py`, `test_multi_account_harness.py`, `test_option_delivery_integrity.py` | Ledgers and premium allocations are account-scoped: a disposal consumes its own account's lots, and same-day option consumption retains chronology so repeated and partial deliveries cannot consume another account's premium. See Q2 below for the chosen reading, the separate GT-ESTG20-004 treatment deviation, and what this does **not** yet cover. |
| GT-ESTG20-061 | implements | `src/parsers/parsing_orchestrator.py` — every account's row recorded, for the opening and closing snapshots, the checkpoint marks, the preceding year's Vorabpauschale snapshots and the cash-balance report; `src/domain/assets.py` — `person_snapshot()` sums them into the person's holding | `test_person_level_snapshot.py` — the opening read, the closing read, a checkpoint mark, the preceding year's three snapshots, a currency held in two accounts, a fund held in two accounts reaching Zeilen 9–13, and the refusal to add two currencies | The taxable subject is the person (§ 2 Abs. 1 S. 1 Nr. 5, § 25 Abs. 1 EStG), so what is declared is the total across that person’s accounts. A Flex Query covering several accounts emits one snapshot row per account; each row was assigned in turn, so the record that survived was whichever the file ended with — one account's holding, presented as the whole. Every snapshot is now recorded under the account that reported it, so the rows cannot overwrite each other, and the person's figure is `person_snapshot()` / `person_mark()` derived from them rather than stored. Any missing additive contribution keeps the total `None`, including mixed populated/blank rows within one account. `test_snapshot_integrity.py` verifies the refusal at opening and checkpoint reconciliation. Price conflicts are retained separately from absence until independently resolved. **Which lot a disposal consumes** is governed by [GT-ESTG20-013]: securities ledgers are now keyed per account. This claim requires aggregation for assessment; it does not authorize pooling lots before account-specific calculations. **For a currency balance, what the store settles is narrower and is worth stating exactly.** [GT-FX-008] gives Rz. 131 verbatim -- FIFO over *gleichartige Fremdwaehrungsbetraege* -- and records that § 20 Abs. 4 Satz 7's *einzelnes Depot* condition cannot reach a Fremdwaehrungsguthaben at all, which is neither a Wertpapier nor in Sammelverwahrung. So the Depot boundary that Rz. 97 imposes on securities has **no source that carries it over** to a currency balance; that the pool therefore crosses accounts is an inference from the absence of a boundary, not a sentence anyone wrote. **And what is open is a reading, not an unread source**: Rz. 131 is in `reference/` verbatim and in full, retrieved and read on 2026-08-03, and the FIFO sentence above is the last sentence of its **second** paragraph. What that paragraph also says is that moving a balance *"auf ein anderes verzinsliches Konto bei demselben oder einem anderen Kreditinstitut"* is a disposal of the original Kapitalforderung and an acquisition of a new one -- which bears directly on whether each account's balance is its own. **That is now settled: [GT-FX-009] reads each account's balance as its own Kapitalforderung and [GT-FX-010] values a move between two of them (Reading A), and the currency ledgers are keyed per account accordingly** — the store claim was written and verified before the code, as the Ground Truth Rule requires. Incidence is in `VALIDATION_REPORT.md`. |
| GT-ESTG20-014 | implements for the documented transfer scope | `transfers_parser.py`, `domain_event_factory.py`, `event_ordering.py`; `FifoLedger.prepare_transfer_delivery` / `prepare_transfer_receipt`, coordinated by `apply_internal_transfer` | `test_internal_transfers.py`, `test_transfers_parser.py`, `test_transfer_integrity.py` | Reciprocal observations are matched without dropping distinct same-size moves; both source ids survive. Each account prepares only its own state, and both validate before commit. The same lot objects preserve dates, basis, provenance and accrued Vorabpauschale. Current-year disposal checks include newly received lots. Per-day lot detail selects whole acquisition days; sub-day selection and long/short netting remain unsupported. The ledger supplies basis; this does not certify the separate option-premium treatment. A currency (cash) move is a different question, handled separately: a currency balance is not a Wertpapier and a move of one is a disposal plus an acquisition, not a relocation — each account's balance is its own Kapitalforderung ([GT-FX-009]) and the move is valued at [GT-FX-010], read as an `InternalCashTransferEvent` (currency ledgers keyed per account). See the [GT-ESTG20-013] and [GT-ESTG20-061] blocks. |
| GT-ESTG20-039 | implements | `DomainEventFactory._trade_contract_date()` in `src/parsers/domain_event_factory.py`, feeding `FinancialEvent.event_date` | `test_trade_event_date.py` — the rule, the signature, the absent-date case, and the wiring through `create_events_from_trades` | Rn. 85: the obligatorisches Rechtsgeschäft fixes the FX rate and the gain computation, so the trade date governs and settlement does not. **By rule since 2026-08-07**, not by fallback: the trade path has its own helper, which takes no settlement or report parameter, and `RawTradeRecord` no longer declares a settlement field. Previously the trades path used the general helper, which orders settlement first, and was right only because IBKR's Trades export omits `SettleDateTarget` — measured that day, 0 of 6,976 rows across `Trades-2021.csv`…`Trades-2025.csv`. |
| GT-ESTG20-040 | implements | as above | as above. The § 23 tests (`test_section23_holding_period.py`, `test_section23_holding_period_guards.py`) build lots directly and do not reach the parser's choice of date, which is why `test_trade_event_date.py` exists | Rn. 317 defines *Erwerb* as the rechtswirksam abgeschlossener obligatorischer Vertrag; BFH IX R 18/13 (BStBl II 2014, 826, Rz 29) is to the same effect for § 23 and does not stand alone. Acquisition dates are therefore trade dates, which is what the ledger holds. The claim reaches past the Vorabpauschale: it also fixes the § 23 Jahresfrist and the month for § 18 Abs. 2. |
| GT-ESTG20-041 | implements | `FifoLedger.receive_all_lots_from_merger()` in `src/engine/fifo_manager.py` carries `acquisition_date` across to the replacement lots | `test_stock_merger_fifo.py` asserts the carry-over (four separate assertions on the surviving lot's `acquisition_date`) | Rn. 184a: a steuerneutrale Fondsverschmelzung restates the count *"unter Berücksichtigung des Umtauschverhältnisses"* and does not create a new Anschaffungszeitpunkt. **What the guarding test does not cover:** every case it exercises is a stock merger. The path is shared, but no test merges an `InvestmentFund`, so the § 18 Abs. 2 consequence — a merged fund keeping its acquisition month — is unguarded. The per-acquisition half of Rn. 184a is what grounds GT-INVSTG-011. |

**GT-ESTG20-039 and GT-ESTG20-040 — done, 2026-08-07.** The follow-up recorded here was to make
the trade date the stated rule rather than the third fallback behind settlement. It landed in two
steps: the trade path got its own helper, and then the concept was made unambiguous end to end —
`event_date` now documents which date each event kind carries and why, the general helper is named
`_zufluss_date` and says never to call it for a trade, `RawTradeRecord` no longer declares a
settlement field, and `input_data_spec.md` says not to add the column.

**What the pre-fix state actually risked, corrected twice on the day.** It was first written here
as one Flex Query checkbox away from silently misdating every lot. It is not: the trades parser
validates with `allow_extra=False`, so that column alone aborts the run. The silent path needed
two edits — the column added to the query *and* to `TRADES_COLUMNS` — or no CSV at all, since the
raw model declared the field and a record built in code never meets the validator. Removing the
field closes the second route; the validator closes the first.

> **Two corrections to this block, both on 2026-08-07, kept because the pattern matters.** It
> first claimed the hazard was one Flex Query checkbox — asserted from the shape of the helper
> without reading `validate_csv_columns`. Restated as a two-step hazard, it then stood as an open
> follow-up for an hour after the first half had already been fixed, because the commit that fixed
> it did not update the row. Both are the same failure: writing about code from what it looks like
> it does rather than from what it does.

**GT-ESTG20-013 — implemented.** Every FIFO ledger is keyed by `(account_key(account_id), asset_id)`,
and `FinancialEvent.account_id` — populated in `DomainEventFactory` from each row's `ClientAccountID`
— carries the account from the export to the ledger. One ledger per account holds that account's
lots; a disposal is dispatched to the ledger of the account it was made from, so it consumes that
account's shares (**BMF Rz. 97 Satz 2**). The historical replay gives each account only its own
past, the checkpoint marks and the opening snapshot reconcile each account against its own reported
row, and the end-of-year check compares each `(account, asset)` on its own — a misplacement that nets
to the person's correct total (90 held where 100 was, 110 where 100 was) fails here where a
person-level check passed. The four sources that decide which accounts hold an asset are the
historical events, the tax-year events, the opening snapshot (a non-zero holding) and the checkpoint
marks; the closing snapshot is deliberately not one. An export without a `ClientAccountID` column, and
every single-account export, collapse to one `DEFAULT_ACCOUNT` ledger, so single-account behaviour is
unchanged. Currency (foreign-cash) ledgers are now keyed per account too — each account's balance is its own
Kapitalforderung ([GT-FX-009], the Umbuchung valued at [GT-FX-010]); see those rows, the
`GT-ESTG20-061` row and `reference/`.

**Open question Q2 — Reading A, chosen by the taxpayer on 2026-08-11.** Whether the *"einzelnes
Depot"* boundary of Rz. 97 Satz 2 transposes to a foreign broker's account and sub-account structure
is not settled by a Tier 1/2 source; both readings are stated in
`reference/research/open-legal-questions.md` (Q2). Reading A — each IBKR account (and sub-account,
Rz. 98) is its own Depot, so FIFO is applied per account — is what the engine implements. It is a
position the Finanzamt may assess differently, not a dispute with the statute or the guidance, and it
is recorded here because the per-account FIFO above rests on it.

**A move between the taxpayer's own accounts is now read — [GT-ESTG20-014].** The Transfers export is
parsed and each move relocates its lots between the two accounts' ledgers, keeping their acquisition
date and cost basis, so the receiving account no longer holds units it never acquired and nothing is
synthesised. `MULTI_ACCOUNT_LIMITATIONS` accordingly fires **only when no Transfers export was
supplied at all** (a move — securities or currency — would then still be invisible); with the export
read there is nothing left to warn about, and a supplied export missing a year of the window stops
the run (`TRANSFERS_WINDOW_INCOMPLETE`). The
currency half is now closed too: each account's foreign-currency balance is its own Kapitalforderung
([GT-FX-009]), and a cash Umbuchung between accounts is read and measured ([GT-FX-010], Reading A).

### Abs. 4a — corporate actions

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG20-015 | implements | `CORP_MERGER_STOCK` → tax-neutral basis transfer (FIFO drain/receive) | `test_stock_merger_fifo.py` (incl. `test_merged_in_shares_sold_inside_the_historical_window`), `test_historical_merger_replay_guard.py` | Cash consideration is handled separately as `CORP_MERGER_CASH` → `CASH_MERGER_PROCEEDS`. Until issue #56 the transfer did not survive a disposal of the merged-in shares *inside* the historical window: the replay applied mergers after every ledger event, so the reconstruction overshot, reconcile discarded it and substituted a lot with a fabricated acquisition date. Basis and date now transfer in that case too. |
| GT-ESTG20-016 | **deviates** | `CORP_STOCK_DIVIDEND` → new shares at EUR 0 basis | `test_stock_merger_fifo.py` (adjacent coverage only) | Satz 5 is the *residual* case, conditional on Sätze 3, 4 and 7 not applying. The engine applies the EUR 0 treatment without testing those three conditions. |
| GT-ESTG20-017 | not reached | — | — | Abspaltung. No corporate-action type maps to it. |
| GT-ESTG20-018 | implements | Merger streamed chronologically at its own date (`engine/replay.py` `Phase.LEDGER_EVENTS`, `calculation_engine._replay_historical_merger`) | `test_stock_merger_fifo.py::TestMergerIntraDayOrdering`, `test_merged_in_shares_sold_inside_the_historical_window` | Satz 6 has two consequences and the engine reaches one. **Reached:** the measure takes effect at that moment, so the same day's disposals can consume the delivered lots — this is what fixed issue #56, and the intra-day rule is merger-before-trades. **Not reached:** *which* date is the Einbuchung. The engine uses the corporate action's reported date as a proxy; no input distinguishes the two. Note Satz 6 governs Sätze 1–5 only, not the Satz 7 Abspaltung. |
| GT-ESTG20-019 | not reached | — | — | Wandel-/Umtauschanleihen. |
| GT-ESTG20-020 | not reached | — | — | Bezugsrechte. |

### Abs. 6 — loss offsetting

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG20-030 | implements | `src/engine/loss_offsetting.py` — capital income pooled apart from § 23 | `test_group6_loss_offsetting.py` | |
| GT-ESTG20-031 | out of scope | — | — | Carryforward to later VZ is the Finanzamt's step; the engine reports one year. |
| GT-ESTG20-032 | out of scope | — | — | Spousal pooling happens at Veranlagung across both spouses' returns. |
| GT-ESTG20-033 | implements | `src/engine/loss_offsetting.py` — Aktienverlusttopf kept separate | `test_group6_loss_offsetting.py::TestLossOffsettingFromSpec` | Zeile 23 apart from Zeile 22. |
| GT-ESTG20-034 | not reached | — | — | Bescheinigung under § 43a Abs. 3 Satz 4 applies to losses that bore Kapitalertragsteuer. Foreign-broker income bears none. |
| GT-ESTG20-035 | implements (as repealed) | `src/tax_law/registry.py` — `derivative_loss_cap_applies` is `False` in **every** year entry | `test_tax_law_registry.py::TestFormYearRules::test_cap_repealed_for_every_configured_year`, `test_group6_loss_offsetting.py::TestLossOffsettingDerivativeCapRepealed` | |
| GT-ESTG20-036 | implements (as repealed) | same | same | |
| GT-ESTG20-037 | implements | the two rows above | same | *"Alle offenen Fälle"* means no assessment year applies the cap — not that it applies before 2025. |
| GT-ESTG20-060 | — | — | — | Version history of the BMF circular. Bibliographic, no engine position. |

---

## Anlage KAP — form structure

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-FORM-001 | implements | everything routes to Zeile 19 | `test_group6_loss_offsetting.py` | Correct **because the broker is foreign**. A German Zahlstelle would need Zeile 18; nothing implements that. |
| GT-FORM-002 | implements | `src/engine/loss_offsetting.py:249-275` | `test_group6_loss_offsetting.py` | Zeile 19 is a net figure; Zeilen 20/21/22/23 restate parts of it, Zeilen 24/25 do not (*ausschließlich*). The engine gets the Zeile 24 half right and the Zeile 25 half wrong — next row. |
| GT-FORM-003 | **deviates** | — | — | **Zeile 25 has no representation.** Forderungsausfall and wertlose Ausbuchung losses fall into `ANLAGE_KAP_SONSTIGE_VERLUSTE` (Zeile 22), which the 2024 Anleitung expressly forbids — *"ausschließlich in Zeile 25"*. Because *ausschließlich* also excludes them from Zeilen 18/19, the same defect **understates nothing but misplaces twice**: the loss appears in Zeile 22 where it may not, and inside the Zeile 19 net figure where it may not. No input in the maintainer's data produces such a loss today, so the path is unexercised, but nothing detects one if it appears. |
| GT-FORM-004 | **deviates** | — | — | Same shape: a worthless-share write-off should go to Zeile 23 in VZ 2025, and there is no event kind for it. |
| GT-FORM-005 | implements | `src/reporting/form_rules.py` — the 2025 rules write nothing to Zeilen 21/24/25 | `test_group6_loss_offsetting.py` | Nothing is entered on the separate derivative lines for VZ 2025, which is what the claim asserts and what the engine does. Whether the form still prints those numbers is a layout point that decides no figure; it was carried as open question Q3 until 2026-08-07 and is now a note in `reference/tax-forms/anlage-kap-zeilen.md`. |
| GT-FORM-006 | **implements (dividends from US, CA, FR, JP, KR, NL, TW; Irish interest); not reached -- the run stops (every other source state or income kind)** | `ANLAGE_KAP_FOREIGN_TAX_PAID` — sum of withholding events, each reduced to its treaty-creditable amount (GT-CREDIT-026) | `test_withholding_tax_linker.py`, `test_foreign_withholding_treaty_guard.py` | The Satz 1 25 %-per-Kapitalertrag and Satz 3 per-VZ **ceilings** are still the Finanzamt's (GT-CREDIT-005/006). Distinct from those, the per-income **treaty-rate** reduction (Ermäßigungsanspruch) is applied here for every source state and income kind with a creditable rate in the store (GT-CREDIT-029/030). **Re-decided 2026-09-22:** the store now quotes the Anleitung's *"anzurechnende Steuern"* for Zeilen 37–42, the ground for entering the reduced rather than the withheld amount; position unchanged. **Re-decided 2026-09-23 after review:** the ground is § 32d Abs. 5 Satz 1 itself, the heading only consistent with it (the store now says so). At that point the position was **implements** only for US dividends: for any other source state, and for interest, Zeile 41 carried the *withheld* tax (`FOREIGN_WHT_RATE_NOT_VERIFIED`, WARNING). The dividend rates, the Irish interest rate and the blank-country fix closed that for the states and kinds in the store on 2026-09-23 (GT-CREDIT-026, GT-CREDIT-029/030); any other state or income kind carried the withheld tax until the F1 change below. **Re-decided 2026-09-23 after the maintainer's review (F1):** a row with no supported creditable amount -- no rate for its state, income kind or year, no linked income, or no state -- no longer reaches Zeile 41 as withheld. It is itemised (`FOREIGN_WHT_RATE_NOT_VERIFIED`, `_RATE_YEAR_NOT_RESEARCHED`, `_UNLINKED`) and the run stops (`FOREIGN_WHT_CREDIT_UNSUPPORTED`, FAIL_FAST), naming every such row. So no declared figure rests on an unsupported credit; the uncovered cases are *not reached* rather than *deviates*. |
| GT-FORM-007 | **partially implements** | `src/engine/loss_offsetting.py` | `test_german_kest_detection.py`, `test_withholding_tax_linker.py` | The negative half is implemented: German KESt is off Zeile 41. The positive half (Zeilen 7/37/38/39) is not computable — see GT-CREDIT-021. |
| GT-FORM-008 | out of scope | — | — | Zeile 4 (Günstigerprüfung) and Zeile 5 (Überprüfung des Steuereinbehalts) are taxpayer elections, not computed figures. |
| GT-FORM-009 | implements | classification decides the Anlage | `test_futures.py::TestFuturesClassification`, `test_section23_holding_period.py` | Fund → KAP-INV, private sale asset → SO, Einlagenrückgewähr (`CAPITAL_REPAYMENT`) → not taxable. |
| GT-FORM-010 | implements | `src/tax_law/registry.py` `FormYearRules(separate_derivative_lines=True)` for 2021 and 2024 | `test_tax_law_registry.py::TestFormYearRules` | |
| GT-FORM-011 | implements | `FormYearRules(separate_derivative_lines=False)` for 2025 | `test_tax_law_registry.py::TestFormYearRules::test_2024_vs_2025_form_structure` | |
| GT-FORM-012 | implements | `src/tax_law/registry.py` — 2021 is the earliest entry; `get_form_rules` **raises** for any earlier year rather than falling back | `test_tax_law_registry.py::test_years_before_the_earliest_verified_form_raise`, `test_every_configured_year_2021_to_2023_matches_2024`; `test_form_verification_warning.py` | Backward projection refused because Zeilen 21/24 were *frei* on the VZ 2020 form. Verified 2022/2023 reuse of the 2021 entry is distinguished from unverified forward carry-over; only the latter warns in the log and reports. The raising behaviour used to be stated in the reference file itself, naming the function; moved here 2026-08-03 under the Purity Rule. |

**`FormYearRules`** (`src/tax_law/registry.py`, re-exported by `src/reporting/form_rules.py`) is
the single place year-specific form structure lives. Entries for **2021** (covering 2021–2023 by
verified reuse recorded in `_VERIFIED_FORM_YEAR_SOURCES`), **2024** and **2025**.
`form_rules_are_carried` describes source reuse; `unverified_form_rules_source`
determines whether that reuse lacks year-specific verification. Only `separate_derivative_lines`,
`z19_subtracts_derivative_losses` and `z22_includes_derivative_losses` vary by year;
`derivative_loss_cap_applies` is `False` throughout.

---

## Anlage KAP-INV — InvStG

### § 16 — what fund income is

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-001 | implements | `DISTRIBUTION_FUND`, Vorabpauschale computation, fund disposals | `test_vorabpauschale.py`, `test_group6_loss_offsetting.py::TestLossOffsettingFundIsolation` | All three limbs of Abs. 1. **Re-decided unchanged 2026-08-09 by the issue #75 audit**, which quoted Abs. 1 for the first time and recorded two features the paraphrase had lost: the list is closed, and Nr. 1 names the payer as *"des Investmentfonds"*. Nothing about the three limbs moved; both features bear on GT-INVSTG-059. |
| GT-INVSTG-002 | implements | `src/domain/enums.py` `ANLAGE_KAP_INV_*` categories | `test_vorabpauschale.py::TestGetVpReportingCategory` | |
| GT-INVSTG-003 | not reached | — | — | Disapplication of § 3 Nr. 40 EStG / § 8b KStG. Neither is in the computation to begin with. |
| GT-INVSTG-004 | out of scope | — | — | Altersvorsorge contracts and DBA-Freistellung of a foreign fund's distribution. |
| GT-INVSTG-005 | implements | gross figures per fund type; no Teilfreistellung applied to the declared amount | `test_vorabpauschale.py`, `test_group6_loss_offsetting.py` | |
| GT-INVSTG-057 | implements, **except for the case at GT-INVSTG-059** | `src/parsers/domain_event_factory.py` classifies a positive fund cash inflow as `DISTRIBUTION_FUND`; `_collect_fund_distributions_for_year()` in `src/engine/calculation_engine.py` sums it | `test_dividend_handling.py`, `test_vorabpauschale.py` | § 2 Abs. 11 with Rz. 2.44. The two conditions are that the amount reach the **Anleger** and come **from the fund**; the engine tests neither, and cannot — it has one signal, a cash credit against a fund asset. That is right for an ordinary distribution and is the whole of the question at GT-INVSTG-059. Rz. 2.45's gross-up by foreign withholding is a separate point and is not checked here. |
| GT-INVSTG-058 | not reached | — | — | § 2 Abs. 10: the Anleger is fixed by § 39 AO attribution, not by the account a unit sits in. The engine has no attribution concept and takes the broker's position report as the holding, which is the same answer in every case the export can distinguish. See the § 39 AO section above for why the input cannot reach the question. |

### § 18 — Vorabpauschale

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-010 | implements (Satz 2 price), see GT-INVSTG-017 for the unit count | `_calculate_vorabpauschale()` in `src/engine/calculation_engine.py`; the Satz 2 price for a fund bought mid-year comes from `src/processing/fund_prices.py` | `test_vorabpauschale.py::TestVorabpauschaleCalculation`, `test_vorabpauschale.py::TestAFundTheEngineCannotPrice`, `test_vorabpauschale_reclassification.py`, `test_fund_price_store.py` | Sätze 1–3: Basisertrag, the value-gain cap, and the distribution subtraction. **Where Satz 1's subtraction falls relative to Abs. 2 is GT-INVSTG-056**, not this row. **Where the position report does not determine a per-unit price, none is recorded**, added 2026-08-31: one ISIN listed on two exchanges arrives as two rows the asset resolver treats as one instrument, and their market prices differ. Quantities and values add — one ISIN is one holding — but neither venue's price is the Rücknahmepreis Satz 2 asks for, and no average of the two produces it. The snapshot price is therefore the value the rows agree on or nothing, which puts Satz 2 on the ordinary resolution path (stored figure, issuer NAV, taxpayer, then a stopped run) and makes Satz 3's cap raise `VORABPAUSCHALE_PRICE_UNUSABLE` naming the fund rather than capping with one exchange's close. Nothing downstream would have caught the wrong price: the end-of-year reconciliation compares quantities. Zero incidence — no ISIN appears under two Conids in any Positions file of the window, and no (account, instrument) pair is reported twice. Reached only for some funds until 2026-08-04, and a fund it could not price dropped out silently until 2026-08-09 — see below. **Re-decided unchanged 2026-08-09 by the issue #75 audit**, which added one point to the store and takes nothing away from this row: *Ausschüttungen* is one defined term used twice in Abs. 1, so the Satz 3 cap and the Satz 1 subtraction always take the same amount and no separate enquiry is owed for the cap. The engine already feeds both from one sum. **What is an Ausschüttung in the first place is GT-INVSTG-059**, not this row. |
| GT-INVSTG-011 | implements | `abs2_retained_twelfths()` in `src/engine/vorabpauschale_attribution.py`, used by `_calculate_vorabpauschale()` and the Zeile 53 distribution key | `test_vorabpauschale_abs2.py`, `test_vorabpauschale_zeile53.py::TestAbs2Twelfths`, `test_vorabpauschale.py::TestAFundAcquiredDuringTheYear`, `test_vorabpauschale.py::TestUnitsTheReconstructionCouldNotDate`, `test_snapshot_integrity.py` | Abs. 2 applies per acquisition; what the twelfths multiply is GT-INVSTG-056. Dated pre-year acquisitions retain twelve twelfths; dated acquisitions within the year receive the statutory reduction. **Corrected 2026-09-17:** an earlier position count cannot prove that undated closing units are the same units: the old holding may have been sold and replaced. A positive Vorabpauschale requiring that timing now stops with `VORABPAUSCHALE_ACQUISITION_DATE_UNKNOWN`, naming every affected fund (or `ProcessingError` without a collector). If the rate, cap or distributions already establish zero, no acquisition factor is needed. No date or full-year factor is invented. GT-INVSTG-055's automatic full-year fallback applies to withholding, not this declaration. The 2026-08-31 quantity-only exemption is superseded; the statutory per-acquisition reading settled by Q13 is unchanged. |
| GT-INVSTG-012 | implements | `VorabpauschaleData.vorabpauschale_year` and `.declaration_year` | `test_vorabpauschale.py::TestVorabpauschaleDeclarationYear`, `test_pdf_vorabpauschale.py` | The VZ `Y` return carries the Vorabpauschale for calendar `Y-1`. All three output surfaces select on `declaration_year`; the PDF read the pre-rename field until 2026-08-04. Re-decided 2026-08-07 on Rz. 18.12, now recorded: the Zuflussfiktion is stated there as a Steuerabzug convenience so that a full Sparer-Pauschbetrag is available, **not** as a holding test — which is why it could not carry GT-INVSTG-016 and no longer has to. |
| GT-INVSTG-013 | implements | `src/tax_law/registry.py` `BASISZINS_PCT` | `test_tax_law_registry.py::TestBasiszinsLookup` | Re-decided 2026-08-07 on Rz. 18.13 and 18.14, now recorded. Rz. 18.14 fixes the rate as the value determined for the **erster Börsentag** of the calendar year, which is 2 January only in years whose first exchange day falls on it. This does not reach the engine: it looks up the value the BMF published for the year, and choosing the day is the BMF's step, not the engine's. It bore on GT-INVSTG-018, where a 2 January date *was* used as a Stichtag; that was closed on 2026-08-08 and the two now read the same way. |
| GT-INVSTG-014 | implements | `ParsingOrchestrator.prior_soy_positions` / `.prior_eoy_positions` / `.prior_opening_positions`, one `PositionSnapshot` per `(account, asset)`; files resolved by `src/data_preparation.py` and rows read by `ParsingOrchestrator.process_positions()` | `test_vorabpauschale.py::TestVorabpauschaleDeclarationYear`, `test_vorabpauschale_reclassification.py` | Records which *year* each input is drawn from; the day within it is GT-INVSTG-010. Where the prior year's snapshots are absent and funds are held, the run stops with a `FAIL_FAST` data gap rather than substituting the tax year's own snapshot. Where they are present but do not survive classification, the run stops with a `DataIntegrityError` — see below. |
| GT-INVSTG-015 | implements | gross on Zeilen 9–13 | `test_vorabpauschale.py::TestTeilfreistellungNegativeDistribution` | |
| GT-INVSTG-016 | implements | the unit count at the close of 31 December, from the ledger's own lots — see GT-INVSTG-017 | `test_vorabpauschale.py`, `test_vorabpauschale_price_and_units.py` | **No longer a choice under uncertainty.** The 2026-08-07 audit closed Q5 on Rz. 18.4: the multiplier is the holding at the close of 31 December, so a fund disposed of in full produces nothing without any rule about disposal being needed. The engine already computed it that way. Superseded position: **choice under uncertainty**, reasoned from the Abs. 3 Zuflussfiktion — see below. |
| GT-INVSTG-017 | implements | the unit count is taken from the ledger's own lots at the close of 31 December, snapshotted immediately after the historical replay reconciles | `test_vorabpauschale_price_and_units.py` | Rz. 18.4 multiplies by the units held at the **close of 31 December** of the calendar year, and the engine does exactly that. Rounding is compliant: full precision throughout, quantised to two places once, after every multiplication. See below for what it replaced and why the moment of the snapshot matters. |
| GT-INVSTG-018 | implements | ECB conversion at the day each price was set, carried on `PositionSnapshot.mark_price_date` in the preceding year's registries and applied in `_calculate_vorabpauschale()`; the days themselves come from `src/utils/snapshot_dates.py` | `test_vorabpauschale_stichtag.py`, `test_vorabpauschale.py::TestVorabpauschaleCalculation` | Rz. 18.6 converts each input at the ECB rate of its own Stichtag, and a Stichtag is a day a price was set, never a fixed calendar date — the reading Rz. 18.14 confirms by anchoring the year on its **erster Börsentag**. **Re-decided 2026-08-08, and the imprecision is closed.** Superseded position: *"implements, with a known imprecision"* — the Jahresanfang Stichtag was hardcoded to 2 January and the Jahresende to 31 December. Measured over 2021–2025, 2 January is the first trading day in only 2024 and 2025, and in 2021 and 2022 it is a Saturday and a Sunday, so the ECB had no rate and `MAX_FALLBACK_DAYS_EXCHANGE_RATES` silently supplied one from another day. The 31 December instance was in neither this row nor issue #60 and was found by measurement: it is a weekend in 2022 and 2023. **What remains, and is not this claim's:** the day is derived from the snapshot naming convention, not read from the export, because the Positions report carries no date — issue #59. |
| GT-INVSTG-035 | **implements** where a price can be fetched, re-decided 2026-08-08 | `_first_price_set_in_year()` in `src/processing/fund_price_sources.py`; `src/processing/fund_prices.py` otherwise | `test_fund_price_sources.py::TestFirstPriceSetInYear`, `test_fund_price_store.py` | Rz. 18.7: a fund launched during the year takes its first set price, with Abs. 2 pro-rata on top. **No launch date is needed** — a provider's published series begins at launch, so the first new publication in the calendar year is Rz. 18.7's base for a launch year and the ordinary Satz 2 base otherwise, by one rule. Measured 2026-08-08 on a fund with an 18 April 2018 inception: calendar 2018 resolves to 19 April 2018, calendar 2019 to 2 January. Superseded positions: **deviates** — first *"skips any fund without a start-of-year position outright"*, then *"the launch date is still unknown"*. The second was written the same day and was wrong. |
| GT-INVSTG-036 | **not reached**, re-decided 2026-08-08 | — | — | Rz. 18.8: where a fund does not set a Rücknahmepreis at least monthly, the market price takes its place. **Both branches land on a price the engine already uses** — the Rücknahmepreis where one is set, the broker's market price where none is — so the determination cannot change a figure here and no behaviour follows from it. Superseded position: **deviates**, on the ground that the engine *"has no notion of whether a Rücknahmepreis exists and always uses the broker's mark price"*. Both halves were wrong: the second stopped being true on 2026-08-08, and the first described a distinction with no consequence. Which price is used, and why, is GT-INVSTG-010 Satz 4 below. |
| GT-INVSTG-055 | **not reached** (Satz 1) / **out of scope** (Satz 2) | — | — | Rz. 18.9. Satz 1 is confined to the Steuerabzugsverfahren, which a foreign custodian does not perform. Satz 2 is a refund route in the assessment for tax over-withheld by a domestic agent — there is none here. Recorded because it is the administrative statement that the Abs. 2 reduction turns on *Anschaffungsdaten* attaching to units, which is part of what closed Q13 (GT-INVSTG-011). No behaviour follows from it. |
| GT-INVSTG-056 | implements | `_calculate_vorabpauschale()` in `src/engine/calculation_engine.py` — Satz 1 subtracts the per-unit distributions, and the tranche loop applies the Abs. 2 twelfths to what remains | `test_vorabpauschale.py::TestAFundAcquiredDuringTheYearThatAlsoDistributed` | Rz. 18.3 computes Satz 3's cap, then Satz 1's subtraction, and Rz. 18.11 takes 6/12 of what remains — so the twelfths multiply `Basisertrag − Ausschüttungen`. **Superseded position: deviates**, from the day Abs. 2 pro-rata was added until 2026-08-09 — the twelfths were applied to each tranche's Basisertrag and the distributions taken off the sum afterwards, which is lower by `Ausschüttungen × (12 − k)/12`, and where that drove the result to zero or below the fund was dropped and nothing declared at all. Measured on the module's own harness before the fix: a July acquisition with distributions at 37% of the Basisertrag gave 20.15 against 50.15, and at 75% it declared nothing against 20.15. `calculated_base_return_eur` carried the twelfths-reduced amount over the same period and now carries the Rz. 18.4 product, which is what Abs. 1 defines; nothing reads that field, so it moved no output. Issue #58. |
| GT-INVSTG-059 | **implements** (branch A, taxpayer's assertion 2026-08-09) | `src/parsers/domain_event_factory.py` — a positive cash transaction whose type contains *Dividend* becomes `DISTRIBUTION_FUND` when the asset is an `InvestmentFund` | `test_payment_in_lieu_credit_route.py` (branch A: parser routing, Zeile 4 vs Zeile 19, and the Vorabpauschale reduction), calibrated against a tree mutated to branch B | **Branch chosen: A.** The § 39 AO attribution stays with the taxpayer, so the substitute payment is the fund's Ausschüttung ([GT-ESTG20-045], Rz. 12) and enters § 18 Abs. 1 on both sides. **Basis, from the lending terms and verified 2026-08-09** against IBKR's own description of the Stock Yield Enhancement Program, `https://www.interactivebrokers.com/en/pricing/stock-yield-enhancement-program.php`. The criteria of Rz. 3 to 9 are contract facts that no export carries, so this is where they are recorded. **Rz. 2's own test is not met**, which matters more than the Ausnahme indicators: the borrower must be able to exclude the lender economically from the asset, and *"You remain the owner of the stock, which means you continue to have market risk and will recognize any profit (or loss) if the stock price moves. You can sell your shares at any time without restriction"* — so the Kursrisiken und -chancen Rz. 2 names as the decisive attribute never pass. **Rz. 8 is met squarely**: *"Selling your shares or borrowing against them or withdrawing cash in a margin account will terminate the loan transaction"* — the borrower's position is withdrawable at will. **The Gesamtschau is not one-sided, and the contrary points are recorded rather than omitted:** Rz. 7 does not help, because the borrower does get the votes — *"During any period in which your securities are loaned out, you will forfeit your right to vote those shares by proxy"*; Rz. 5 is not met, the fee being a market rate rather than one measured on a tax advantage; and Rz. 9 is not met, since the borrower does put the stock to real use. **A fourth ground previously asserted here has been withdrawn:** Rz. 4's short period across the Ausschüttungsstichtag — the terms do not state loan durations and it was assumed, not read. Rz. 4's burden on the borrower stands. The engine already produced this result, so no figure moves; **the follow-up test is now written** — `fix-nonfunc`, `test_payment_in_lieu_credit_route.py`, calibrated against a tree mutated to branch B (issue #78). Superseded position: **deviates** — the condition was not checked, which is what the assertion now supplies. **Incidence, measured 2026-08-09** by cross-checking the classified fund ISINs against `Positions-{Y}-EoY.csv` and `Cash_Transactions-{Y}.csv`: funds held at a year end with any such payment — 0 in 2021, 0 in 2022, 0 in 2023, 0 in 2024, **2 in 2025**, of which one is positive and reaches the computation. The conclusion first drawn from it, that VZ 2026 is the only assessment year the branch can move, is withdrawn (below). Issue #75. **Scope of that incidence, added 2026-09-23:** it counts the Vorabpauschale half (a fund held at a year end). The distribution half — whether the payment itself is the fund's Ausschüttung on KAP-INV Zeile 4 — is reached wherever a fund receives a payment in lieu, held at year end or not: DEM, 3 rows in VZ 2023 and 1 in VZ 2024 (`Cash_Transactions-{2023,2024}.csv`), so the branch does move VZ 2023 and VZ 2024 figures through that half. The current `Cash_Transactions-2025.csv` has no payment-in-lieu row at all (measured 2026-09-23); the "2 in 2025" above cannot be reproduced: every retained copy of `Cash_Transactions-2025.csv`, from 2026-08-03 to 2026-09-22 and so spanning the 2026-08-09 count, has 0 rows matching *payment in lieu* (case-insensitive grep, measured 2026-09-23). The count and the "VZ 2026 only" conclusion resting on it are withdrawn. The Vorabpauschale half has no measured incidence in the window; the distribution half moves VZ 2023 and VZ 2024. |

**GT-INVSTG-010 and GT-INVSTG-014 — reached only for some funds until 2026-08-04.** A positions
row is resolved without its `SubCategory`, so the description is the only fund signal that
survives: an instrument described as an ETF is created as an `InvestmentFund` outright, and any
other fund is created as a `Stock` and retyped when the user's classification is applied — which
is after the prior-year snapshot has been read onto it. Retyping copies a hand-listed set of
fields and the `prior_year_*` fields were not on it, so a retyped fund reached § 18's
computation with no year-start Rücknahmepreis and was skipped, with nothing recorded. A fund
created as a fund was unaffected. **On this repository's own data the distinction is not a
mitigation:** no fund description contains "ETF", so every one was retyped and Zeilen 9–13 were
empty on every run, whether or not deemed income was due.

**The copy list is gone, and with it that whole class of loss.** The preceding year's snapshot
is no longer a set of fields on `Asset`: it is a `PositionSnapshot` per `(account, asset)`, held
in a registry keyed by `internal_asset_id`, and `replace_asset_type` re-uses that id when it
rebuilds an asset as a different Python type. There is no list a field can be left off. What can
still lose a record is a **merge** — two identifiers resolving to one asset deletes the loser,
and rows filed under its id become unreachable — and that is what the guard now names. Measured
2026-08-31 over every Positions, Trades and Cash_Transactions row in the export window: **0
merges in 718 rows**, so the guard has never fired on this data.

The guard stands where that failed. The assets a snapshot was read for are checked against the
assets the engine will see (`ParsingOrchestrator._verify_prior_year_snapshot_survived_classification`,
`DataIntegrityError`, naming every affected fund); it falls back to an alias where the recorded
id no longer resolves, so an instrument merged into another after its snapshot was read is
followed to the survivor, and it reports investment funds only, since nothing else can lose a
declared figure this way. And the
itemisation is exercised with a record present (`test_pdf_vorabpauschale.py`) — the PDF read the
pre-rename `tax_year` field and would have raised `AttributeError` on the first run that
produced one.

**GT-INVSTG-010, Satz 4 — closed for any fund a provider publishes, 2026-08-08.** The
Ruecknahmepreis is the primary measure and a market price substitutes only where none was set. An
open-ended fund that redeems units at its NAV sets one — *Rücknahme* plus *Preis*, the price it
takes the share back at.

The engine therefore looks that price up, by ISIN, **for every fund held across the year end** —
not only for one the start-of-year position report cannot price. Until 2026-08-08 it used the
report's mark wherever it had one and only went looking when it did not, which put Satz 4's
substitute ahead of the primary measure for every fund held on 1 January. Superseded positions:
first *"uses the broker's position mark price unconditionally"*; then, for one day, a
`--vorabpauschale-strict-nav` switch that made the NAV opt-in. The switch is gone — an opt-in
default is still the substitute for everyone who does not know to ask for it.

**What remains is the fallback, and it is recorded.** Where no Ruecknahmepreis can be obtained the
taxpayer is asked and offered the report's price, and in a non-interactive run that price is used
outright; both record `VORABPAUSCHALE_PRICE_MARKET_FALLBACK` against the fund, so a reader can see
which figures rest on the substitute. A fund that nothing can price stops the run.

**GT-INVSTG-010 — the Satz 2 price.** *Ruecknahmepreis zu Beginn des Kalenderjahres* is the
first Rücknahmepreis set in the calendar year. Rz. 18.3 of the BMF-Schreiben demonstrates it: one
figure serves as both the Satz 2 base and the Satz 3 cap's lower bound, which Satz 3 defines as
the first price set in the year. Rz. 18.7 anchors a mid-year fund on the first price actually set.

The engine takes it from the calendar year's own start-of-year position report; where a fund was
sold on that day and so has no price there, the last price set before the year began is used and a
`VORABPAUSCHALE_PRICE_WRONG_DAY` data gap is recorded. How the stored reports are read into a
position history is described in `src/data_preparation.py` and
`src/parsers/parsing_orchestrator.py`.

**A third source, for the fund the export cannot price at all.** A fund bought during the year has
no row in that year's start-of-year report, because the report lists what was held. The price
nevertheless exists — it is a property of the fund, not of the holding — so the figure is due and
buying mid-year is an ordinary event, not a data gap. `src/processing/fund_prices.py` asks the
taxpayer for the price and caches it under the asset's classification key and the calendar year,
the same shape as the classification cache; each supplied price is recorded as a
`VORABPAUSCHALE_PRICE_USER_SUPPLIED` gap at WARNING so the report states what the Basisertrag rests
on and where it came from. **Nothing is invented:** a run that cannot obtain a price stops on a
`VORABPAUSCHALE_YEAR_START_PRICE_UNKNOWN` FAIL_FAST naming every affected fund. Neither IBKR nor
any broker export can supply this price — measured 2026-08-08: IBKR's historical endpoints serve
market prices only, and its ETF NAV ticks (92–99) reach one session back.

The conversion of this price is no longer pinned to 2 January; the follow-up that stood here is
closed under GT-INVSTG-018 below.

**A price the engine cannot use no longer removes the figure quietly, 2026-08-09.** Four paths in
`_calculate_vorabpauschale()` dropped a single fund and let the run finish: no Satz 2 price, that
price not convertible to EUR, no Satz 3 price though units were held at the close, that price not
convertible. Each was a log line and a `continue`, so an instrument the engine had itself
classified as an investment fund contributed no deemed income and the report said nothing —
measured on 2026-08-07, four funds across VZ 2024 and VZ 2025 with Anlage KAP-INV Zeilen 9–13 at
0.00 and an empty gap section. All four now collect and record one `VORABPAUSCHALE_PRICE_UNUSABLE`
FAIL_FAST naming every affected fund with its reason. The figure in these cases is not zero, it is
un-computable, and a zero on Zeile 9 is indistinguishable from a lawful one (issue #55).

Two boundaries on that gap. It is **not** recorded for a calendar year whose Basiszins is not
positive — Satz 2 multiplies by it, so no fund owes anything whatever its price was, and calendar
2021 and 2022 are such years; without the guard VZ 2023's lawful zero would start aborting. And it
is recorded **after** `VORABPAUSCHALE_ACQUISITION_DATE_UNKNOWN`, so a tree missing both keeps
aborting on the acquisition dates as it did before: a FAIL_FAST raises where it is recorded, so
only the first of two ever reaches the report.

**GT-INVSTG-017 — the unit count. Closed.** Rz. 18.4 multiplies the per-unit Basisertrag by the
units held at the close of 31 December of the calendar year, and the engine now does exactly that,
taking them from the ledger's own lots at that moment. It previously multiplied by the units held
when the year opened. The two coincide for an unchanged holding; on VZ 2024 real data they give Anlage
KAP-INV Zeile 13 393.27 against 491.59.

Bearing on the choice: § 18 Abs. 2 reduces the Vorabpauschale pro rata for units *acquired during
the year*, which presupposes those units are counted; and GT-INVSTG-016 — no longer a reading but
a consequence of this very Randziffer — gives no Vorabpauschale for a fund fully disposed of
during the year.

**Re-decided 2026-08-07 and strengthened.** Rz. 18.4 is not a Steuerabzug convention: it sits in
Textziffer 18.1 *"Ermittlung der Vorabpauschale"* and is unqualified, where the Randziffern of
this section that *are* confined to withholding say so (Rz. 18.9, Rz. 18.10, both *"im
Steuerabzugsverfahren"*). It therefore governs the amount itself, which is what lets it carry
GT-INVSTG-016 as well as the count.

Done. The lots are snapshotted immediately after the historical replay reconciles, which is the
one moment they describe the close of the preceding calendar year and still carry their
acquisition dates.

**GT-INVSTG-035 — partly closed, and re-decided 2026-08-08.** The Abs. 2 pro-rata applies to units
acquired during the year (`e70099b`), and the price is no longer unobtainable: a fund with no
start-of-year row is asked about rather than skipped, so a taxpayer who has the first price the
fund actually set can enter it and Rz. 18.7's base is used.

**It does not need to tell the two apart.** The engine cannot distinguish a fund *newly launched*
mid-year from one merely *bought* mid-year, and that turns out not to matter: it asks the provider
for the first value published in the calendar year, and a series that starts at launch answers
Rz. 18.7 without anyone establishing a launch date. The earlier note here said closing this
*"needs the launch date, which no input this pipeline holds supplies"*; that was wrong.

**The manual path proposes no day it was not given.** Where no provider can be reached the
taxpayer is asked, and where the fund has no start-of-year row the prompt offers no default date:
the year's first trading day is wrong for a fund launched in April, and a proposed date is the
kind of thing that gets accepted with Enter. An empty answer is a refusal, not a guess
(`test_fund_price_store.py::TestThePromptDefaults::test_with_no_report_row_no_day_is_proposed`).
Superseded position, written 2026-08-08 in the same commit that fixed it: *"What is still open is
the manual path … the prompt offers the year's first trading day as the default date."* It
described the behaviour the code half of `366f832` had already removed.

**GT-INVSTG-036 — follow-up withdrawn 2026-08-08.** It named a `fix-func(engine)` to distinguish a
fund that sets a Rücknahmepreis at least monthly from one that does not. There is nothing for it to
close: both branches of Rz. 18.8 land on a price the engine already uses, so the distinction cannot
move a figure. The Satz 4 choice it also claimed to close is a separate matter and is decided under
GT-INVSTG-010 above.

**GT-INVSTG-016 — settled 2026-08-07, formerly open question Q5.** The engine's behaviour is
unchanged; its justification is not. The reading was previously *chosen* from the Abs. 3
Zuflussfiktion — the units are gone by the first working day of the following year — and recorded
as a defensible guess. It now rests on Rz. 18.4, which states the multiplier as the units held
*"mit Ablauf des 31. Dezember des Kalenderjahres"*. A fund disposed of in full is multiplied by
nothing; no rule about disposal is needed, and none exists. Rz. 20.4 confirms the direction: a
merely deemed disposal under § 22 Abs. 1 leaves the units in the count and the full year stands
(GT-INVSTG-054).

This is the same Randziffer the engine already implements for the unit count (GT-INVSTG-017), so
Q5 was never a separate decision — it was a consequence of one already taken. Recording it as an
open question, and reasoning it from the wrong Absatz, is the defect the audit corrected.

**Follow-up from closing Q5 and Q13:** `fix-nonfunc(engine)` — three comments now assert something
false and a reader would trust them. `src/engine/calculation_engine.py:1299` says *"Both readings
are in reference/research/open-legal-questions.md Q13"*; there are no longer two readings there,
only a retirement note. Line 1331 attributes the disposal-year result to *"Q5 Reading A: the
Abs. 3 Zufluss falls after the disposal"*, which is the reasoning this audit replaced — the ground
is Rz. 18.4. And `tests/test_vorabpauschale_abs2.py:12` describes Q13 as an open question. None
changes behaviour, which is why they are not in this `ks-maint`; a comment that misstates why a
figure is correct is how the next reader reopens a settled point or, worse, "fixes" it.

### § 19 — disposal gains

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-030 | implements | fund disposals → `ANLAGE_KAP_INV_*_GEWINN_GROSS`, net of the Satz 3 deduction; Satz 4's gross ordering in `RealizedGainLoss.__post_init__` (`src/domain/results.py`) | `test_group6_loss_offsetting.py::TestLossOffsettingFundIsolation`, `test_vorabpauschale_zeile53.py::TestSatz4GrossDeductionThenTeilfreistellung` | All four Sätze. Satz 3's deduction reaches the lot through `FifoLot.vorabpauschale_gross_eur`; Satz 4 fixes the order — the full, pre-Teilfreistellung amount comes off the gain first, and the Teilfreistellung is applied to what is left. Was "implements (partly)" until issue #63. |
| GT-INVSTG-031 | not reached | — | — | A fund leaving the InvStG's scope is not reported in any broker statement. |
| GT-INVSTG-032 | out of scope | — | — | Wegzug and related, gated by a 1 % / EUR 500 000 threshold. |
| GT-INVSTG-033 | implements | `ANLAGE_KAP_INV_VORABPAUSCHALE_ABZUG_Z53`, summed in `src/engine/loss_offsetting.py` | `test_vorabpauschale.py::TestZeile53VorabpauschaleDeduction`, `test_vorabpauschale_zeile53_engine.py::TestTheDeductionReachesTheFormLine` | The figure is on the right line, and the gain lines are net of it because the form reaches them through Zeile 54. |
| GT-INVSTG-034 | implements | `src/processing/vorabpauschale_declarations.py` (what was declared) with `src/engine/vorabpauschale_attribution.py` (distributing it to the lots); `src/engine/calculation_engine.py` reports every holding-period year that reached no lot | `test_vorabpauschale_zeile53.py`, `test_vorabpauschale_zeile53_engine.py::TestAYearWithNoDeclarationRecord` and `::TestDivergenceFromWhatWasDeclared` | See below. Was **deviates — reports the gap** until issue #63. |

**GT-INVSTG-034 / GT-FORM-033 — the Zeile 53 deduction, and what it may rest on.** The deduction
is the mirror of a declaration, not a second quantity the engine may derive: for units that never
bore inländischer Steuerabzug the Anleitung admits it *"nur, soweit Sie diese Vorabpauschalen der
Besteuerung unterworfen haben (Zeile 9 bis 13)"*, and requires the taxpayer to demonstrate it. So
three things had to hold together, and each is a place a plausible wrong number was available:

- **It follows the lot.** `FifoLot.vorabpauschale_gross_eur` accumulates as the replay passes each
  year end — the moment the ledger describes the Rz. 18.4 holding — and every consumption path
  hands the disposed units their pro-rata share. A partial sale therefore deducts the tranches
  FIFO consumed and nothing else.
- **What is spread is what was declared.** The annual figure per fund is the taxpayer's input,
  recorded write-once at filing (`--commit-vorabpauschale-declaration`); the engine's own § 18
  Abs. 2 split is only the key that distributes it, and the prices cancel out of that key, so a
  year whose prices this run never loaded can still be distributed. For calendar `tax_year-1` the
  declaration is *this return's own Zeilen 9-13*, which is why that year needs no stored record.
  Where a stored figure and this run's computation disagree, the stored one governs and the
  divergence is reported while the return is amendable.
- **A year with no record deducts nothing, and is named.** Never the engine's recomputation
  standing in for a declaration — that is the invented input CLAUDE.md refuses. A year whose
  Basiszins was not positive is excluded from the demand instead of reported, because § 18
  Abs. 1 Satz 2 yields no Vorabpauschale for any fund in such a year (2021 and 2022).

Superseded text: *"the Zeile 53 deduction is not computed, deliberately … It now emits no figure
and records a data gap when fund units are disposed of"* — true from 2026-08-03 until issue #63,
and before that the line carried the current year's gross Vorabpauschalen on Zeile 55.

### § 20 — Teilfreistellung

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-020 | implements | `registry.teilfreistellung_rate` → 30 % | `test_tax_law_registry.py::TestTeilfreistellung` | Applied to derive net figures for offsetting; the declared figure stays gross. |
| GT-INVSTG-021 | implements | → 15 % | same | |
| GT-INVSTG-022 | implements | → 60 % | same | |
| GT-INVSTG-023 | implements | → 80 % | same | |
| GT-INVSTG-024 | implements | → 0 % | same | |
| GT-INVSTG-025 | out of scope | — | — | Betriebsvermögen rates. |
| GT-INVSTG-026 | **not implemented — human input** | `src/classification/asset_classifier.py:25-29` | — | See below. |
| GT-INVSTG-027 | **not implemented — human input** | same | — | Mischfonds is *mindestens 25 %*, inclusive, where Aktienfonds is *mehr als 50 %*, exclusive. |
| GT-INVSTG-028 | not reached | — | — | The 51 % look-through for fund-of-funds. Nothing computes a quota. |
| GT-INVSTG-029 | **not implemented — human input** | same | — | |
| GT-INVSTG-019 | out of scope | — | — | Teilfreistellung on proof of the actual quota is an application in the assessment. |

**GT-INVSTG-026/027/029 — the engine does not classify funds; a person does.** Fund type comes
from interactive classification or the classification cache
(`src/classification/asset_classifier.py`), and **no quota is computed anywhere.** The thresholds
therefore constrain the human making the choice, not any code path. This is why the *">= 51 %"*
error corrected on 2026-08-03 was figure-changing even though no code changed: it would have led
someone to classify a fund at 50.5 % as Sonstiger Fonds (0 %) when it is an Aktienfonds (30 %).

### § 22 — change of the applicable rate

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-040 | not reached | — | — | A change of Teilfreistellungssatz triggers a deemed disposal and reacquisition. No input signals a fund's type changing; the classification cache would simply be edited, silently. |
| GT-INVSTG-041 | out of scope | — | — | Lapse of a § 20 Abs. 4 proof. |
| GT-INVSTG-042 | not reached | — | — | The Rücknahmepreis to use for the fiction. |
| GT-INVSTG-043 | not reached | — | — | Abs. 3 Satz 1 — the fiktive-Veräußerung gain is deemed to flow only on the **actual** disposal. Nothing reaches it because GT-INVSTG-040 is not reached either, but it changes what a fix would have to do: see below. |
| GT-INVSTG-054 | **not reached** | — | — | Rz. 20.4, as amended 29.04.2021: in a year the § 22 Abs. 1 fiction bites, the Vorabpauschale is set for the **whole** calendar year — a deemed acquisition triggers no Abs. 2 reduction — and the Teilfreistellung follows the rate at the Abs. 3 Zuflusszeitpunkt. Not reached for the same reason as GT-INVSTG-040: nothing detects a rate change. **It constrains the eventual § 22 fix**, which must not pro-rate the Vorabpauschale of the fiction year. Its Sätze 3–5 are a 2018/2019 Steuerabzug Nichtbeanstandung and are out of scope by their own wording. Recorded now because the audit found the 29.04.2021 amendment, which no file in this repository had. |

**GT-INVSTG-043 changes the shape of the GT-INVSTG-040 gap.** Implementing § 22 is not "emit a
disposal in the year the rate changes". Abs. 3 Satz 1 defers the Zufluss to the actual disposal, so
a correct implementation must **carry** a per-lot deferred gain across years and release it when
the units are sold — the same multi-year per-lot record the Zeile 53 deduction needs
(GT-INVSTG-034), and the engine holds neither. Emitting the gain in the year of the fiction would
declare income a year or more early and then omit it at the real disposal.

**GT-INVSTG-040 is the sharpest of the "not reached" rows.** Editing a fund's cached
classification changes the Teilfreistellung applied from that run onward, with no deemed disposal
and no reacquisition — which is what § 22 Abs. 1 Satz 1 requires if the *applicable rate* actually
changed. Reclassifying to correct a past mistake is a different thing from a rate that changed,
and nothing distinguishes them.

### Basiszins (BMF, under § 18 Abs. 4)

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-INVSTG-050 | implements | `src/tax_law/registry.py` `BASISZINS_PCT` — law as data, not configuration | `test_tax_law_registry.py::TestBasiszinsReferenceConsistency` | **The consistency test parses the table out of `reference/bmf-guidance/basiszins-vorabpauschale.md` and asserts the registry equals it row for row.** The doc is authoritative; the code follows. |
| GT-INVSTG-051 | implements | `vorabpauschale_year = tax_year - 1` | `test_vorabpauschale.py::TestVorabpauschaleDeclarationYear` | |
| GT-INVSTG-052 | out of scope | — | — | How the Bundesbank derives the rate. |
| GT-INVSTG-053 | implements | `registry.basiszins_pct()` distinguishes the two cases | `test_tax_law_registry.py::TestBasiszinsLookup` (all four tests), `test_vorabpauschale.py::TestBasiszinsTableCoverage` | Pre-2018 → INFO, nothing missed. 2018 or later and absent → **WARNING**, because skipping would understate deemed income. 2021/2022 are negative *values*, not gaps. |

---

## Anlage SO — § 23 EStG

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-ESTG23-001 | implements | assets classified `PRIVATE_SALE_ASSET` | `test_section23_holding_period.py::TestSection23LedgerClassification` | |
| GT-ESTG23-002 | implements | the broker's trade date is used, never the settlement date | `test_section23_holding_period.py` | Trade date is when the contract became binding — the obligatorisches Geschäft the rule points at. |
| GT-ESTG23-003 | implements | `is_within_section23_speculation_period()` in `src/tax_law/holding_period.py` | `test_section23_holding_period.py::TestSpeculationPeriodRule`, `test_section23_holding_period_guards.py` | Anniversary arithmetic per §§ 187/188 BGB, implemented once and called from the three `FifoLedger` disposal paths. A `days <= 365` shortcut is wrong across a 29 February and is not used. |
| GT-ESTG23-004 | **choice under uncertainty** | `src/tax_law/holding_period.py` | `test_section23_holding_period.py::TestSpeculationPeriodRule` | See below. |
| GT-ESTG23-005 | **deviates** | — | — | **The ten-year period is not implemented**; one year is applied unconditionally. Idle for the instruments currently classified `PRIVATE_SALE_ASSET`, which produce no income from the asset itself — but that is a property of those instruments, not a safeguard. Adding an income-producing "anderes Wirtschaftsgut" makes this wrong. **Re-decided unchanged by the issue #66 audit, 2026-08-08:** the claim's text lost its reference to Crypto ETPs, but the instruments the taxpayer has classified `PRIVATE_SALE_ASSET` are the same set and none of them produces income from the asset itself, so the deviation's scope and its idleness are both where they were. |
| GT-ESTG23-006 | **deviates** | `consume_short_lots_for_cover` in `src/engine/fifo_manager.py` | — | Nr. 3 has **no holding period**. The engine applies the Nr. 2 Jahresfrist to a short cover, so a short held longer than a year would be reported exempt where Nr. 3 makes it taxable. Unexercised — no sell-to-open on any `PRIVATE_SALE_ASSET` in the maintainer's data (checked 2026-08-02) — and wrong if reached. |
| GT-ESTG23-007 | not reached | — | — | Inherited or gifted assets carry the predecessor's acquisition date. No input represents an unentgeltlicher Erwerb. |
| GT-ESTG23-008 | implements | `src/engine/fifo_manager.py`; the cost and proceeds it works from are built in `src/processing/enrichment.py`, which does not look at the asset's category — a § 23 asset trades as `AssetClass` `STK` and takes the same path as a share | `test_section23_holding_period.py`, `test_section23_trade_costs.py` | Commission and transaction tax raise the cost of a purchase and lower the proceeds of a sale, as under § 20 (GT-ESTG20-068). A commission **credit** lowers the cost and raises the proceeds: the net execution-price arrangement under GT-ESTG20-069 and § 23 Abs. 3 Satz 1. Re-decided 2026-09-22: implements; separate services and independent refunds are not inferred from execution pricing. |
| GT-ESTG23-009 | out of scope (deliberate) | — | — | The Freigrenze applies to the taxpayer's *total* private-sale gain for the year, which one portfolio cannot establish. The engine reports the gross figure and leaves the threshold to the taxpayer and the Finanzamt. |
| GT-ESTG23-010 | implements | `src/engine/loss_offsetting.py` — § 23 pool separate from § 20 | `test_group6_loss_offsetting.py` | Carryback and carryforward are the Finanzamt's step. |
| GT-ESTG23-011 | **deviates** (crypto ETPs) / **implements — as a question, not an inference** (Rohstoff ETCs) | `src/classification/asset_classifier.py` — the two dialog options that are Rz. 57's two outcomes; `AssetCategory.SONSTIGE_KAPITALFORDERUNG` | `test_sonstige_kapitalforderung.py::TestSonstigeKapitalforderungIsClassifiable` | **Re-decided 2026-08-08 by the issue #66 audit; the Rohstoff half is unchanged from the 2026-08-07 re-decision under issue #53.** Rz. 57's test — physical backing plus an exclusive delivery-or-proceeds claim — turns on the Emissionsbedingungen, which no input carries, so the engine asks. Both of Rz. 57's outcomes have had a dialog option since #53; before it, an unbacked ETC had nowhere to go but `BOND` or a wrong category. `test_it_is_never_a_preliminary_classification` holds the store's own conclusion in place: no heuristic may infer this from an asset class label. **What the #66 audit changed:** the claim no longer lists Crypto ETPs, because Rz. 57 reaches Gold und andere Rohstoffe only and the crypto row never had an authority. The `deviates` this opened — the engine answering the crypto question in three places, the `preliminary_classify` branch, the dialog default it produced, and the § 23 option label naming *Krypto-ETP* — **is closed**: `preliminary_classify` returns `UNKNOWN` for a crypto product, which is the one category that suppresses the dialog default and raises in a non-interactive run, and the label names no instrument the Randziffer does not reach. Guarded by `test_crypto_etp_is_not_pre_answered.py`, 19 tests. The category a crypto ETP belongs in is now the taxpayer's determination alone, recorded in the classification cache; the engine holds no position and states none. |
| GT-ESTG23-012 | implements | `SECTION_23_ESTG_TAXABLE_GAIN` / `_TAXABLE_LOSS` / `_EXEMPT_HOLDING_PERIOD_MET` | `test_section23_holding_period_guards.py::TestSpeculationPeriodFlagIsTruthful` | Dates that cannot decide the question raise `ProcessingError` rather than defaulting to exempt — an undecidable § 23 case is unreported income, not tax-free income. |
| GT-ESTG23-013 | implements | `src/engine/fifo_manager.py` — currency ledgers consume lots first-in-first-out | `test_group7_currency_fifo.py` | Nr. 2 Satz 3, the statutory FIFO fiction for *gleichartige Fremdwährungsbeträge*. **This is the Tier 1 grounding the currency FIFO always needed and never had.** Until this audit the store cited § 20 Abs. 4 Satz 7, which is confined to vertretbare Wertpapiere in Sammelverwahrung and cannot reach a currency balance. The engine's behaviour is unchanged and was already right; what changes is that it is now sourced. Applies from 31.07.2014 (Art. 2 G. v. 25.07.2014, BGBl. I S. 1266) — earlier assessment years have no statutory ordering for currency. |

**GT-ESTG23-004, open question Q1 — reading chosen: no extension.** The period ends on the
anniversary day whatever weekday it falls on. Reasons: it follows FG Köln 02.06.1997, the only
§ 23-specific authority located, and what the commentary describes as practice; and the extension
reading would make the Jahresfrist depend on a Land-specific Feiertagskalender, itself an
unresolved input. **This is a choice between two defensible readings** — BFH IX R 68/98 points the
other way — and it changes a declared figure. A disposal falling between a weekend or holiday
anniversary and the next working day should be reviewed by hand.

### Anlage SO form structure

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-FORM-020 | implements | § 23 gains and losses → Zeile 54 | `test_section23_holding_period.py` | |
| GT-FORM-021 | out of scope | — | — | Same as GT-ESTG23-009. |
| GT-FORM-022 | implements | separate § 23 pool | `test_group6_loss_offsetting.py` | |
| GT-FORM-023 | **choice under uncertainty** | `src/engine/fifo_manager.py` applies FIFO to § 23 assets | `test_section23_holding_period.py` | See below. **Re-decided unchanged by the issue #66 audit, 2026-08-08:** the claim's text no longer offers Crypto ETPs as an example of the *anderes Wirtschaftsgut* the gap bites on. The gap itself is unmoved — it is defined by § 23 Abs. 1 Satz 1 Nr. 2 Satz 3 covering currency and nothing else, not by which instruments are listed beside it. |

**GT-FORM-023, open question Q6 — reading chosen: FIFO.** § 23 contains no lot-identification
rule, and § 20 Abs. 4 Satz 7 is confined by its wording to *vertretbare Wertpapiere* in
Sammelverwahrung, so it does not reach an "anderes Wirtschaftsgut". FIFO is applied for
consistency with the § 20 treatment and because it is the conservative ordering in a rising
market. **No source supports it.** Until 2026-08-03 the store asserted this was "the general
principle applied by the Finanzverwaltung", which was unsourced. The ordering decides which
acquisition date is compared with the disposal date, so it can decide taxability outright.

---

## Anlage KAP-INV form structure

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-FORM-030 | implements | `ANLAGE_KAP_INV_*_AUSSCHUETTUNG_GROSS`, one per fund type | `test_vorabpauschale.py::TestGetVpReportingCategory` | Zeilen 4–8. |
| GT-FORM-031 | implements | `ANLAGE_KAP_INV_*_VORABPAUSCHALE_BRUTTO` | `test_vorabpauschale.py` | Zeilen 9–13, carrying the **prior** calendar year's Vorabpauschale. |
| GT-FORM-032 | implements | `ANLAGE_KAP_INV_*_GEWINN_GROSS` | `test_group6_loss_offsetting.py::TestLossOffsettingFundIsolation` | Zeilen 14/17/20/23/26. |
| GT-FORM-033 | implements | `src/engine/loss_offsetting.py` (Zeile 53 total; gain lines net of it) | `test_vorabpauschale.py::TestZeile53VorabpauschaleDeduction`, `test_vorabpauschale_zeile53_engine.py` | See GT-INVSTG-034. Was **deviates** until issue #63. |
| GT-FORM-034 | implements | gross figures throughout | `test_vorabpauschale.py`, `test_group6_loss_offsetting.py` | Teilfreistellung is used internally for offsetting, never applied to a declared amount. |

**Not produced at all:** Zeilen 15/18/21/24/27 (bestandsgeschützte Alt-Anteile, § 56 Abs. 6 Satz 1
Nr. 2 InvStG) and Zeilen 16/19/22/25/28 (fiktive Veräußerung of non-bestandsgeschützte Alt-Anteile
at 31.12.2017). Both need pre-2018 data the engine has no source for — an acquisition date before
01.01.2009, and a 31.12.2017 valuation. A taxpayer holding such units must complete these by hand.

---

## Foreign tax credit and withholding — §§ 32d, 34c, 34d, 36, 45a

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-CREDIT-001 | out of scope | — | — | The 25 % rate is applied by the Finanzamt. The engine produces pre-tax figures. |
| GT-CREDIT-002 | implements (as premise) | the whole pipeline | — | Every figure the engine produces exists *because* of Abs. 3: foreign broker, no inländische Zahlstelle, no Steuerabzug, so the income must be declared. |
| GT-CREDIT-003 | not reached | — | — | There is no Steuereinbehalt on foreign-broker income to review. |
| GT-CREDIT-004 | implements | withholding events summed into `ANLAGE_KAP_FOREIGN_TAX_PAID`, each row first reduced to its treaty-creditable amount (GT-CREDIT-026) | `test_withholding_tax_linker.py`, `test_foreign_withholding_treaty_guard.py` | The sum is now of the *anrechenbare* per-row amount, not the raw withheld tax. Equal to the raw sum while no row exceeds the treaty rate — incidence at GT-CREDIT-026 (0 of 28 US rows VZ 2023–2025 above the rate), so the guard moves no historical figure. The reduction covers the states and income kinds with a creditable rate in the store (GT-CREDIT-029/030); every other row stops the run (GT-CREDIT-026, F1). **Reversals, 2026-09-22:** a positive withholding row reverses an earlier one and both are dropped — only tax *festgesetzt und gezahlt* is credited. One in the window (VZ 2025, NL); VZ 2025 Zeile 41 fell by exactly two bookings of that tax, VZ 2023/2024 unchanged. `test_cash_transaction_reversals.py`. |
| GT-CREDIT-005 | out of scope | — | — | The per-Kapitalertrag 25 % ceiling is applied by the Finanzamt. |
| GT-CREDIT-006 | out of scope | — | — | The per-VZ ceiling likewise. |
| GT-CREDIT-007 | out of scope | — | — | Günstigerprüfung is a taxpayer election (Zeile 4). |
| GT-CREDIT-010 | out of scope | — | — | Definitional scope of § 34d. |
| GT-CREDIT-011 | not reached | — | — | The Schuldner-domicile test has no expression on the declaration for a foreign-broker portfolio under Abgeltungsteuer. |
| GT-CREDIT-012 | not reached | — | — | The § 34c carve-out is why no per-country computation is needed. Nothing to implement. **Re-decided unchanged 2026-09-22:** § 34c Abs. 6 Sätze 2 and 3 added to the store; Satz 2 carries the same carve-out for treaty cases. |
| GT-CREDIT-013 | not reached | — | — | Günstigerprüfung stays inside the carve-out, so it does not restore a per-country mechanism either. |
| GT-CREDIT-014 | **deviates (no longer silently)** | `src/engine/loss_offsetting.py` `_is_german_kest` | `test_german_kest_detection.py` | Domicile is now tested by two proxies — issuer country where the broker supplies one, the 26.375% composite otherwise. Rows matching neither are still treated as foreign, but that is now a stated fallback rather than an untested assumption. |
| GT-CREDIT-020 | not reached | — | — | German KESt is withheld upstream, not by the broker. |
| GT-CREDIT-021 | **deviates — by design** | — | `test_german_kest_detection.py::TestTheExcludedAmountReachesTheUser` | Zeilen 7/37/38/39 have no representation, and will not: they transcribe a Steuerbescheinigung the engine does not hold. The amount reaches the user as a data gap instead. |
| GT-CREDIT-022 | implements | `src/engine/loss_offsetting.py` `_record_german_kest_gap` | `test_german_kest_detection.py::TestTheExcludedAmountReachesTheUser` | The report now names the amount, the Zeilen 7/37/38 route, and that § 36 Abs. 2 Satz 2 bars the credit without a certificate obtained from the German custodian. |
| GT-CREDIT-023 | not reached | — | — | That the certificate is obtainable on request is a fact about the broker, not a computation. |
| GT-CREDIT-024 | not reached | — | — | § 36a Cum/Cum, with a EUR 20 000 Bagatellgrenze. |
| GT-CREDIT-025 | **implements (detection); deviates (credit route)** | `src/engine/loss_offsetting.py` `_is_german_kest` | `test_german_kest_detection.py`, `test_withholding_tax_linker.py::test_german_kest_is_excluded_from_zeile_41` | German KESt is identified and kept off Zeile 41. It is not re-declared — see below. |
| GT-CREDIT-026 | **implements (dividends from US, CA, FR, JP, KR, NL, TW; Irish interest); not reached -- the run stops (every other source state or income kind)** | `src/tax_law/treaty_withholding.py` (`assess_withholdings`, all the rows linked to one income together), applied in `src/engine/loss_offsetting.py` at the Zeile 41 sum | `test_foreign_withholding_treaty_guard.py` (over-treaty-rate capped, cent tolerance, unknown state not defaulted, unlinked reported, B8 two rows on one dividend measured together), `test_german_kest_detection.py::test_foreign_code_wins_over_a_german_looking_rate` | Only the anrechenbare amount reaches Zeile 41: the withheld tax reduced by the Ermäßigungsanspruch, capped at the treaty rate where the source state's law and the DBA coincide (cap-and-report, WARNING gap `FOREIGN_WHT_ABOVE_TREATY_RATE`). At or below the rate nothing moves. The engine applies it where the source state applies the DBA, whether the two grounds of the BZSt sentence (*"nach dessen nationalem Recht oder aufgrund eines DBA"*) give the same rate (a US dividend on branch A) or different ones (FR, TW, Irish interest: the lower rate, the BZSt's column C, GT-CREDIT-029/030). Where the source state does not apply the DBA's allocation (Art. 21, branch B) it is Q23 and not reached. **Incidence, measured 2026-09-22** on `data_import/Cash_Transactions-{2023,2024,2025}.csv`: 28 dividend/PIL withholding rows carry the `- US TAX` suffix (10 / 6 / 12), each paired to its income row by account, symbol, settle date and kind; 0 are above 15 % + 1 cent. `IssuerCountryCode` is set to `US` on 21 of the 28 (3 / 6 / 12); the other 7, all VZ 2023, have it blank. Since 2026-09-23 the parser fills a blank column from the `- XX Tax` suffix (`DomainEventFactory`, `test_withholding_state_from_suffix.py`), so all 28 reach the guard as US. Measured on `Cash_Transactions-{2022..2025}.csv`: the suffix is on every dividend/PIL withholding row and agrees with the column on all 49 rows where both are set. **Exempt RIC dividend** ([GT-CREDIT-027] *falls keine Befreiung*): the guard cannot tell one and would credit up to 15 % where 0 is right; US-suffixed withholding paired to income described as exempt, 0 of 28 — assumption written at `CREDITABLE_DIVIDEND_RATES` in `src/tax_law/registry.py`, no work opened. The Satz 1/Satz 3 ceilings stay the Finanzamt's (GT-CREDIT-005/006); this is the distinct treaty-rate cap. Red-first verified (guard disabled → all guard tests red); calibrated against the EUR/foreign-currency mutation. **Re-decided 2026-09-22 after review:** the store claim no longer asserts the Ermäßigungsanspruch is judged by source-state law alone; position unchanged for branch A. **Re-decided 2026-09-23 after the third review: deviates outside US dividends.** The claim is not US-specific, but the store then carried a treaty rate for the US only, so every other row kept its withheld amount on Zeile 41 under a WARNING. Measured 2026-09-23 on `data_import/Cash_Transactions-{2023,2024,2025}.csv`, each dividend withholding row with a `- XX TAX` suffix paired to the one income row of the same account, symbol, settle date and per-share token (German KESt excluded): **14 non-US rows are above 15 % + 1 cent** — FR 1 in 2023; FR 1, JP 1 in 2024; FR 3, JP 2, TW 3, KR 3 in 2025 — and reach Zeile 41 as withheld in VZ 2023, 2024 and 2025. Whether any of the excess is creditable is unknown until the store has those states' rates; 15 % is only the comparison threshold, not their rate. Closed by the follow-up recorded in the issue #78 PR: a store extension for the treaty rates of CA, FR, IE, JP, KR, NL, TW and for interest, then a `fix-func(engine)` adding the table rows; done when no `FOREIGN_WHT_RATE_NOT_VERIFIED` remains on VZ 2023–2025. **Dividend half closed 2026-09-23** by [GT-CREDIT-029]: FR 12,8, JP/CA/KR/NL 15, TW 10 on share dividends. **Interest half closed 2026-09-23** by [GT-CREDIT-030] (Irish interest 0 %, taxing state from `BROKER_ENTITY_COUNTRY`). **Blank-country half closed 2026-09-23:** the 11 VZ 2023 rows with a blank `IssuerCountryCode` (7 US, 3 CA, 1 FR) take their state from the `- XX Tax` suffix; VZ 2023 Zeile 41 moves by the FR row's excess over 12,8 %. **Formerly deviated:** any state or fund distribution outside the table kept its withheld amount under `FOREIGN_WHT_RATE_NOT_VERIFIED`; see F1 below. **Re-decided 2026-09-23 after the sixth review, unchanged:** the store now says the BZSt table is written for the paying agent's credit, the rule it states being § 32d Abs. 5 Satz 1, which the Veranlagung applies too; and it narrows the open case to a source state that does not apply the DBA's allocation (Q23), a divergence in rate where it does apply the DBA being settled at the lower rate. This row previously said the engine applied the reduction only where both grounds give the same rate, which the FR, TW and Irish-interest rates had already made untrue. **Re-decided 2026-09-23 after the maintainer's review (F1):** a row with no supported creditable amount -- no rate for its state, income kind or year, no linked income, or no state -- no longer reaches Zeile 41 as withheld. It is itemised (`FOREIGN_WHT_RATE_NOT_VERIFIED`, `_RATE_YEAR_NOT_RESEARCHED`, `_UNLINKED`) and the run stops (`FOREIGN_WHT_CREDIT_UNSUPPORTED`, FAIL_FAST), naming every such row. So no declared figure rests on an unsupported credit; the uncovered cases are *not reached* rather than *deviates*. |
| GT-CREDIT-027 | **deviates** (the RIC exemption and the REIT conditions are assumed, not established) | `src/tax_law/registry.py` `CREDITABLE_DIVIDEND_RATES` (US, per year) and `CREDITABLE_DIVIDEND_KINDS` (share dividends and fund distributions) | `test_foreign_withholding_treaty_guard.py` (B1/B2/B3 US 15 %; B4 an unsourced state is not defaulted), `test_withholding_link_same_day_incomes.py` (the tax measured against its own income) | The US row of the per-year rate table; the other states are GT-CREDIT-029, Irish interest GT-CREDIT-030. A source state or income kind with no rate is reported `FOREIGN_WHT_RATE_NOT_VERIFIED` and stops the run (F1, GT-CREDIT-026) — never defaulted. Adding one is a store extension plus one table row. **Re-decided 2026-09-23: deviates on how the rate is measured.** The store now states that Art. 10 Abs. 2 limits all the tax on one dividend against that dividend's gross. The guard measures each tax row alone against the income the linker gave it, and the linker breaks a tie between two same-day incomes by list order — on the four DEM dates in VZ 2023/2024 (a payment in lieu and a dividend on one day) three tax rows are "sequential" to both. No figure moves today (measured: every cross-link is either not US-coded or at or below 15 %). Closed by the two `fix-func` commits that follow in the issue #78 PR (linker tie-break; per-dividend assessment). **Linker half closed 2026-09-23:** between equal scores the linker takes the income booked nearest before the tax row (`WithholdingTaxLinker._find_best_match`); `test_withholding_link_same_day_incomes.py`. **Per-dividend half closed 2026-09-23:** every foreign row linked to one income is assessed together (`assess_withholdings`); `test_foreign_withholding_treaty_guard.py::test_b8_two_tax_rows_on_one_dividend_are_measured_together`. Position: **implements** for the US rate; rows on one income naming different source states are reported rate-not-verified rather than split. **Re-decided 2026-09-23 after the fifth review, unchanged: implements.** The store now quotes Art. 10 Abs. 4 Satz 3: a US REIT's dividend is on the 15 % only if the holder meets one of three conditions (for a natural person, not more than 10 % of the REIT); otherwise Abs. 2 sets no ceiling. The engine does not check the condition and gives every US share dividend 15 % — **assumed, not checked, that a REIT holding is at most 10 %**; the export carries no holding percentage, and the assumption is written at `CREDITABLE_DIVIDEND_RATES`. Were it false, the treaty would not limit the US tax on that dividend, and a cap at 15 % could understate Zeile 41. Incidence, measured 2026-09-23 on `data_import/Cash_Transactions-{2022..2025}.csv`: the 30 `- US TAX` withholding rows come from five payers (DEM, GOOGL, IBKR, MU, NVDA), none a REIT — 0 of 30. **Re-decided 2026-09-23 after the maintainer's review (F2):** the store now states what the two conditions of the 15 % turn on. The RIC exemption is whatever part of *each* dividend the RIC reports as an interest-related or short-term capital gain dividend (26 U.S.C. § 871(k)), so neither the withholding nor the fund's kind shows it. REIT status is held per taxable year (§ 856(c)(1)), and the Art. 10 Abs. 4 Satz 3 conditions concern the holder's participation. The registry applies 15 % to every US row on the assumption that neither condition bites, and the absence of an exemption marker cannot establish that. **Deviates** until the `fix-func` that follows in this PR takes both facts from the taxpayer, per instrument and year, and stops the run where they are missing. **Linker, 2026-09-23 (maintainer's review, F3):** the linker now matches a tax row only against income of its own account; another account's dividend is another dividend. `test_withholding_link_account_local.py`. |
| GT-CREDIT-028 | **implements (branch A: income and 15 % credit); branch B not reached (Q23)** | `src/parsers/domain_event_factory.py` (branch A income character, per GT-INVSTG-059); credit capped to 15 % via `src/tax_law/treaty_withholding.py` (GT-CREDIT-026/027) | `test_payment_in_lieu_credit_route.py` (branch A income), `test_foreign_withholding_treaty_guard.py` (15 % credit) | On branch A the substitute payment is an Art. 10 dividend and 15 % is creditable. Branch B (Art. 21) is `open-legal-questions.md` Q23 — 15 % on the text of § 32d Abs. 5 Satz 1 and Rn. 207a, or 0 % on the BZSt's *"aufgrund eines DBA"*. Not reached: the engine takes branch A unconditionally on the taxpayer's assertion at GT-INVSTG-059, so no figure depends on Q23. **Re-decided 2026-09-22 after review.** Superseded position: *"credit figure invariant"* across both readings, which cited only half of the BZSt sentence and mischaracterised § 34c Abs. 6 Satz 3; recorded as settled without an open-questions entry. **Re-decided 2026-09-23 after the third review:** reading A itself is a subsumption, not a sourced rule — the payer is in fact the borrower, and the payment enters Art. 10 through Abs. 5 and the agreement of both states on its character, not through Abs. 1 (the store now says so). **It decides real figures:** measured 2026-09-23 on `data_import/Cash_Transactions-{2023,2024,2025}.csv`, payment-in-lieu rows carrying US tax — VZ 2023: 5 (DEM, an Aktienfonds, 3 → KAP-INV Zeile 4; IBKR, a share, 2 → Zeile 19), VZ 2024: 1 (DEM), VZ 2025: 0. Their tax is on Zeile 41. All of them reach the guard as US: the 4 with a blank `IssuerCountryCode` take it from the `- US Tax` suffix (since 2026-09-23). Under reading A that tax is creditable up to 15 %; were Art. 21 to apply even on branch A, it would fall into Q23. |
| GT-CREDIT-029 | **implements** (share dividends; per assessment year 2023–2026); **deviates** (the rate is keyed on the income kind, not on the instrument being an ordinary share) | `src/tax_law/registry.py` `CREDITABLE_DIVIDEND_RATES` (one entry per researched edition), `creditable_dividend_rate`; applied by `src/tax_law/treaty_withholding.py` | `test_foreign_withholding_treaty_guard.py::test_b9_*` (FR at 25 % → 12,8; FR at 12,8 in full; TW 21 % → 10; JP 15,315 % → 15; a FR fund distribution not given the rate), `::test_b10_*` (each researched year uses its own rate; 2022 and 2027 get none), `test_tax_law_registry.py::TestCreditableDividendRatesReferenceConsistency` (registry equals the store's per-edition columns) | The BZSt column-C creditable dividend rates for FR, JP, CA, KR, NL, TW. **Per year, no carry (fsaupe's rule, 2026-09-23):** a tax year without a researched edition gets no rate; every row is reported under `FOREIGN_WHT_RATE_YEAR_NOT_RESEARCHED`, which names the year, and the run stops (F1). Superseded positions: deviates, the engine carrying the US rate alone; then deviates, one rate for every year. Share dividends only — a fund distribution is outside the table's *Dividenden*: `FOREIGN_WHT_RATE_NOT_VERIFIED`, and the run stops (F1). Measured 2026-09-23: every non-US withholding row in `Cash_Transactions-{2023..2025}.csv` is on a share. **Re-decided 2026-09-23 after the sixth review, unchanged:** the store now quotes the BZSt's Prüfschema for how column C is derived, and says which of two national rates (JP, US) the DBA ceiling is compared with. The registry takes column C directly, so neither moves a rate. **Re-decided 2026-09-23 after the maintainer's review (F2):** the store now gives column F per edition. Kanada, Korea (all four editions), Niederlande (2026 only) and Taiwan carry a profit-participation note beside Frankreich's; the earlier *"Japan, Kanada, Korea and Niederlande carry none"* was a misreading of the flowed text. Each note takes income on a right or share whose payment the payer deducts out of column C, so column C holds for a dividend on an ordinary share only. The registry applies it to every `DIVIDEND_CASH` of the state, whatever the instrument: an instrument within a note, booked by the broker as a dividend, would be credited at column C. **Deviates** until the `fix-func` that follows in this PR limits the non-US rates to an income whose asset is classified Aktie. Incidence, measured 2026-09-23: the 32 withholding rows of `Cash_Transactions-{2023..2025}.csv` taxed by FR, JP, CA, KR, NL or TW (country code, else the `- XX Tax` suffix) are all on an instrument classified `STOCK` in the classification cache; 0 elsewhere, so no figure moves. |
| GT-CREDIT-030 | **implements** (per assessment year 2023–2026) | `src/tax_law/registry.py` `CREDITABLE_INTEREST_RATES`, `creditable_rate`; the taxing state from `config.BROKER_ENTITY_COUNTRY` via `ParsingOrchestrator` → `DomainEventFactory` | `test_foreign_withholding_treaty_guard.py::test_b11_*` (IE → 0; no configured state → the run stops naming the setting; unresearched year → the run stops), `test_broker_entity_country.py`, `test_tax_law_registry.py::TestCreditableInterestRatesReferenceConsistency` | Irish interest withholding is 0 % creditable in each of 2023–2026. **Input the figure depends on: the taxing state**, which the export does not give. It is the country of the broker entity paying the interest, supplied by the taxpayer as `BROKER_ENTITY_COUNTRY` and not re-derived from the export (fsaupe 2026-09-23: Interactive Brokers Ireland Limited, so `IE`; the 2025 annual activity statements name that entity as issuer, and it books the deduction as *Withholding on Interest Received* on the interest it pays). Unset (the template's `None`, or absent from an older `config.py`): no state is assumed; the row is `FOREIGN_WHT_RATE_NOT_VERIFIED` and the run stops, naming the setting (F1). Superseded position: deviates — the parser wrote a hardcoded `IE` and no rate was applied. Incidence, measured 2026-09-23 on `data_import/Cash_Transactions-{2023,2024,2025}.csv`: 41 rows `WITHHOLDING @ … ON CREDIT INT`, VZ 2023 11, 2024 7, 2025 23, all with a blank `IssuerCountryCode`. 15 are described `@ 20%` (Ireland's national rate, B a)); 26 are described `@ 0%` yet carry a withheld amount (VZ 2024 3, VZ 2025 23). Measured against the credit-interest row of the same account, currency and month: the `@ 20%` rows withhold 20 %; the `@ 0%` rows (from Sep 2024) withhold about 10 % (EUR 10.0 %, SGD 9–11 %), a rate neither the export nor the statement explains. It does not move the figure: column D is 0 for any amount Ireland withholds. The description's rate is not read. |
| GT-CREDIT-031 | **not implemented** (CN has no rate in the registry) | — | — | China's column C is *0 / 10*: 10 % on a dividend of a company resident in mainland China, 0 % where China's own law exempts it, and outside column C for an Art. 10 Abs. 2 b investment vehicle. Added 2026-09-23 because the maintainer's VZ 2024 data carries a CN-taxed dividend. Until the `fix-func` that follows in this PR, a CN row has no creditable rate: it is `FOREIGN_WHT_RATE_NOT_VERIFIED`, and from the F1 fix onwards it stops the run. Incidence on the contributor's `Cash_Transactions-{2023..2025}.csv`: 0 CN-taxed rows (measured 2026-09-23, country code or `- CN Tax` suffix). |

**GT-CREDIT-025 / GT-CREDIT-021 / GT-CREDIT-022 / GT-CREDIT-014 — one defect, four claims.**

`src/engine/loss_offsetting.py` sums **every** withholding event into
`ANLAGE_KAP_FOREIGN_TAX_PAID` (Zeile 41) with **no country filter**, and the engine has no
representation of Zeilen 7, 37, 38 or 39 at all. German Kapitalertragsteuer withheld upstream on a
German issuer's dividend is therefore declared as anrechenbare *ausländische* Steuer, on the wrong
line and through the wrong credit mechanism.

### Recognising German KESt in IBKR data

This is an input-data question, not a legal one, which is why it is recorded here and not in the
store. Two signals, and neither is sufficient alone.

**1. `IssuerCountryCode`, where IBKR populates it.** The column exists in the Cash Transactions
export, is parsed onto the withholding event, and is authoritative when non-empty. **Its
availability is a function of export vintage:** essentially absent from older exports, partial in
2024, fully populated in 2025. `XX` occurs as a value and is not a country. A country filter alone
therefore fixes recent assessment years and leaves older ones untouched.

**2. The 26.375 % composite** ([GT-CREDIT-025]), for the years where no country code exists.
Measured against real data, the observed rates cluster at 26.369–26.375 % — the withheld amount is
*not* reproducible from the paired gross by any simple rounding rule. Three hypotheses were tested
against the German-signature rows and each matched exactly half of them: one-step
`round(gross × 0.26375, 2)`, two-step KESt-then-SolZ with half-up rounding, and the same with
round-down. **So any tolerance used here is empirical, not derived, and must be recorded as such.**
Observed deviation from the one-step figure reaches two cents.

**Why the credit cannot simply be moved to Zeilen 7/37/38/39.** [GT-FORM-007] routes it there, but
Zeilen 7–15 are defined as the figures *taken from* the Steuerbescheinigung of the inländische
auszahlende Stelle, and § 36 Abs. 2 Satz 2 bars the credit outright when no certificate is
presented ([GT-CREDIT-022]). Zeile 7 is a transcription of a document the taxpayer holds, not a
figure this engine can compute. Populating it from calculated values would fabricate the one thing
the form defines as copied.

What a fix can therefore do: stop declaring German KESt as ausländische Steuer on Zeile 41, and
tell the user the amount, the correct route, and that the certificate must be obtained from the
German custodian through the broker.

---

## Foreign currency

| Claim | Position | Module | Guarding tests | Notes |
|---|---|---|---|---|
| GT-FX-001 | implements | `FX_CONVERSION_SALE`, `FX_CONVERSION_SHORT_COVER`, `FX_IMPLICIT_SECURITY_PURCHASE`, `FX_IMPLICIT_SECURITY_SALE`, `FX_IMPLICIT_CASHFLOW_EXPENSE`, `FX_IMPLICIT_CASHFLOW_INCOME` → `ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE` / `_VERLUSTE` | `test_group7_currency_fifo.py`, `test_group9_variable_fx.py`, `test_group11_cashflow_currency.py`, `test_fx_rgl_hardening.py` | All currency balances are treated as § 20; see Q7. **The cash-flow debit case (`FX_IMPLICIT_CASHFLOW_EXPENSE`/`_INCOME`) is an extension of this claim, not one of the disposing events Rz. 131 enumerates — see Q9, instance (b).** |
| GT-FX-002 | not reached | — | — | Non-interest-bearing accounts. A margin brokerage account pays or charges interest on balances, so the § 23 branch is not exercised — **but nothing tests the account's actual character.** |
| GT-FX-003 | not reached | — | — | Pure payment accounts. |
| GT-FX-004 | not reached | — | — | Retroactivity to VZ 2009 and the 2025 bank withholding duty both concern German Zahlstellen. |
| GT-FX-005 | implements | as GT-FX-001 | same | § 20 throughout. Reason: the administrative position, and a margin account's balances bear interest. The § 23 reading would make gains after a year tax-free, so this is **not** the taxpayer-favourable choice — and under the grey-area rule in CLAUDE.md it is not a choice at all. BMF 14.05.2025 Rz. 131 states the § 20 treatment at Tier 2, verbatim and verified, drawn on the verzinslich/unverzinslich line; the rule's first condition bars implementing against it, whichever way it falls. **Do not reopen this on the ground that the favourable reading exists.** What remains genuinely open is whether the administration's position is correct, which is Q7 and is not something a generated figure should take a side on. Position changed from *"choice under uncertainty"* on 2026-08-07: Rz. 131 having been verified, following it is compliance, not a selection. |
| GT-FX-006 | **choice under uncertainty** | short currency positions tracked and taxed symmetrically with long ones | `test_group7_currency_fifo.py` | No guidance addresses a negative balance in Privatvermögen. Symmetry is an assumption. |
| GT-FX-007 | **choice under uncertainty — now unsourced outright** | currency legs of securities trades measured separately (`FX_IMPLICIT_*`) | `test_group9_variable_fx.py`, `test_group10_options_variable_fx.py` | See below. |
| GT-FX-008 | implements | `src/engine/fifo_manager.py` — currency lots consumed FIFO | `test_group7_currency_fifo.py` | FIFO for currency, now sourced on both branches: BMF 14.05.2025 Rz. 131 for § 20, § 23 Abs. 1 S. 1 Nr. 2 S. 3 for § 23 ([GT-ESTG23-013]). Same ordering either way, so the unresolved classification in GT-FX-005 does not put the lot order in doubt. |
| GT-FX-009 | implements for account ownership; opening limitations stated | `src/engine/calculation_engine.py` — account-keyed currency ledgers, `_reconcile_currency_soy`, per-account EoY comparison; `src/parsers/parsing_orchestrator.py` — exact opening/closing observations | `test_per_account_currency.py`, `test_currency_opening_boundaries.py`, `test_group7_currency_fifo.py`, `test_data_gap_channel_guards.py`, `test_person_level_snapshot.py::TestACurrencyHeldInTwoAccounts` | Each account's balance is its own Kapitalforderung. Its opening, historical events and tax-year events establish its ledger; assessment aggregates results afterward. **Issue #67 follow-up:** every supplied opening and closing is retained, including zero/tiny quantities. A reported opening below the existing 0.01 currency comparison tolerance clears both replayed long and short lots, without synthesizing dated acquisitions or current-year realizations. The exact sub-tolerance observation remains in the snapshot; the lot ledger treats it as empty within numerical tolerance, not as a tax exemption. A missing opening leaves replay untouched and is not interpreted as zero. Missing closing coverage for a nonzero ledger remains `CURRENCY_EOY_UNRECONCILED`; supplied closings are compared normally, so current-year discrepancies remain visible. **Limitations:** historical input discrepancies are not diagnosed by clearing an empty opening; the existing adjustment-lot policy for nonempty openings and the short-currency filing position remain separate. The absent-opening case still lacks an independently observed opening boundary. |
| GT-FX-010 | **choice under uncertainty** | `InternalCashTransferEvent` (`src/domain/events.py`), built from the export's `CASH` rows by `DomainEventFactory.create_events_from_transfers`; `InternalCashTransferProcessor` (`src/engine/event_processors/transfer_processor.py`) for the tax year and `apply_historical_cash_transfer` (`src/engine/calculation_engine.py`) for earlier years, both through the one `_coordinate_cash_umbuchung` prepare-both-then-commit boundary | `test_per_account_currency.py::TestMovingMoneyBetweenYourAccounts`, `::TestAMoveInAnEarlierYear`, `::TestWhatACashMoveDoesNotDo`, `test_transfers_parser.py::TestCollapsingRowsIntoMoves` | **Reading A of Q15 is taken.** Two questions have to be kept apart. **The disposal's timing is settled, not open:** Rz. 131 ¶2 says the Umbuchung *"stellt … eine Veräußerung der ursprünglichen Kapitalforderung … dar"* — the disposal is at the move. **What no source states is the proceeds**, and that is the selection this row records. Reading B (nothing realised until the balance is later genuinely spent, against its original cost) is not chosen because it relocates the disposal to a later year and so contradicts Rz. 131 ¶2's timing — a reading that needs a Tier 2 sentence to be wrong, which CLAUDE.md's grey-area rule bars whichever way it falls, so the lean-to-the-taxpayer rule does not reach it either. Among the readings that keep the disposal where the Randziffer puts it, Reading A values both legs at the gemeiner Wert of the Kapitalforderung received — the amount moved, converted on the move day per [GT-ESTG20-022] — extending the principle Rn. 65/66, 66a and 69 state for a non-money consideration in every configuration the administration addresses, none of them a currency account. **It is a selection on that valuation, not compliance**, which is why this row is `choice under uncertainty` and not `implements`: no located source names this case, so the store keeps it in *Open questions* stating both readings rather than asserting one. **The two written readings are not a documented legal dispute:** Reading B has no located advocate — it is written down only because the alternative to Reading A must be — so this selection rests on the reasoned interpretation above, not on a dispute or on the lean-to-the-taxpayer rule. **Taxpayer confirmation is not maintainer approval.** The taxpayer chose Reading A for the filing on 2026-09-02; that is the taxpayer's decision, which the taxpayer signs, and it is recorded here as such. It is distinct from the maintainer's review of this claim, which is a separate step and is not asserted by this row. **Not covered, and refuses:** a move naming an account the input reports nowhere else (`TRANSFER_COUNTERPARTY_UNKNOWN`, FAIL_FAST) — [GT-FX-009] reaches the taxpayer's own accounts and IBKR's `INTERNAL` does not establish that; a move naming one account on both sides (a Kapitalforderung is not disposed of to itself — `DataIntegrityError`); a cash row whose `CashTransfer` is zero or blank; a move whose day has no exchange rate, on either path. A move of EUR is read and produces nothing. |

**GT-FX-007 — the citation that supported this was checked and does not say it.** BMF 14.05.2025
was retrieved on 2026-08-03 and Rz. 131 read in full. It addresses Fremdwährungs*beträge* —
accounts, deposits, payment balances — and says nothing about the currency leg of a securities
transaction. The store had cited it for separate measurement; it does not carry that. The engine's
`FX_IMPLICIT_*` treatment is unchanged and remains the conservative reading (it cannot understate
income), but it is now recorded as **reasoned, not sourced**, and it is the most heavily exercised
FX path in the engine. Combined with the blind spot noted at the end of this section — reversing
the order of every historical currency event leaves the suite green — this is the area to treat
with the most caution.

**The currency area, restated after the 2026-08-03 audit.** The BMF circular that carried this
area had never been retrieved; it now has been, and the picture is better in most places and worse
in one:

- **Better:** GT-FX-001, -002, -003 and -004 are verified Tier 2 verbatim (Rz. 131, Rz. 324), and
  currency FIFO has a Tier 1 anchor it never had (GT-FX-008 / GT-ESTG23-013). Rz. 131 also supplies
  detail the engine should be checked against and the store never carried: **prolongation of a
  daily-callable deposit and a change of interest rate are not disposals**, but a balance becoming
  interest-bearing for the first time, or ceasing to be, *is* an event.
- **Worse:** GT-FX-007's only citation turned out not to say what it was cited for.

So the earlier summary — "four of seven claims resting on a circular never retrieved" — no longer
holds. Three choices under uncertainty remain (GT-FX-005, -006, -007) and they are genuine ones.

**Known blind spot:** per CLAUDE.md's *Where the suite is blind*, reversing the chronological order
of every historical currency event leaves the whole suite green. Currency changes must be probed
by mutation, not by running the suite.

### PR #87 acquisition-history and commission-correction boundaries

GT-ESTG20-011/013/014/022: `calculation_engine._require_disposal_history` collects
account-local unresolved acquisition histories before securities disposals. Long and
short reconstructed lots remain unresolved through merger transformations.
`test_account_boundary_integrity.py` covers opening/checkpoint reconstruction,
long/short disposals, multiple affected holdings and merger provenance. PR #88
adds evidenced outgoing/incoming movements and repeats the provenance check at
each current-year consumption, so incoming lots cannot bypass the opening check.

The blanket `COMMISSION_REFUND_UNCLASSIFIED` refusal was a compatibility regression.
On 2026-09-17 the maintainer confirmed the interpretation of the credit as a refund
of an earlier commission overcharge. `DomainEventFactory` now creates a `FeeEvent`
whose `is_refund` flag preserves the credit direction; charges retain their old
direction. Current-year and historical currency processing credit the observed
amount once using its currency and date (GT-FX-001/008). No trade identifier or
arbitrary small-amount threshold is required, and no security link is fabricated.

This restores cash processing, not a general exemption of fee refunds under
GT-ESTG20-010/048 or a newly allocated transaction-cost correction under
GT-ESTG20-011. The credit is no longer mislabelled as capital repayment. The
pre-existing treatment of unallocated fees in the assessment is unchanged; this
correction does not assign the credit to an arbitrary lot or introduce separate
principal income. Tests cover account labels, both adjustment labels, positive
and negative cash balances, charges and historical replay. Currency dispatch is
keyed per account ([GT-FX-009]); the refund credit lands in the sending account's
own currency ledger, not a pool.

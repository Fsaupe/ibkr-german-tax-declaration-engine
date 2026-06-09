# TODO — Per-Depot FIFO

Context: per-Depot (per-custody-account) FIFO for securities **and** FX, plus internal
Depotübertragungen (transfers), is implemented on branch `per-depot-fifo`. The full suite is green
(448) and the 2025 securities figures are byte-identical to the pre-per-Depot baseline. But **two
real bugs and ~69 spurious warnings got past the green suite** and were only found by eyeballing the
PDF/logs. The test gaps below are the priority.

## 0. Why this list exists (lessons from this round)
- A green 448-test run still shipped: (a) FX disposals **silently dropped** when a currency was
  disposed from an account with no opening balance (CHF/HKD), and (b) 46 spurious "SOY quantity
  None" + 23 transfer-reconstruction warnings. **No test exercises a multi-account scenario** — the
  existing harness injects a single `ClientAccountID` (`U_TEST`), so per-Depot logic is effectively
  untested end-to-end. Fixing that harness gap is prerequisite #1.

## 1. Test-harness prerequisite — DONE (self-contained, no shared-helper edits)
- [x] Multi-account input is now built directly in `tests/test_per_depot_cross_account.py`
      (per-row `ClientAccountID` for trades / positions / cash balances + a Transfers file). The
      shared YAML harness was left untouched per the "don't modify existing tests" constraint.

## 2. Per-Depot FX tests — DONE (`test_per_depot_cross_account.py::TestPerDepotFxNoOpeningBalance`)
- [x] **Currency disposed from an account with NO opening balance** → FX realised (the CHF/HKD bug):
      `test_currency_disposed_from_account_without_opening_balance_realises_fx` (asserts FX gain 1200).
- [x] Conversion/consumption in an account with no cash-balance row → ledger created under the
      event's account and realised (same test; FX RGL present means it was not skipped).
- [~] Currency co-held across two accounts / no double-count: implicitly covered (the no-opening
      account gets the correct FX number; a double-count would make it wrong). A dedicated co-hold
      assertion is still nice-to-have.
- [ ] **Non-EUR cash internal transfer** moving currency lots — NOT added: historical cash transfers
      are currently skipped (currency ledgers don't exist at transfer-replay time) and the post-
      transfer SoY balance is authoritative, so there's nothing to assert until §6 lands.

## 3. Internal transfer tests — DONE (`test_per_depot_cross_account.py::TestInternalTransferAcrossYears`, `test_per_depot_transfers.py`)
- [x] buy A → transfer A→B → sell from B (later year) → original basis + acquisition date carried
      (`test_buy_A_transfer_to_B_sell_from_B_carries_basis_and_date`, with a deliberately-wrong SoY
      cost to detect a fallback).
- [x] **Partial** transfer splits the lot; both sides keep original per-unit basis + date
      (`test_partial_transfer_splits_lot_basis_preserved_both_sides`).
- [x] Transfer leg realises no gain (`test_transfer_itself_realises_no_gain`).
- [x] EUR cash transfer ignored; lot drain/receive unit tests (`test_per_depot_transfers.py`).
- [ ] buy→transfer→sell **all within history** (warning case) — deferred to §6 (figure-neutral, and
      hard to assert since it produces no tax-year RGL).
- [ ] Holding-period preservation for a transferred `PrivateSaleAsset` sold <1y (§23) — nice-to-have.

## 4. account_id propagation tests — DONE (`test_per_depot_account_propagation.py`)
- [x] `account_id` reaches TradeEvent, **OptionLifecycleEvent** (the miss that bit us),
      CurrencyConversionEvent (`test_trade_option_lifecycle_and_conversion_carry_account_id`).
- [x] `ClientAccountID` read from a **UTF-8-BOM** file (`test_client_account_id_read_from_utf8_bom_file`).
- [~] CashFlow/WHT/Fee/CorpAction/OptionCashSettlement/BM propagation — exercised indirectly by the
      FX/securities integration tests (per-account routing); a direct unit assertion is nice-to-have.

## 5. Golden / regression tests — DONE (`test_per_depot_cross_account.py`)
- [x] Single-account input collapses to the identical single-ledger result
      (`TestSingleAccountStillCollapses`).
- [x] Co-held-and-sold case proves per-Depot **differs** from merged (sell from B consumes B's
      50@40, not A's older 100@10): `test_co_held_security_sold_from_one_depot_uses_that_depots_lots`.

## 6. Chronological historical reconstruction + short transfers — DONE
- [x] **Chronological replay** ("Pass A"): historical trades/splits/dividends and inter-account
      security transfers now replay in one date-ordered stream (historical mergers run in Pass 2
      after Pass A, so a transfer feeding a historical merger is ordered correctly).
      `simulate_historical_events` was decomposed into a per-event
      `FifoLedger.apply_historical_event`; the dead `initialize_lots_from_soy` /
      `simulate_historical_events` wrappers were removed. A *buy in A → transfer A→B → sell from B*
      entirely within history is now rebuilt lot-exactly (test
      `TestHistoricalTransferReconstruction` — was a real basis bug: it returned the SoY-fallback
      cost, not the carried lot basis).
- [x] **Short-position transfers**: `transfer_out_short_lots` / `receive_transferred_short_lots` +
      engine routing — a short opened in one Depot, transferred, and covered in another carries its
      open-short proceeds + opening date (tests in `test_per_depot_transfers.py` and
      `TestShortPositionTransfer`). This cleared the real-data "insufficient short lots" /
      "transfer source empty" warnings (US55328R1095, US36467W1099 were transferred shorts).
- [x] **Merger ↔ transfer same-day ordering**: discovery tests in
      `test_per_depot_merger_transfer.py` (A–F) showed merger+transfer interactions are handled
      correctly EXCEPT a current-year, same-day transfer of a merger's SOURCE into the merger's
      account (the default intra-day sort runs the merger first → crash). Fixed via
      `_order_current_year_events_for_merger_deps`: the merger event's account disambiguates, so the
      delivering transfer is moved before its merger. Figure-neutral on real data (no mergers).
- Result: the only remaining warning on the real 2025 run is the US45841N1072 reward-share SoY
  fallback (gifted share, no purchase history — expected). All 463 tests pass; the 21 non-currency
  RGLs stay byte-identical to baseline; the only figure change vs the backup is USD FX
  (per-Depot vs merged), reconciled exactly.

## 7. Housekeeping
- [ ] Fold the FX per-Depot fix + SOY-None fix into the branch commits (they touch
      `calculation_engine.py` currency-init / `_AccountAssetView`).
- [ ] Add a regression test asserting a known multi-account run is **warning-clean** (no SOY-None, no
      skipped FX) so this class of regression fails CI instead of needing a human to read logs.
- [ ] (Separate, pre-existing) Decide on scrubbing account id `U7542366` from tracked history
      (`input_data_spec.md`, docs) before pushing.

## Verification per change
`uv run pytest` + re-run the non-interactive 2025 report and diff the non-currency RGLs against the
baseline (must stay identical); confirm the warning log is clean.

"""Awarded shares, end to end, through the real pipeline.

legal_basis: established for ONE programme, Interactive Brokers' Refer-A-Friend award
([GT-ESTG20-063]). [GT-ESTG20-064] applies the Zufluss test to that programme's terms and
puts Zufluss on the lapse of the transfer restriction: the award books a holding without
cost or acquisition date, and the vesting is the receipt;
[GT-ESTG20-065] makes the vesting day's value the Anschaffungskosten on a later disposal;
[GT-ESTG20-067]'s boundary makes a return before Zufluss no tax event at all;
[GT-ESTG20-066] says no rule of law orders a same-day return against a sale. All in
reference/tax-law/estg-22-nr3-leistungen.md.

**What the unit tests beside this file cannot see.** `test_stock_award_lots.py` calls the
three `FifoLedger` methods directly, so it stays green while the events never reach the
ledger at all. Deleting any one of the links in the chain left the whole suite green
before this file existed.

**Calibration, measured link by link** (2026-09-20). Each mutant applied, this file and
`test_stock_award_lots.py` run, the file restored; 48 passed on the unmutated tree (49 once the refusal-site test in the other file was added):

| mutant | red |
|---|---|
| current-year processor entry for the vesting deleted | 6 |
| current-year processor entry for the award deleted | 7 |
| historical dispatch: vesting call replaced by `pass` | 5 |
| historical dispatch: award call replaced by `pass` | 13 |
| processor: `vest_stock_award_lot` call deleted | 4 |
| processor: receipt disclosure call deleted | 3 |
| sale loop: skip of unvested units and its guard deleted | 8 |
| vesting leaves the lot's cost untouched | 12 |
| vesting leaves the lot's date untouched | 10 |
| vesting quantity check disabled | 1 |
| return-after-vesting refusal disabled | 1 |
| factory: positive-vesting-price guard disabled | 2 |
| factory: vesting dated on `ReportDate` | 6 |
| enrichment of stock-award events disabled | 13 |
| vesting price converted at the AWARD day's rate | 1 |
| PDF manual-entry block deleted | 1 |
| parser matching a substring instead of the whole description | 3 (measured earlier, code unchanged) |
| **sort-key band in `get_event_sort_key`** | **0 -- and the suite cannot** |

The sort-key band is written up in CLAUDE.md's *Where the suite is blind*: a stock-award
event carries no broker transaction id, and in the secondary key an empty id sorts before
every trade's id, so it stays ahead of same-day trades with or without the branch.

The award-inside-the-tax-year case is the one that motivated the file: an award or a
reversal that goes unapplied is caught by the end-of-year quantity reconciliation, and
the award also records the undeclared § 22 Nr. 3 receipt. A vesting moves no shares and
would reconcile clean while leaving the lot without a cost, so it is dispatched explicitly
and a sale reaching an unvested lot stops the run.

All identifiers and amounts are invented. CLAUDE.md forbids an account number, a position
value or a cash balance copied from a real export reaching a commit.
"""
from decimal import Decimal

import pytest

from src.domain.enums import TaxReportingCategory
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import trade_row, position_row, conid_for, transfer_row
from tests.support.mock_providers import MockECBExchangeRateProvider

ACCOUNT = "U_AWARD_1"
ISIN = "TEST00AWARD01"
TAX_YEAR = 2023


def grant_row(activity, report_date, award_date, vesting_date, qty, price,
              account=ACCOUNT, isin=ISIN, currency="EUR"):
    """One Grants row, in GRANTS_COLUMNS order."""
    q = Decimal(str(qty))
    p = Decimal(str(price))
    return [account, currency, "STK", "COMMON", isin[:6], f"{isin[:6]} security",
            conid_for(isin), isin, Decimal("1"), report_date, activity, award_date,
            vesting_date, q, p, q * p, ""]


class TestAwardedSharesReachTheLedger(FifoTestCaseBase):

    def _sale_gain(self, results):
        ids = {a.internal_asset_id
               for a in results.asset_resolver.assets_by_internal_id.values()
               if getattr(a, "ibkr_isin", None) == ISIN}
        rgls = [r for r in results.realized_gains_losses if r.asset_internal_id in ids]
        assert len(rgls) == 1, f"expected one disposal, got {len(rgls)}"
        return rgls[0]

    def test_a_vesting_inside_the_tax_year_sets_the_date_and_the_cost(self):
        """The vesting is the Zufluss ([GT-ESTG20-064]), so its day and its price
        are the acquisition.

        The award is booked before the tax year at 4 and vests INSIDE the tax year at 7;
        the shares are sold that year at 10. The gain is 10 - 7 = 3 per unit. A build that
        kept the award price would read 6, with the quantity, and therefore the
        reconciliation, identical either way. The unvested lot also has to survive the
        start-of-year reconciliation for the vesting to find it.
        """
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220302", "20220302", "20230401", "10", "4"),
                grant_row("Stock Award Vesting",
                          "20230405", "20220302", "20230401", "10", "7"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("70"), (
            "the VESTING price is the Anschaffungskosten; 40 would be the award price")
        assert rgl.gross_gain_loss_eur == Decimal("30")
        assert rgl.acquisition_date == "2023-04-01", (
            "acquisition falls at Zufluss, which is the vesting ([GT-ESTG20-064])")

    def test_an_award_vested_before_the_tax_year_gives_the_sale_a_real_basis(self):
        """Covers the historical bucket and the replay dispatch, vesting included.

        Without the grant report the opening snapshot supplies the quantity and the
        engine has no acquisition to measure a sale against; with it, the lot carries the
        vesting's own date and the vesting-day cost ([GT-ESTG20-064], [GT-ESTG20-065]).
        """
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220302", "20220302", "20220902", "10", "4"),
                grant_row("Stock Award Vesting",
                          "20220905", "20220302", "20220902", "10", "6"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "60", price="6")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("60")
        assert rgl.acquisition_date == "2022-09-02"

    def test_a_same_day_vesting_and_sale_take_the_vesting_as_the_basis(self):
        """A vesting and a sale of the vested shares on the same day: the vesting is applied
        first, so the lot is acquired when the sale consumes it. This documents the intended
        intra-day order; it is NOT a guard for the sort-band branch -- deleting that branch
        leaves the vesting ahead of the sale anyway, because a stock-award event carries no
        broker transaction id and an empty id sorts before every trade's id (CLAUDE.md's
        sort-band blind spot)."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220301", "20220301", "20230301", "10", "4"),
                grant_row("Stock Award Vesting",
                          "20230301", "20220301", "20230301", "10", "7")],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-03-01", "-10", "10", "SELL", "C", "T_SELL")],
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("70"), "the sale takes the vesting basis"
        assert rgl.acquisition_date == "2023-03-01", "dated on the vesting day"

    def test_a_return_before_vesting_is_not_a_disposal(self):
        """It produces no RealizedGainLoss of its own, and the survivors are acquired at the
        vesting price -- not at the award's and not at the return row's."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220302", "20220302", "20220902", "10", "4"),
                grant_row("Stock Award Return for Cash Withdrawal",
                          "20220601", "20220302", "20220902", "-4", "9"),
                grant_row("Stock Award Vesting",
                          "20220905", "20220302", "20220902", "6", "6"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-6", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "6", "36", price="6")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.quantity_realized == Decimal("6"), "4 of the 10 were taken back"
        assert rgl.total_cost_basis_eur == Decimal("36"), "at the vesting price"

    def test_a_grant_inside_the_tax_year_books_the_units(self):
        """The current-year dispatch. A grant dated in the declared year goes through
        `StockAwardProcessor`, not the historical replay.

        Without the processor entry the grant is dropped with a log line, the units never
        exist, and the end-of-year reconciliation against the broker's 10 fails. Nothing is
        received yet, so the run states no receipt either.
        """
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230210", "20230210", "20240210", "10", "4"),
            ],
            positions_start_data=[],
            positions_end_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
        )
        assert not results.realized_gains_losses
        assert not [g for g in results.data_gaps if g.code.startswith("STOCK_AWARD_")]

    def test_a_sale_of_unvested_shares_stops_the_run(self):
        """The programme's terms forbid it, and the lot has no cost to measure a gain
        against. A sale that needs unvested units is a missing vesting row or a liquidation
        nobody has classified; either way no figure is emitted."""
        with pytest.raises(BaseException, match="have not vested"):
            self._run_pipeline(
                tax_year=TAX_YEAR,
                grants_data=[
                    grant_row("Stock Award Grant for Cash Deposit",
                              "20230210", "20230210", "20240210", "10", "4"),
                ],
                trades_data=[
                    trade_row(ACCOUNT, ISIN, "2023-08-01", "-10", "10", "SELL", "C", "T_SELL"),
                ],
                positions_start_data=[], positions_end_data=[],
            )

    def test_a_currency_vesting_is_converted_at_the_vesting_days_rate(self):
        """Covers the enrichment link, with the award and the vesting apart in price AND in
        rate. A non-EUR vesting whose price is never converted would reach the ledger with no
        EUR value and stop the run; one converted at the award day's rate, or an award price
        relabelled as the vesting's, would each give a different basis."""
        from datetime import date
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            # 1 USD = 2 EUR on the award day, 3 EUR from the vesting day on.
            custom_rate_provider=MockECBExchangeRateProvider(rate_schedule=[
                (date(2022, 1, 1), Decimal("2")), (date(2022, 9, 2), Decimal("3"))]),
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220302", "20220302", "20220902", "10", "4", currency="USD"),
                grant_row("Stock Award Vesting",
                          "20220905", "20220302", "20220902", "10", "6", currency="USD"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "10", "SELL", "C", "T_SELL",
                          currency="USD"),
            ],
            positions_start_data=[
                position_row(ACCOUNT, ISIN, "10", "60", currency="USD", price="6")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        # 10 shares vested at 6 USD at the vesting day's 3 EUR/USD = 180 EUR.
        assert rgl.total_cost_basis_eur == Decimal("180"), (
            "120 is the vesting price at the award day's rate, 80 the award price at the award "
            "day's rate, 60 the foreign figure taken as EUR")
        assert rgl.total_realization_value_eur == Decimal("300"), (
            "sale proceeds are the actual proceeds at the sale day's rate, untouched by this")
        assert rgl.acquisition_date == "2022-09-02", "the lot is dated on the vesting date"


def test_an_unclassified_activity_kind_stops_the_run(tmp_path):
    """The parser's headline promise, and nothing observed its removal.

    An award and a vesting differ in nothing a parser can see except this text, so a kind
    nobody classified is as likely to move the position as not. Tested at the parser
    rather than through the pipeline because the scenario harness converts an exception
    into a test failure, which would make the refusal unassertable.
    """
    from src.domain.exceptions import DataIntegrityError
    from src.parsers.grants_parser import parse_grants_csv
    from tests.support.csv_creators import create_grants_csv_string

    path = tmp_path / "grants.csv"
    path.write_text(create_grants_csv_string([
        grant_row("Stock Award Reinvestment For Something New",
                  "20220302", "20220302", "20220902", "10", "4"),
    ]), encoding="utf-8-sig")

    with pytest.raises(DataIntegrityError, match="does not classify"):
        parse_grants_csv(str(path))


@pytest.mark.parametrize("description", [
    # BMF 14.05.2025 Rz. 129b para 2: a premium conditioned on buying securities reduces
    # their Anschaffungskosten and is no income -- not the supported programme.
    "Stock Award Grant for Securities Purchase",
    "Stock Award Return for Securities Sale",
    "Stock Award Vesting Accelerated",
])
def test_a_row_of_another_programme_stops_the_run(tmp_path, description):
    """[GT-ESTG20-063] is established for one programme. A row that merely CONTAINS a known
    kind belongs to some other one, whose terms nobody has read; treating it as a § 22
    Nr. 3 award would mis-state both the receipt and the basis. The match is on the whole
    activity description."""
    from src.domain.exceptions import DataIntegrityError
    from src.parsers.grants_parser import parse_grants_csv
    from tests.support.csv_creators import create_grants_csv_string

    path = tmp_path / "grants.csv"
    path.write_text(create_grants_csv_string([
        grant_row(description, "20220302", "20220302", "20230302", "10", "4"),
    ]), encoding="utf-8-sig")

    with pytest.raises(DataIntegrityError, match="does not classify"):
        parse_grants_csv(str(path))


def test_an_award_of_zero_shares_stops_the_run():
    """A no-op award would leave the ledger disagreeing with the broker for a reason
    nothing recorded. Tested at the factory, for the reason above."""
    from unittest.mock import MagicMock
    from src.domain.enums import AssetCategory
    from src.domain.exceptions import DataIntegrityError
    from src.identification.asset_resolver import AssetResolver
    from src.parsers.domain_event_factory import DomainEventFactory
    from src.parsers.raw_models import RawGrantRecord

    classifier = MagicMock()
    classifier.preliminary_classify.return_value = (AssetCategory.STOCK, None)
    factory = DomainEventFactory(AssetResolver(classifier))
    row = RawGrantRecord(**dict(zip(
        [c for c in __import__("src.parsers.column_validator", fromlist=["x"]).GRANTS_COLUMNS],
        grant_row("Stock Award Grant for Cash Deposit",
                  "20220302", "20220302", "20220902", "0", "4"))))

    with pytest.raises(DataIntegrityError, match="zero shares"):
        factory.create_events_from_grants([row])


@pytest.mark.parametrize("price", ["0", "-4"])
def test_a_vesting_without_a_positive_value_stops_the_run(price):
    """[GT-ESTG20-064] values the receipt at the market price of a listed share on the day of
    Zufluss, and [GT-ESTG20-065] makes that the Anschaffungskosten. A listed share has a
    price, so a vesting row at zero carries no valuation at all -- and read as one, it gives
    the lot a nil basis and declares the whole later proceeds as gain, with nothing to tell
    that figure from a measured one. Tested at the factory, where every row-level refusal
    is collected."""
    from unittest.mock import MagicMock
    from src.domain.enums import AssetCategory
    from src.domain.exceptions import DataIntegrityError
    from src.identification.asset_resolver import AssetResolver
    from src.parsers.domain_event_factory import DomainEventFactory
    from src.parsers.raw_models import RawGrantRecord
    from src.parsers.column_validator import GRANTS_COLUMNS

    classifier = MagicMock()
    classifier.preliminary_classify.return_value = (AssetCategory.STOCK, None)
    factory = DomainEventFactory(AssetResolver(classifier))
    row = RawGrantRecord(**dict(zip(GRANTS_COLUMNS, grant_row(
        "Stock Award Vesting", "20230302", "20220302", "20230302", "10", price))))

    with pytest.raises(DataIntegrityError, match="positive per-share value"):
        factory.create_events_from_grants([row])


def test_an_award_or_return_row_may_carry_any_price():
    """Their `Price` is never used -- an award books units without a cost and a return takes
    unvested units back ([GT-ESTG20-067], Boundary) -- so nothing is demanded of it."""
    from unittest.mock import MagicMock
    from src.domain.enums import AssetCategory
    from src.identification.asset_resolver import AssetResolver
    from src.parsers.domain_event_factory import DomainEventFactory
    from src.parsers.raw_models import RawGrantRecord
    from src.parsers.column_validator import GRANTS_COLUMNS

    classifier = MagicMock()
    classifier.preliminary_classify.return_value = (AssetCategory.STOCK, None)
    factory = DomainEventFactory(AssetResolver(classifier))
    rows = [RawGrantRecord(**dict(zip(GRANTS_COLUMNS, grant_row(
        kind, "20220601", "20220302", "20230302", qty, "0"))))
        for kind, qty in [("Stock Award Grant for Cash Deposit", "10"),
                          ("Stock Award Return for Cash Withdrawal", "-4")]]
    assert len(factory.create_events_from_grants(rows)) == 2


class TestTheGuardsAreObserved(FifoTestCaseBase):
    """The guards the suite could not see removed.

    Each of these was probed by deleting the guard and running the whole suite: before
    this class, all three left it green. A guard nothing would notice the removal of is
    the instrument-nobody-broke-on-purpose case CLAUDE.md names.
    """

    def test_a_vesting_is_dated_on_its_vesting_date_not_the_broker_s_report_date(self):
        """Load-bearing whenever the two differ: the vesting day is the acquisition date and
        the day whose ECB rate values the receipt. The broker books the row a day or more
        later; built here with the two apart so the choice is pinned."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220302", "20220302", "20220902", "10", "4"),
                # Restriction lapsed on 2 September, booked by the broker on the 5th.
                grant_row("Stock Award Vesting",
                          "20220905", "20220302", "20220902", "10", "6"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "60", price="6")],
            positions_end_data=[],
        )
        rgls = [r for r in results.realized_gains_losses]
        assert len(rgls) == 1
        assert rgls[0].total_cost_basis_eur == Decimal("60")
        # A lot dated on the report date reconciles identically in quantity, cost basis,
        # proceeds and gain -- only the acquisition date differs (the SoY-snapshot blind
        # spot in CLAUDE.md), so this is the assertion that instruments the choice.
        assert rgls[0].acquisition_date == "2022-09-02"


def _processor_events():
    from decimal import Decimal as D
    from src.domain.enums import FinancialEventType as T
    from src.domain.events import StockAwardEvent
    from tests.test_stock_award_lots import ASSET_ID

    def event(kind, date, qty, price):
        ev = StockAwardEvent(ASSET_ID, date, event_type=kind, award_date="2022-11-02",
                             quantity=D(qty), unit_price_foreign=D(price), currency="EUR")
        ev.unit_cost_basis_eur = D(price)
        return ev
    return (event(T.STOCK_AWARD_GRANTED, "2022-11-02", "10", "4"),
            event(T.STOCK_AWARD_REVERSED, "2023-03-01", "4", "9"),
            event(T.STOCK_AWARD_VESTED, "2023-11-02", "6", "7"))


def test_a_vesting_in_the_tax_year_reports_the_receipt_it_does_not_declare():
    """The one thing standing between a user and an understated return.

    The engine takes the vesting-day value as the Anschaffungskosten -- which LOWERS the
    gain declared on a later disposal -- and cannot declare the matching § 22 Nr. 3
    receipt, because there is no Anlage SO line for it (issue #76). Taking the half that
    reduces a figure and dropping the half that adds one is understatement, so the
    omission has to reach the report rather than only the README.

    Asserted here on the processor; `TestTheAnlageSoAmountsReachTheRunsOutput` asserts the
    same line on the pipeline's output, which carries WARNING gaps.
    """
    from src.engine.event_processors.stock_award_processor import (
        StockAwardProcessor, STOCK_AWARD_RECEIPT_NOT_DECLARED)
    from src.processing.data_gaps import DataGapCollector, GapSeverity
    from tests.test_stock_award_lots import _ledger

    ledger, collector = _ledger(), DataGapCollector()
    for ev in _processor_events():
        StockAwardProcessor().process(ev, ledger, {'data_gap_collector': collector})

    gaps = [g for g in collector.gaps if g.code == STOCK_AWARD_RECEIPT_NOT_DECLARED]
    assert len(gaps) == 1, "the undeclared receipt must reach the report, once"
    assert gaps[0].severity is GapSeverity.WARNING
    assert "EUR 42.00" in gaps[0].detail, "6 vested units x 7, not the award's 4 nor 10 units"
    assert "Anlage SO" in gaps[0].subject and "2023-11-02" in gaps[0].subject


def test_an_award_and_a_return_before_vesting_report_nothing():
    """Only the vesting is the Zufluss. The award is a holding, and shares handed back
    before they were received are neither a receipt nor a negative Einnahme -- the law does
    not know a receipt manufactured only to be repaid ([GT-ESTG20-067], Boundary)."""
    from src.engine.event_processors.stock_award_processor import StockAwardProcessor
    from src.processing.data_gaps import DataGapCollector
    from tests.test_stock_award_lots import _ledger

    ledger, collector = _ledger(), DataGapCollector()
    award, returned, _vesting = _processor_events()
    for ev in (award, returned):
        StockAwardProcessor().process(ev, ledger, {'data_gap_collector': collector})

    assert not collector.gaps
    assert ledger.get_current_position_quantity() == Decimal("6")


class TestTheProgrammeIsConfirmedNotAssumed(FifoTestCaseBase):
    """The export does not name the programme, and the treatment follows from its terms
    ([GT-ESTG20-063]). Matching the row text cannot prove which terms applied, so the user
    states it once in config; grant rows without that statement stop the run."""

    GRANT = [grant_row("Stock Award Grant for Cash Deposit",
                       "20230210", "20230210", "20240210", "10", "4")]

    @pytest.mark.parametrize("value", [None, "SOME_OTHER_PROGRAMME"])
    def test_grant_rows_without_the_confirmation_stop_the_run(self, monkeypatch, value):
        from src import config as app_config
        monkeypatch.setattr(app_config, "STOCK_AWARD_PROGRAMME", value, raising=False)
        with pytest.raises(BaseException, match="STOCK_AWARD_PROGRAMME"):
            self._run_pipeline(
                tax_year=2023, positions_start_data=[],
                positions_end_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
                grants_data=self.GRANT)

    def test_an_empty_grants_file_needs_no_confirmation(self, monkeypatch):
        from src import config as app_config
        monkeypatch.setattr(app_config, "STOCK_AWARD_PROGRAMME", None, raising=False)
        out = self._run_pipeline(tax_year=2023, positions_start_data=[],
                                 positions_end_data=[], grants_data=[])
        assert not out.realized_gains_losses


class TestTheAnlageSoAmountsReachTheRunsOutput(FifoTestCaseBase):
    """The receipt is not declared (issue #76), so what the reader is told to enter is the
    whole of the engine's Anlage SO output for an award. Asserted on the pipeline's own
    output, where a deleted call site shows, not only on the processor."""

    # 10 awarded @4 in 2022, 4 handed back @9 before vesting, 6 vest in 2023 @7:
    # the receipt is 6 x 7 = 42.00 in 2023. Neither 40 (award) nor 16/36 (return) exists.
    GRANTS = [
        grant_row("Stock Award Grant for Cash Deposit",
                  "20220210", "20220210", "20230210", "10", "4"),
        grant_row("Stock Award Return for Cash Withdrawal",
                  "20220601", "20220210", "20230210", "-4", "9"),
        grant_row("Stock Award Vesting",
                  "20230213", "20220210", "20230210", "6", "7"),
    ]

    def _award_gaps(self, out):
        return {g.code: g for g in out.data_gaps if g.code.startswith("STOCK_AWARD_")}

    def _run(self):
        return self._run_pipeline(
            tax_year=2023,
            positions_start_data=[position_row(ACCOUNT, ISIN, "6", "24", price="4")],
            positions_end_data=[position_row(ACCOUNT, ISIN, "6", "42", price="7")],
            grants_data=self.GRANTS)

    def test_a_vesting_in_the_year_states_amount_year_and_destination(self):
        gaps = self._award_gaps(self._run())
        assert set(gaps) == {"STOCK_AWARD_RECEIPT_NOT_DECLARED"}
        receipt = gaps["STOCK_AWARD_RECEIPT_NOT_DECLARED"]
        assert "EUR 42.00" in receipt.detail and "Anlage SO" in receipt.subject
        assert "2023-02-10" in receipt.subject, "the vesting day, not the broker's booking day"

    def test_the_generated_pdf_carries_the_manual_entry(self, tmp_path):
        # The gap collection reaching the pipeline output proved nothing about the PDF: it
        # rendered only the reconciliation gaps, so the summary looked complete with the
        # Anlage SO entry absent. Asserted on the file, built with main's own arguments.
        import pymupdf
        from src.engine.loss_offsetting import LossOffsettingEngine
        from src.reporting.pdf_generator import PdfReportGenerator

        out = self._run()
        summary = LossOffsettingEngine(
            realized_gains_losses=out.realized_gains_losses,
            vorabpauschale_items=out.vorabpauschale_items,
            current_year_financial_events=out.processed_income_events,
            asset_resolver=out.asset_resolver, tax_year=2023,
            apply_conceptual_derivative_loss_capping=False).calculate_reporting_figures()
        pdf = tmp_path / "award.pdf"
        PdfReportGenerator(
            loss_offsetting_result=summary,
            all_financial_events=out.processed_income_events,
            realized_gains_losses=out.realized_gains_losses,
            vorabpauschale_items=out.vorabpauschale_items,
            assets_by_id=out.asset_resolver.assets_by_internal_id,
            tax_year=2023, eoy_mismatch_details=[],
            data_gaps=out.data_gaps).generate_report(str(pdf))
        with pymupdf.open(pdf) as doc:
            text = " ".join(" ".join(page.get_text() for page in doc).split())
        assert "EUR 42.00" in text and "2023-02-10" in text
        assert "Anlage SO" in text and "manuell einzutragen" in text

    def test_an_award_and_a_return_in_the_year_state_nothing(self):
        # Nothing has zugeflossen by the end of 2023: no receipt, and no negative Einnahme
        # for the 4 units handed back. The 6 that remain are held, unvested.
        out = self._run_pipeline(
            tax_year=2023, positions_start_data=[],
            positions_end_data=[position_row(ACCOUNT, ISIN, "6", "24", price="4")],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230210", "20230210", "20240210", "10", "4"),
                grant_row("Stock Award Return for Cash Withdrawal",
                          "20230601", "20230210", "20240210", "-4", "9"),
            ])
        assert not self._award_gaps(out)
        assert not out.realized_gains_losses

    def test_a_vesting_before_the_year_states_nothing_but_still_sets_the_basis(self):
        # Its Einnahme belonged to 2022, which is not the year declared. What it leaves
        # behind is the lot: 6 @7 = 42, against which the 2023 sale is measured.
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[position_row(ACCOUNT, ISIN, "6", "42", price="7")],
            positions_end_data=[],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20210210", "20210210", "20220210", "10", "4"),
                grant_row("Stock Award Return for Cash Withdrawal",
                          "20210601", "20210210", "20220210", "-4", "9"),
                grant_row("Stock Award Vesting",
                          "20220210", "20210210", "20220210", "6", "7"),
            ],
            trades_data=[trade_row(ACCOUNT, ISIN, "2023-09-01", "-6", "10", "SELL", "C", "300")])
        assert not self._award_gaps(out)
        assert sum(r.total_cost_basis_eur for r in out.realized_gains_losses) == Decimal("42")


class TestASameDayReturnAndSale(FifoTestCaseBase):
    """[GT-ESTG20-066]: no rule of law orders a same-day return against a sale, and none is
    needed. A return takes unvested units of ITS OWN award; a sale is measured against
    acquired shares only and never touches unvested ones. The two cannot compete for a
    unit, so the result may not depend on how the input happens to be ordered."""

    @pytest.mark.parametrize("historical", [False, True])
    @pytest.mark.parametrize("reverse_rows", [False, True])
    def test_the_sale_is_measured_against_the_bought_shares(self, historical, reverse_rows):
        # Award 10, buy 10 @9, then on ONE day hand back 4 and sell 8 @10: the sale takes
        # 8 of the bought shares = 72, whatever the order. 2 bought + 6 unvested remain;
        # the 2 are sold later (18). In the historical variant the 6 vest in 2023 @7 and
        # stay held, so the closing position is 6 either way.
        y = 2022 if historical else 2023
        grants = [
            grant_row("Stock Award Grant for Cash Deposit",
                      f"{y}0102", f"{y}0102", f"{y + 1}0102", "10", "4"),
            grant_row("Stock Award Return for Cash Withdrawal",
                      f"{y}0601", f"{y}0102", f"{y + 1}0102", "-4", "4"),
        ]
        if historical:
            grants.append(grant_row("Stock Award Vesting",
                                    "20230102", "20220102", "20230102", "6", "7"))
        trades = [
            trade_row(ACCOUNT, ISIN, f"{y}-02-01", "10", "9", "BUY", "O", "100"),
            trade_row(ACCOUNT, ISIN, f"{y}-06-01", "-8", "10", "SELL", "C", "200"),
            trade_row(ACCOUNT, ISIN, "2023-09-01", "-2", "10", "SELL", "C", "300"),
        ]
        if reverse_rows:
            grants.reverse()
            trades.reverse()
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=(
                [position_row(ACCOUNT, ISIN, "8", "72", price="9")] if historical else []),
            positions_end_data=[position_row(ACCOUNT, ISIN, "6", "42", price="7")],
            grants_data=grants, trades_data=trades)

        sales = out.realized_gains_losses
        later = [r for r in sales if r.realization_date == "2023-09-01"]
        assert sum(r.total_cost_basis_eur for r in later) == Decimal("18"), (
            "the bought shares (acquired 2022/2023-02-01) precede the vested award in FIFO")
        if not historical:
            same_day = [r for r in sales if r.realization_date == "2023-06-01"]
            assert sum(r.total_cost_basis_eur for r in same_day) == Decimal("72")
        assert not [g for g in out.data_gaps if "REVERSAL_ORDER" in g.code], (
            "a scheduling convention is not something for the reader to assess")


def test_a_grants_window_hole_stops_the_run_unit():
    """The condition, unit level: a hole in a SUPPLIED Grants export is refused (FAIL_FAST);
    a complete supplied export and a total absence are both quiet. Mirrors the Transfers
    window rule, minus the multi-account gate -- an award belongs to one account.

    Red on the base: `_require_a_complete_grants_window` did not exist, so a grants hole was
    only logged in data_preparation and nothing stopped the run.
    """
    from src.engine.calculation_engine import (
        _require_a_complete_grants_window, GRANTS_WINDOW_INCOMPLETE)
    from src.processing.data_gaps import DataGapCollector, DataGapError, GapSeverity

    # Supplied export with a hole -> FAIL_FAST, naming the year to export.
    c = DataGapCollector()
    with pytest.raises(DataGapError) as e:
        _require_a_complete_grants_window(True, "2024", c)
    assert GRANTS_WINDOW_INCOMPLETE in str(e.value) and "2024" in str(e.value)
    assert any(g.code == GRANTS_WINDOW_INCOMPLETE and g.severity is GapSeverity.FAIL_FAST
               for g in c.gaps)

    # Supplied and complete -> quiet.
    c2 = DataGapCollector()
    _require_a_complete_grants_window(True, "", c2)
    assert not c2.gaps

    # Absent for every year -> quiet: the feature simply does not fire, absence is legitimate.
    c3 = DataGapCollector()
    _require_a_complete_grants_window(False, "2024", c3)
    assert not c3.gaps


class TestAPartlyExportedGrantsWindowStopsTheRun(FifoTestCaseBase):
    """The engine acts on the grants hole data_preparation counted -- end to end, so the
    wiring (main -> pipeline_runner -> run_main_calculations) is exercised, not just the
    predicate. A supplied Grants export missing a year of the window stops the run."""

    def test_a_missing_grant_year_in_a_supplied_export_stops_the_run(self):
        from decimal import Decimal as D
        from src.processing.data_gaps import DataGapError
        from tests.support.mock_providers import MockECBExchangeRateProvider

        with pytest.raises(DataGapError) as excinfo:
            self._run_pipeline(
                tax_year=TAX_YEAR,
                grants_data=[],                    # an export WAS supplied ...
                grants_missing_years="2024",        # ... but it is missing a year
                trades_data=[
                    trade_row(ACCOUNT, ISIN, "2023-03-01", "10", "20", "BUY", "O", "T1")],
                positions_start_data=[],
                positions_end_data=[position_row(ACCOUNT, ISIN, "10", "200", price="20")],
                custom_rate_provider=MockECBExchangeRateProvider(D("1.00")),
            )
        msg = str(excinfo.value)
        assert "GRANTS_WINDOW_INCOMPLETE" in msg
        assert "2024" in msg, "the year the reader must export"


class TestGrantTransferInteractions(FifoTestCaseBase):
    """Awards that are transferred between accounts and later reversed or sold.

    Red-first on the base (measured 2026-09-20 with `git stash` of the src/ fix):
    * `test_transferred_same_date_awards_keep_reversal_identity` -> basis 114, not 94;
    * `test_award_before_same_day_transfer_is_not_symbol_dependent[ZZZ]` ->
      aborts INTERNAL_TRANSFER_PARTIAL because the transfer ran before the grant.
    """

    def test_transferred_same_date_awards_keep_reversal_identity(self):
        """F1: two accounts grant the same security on one day; the holdings are moved
        around so both awards end up in one account; then that account returns part of ITS
        OWN award, which later vests. The return must take that award's units, not the
        co-located same-date award of the other account. Keyed on the award date alone, the
        two awards collided once relocated and the return took the first lot -- and the
        vesting of 6 would then meet a lot still holding 10 and stop the run."""
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[position_row("U_A", ISIN, "10", "40", price="4"),
                                  position_row("U_B", ISIN, "10", "90", price="9")],
            positions_end_data=[position_row("U_B", ISIN, "10", "70", price="7")],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220601", "20220601", "20230601", "10", "4", account="U_A"),
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220601", "20220601", "20230601", "10", "9", account="U_B"),
                grant_row("Stock Award Return for Cash Withdrawal",
                          "20230401", "20220601", "20230601", "-4", "9", account="U_B"),
                grant_row("Stock Award Vesting",
                          "20230601", "20220601", "20230601", "6", "8", account="U_B"),
            ],
            transfers_data=[
                transfer_row("U_B", "U_A", "OUT", "20230301", isin=ISIN, quantity="-10", tx_id="100"),
                transfer_row("U_A", "U_B", "IN", "20230301", isin=ISIN, quantity="10", tx_id="101"),
                transfer_row("U_A", "U_B", "OUT", "20230302", isin=ISIN, quantity="-20", tx_id="200"),
                transfer_row("U_B", "U_A", "IN", "20230302", isin=ISIN, quantity="20", tx_id="201"),
            ],
            trades_data=[
                trade_row("U_B", ISIN, "2023-09-01", "-6", "10", "SELL", "C", "300")],
        )
        basis = sum(r.total_cost_basis_eur for r in out.realized_gains_losses
                    if r.realization_date == "2023-09-01")
        assert basis == Decimal("48"), (
            "B's own award: 10 - 4 returned = 6 vested @8 = 48; A's same-date award stays "
            "unvested in the same ledger and is never sold")

    @pytest.mark.parametrize("symbol", ["AAA", "ZZZ"])
    def test_award_before_same_day_transfer_is_not_symbol_dependent(self, symbol):
        """F2: a grant and a same-day transfer of the awarded shares out of the granting
        account must order grant -> transfer for any ticker. The same-day order was decided
        by the sort-key tail (grant symbol vs the transfer's category name), so a symbol
        sorting after it ran the transfer first and aborted INTERNAL_TRANSFER_PARTIAL. The
        unvested lot travels with its flag: the receiving account reconciles at 10."""
        isin = symbol + "AWARD0001"
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[],
            positions_end_data=[position_row("U_B", isin, "10", "40", price="4")],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230301", "20230301", "20240301", "10", "4",
                          account="U_A", isin=isin)],
            transfers_data=[
                transfer_row("U_A", "U_B", "OUT", "20230301", isin=isin, quantity="-10", tx_id="100"),
                transfer_row("U_B", "U_A", "IN", "20230301", isin=isin, quantity="10", tx_id="101")],
        )
        assert not out.realized_gains_losses, "grant->transfer must hold whatever the ticker"

    def test_a_sub_freigrenze_award_still_carries_full_basis(self):
        """[GT-ESTG20-065]: an award whose receipt value stays under the 256-euro Freigrenze
        still supplies its full vesting-day value as the basis of a later disposal -- the
        shares are acquired for consideration, and the Freigrenze exempts the income without
        turning that consideration into a gift (BMF 06.03.2025 Rn. 75, BMF 14.05.2025 Rz. 87).
        Not red-first -- the engine never applied the Freigrenze to the basis, so this pins
        the rule rather than catching a regression."""
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
            positions_end_data=[],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220210", "20220210", "20230210", "10", "4"),
                grant_row("Stock Award Vesting",
                          "20230210", "20220210", "20230210", "10", "4")],  # receipt 40 EUR < 256
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "20", "SELL", "C", "S1")],
        )
        rgls = list(out.realized_gains_losses)
        assert len(rgls) == 1
        assert rgls[0].total_cost_basis_eur == Decimal("40"), (
            "the sub-Freigrenze receipt still gives the full vesting-day value as basis")

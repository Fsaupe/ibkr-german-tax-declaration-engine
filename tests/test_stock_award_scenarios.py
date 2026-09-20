"""Awarded shares, end to end, through the real pipeline.

legal_basis: [GT-ESTG20-064] puts Zufluss on the booking -- a condition under which the
grantor may later reclaim the shares does not defer it, only a disposal being rechtlich
unmoeglich would; [GT-ESTG20-065] makes the value brought to tax then the
Anschaffungskosten on a later disposal. Both in reference/tax-law/estg-22-nr3-leistungen.md.

**What the unit tests beside this file cannot see.** `test_stock_award_lots.py` calls the
three `FifoLedger` methods directly, so it stays green while the events never reach the
ledger at all. Deleting any one of the links in the chain left the whole suite green
before this file existed.

**Calibration, measured link by link -- and two are still not covered.** Deleting each and
running this file:

| link deleted | caught |
|---|---|
| current-year processor entry | yes -- 1 of 4 red |
| historical bucket entry | yes -- 2 of 4 red |
| EUR conversion in enrichment | yes -- 4 of 4 red |
| parser's unclassified-kind refusal | yes |
| factory's zero-quantity guard | yes |
| **sort-key band in `get_event_sort_key`** | **no -- and the suite cannot** |
| award dated on `ReportDate` instead of `AwardDate` | yes -- 1 red (acquisition date) |

The sort-key band is written up in CLAUDE.md's *Where the suite is blind*, and deleting the
`StockAwardEvent` branch is figure-neutral for award-versus-trade order: the award carries no
broker transaction id, and in the secondary key an empty id sorts before every trade's id, so
the award stays ahead of same-day trades with or without the branch. The branch's only real
effect is award-versus-corporate-action precedence (both share the lot-delivering band), which
no current scenario exercises. `test_a_same_day_award_and_sale_take_the_award_as_the_basis`
documents the award-first intra-day order and its figure; it is not a guard for the branch, for
the reason just given. `test_an_award_is_dated_on_its_award_date_not_the_broker_s_report_date`
now asserts the acquisition date, the only figure the report-date mutation moves under a
start-of-year snapshot, so it does instrument that choice.

The award-inside-the-tax-year case is the one that motivated the file: an award or a
reversal that goes unapplied is caught by the end-of-year quantity reconciliation, and
the award also records the undeclared § 22 Nr. 3 receipt. A vesting moves no shares and
is inert (Zufluss fell on the award), so it is handled explicitly rather than left to
fall through.

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

    def test_a_vesting_inside_the_tax_year_does_not_move_the_cost(self):
        """Zufluss was the booking ([GT-ESTG20-064]), so the award's price is final and a
        later vesting changes nothing.

        The award is booked before the tax year at 4 and vests INSIDE the tax year at 7;
        the shares are sold that year at 10. The gain is 10 - 4 = 6 per unit. A build that
        restated the lot at vesting would read 3 -- the retired reading -- with the
        quantity, and therefore the reconciliation, identical either way.
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
        assert rgl.total_cost_basis_eur == Decimal("40"), (
            "the AWARD price is the Anschaffungskosten; 70 would be the retired "
            "vesting-restatement reading")
        assert rgl.gross_gain_loss_eur == Decimal("60")
        assert rgl.acquisition_date == "2022-03-02", (
            "acquisition falls at Zufluss, which is the booking ([GT-ESTG20-064])")

    def test_an_award_before_the_tax_year_gives_the_sale_a_real_basis(self):
        """Covers the historical bucket and the replay dispatch.

        Without the grant report the opening snapshot supplies the quantity and the
        engine synthesises a lot; with it, the lot carries the award's own date and the
        vested cost.
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
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("40")
        assert rgl.acquisition_date == "2022-03-02"

    def test_a_same_day_award_and_sale_take_the_award_as_the_basis(self):
        """A grant and a sale of the awarded shares on the same day: the award is applied
        first, so the lot exists when the sale consumes it, and the sale carries the award's
        basis and date. This documents the intended intra-day order; it is NOT a guard for
        the sort-band branch -- deleting that branch leaves the award ahead of the sale
        anyway, because the award carries no broker transaction id and an empty id sorts
        before every trade's id (CLAUDE.md's sort-band blind spot)."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230301", "20230301", "20240301", "10", "4")],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-03-01", "-10", "10", "SELL", "C", "T_SELL")],
            positions_start_data=[], positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("40"), "the sale takes the award basis"
        assert rgl.acquisition_date == "2023-03-01", "dated on the award day, not the sale"

    def test_a_reversal_is_not_a_disposal(self):
        """It produces no RealizedGainLoss of its own, and leaves the survivors at the
        cost they were awarded at -- not at the reversal row's price."""
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
            positions_start_data=[position_row(ACCOUNT, ISIN, "6", "24", price="4")],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.quantity_realized == Decimal("6"), "4 of the 10 were taken back"
        assert rgl.total_cost_basis_eur == Decimal("24"), "at the awarded price"

    def test_a_grant_inside_the_tax_year_creates_its_lot(self):
        """The current-year dispatch. A grant dated in the declared year goes through
        `StockAwardProcessor`, not the historical replay, and nothing else reaches that
        path -- a vesting is inert and a reversal needs a grant to reverse.

        Without the processor entry the grant is dropped with a log line, the lot never
        exists, and the sale has nothing to consume.
        """
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230210", "20230210", "20240210", "10", "4"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-08-01", "-10", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[],
            positions_end_data=[],
        )
        rgl = self._sale_gain(results)
        assert rgl.total_cost_basis_eur == Decimal("40")
        assert rgl.acquisition_date == "2023-02-10"

    def test_a_currency_award_is_converted_at_the_event_date_not_left_foreign(self):
        """Covers the enrichment link. A non-EUR award whose price is never converted
        would reach the ledger with no EUR cost and stop the run; one converted at the
        wrong date would give a different basis."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            custom_rate_provider=MockECBExchangeRateProvider(Decimal("2")),
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
        # 1 USD = 2 EUR (fixed provider): 10 shares awarded at 4 USD -> 40 USD -> 80 EUR.
        # A deterministic rate lets the exact basis be asserted; the live ECB rate could not.
        assert rgl.total_cost_basis_eur == Decimal("80"), (
            "basis is the award-day USD price converted at the award-date rate, not the "
            "foreign figure (60) taken as EUR nor a live-rate value")
        assert rgl.acquisition_date == "2022-03-02", "the lot is dated on the award date"


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


class TestTheGuardsAreObserved(FifoTestCaseBase):
    """The guards the suite could not see removed.

    Each of these was probed by deleting the guard and running the whole suite: before
    this class, all three left it green. A guard nothing would notice the removal of is
    the instrument-nobody-broke-on-purpose case CLAUDE.md names.
    """

    def test_an_award_is_dated_on_its_award_date_not_the_broker_s_report_date(self):
        """Load-bearing whenever the two differ, which the maintainer's export does not
        exercise -- every award row there has them equal. Built here so the choice is
        pinned by something rather than by that coincidence."""
        results = self._run_pipeline(
            tax_year=TAX_YEAR,
            grants_data=[
                # Awarded in March, booked by the broker in May.
                grant_row("Stock Award Grant for Cash Deposit",
                          "20220510", "20220302", "20220902", "10", "4"),
                grant_row("Stock Award Vesting",
                          "20220905", "20220302", "20220902", "10", "6"),
            ],
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "10", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "10", "40", price="4")],
            positions_end_data=[],
        )
        rgls = [r for r in results.realized_gains_losses]
        assert len(rgls) == 1
        assert rgls[0].total_cost_basis_eur == Decimal("40")
        # The lot is dated on the award date, not the broker's report date. A lot dated on
        # the report date reconciles identically in quantity, cost basis, proceeds and gain
        # -- only the acquisition date differs (the SoY-snapshot blind spot in CLAUDE.md),
        # so this is the assertion that instruments the choice rather than documenting it.
        assert rgls[0].acquisition_date == "2022-03-02"

def test_an_award_in_the_tax_year_reports_the_receipt_it_does_not_declare():
    """The one thing standing between a user and an understated return.

    The engine takes the award value as the Anschaffungskosten -- which LOWERS the
    gain declared on a later disposal -- and cannot declare the matching § 22 Nr. 3
    receipt, because there is no Anlage SO line for it (issue #76). Taking the half that
    reduces a figure and dropping the half that adds one is understatement, so the
    omission has to reach the report rather than only the README.

    Asserted on the collector rather than through the scenario harness: the gap is a
    WARNING, so the run completes and the harness returns before the report is rendered.
    """
    from decimal import Decimal as D
    from src.domain.enums import FinancialEventType as T
    from src.domain.events import StockAwardEvent
    from src.engine.event_processors.stock_award_processor import (
        StockAwardProcessor, STOCK_AWARD_RECEIPT_NOT_DECLARED)
    from src.processing.data_gaps import DataGapCollector, GapSeverity
    from tests.test_stock_award_lots import _ledger, ASSET_ID

    ledger = _ledger()
    award = StockAwardEvent(ASSET_ID, "2023-01-02",
                            event_type=T.STOCK_AWARD_GRANTED, award_date="2023-01-02",
                            quantity=D("10"), unit_price_foreign=D("4"), currency="EUR")
    award.unit_cost_basis_eur = D("4")

    collector = DataGapCollector()
    StockAwardProcessor().process(award, ledger, {'data_gap_collector': collector})

    gaps = [g for g in collector.gaps if g.code == STOCK_AWARD_RECEIPT_NOT_DECLARED]
    assert len(gaps) == 1, "the undeclared receipt must reach the report"
    assert gaps[0].severity is GapSeverity.WARNING
    assert "40" in gaps[0].detail, "the amount to declare has to be in it, not just the fact"


def test_a_vesting_and_a_reversal_report_no_receipt():
    """Only the award is the Zufluss. Reporting a receipt again on the vesting would tell
    the user to declare the same shares twice."""
    from decimal import Decimal as D
    from src.domain.enums import FinancialEventType as T
    from src.domain.events import StockAwardEvent
    from src.engine.event_processors.stock_award_processor import (
        StockAwardProcessor, STOCK_AWARD_RECEIPT_NOT_DECLARED)
    from src.processing.data_gaps import DataGapCollector
    from tests.test_stock_award_lots import _ledger, ASSET_ID

    ledger = _ledger()
    collector = DataGapCollector()
    award = StockAwardEvent(ASSET_ID, "2023-01-02",
                            event_type=T.STOCK_AWARD_GRANTED, award_date="2023-01-02",
                            quantity=D("10"), unit_price_foreign=D("4"), currency="EUR")
    award.unit_cost_basis_eur = D("4")
    ledger.add_lot_for_stock_award(award)

    vesting = StockAwardEvent(ASSET_ID, "2023-06-01",
                              event_type=T.STOCK_AWARD_VESTED, award_date="2023-01-02",
                              quantity=D("10"), unit_price_foreign=D("7"), currency="EUR")
    vesting.unit_cost_basis_eur = D("7")
    StockAwardProcessor().process(vesting, ledger, {'data_gap_collector': collector})

    reversal = StockAwardEvent(ASSET_ID, "2023-03-01",
                               event_type=T.STOCK_AWARD_REVERSED, award_date="2023-01-02",
                               quantity=D("4"), unit_price_foreign=D("9"), currency="EUR")
    reversal.unit_cost_basis_eur = D("9")
    StockAwardProcessor().process(reversal, ledger, {'data_gap_collector': collector})

    assert not [g for g in collector.gaps if g.code == STOCK_AWARD_RECEIPT_NOT_DECLARED]


def test_a_return_in_the_tax_year_reports_the_negative_receipt_it_does_not_declare():
    """[GT-ESTG20-067]: awarded shares handed back after Zufluss are a negative Einnahme of
    the year of the return, in the amount originally brought to account -- not the value
    on the day of the return (BFH VI R 17/08), and not a correction of the award year
    (EStH H 22.8, BFH VI R 6/18). There is no Anlage SO line for it (issue #76), so the
    run has to hand the reader the amount, the year and the destination.

    The return row carries its own price (9); the award was brought to account at 4. The
    amount is 4 units x 4 = 16.00, and 36 would be the defect.
    """
    from decimal import Decimal as D
    from src.domain.enums import FinancialEventType as T
    from src.domain.events import StockAwardEvent
    from src.engine.event_processors.stock_award_processor import (
        StockAwardProcessor, STOCK_AWARD_RETURN_NOT_DECLARED)
    from src.processing.data_gaps import DataGapCollector, GapSeverity
    from tests.test_stock_award_lots import _ledger, ASSET_ID

    ledger = _ledger()
    collector = DataGapCollector()
    award = StockAwardEvent(ASSET_ID, "2022-11-02",
                            event_type=T.STOCK_AWARD_GRANTED, award_date="2022-11-02",
                            quantity=D("10"), unit_price_foreign=D("4"), currency="EUR")
    award.unit_cost_basis_eur = D("4")
    ledger.add_lot_for_stock_award(award)

    returned = StockAwardEvent(ASSET_ID, "2023-03-01",
                               event_type=T.STOCK_AWARD_REVERSED, award_date="2022-11-02",
                               quantity=D("4"), unit_price_foreign=D("9"), currency="EUR")
    returned.unit_cost_basis_eur = D("9")
    StockAwardProcessor().process(returned, ledger, {'data_gap_collector': collector})

    gaps = [g for g in collector.gaps if g.code == STOCK_AWARD_RETURN_NOT_DECLARED]
    assert len(gaps) == 1, "the undeclared negative receipt must reach the report"
    assert gaps[0].severity is GapSeverity.WARNING
    assert "EUR 16.00" in gaps[0].detail, "original value of the returned units"
    assert "36" not in gaps[0].detail, "never the return-day value"
    assert "Anlage SO" in gaps[0].subject and "2023" in gaps[0].subject
    assert "unsettled" not in gaps[0].detail.lower() and "Q20" not in gaps[0].detail


class TestASameDayReturnAndSale(FifoTestCaseBase):
    """[GT-ESTG20-066]: no rule of law orders a same-day return against a sale, and none is
    needed. A return takes units of ITS OWN award at that award's cost ([GT-ESTG20-067]);
    the shares handed back cannot also be the shares sold. So the sale is measured against
    what is left, and the result may not depend on how the input happens to be ordered."""

    @pytest.mark.parametrize("historical", [False, True])
    @pytest.mark.parametrize("reverse_rows", [False, True])
    def test_the_sale_is_measured_against_what_the_return_left(self, historical, reverse_rows):
        # Award 10 @4, buy 10 @9, then on ONE day hand back 4 and sell 8 @10.
        # The award lot is left with 6 @4, so FIFO sells 6 @4 + 2 @9 = 42.
        # The 8 still held (@9 = 72) are sold later; asserting them catches a return
        # that took its units from the wrong lot.
        y = 2022 if historical else 2023
        grants = [
            grant_row("Stock Award Grant for Cash Deposit",
                      f"{y}0102", f"{y}0102", f"{y + 1}0102", "10", "4"),
            grant_row("Stock Award Return for Cash Withdrawal",
                      f"{y}0601", f"{y}0102", f"{y + 1}0102", "-4", "4"),
        ]
        trades = [
            trade_row(ACCOUNT, ISIN, f"{y}-02-01", "10", "9", "BUY", "O", "100"),
            trade_row(ACCOUNT, ISIN, f"{y}-06-01", "-8", "10", "SELL", "C", "200"),
            trade_row(ACCOUNT, ISIN, "2023-09-01", "-8", "10", "SELL", "C", "300"),
        ]
        if reverse_rows:
            grants.reverse()
            trades.reverse()
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=(
                [position_row(ACCOUNT, ISIN, "8", "72", price="9")] if historical else []),
            positions_end_data=[], grants_data=grants, trades_data=trades)

        sales = out.realized_gains_losses
        later = [r for r in sales if r.realization_date == "2023-09-01"]
        assert sum(r.total_cost_basis_eur for r in later) == Decimal("72")
        if not historical:
            same_day = [r for r in sales if r.realization_date == "2023-06-01"]
            assert sum(r.total_cost_basis_eur for r in same_day) == Decimal("42")
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
        OWN award. The return must take that award's basis, not the co-located same-date
        award of the other account. Keyed on the award date alone, the two awards collided
        once relocated and the return took the first lot -- understating the later gain."""
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[], positions_end_data=[],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230102", "20230102", "20240102", "10", "4", account="U_A"),
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230102", "20230102", "20240102", "10", "9", account="U_B"),
                grant_row("Stock Award Return for Cash Withdrawal",
                          "20230401", "20230102", "20240102", "-4", "9", account="U_B"),
            ],
            transfers_data=[
                transfer_row("U_B", "U_A", "OUT", "20230301", isin=ISIN, quantity="-10", tx_id="100"),
                transfer_row("U_A", "U_B", "IN", "20230301", isin=ISIN, quantity="10", tx_id="101"),
                transfer_row("U_A", "U_B", "OUT", "20230302", isin=ISIN, quantity="-20", tx_id="200"),
                transfer_row("U_B", "U_A", "IN", "20230302", isin=ISIN, quantity="20", tx_id="201"),
            ],
            trades_data=[
                trade_row("U_B", ISIN, "2023-09-01", "-16", "10", "SELL", "C", "300")],
        )
        basis = sum(r.total_cost_basis_eur for r in out.realized_gains_losses
                    if r.realization_date == "2023-09-01")
        assert basis == Decimal("94"), (
            "the return takes B's own award (@9), leaving 10@4 + 6@9 = 94; taking A's "
            "same-date award (@4) would leave 6@4 + 10@9 = 114")

    @pytest.mark.parametrize("symbol", ["AAA", "ZZZ"])
    def test_award_before_same_day_transfer_is_not_symbol_dependent(self, symbol):
        """F2: a grant, a same-day transfer of the awarded shares out of the granting
        account, and a later sale must order grant -> transfer -> sale for any ticker. The
        same-day order was decided by the sort-key tail (grant symbol vs the transfer's
        category name), so a symbol sorting after it ran the transfer first and aborted."""
        isin = symbol + "AWARD0001"
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[], positions_end_data=[],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230301", "20230301", "20240301", "10", "4",
                          account="U_A", isin=isin)],
            transfers_data=[
                transfer_row("U_A", "U_B", "OUT", "20230301", isin=isin, quantity="-10", tx_id="100"),
                transfer_row("U_B", "U_A", "IN", "20230301", isin=isin, quantity="10", tx_id="101")],
            trades_data=[
                trade_row("U_B", isin, "2023-06-01", "-10", "10", "SELL", "C", "200")],
        )
        basis = sum(r.total_cost_basis_eur for r in out.realized_gains_losses)
        assert basis == Decimal("40"), "grant->transfer->sale must hold whatever the ticker"

    def test_a_sub_freigrenze_award_still_carries_full_basis(self):
        """F3 / Q16, Reading A (taxpayer's choice 2026-09-20): an award whose receipt value
        stays under the 256-euro Freigrenze still supplies its full award-day value as the
        basis of a later disposal. Not red-first -- the engine does not apply the Freigrenze,
        so this pins the chosen reading rather than catching a regression."""
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[], positions_end_data=[],
            grants_data=[
                grant_row("Stock Award Grant for Cash Deposit",
                          "20230210", "20230210", "20240210", "10", "4")],  # receipt 40 EUR < 256
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2023-06-01", "-10", "20", "SELL", "C", "S1")],
        )
        rgls = list(out.realized_gains_losses)
        assert len(rgls) == 1
        assert rgls[0].total_cost_basis_eur == Decimal("40"), (
            "the sub-Freigrenze receipt still gives the full award-day value as basis")

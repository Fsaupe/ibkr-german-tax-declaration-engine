"""The three stock-award operations on a FIFO ledger.

Every figure here is invented. The real export is not copied, per CLAUDE.md's
public-repo rule; what is reproduced is the SHAPE the broker's export has -- an award,
a partial reversal of it, and the vesting of what is left -- because that shape is what
the operations are built for.

legal_basis: the application at [GT-ESTG20-064] to the Refer-A-Friend terms: the shares
zufliessen when the programme's transfer restriction lapses. The award books
a holding without cost or acquisition date; the vesting supplies both at the vesting
day's value ([GT-ESTG20-065]); a return before vesting is no tax event ([GT-ESTG20-067],
Boundary).

Calibration is measured for this file and `test_stock_award_scenarios.py` together, mutant
by mutant, and tabulated in that file's docstring. The three refusal sites of
`_refuse_with_unvested_award` are observed only here: deleting any one of them turns
`test_an_event_that_reprices_every_lot_stops_the_run_while_units_are_unvested` red.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.domain.enums import AssetCategory, FinancialEventType
from src.domain.events import StockAwardEvent, TradeEvent
from src.domain.exceptions import ProcessingError
from src.engine.fifo_manager import FifoLedger
from src.utils.currency_converter import CurrencyConverter
from src.utils.exchange_rate_provider import ECBExchangeRateProvider


ASSET_ID = uuid.uuid4()
GRANTED = FinancialEventType.STOCK_AWARD_GRANTED
REVERSED = FinancialEventType.STOCK_AWARD_REVERSED
VESTED = FinancialEventType.STOCK_AWARD_VESTED


def _ledger():
    return FifoLedger(
        asset_internal_id=ASSET_ID,
        asset_category=AssetCategory.STOCK,
        asset_multiplier_from_asset=None,
        currency_converter=MagicMock(spec=CurrencyConverter),
        exchange_rate_provider=MagicMock(spec=ECBExchangeRateProvider),
        internal_working_precision=28,
        decimal_rounding_mode="ROUND_HALF_UP",
    )


def _award(date, award_date, qty, eur_per_unit, kind=GRANTED):
    ev = StockAwardEvent(
        ASSET_ID, date, event_type=kind, award_date=award_date,
        quantity=Decimal(qty), unit_price_foreign=Decimal("1"), currency="USD",
        account_id="U_TEST",
    )
    ev.unit_cost_basis_eur = Decimal(eur_per_unit)
    return ev


def _sale(date, qty, proceeds_eur):
    ev = TradeEvent(ASSET_ID, date, event_type=FinancialEventType.TRADE_SELL_LONG,
                    quantity=Decimal(qty) * -1, price_foreign_currency=Decimal("1"),
                    local_currency="EUR", account_id="U_TEST")
    ev.net_proceeds_or_cost_basis_eur = Decimal(proceeds_eur)
    return ev


def test_award_books_the_units_on_the_day_they_arrived_without_a_cost():
    """The shares are in the account from the award, and a ledger that waited for the
    vesting would reconstruct short of the broker's snapshot. They are not yet acquired:
    the award row's price (4) reaches nothing."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))

    assert len(led.lots) == 1
    assert led.lots[0].quantity == Decimal("10")
    assert led.lots[0].zufluss_pending is True
    assert led.lots[0].total_cost_basis_eur == Decimal("0")
    assert led.get_current_position_quantity() == Decimal("10")


def test_vesting_gives_the_lot_the_vesting_day_and_the_vesting_value():
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))

    lot = led.lots[0]
    assert lot.zufluss_pending is False
    assert lot.acquisition_date == "2021-03-02", "the vesting day, not the award day"
    assert lot.unit_cost_basis_eur == Decimal("7"), "the vesting value, not the award's 4"
    assert lot.total_cost_basis_eur == Decimal("70")


def test_a_return_before_vesting_takes_units_and_is_no_tax_event():
    """Nothing had zugeflossen, so nothing is handed back for tax: the method returns
    nothing to build a negative Einnahme from, and the remaining units still have no cost."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    result = led.reverse_stock_award_lot(
        _award("2020-09-01", "2020-03-02", "4", "9", kind=REVERSED))

    assert result is None
    assert led.lots[0].quantity == Decimal("6")
    assert led.lots[0].zufluss_pending is True
    assert led.lots[0].total_cost_basis_eur == Decimal("0")


def test_a_full_reversal_removes_the_lot():
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.reverse_stock_award_lot(_award("2020-09-01", "2020-03-02", "10", "4", kind=REVERSED))
    assert led.lots == []


def test_the_whole_sequence_leaves_the_broker_s_quantity_and_the_vested_cost():
    """Award, award, partial reversal, two vestings -- the shape the export has."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.add_lot_for_stock_award(_award("2020-06-01", "2020-06-01", "20", "5"))
    led.reverse_stock_award_lot(_award("2020-09-01", "2020-03-02", "4", "4", kind=REVERSED))
    led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "6", "7", kind=VESTED))
    led.vest_stock_award_lot(_award("2021-06-01", "2020-06-01", "20", "8", kind=VESTED))

    assert sum(lot.quantity for lot in led.lots) == Decimal("26"), "10 + 20 - 4"
    assert sum(lot.total_cost_basis_eur for lot in led.lots) == Decimal("202"), \
        "6 x 7 + 20 x 8 -- the vesting values"
    by_award = {lot.source_transaction_id: lot for lot in led.lots}
    assert by_award["STOCK_AWARD:U_TEST:2020-03-02"].acquisition_date == "2021-03-02"
    assert by_award["STOCK_AWARD:U_TEST:2020-06-01"].acquisition_date == "2021-06-01"


def test_a_vesting_must_name_the_units_the_lot_still_holds():
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.reverse_stock_award_lot(_award("2020-09-01", "2020-03-02", "4", "4", kind=REVERSED))
    with pytest.raises(ProcessingError, match="names 10.* holds\\s+6"):
        led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))


def test_a_vesting_without_its_award_or_a_second_vesting_stops_the_run():
    led = _ledger()
    with pytest.raises(ProcessingError, match="no unvested lot"):
        led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))
    with pytest.raises(ProcessingError, match="already vested"):
        led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))


def test_a_lot_is_never_vested_without_a_eur_value():
    """The vesting price is a foreign amount; a lot vested before conversion would carry
    an invented acquisition cost into a later disposal."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    ev = StockAwardEvent(
        ASSET_ID, "2021-03-02", event_type=VESTED, award_date="2020-03-02",
        quantity=Decimal("10"), unit_price_foreign=Decimal("7"), currency="USD",
        account_id="U_TEST")
    with pytest.raises(ProcessingError, match="without a EUR value"):
        led.vest_stock_award_lot(ev)


def test_a_return_after_vesting_stops_the_run():
    """The programme reclaims shares only before the restriction lapses; the negative
    Einnahme a later return would be ([GT-ESTG20-067]) is not implemented."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    led.vest_stock_award_lot(_award("2021-03-02", "2020-03-02", "10", "7", kind=VESTED))
    with pytest.raises(ProcessingError, match="already vested"):
        led.reverse_stock_award_lot(_award("2021-04-01", "2020-03-02", "4", "4", kind=REVERSED))


def test_a_sale_never_consumes_unvested_units():
    """FIFO orders acquired shares. An unvested award is older by booking date than the
    vested one here, and must still be passed over: it has no cost to measure against."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))   # stays unvested
    led.add_lot_for_stock_award(_award("2020-06-01", "2020-06-01", "20", "5"))
    led.vest_stock_award_lot(_award("2021-06-01", "2020-06-01", "20", "8", kind=VESTED))

    rgls = led.consume_long_lots_for_sale(_sale("2021-07-01", "5", "50"))

    assert sum(r.total_cost_basis_eur for r in rgls) == Decimal("40"), "5 x 8, the vested lot"
    assert {r.acquisition_date for r in rgls} == {"2021-06-01"}
    unvested = [lot for lot in led.lots if lot.zufluss_pending]
    assert [lot.quantity for lot in unvested] == [Decimal("10")]


def test_a_sale_reaching_into_unvested_units_stops_the_run():
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    with pytest.raises(ProcessingError, match="have not vested"):
        led.consume_long_lots_for_sale(_sale("2020-07-01", "5", "50"))


def test_reversing_more_than_was_awarded_stops_the_run():
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    with pytest.raises(ProcessingError, match="which holds 10"):
        led.reverse_stock_award_lot(_award("2020-09-01", "2020-03-02", "11", "4", kind=REVERSED))


def test_two_awards_sharing_an_award_date_stop_the_run():
    """The award date is the matching key, so a duplicate would let a later vesting
    vest the wrong award's shares."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))
    with pytest.raises(ProcessingError, match="share the award"):
        led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "5", "4"))


def test_an_event_that_reprices_every_lot_stops_the_run_while_units_are_unvested():
    """A merger or a capital repayment treats every lot as acquired. An unvested lot has no
    cost, so paying it out at zero or draining it into another instrument would produce a
    figure from a placeholder. None has occurred on an awarded share; each site refuses."""
    led = _ledger()
    led.add_lot_for_stock_award(_award("2020-03-02", "2020-03-02", "10", "4"))

    merger = MagicMock()
    merger.cash_per_share_eur = Decimal("12")
    with pytest.raises(ProcessingError, match="cash merger.*have not vested"):
        led.consume_all_lots_for_cash_merger(merger)
    with pytest.raises(ProcessingError, match="stock merger.*have not vested"):
        led.drain_all_long_lots()
    with pytest.raises(ProcessingError, match="capital repayment.*have not vested"):
        led.reduce_cost_basis_for_capital_repayment(Decimal("5"))
    assert led.get_current_position_quantity() == Decimal("10")

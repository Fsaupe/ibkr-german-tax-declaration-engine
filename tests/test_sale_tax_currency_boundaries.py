"""Signed net cash and proceeds: GT-ESTG20-011/068, GT-FX-007.

All data are invented. Currency expectations preserve the standing FX position;
they test direction, rate and FIFO basis, not a new election about currency tax.
"""
from decimal import Context, Decimal
from types import SimpleNamespace
import uuid

import pytest

from src.domain.assets import CashBalance
from src.domain.enums import FinancialEventType, RealizationType
from src.domain.events import TradeEvent
from src.engine.calculation_engine import _apply_historical_currency_event
from src.engine.fifo_manager import FifoLot
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import cash_balance_row, fx_trade_row, position_row, trade_row
from tests.test_transaction_taxes import _usd_cash_position, _RatePerDate

ACCOUNT = "U10000001"
ISIN = "US000000REV1"
D = Decimal


def _currency_results(out):
    return [r for r in out.realized_gains_losses
            if isinstance(out.asset_resolver.get_asset_by_id(r.asset_internal_id), CashBalance)]


class TestSaleTaxCurrencyBoundary(FifoTestCaseBase):
    @pytest.mark.parametrize("tax", ["1", "3"])
    def test_current_year_currency_short_is_covered_at_its_opening_rate(self, tax):
        deficit = D(tax) - D("1") + D(".25")
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2025-03-01", "1", "100", "BUY", "O", "BUY", currency="USD"),
                trade_row(ACCOUNT, ISIN, "2025-06-01", "-1", "1", "SELL", "C", "SELL",
                          currency="USD", taxes="-" + tax, commission="-.25"),
                fx_trade_row(ACCOUNT, "USD", "BUY", deficit, deficit * D(".8"), "1.25", "2025-07-01", "COVER_FX"),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, "100", "80")],
            positions_end_data=[],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "100", "0", year=2025)],
            custom_rate_provider=_RatePerDate({"2025-03-01": ".5", "2025-06-01": ".625", "2025-07-01": ".8"}),
            tax_year=2025,
        )
        expected = D("-30") + deficit * (D(".625") - D(".8"))
        assert sum((r.gross_gain_loss_eur for r in _currency_results(out)), D("0")) == expected
        assert out.data_gaps == []

    @pytest.mark.parametrize("tax", ["0.5", "1", "3"])
    @pytest.mark.parametrize("commission", ["0", "-0.25"])
    def test_current_year(self, tax, commission):
        ending = D("901") - D(tax) + D(commission)
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, ISIN, "2025-03-01", "1", "100", "BUY", "O", "BUY", currency="USD"),
                trade_row(ACCOUNT, ISIN, "2025-06-01", "-1", "1", "SELL", "C", "SELL",
                          currency="USD", taxes="-" + tax, commission=commission),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, "1000", "800")],
            positions_end_data=[_usd_cash_position(ACCOUNT, ending, ending * D(".8"))],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "1000", ending, year=2025)],
            custom_rate_provider=_RatePerDate({"2025-03-01": ".5", "2025-06-01": ".625"}),
            tax_year=2025,
        )
        # First spend 100 at .5 against .8 basis; net sale outflow and commission
        # consume the same original lot at .625. A positive receipt is not a disposal.
        spent = max(D(tax) - D("1"), D("0")) - D(commission)
        expected = D("-30") + spent * (D(".625") - D(".8"))
        assert sum((r.gross_gain_loss_eur for r in _currency_results(out)), D("0")) == expected
        assert out.data_gaps == []

    @pytest.mark.parametrize("tax", ["0.5", "1", "3"])
    @pytest.mark.parametrize("commission", ["0", "-0.25"])
    def test_historical_basis_reaches_later_disposal(self, tax, commission, caplog):
        caplog.set_level("DEBUG")
        ending = D("901") - D(tax) + D(commission)
        out = self._run_pipeline(
            trades_data=[
                fx_trade_row(ACCOUNT, "USD", "BUY", "1000", "1000", "1", "2024-01-15", "FX"),
                trade_row(ACCOUNT, ISIN, "2024-03-01", "1", "100", "BUY", "O", "BUY", currency="USD"),
                trade_row(ACCOUNT, ISIN, "2024-06-01", "-1", "1", "SELL", "C", "SELL",
                          currency="USD", taxes="-" + tax, commission=commission),
                fx_trade_row(ACCOUNT, "USD", "SELL", ending, ending * D(".625"), "1.6", "2025-03-01", "FX_SELL"),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, ending, ending)],
            positions_end_data=[],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", ending, "0", year=2025)],
            custom_rate_provider=_RatePerDate({"2024-01-15": "1", "2024-03-01": ".8",
                                               "2024-06-01": ".5", "2025-03-01": ".625"}),
            tax_year=2025,
        )
        receipt = max(D("1") - D(tax), D("0"))
        old_remaining = D("900") - max(D(tax) - D("1"), D("0")) + D(commission)
        basis = old_remaining + receipt * D(".5")
        results = _currency_results(out)
        assert sum((r.total_cost_basis_eur for r in results), D("0")) == basis
        assert sum((r.gross_gain_loss_eur for r in results), D("0")) == ending * D(".625") - basis
        assert out.data_gaps == []
        assert "Historical currency replay: skipped event" not in caplog.text


@pytest.mark.parametrize("tax", ["1", "3"])
@pytest.mark.parametrize("opening", ["0", "10"])
def test_historical_lots_before_snapshot_reconciliation(tax, opening, caplog):
    """Observe zero cash, a remaining long lot and a new short before any snapshot."""
    caplog.set_level("DEBUG")
    ledger = SimpleNamespace(lots=[], short_lots=[])
    if D(opening):
        ledger.lots.append(FifoLot("2024-01-01", D(opening), D(".8"), D(opening) * D(".8"), "OPEN"))
    event = TradeEvent(
        asset_internal_id=uuid.uuid4(), event_date="2024-06-01",
        event_type=FinancialEventType.TRADE_SELL_LONG, quantity=D("-1"),
        price_foreign_currency=D("1"), local_currency="USD", account_id=ACCOUNT,
        gross_amount_foreign_currency=D("1"), gross_amount_eur=D(".625"),
        transaction_tax_foreign=D(tax), transaction_tax_eur=D(tax) * D(".625"),
        commission_foreign_currency=D("-.25"), commission_currency="USD",
        commission_eur=D("-.15625"), ibkr_transaction_id="SALE",
    )
    _apply_historical_currency_event(event, ledger, "USD", None, Context(prec=28))
    spent = D(tax) - D("1") + D(".25")
    assert sum((l.quantity for l in ledger.lots), D("0")) == max(D(opening) - spent, D("0"))
    assert sum((l.quantity_shorted for l in ledger.short_lots), D("0")) == max(spent - D(opening), D("0"))
    assert all(l.unit_cost_basis_eur == D(".8") for l in ledger.lots)
    assert all(l.unit_sale_proceeds_eur == D(".625") for l in ledger.short_lots)
    assert "Historical currency replay: skipped event" not in caplog.text


class TestSignedShortProceeds(FifoTestCaseBase):
    @pytest.mark.parametrize("opening_year", [2024, 2025])
    def test_partial_covers_keep_signed_opening_proceeds(self, opening_year):
        # 100 shares sold for 1 less 4 costs: -3 opening proceeds. Two covers
        # cost .5 each; each therefore realises -1.5 - .5 = -2.
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, ISIN, f"{opening_year}-03-01", "-100", ".01", "SELL", "O", "OPEN", commission="-4"),
                trade_row(ACCOUNT, ISIN, "2025-06-01", "50", ".01", "BUY", "C", "COVER1"),
                trade_row(ACCOUNT, ISIN, "2025-07-01", "50", ".01", "BUY", "C", "COVER2"),
            ],
            positions_start_data=[position_row(ACCOUNT, ISIN, "-100", "-1", price=".01")] if opening_year == 2024 else [],
            positions_end_data=[], tax_year=2025,
        )
        covers = [r for r in out.realized_gains_losses if r.realization_type == RealizationType.SHORT_POSITION_COVER]
        assert len(covers) == 2
        assert [r.total_realization_value_eur for r in covers] == [D("-1.5"), D("-1.5")]
        assert [r.gross_gain_loss_eur for r in covers] == [D("-2"), D("-2")]

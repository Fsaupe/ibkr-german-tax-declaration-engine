"""Reported currency openings bound replayed holdings (GT-FX-008/009).

The existing 0.01 currency reconciliation tolerance is numerical, not a tax
exemption. Broker observations survive parsing even inside that tolerance.
An empty opening must not supply historical lots to a later disposal.
All quantities, account labels and rates below are invented.
"""
from datetime import date
from decimal import Decimal as D, Context
from types import SimpleNamespace

import pytest

from src.classification.asset_classifier import AssetClassifier
from src.domain.assets import CashBalance, PositionSnapshot
from src.engine.calculation_engine import _reconcile_currency_soy
from src.engine.fifo_manager import FifoLot, ShortFifoLot
from src.identification.asset_resolver import AssetResolver
from src.parsers.parsing_orchestrator import ParsingOrchestrator
from src.parsers.raw_models import RawCashBalanceRecord
from tests.support.base import FifoTestCaseBase
from tests.support.mock_providers import MockECBExchangeRateProvider
from tests.support.multi_account import cash_balance_row, fx_trade_row


@pytest.mark.parametrize('opening', ['0', '0.001', '-0.001'])
@pytest.mark.parametrize('closing', ['0', '0.002', '10'])
def test_parser_preserves_opening_independently_of_closing(opening, closing):
    classifier = AssetClassifier()
    resolver = AssetResolver(classifier)
    parser = ParsingOrchestrator(resolver, classifier, False)
    parser.raw_cash_balances = [RawCashBalanceRecord(
        ClientAccountID='A', CurrencyPrimary='USD', StartingCash=opening,
        EndingCash=closing, FromDate='20250101', ToDate='20251231')]
    parser._process_cash_balance_positions(2025)
    assert [s.quantity for s in parser.soy_positions.values()] == [D(opening)]
    assert [s.quantity for s in parser.eoy_positions.values()] == [D(closing)]


def _ledger(long='0', short='0'):
    longs = [FifoLot('2023-06-01', D(long), D('0.5'), D(long) * D('0.5'),
                    source_transaction_id='OLD_LONG')] if D(long) else []
    shorts = [ShortFifoLot('2023-07-01', D(short), D('0.8'), D(short) * D('0.8'),
                          source_transaction_id='OLD_SHORT')] if D(short) else []
    return SimpleNamespace(lots=longs, short_lots=shorts)


class _NoRates:
    def get_rate(self, *args):
        pytest.fail('Removing stale holdings must not invent a dated adjustment lot')


@pytest.mark.parametrize('opening', ['0', '0.001', '-0.001'])
@pytest.mark.parametrize('long,short', [('25', '0'), ('0', '25'), ('25', '25')])
def test_empty_opening_removes_both_sides_without_a_synthetic_lot(opening, long, short):
    ledger = _ledger(long, short)
    _reconcile_currency_soy(ledger, SimpleNamespace(currency='USD'), 2025,
                            _NoRates(), Context(prec=28), PositionSnapshot(D(opening)))
    assert ledger.lots == []
    assert ledger.short_lots == []


def test_absent_opening_does_not_assert_an_empty_holding():
    ledger = _ledger('25', '10')
    long, short = ledger.lots[0], ledger.short_lots[0]
    _reconcile_currency_soy(ledger, SimpleNamespace(currency='USD'), 2025,
                            _NoRates(), Context(prec=28), None)
    assert ledger.lots == [long] and ledger.short_lots == [short]
    assert long.quantity == D('25') and short.quantity_shorted == D('10')


@pytest.mark.parametrize('quantity', ['0.01', '-0.01', '25', '-25'])
def test_matching_nonempty_opening_keeps_original_lot_identity(quantity):
    value = D(quantity)
    ledger = _ledger(quantity if value > 0 else '0', str(-value) if value < 0 else '0')
    lots = list(ledger.lots), list(ledger.short_lots)
    _reconcile_currency_soy(ledger, SimpleNamespace(currency='USD'), 2025,
                            _NoRates(), Context(prec=28), PositionSnapshot(value))
    assert (ledger.lots, ledger.short_lots) == lots
    remaining = ledger.lots or ledger.short_lots
    assert remaining[0] is (lots[0] or lots[1])[0]


class TestOpeningBoundaryInPipeline(FifoTestCaseBase):
    @pytest.mark.parametrize('history_direction', ['BUY', 'SELL'])
    @pytest.mark.parametrize('opening', ['0', '-0.001', '0.001'])
    def test_disposal_uses_new_acquisition_after_empty_opening(self, history_direction, opening):
        rates = MockECBExchangeRateProvider(rate_schedule=[
            (date(2024, 1, 1), D('0.5')),
            (date(2025, 1, 1), D('1')),
            (date(2025, 7, 1), D('2')),
        ])
        out = self._run_pipeline(
            trades_data=[
                fx_trade_row('A', 'USD', history_direction, '25', '12.5', '2', '2024-06-01', '1'),
                fx_trade_row('A', 'USD', 'BUY', '10', '10', '1', '2025-02-01', '2'),
                fx_trade_row('A', 'USD', 'SELL', '10', '20', '0.5', '2025-08-01', '3'),
            ],
            positions_start_data=[], positions_end_data=[],
            cash_balance_data=[cash_balance_row('A', 'USD', opening, opening)],
            custom_rate_provider=rates, tax_year=2025)
        assert not [g for g in out.data_gaps if g.code.startswith('CURRENCY_EOY_')]
        cash_ids = {a.internal_asset_id for a in out.asset_resolver.assets_by_internal_id.values()
                    if isinstance(a, CashBalance)}
        realized = [r for r in out.realized_gains_losses if r.asset_internal_id in cash_ids]
        assert len(realized) == 1
        assert realized[0].total_cost_basis_eur == D('10')
        assert realized[0].total_realization_value_eur == D('20')
        assert realized[0].gross_gain_loss_eur == D('10')

    def test_empty_account_does_not_clear_another_accounts_historical_basis(self):
        rates = MockECBExchangeRateProvider(rate_schedule=[
            (date(2024, 1, 1), D('0.5')), (date(2025, 1, 1), D('1'))])
        out = self._run_pipeline(
            trades_data=[
                fx_trade_row('A', 'USD', 'BUY', '25', '12.5', '2', '2024-06-01', '1'),
                fx_trade_row('B', 'USD', 'BUY', '10', '5', '2', '2024-06-01', '2'),
                fx_trade_row('B', 'USD', 'SELL', '10', '10', '1', '2025-06-01', '3'),
            ],
            positions_start_data=[], positions_end_data=[],
            cash_balance_data=[cash_balance_row('A', 'USD', '0', '0'),
                               cash_balance_row('B', 'USD', '10', '0')],
            custom_rate_provider=rates, tax_year=2025)
        assert not [g for g in out.data_gaps if g.code.startswith('CURRENCY_EOY_')]
        assert len(out.realized_gains_losses) == 1
        assert out.realized_gains_losses[0].total_cost_basis_eur == D('5')
        assert out.realized_gains_losses[0].gross_gain_loss_eur == D('5')

"""Issue #85: GT-ESTG20-004/070/075, synthetic physical-delivery regressions.

These cases do not assume a receipt date for an ordinary written-option trade.
Writer lots were opened in a previous year: physical assignment must not tax
their premium again or incorporate it into the delivered asset. Holder cases
check the independently required preservation of paid option acquisition cost.
"""
from decimal import Decimal as D

import pytest

from src.domain.enums import AssetCategory, TaxReportingCategory as TC
from tests.support.base import FifoTestCaseBase
from tests.support.mock_providers import MockECBExchangeRateProvider
from tests.support.multi_account import position_row, TRADES_COLUMNS
from tests.test_option_delivery_integrity import option, stock


def _option_position(quantity):
    from tests.support.multi_account import POSITIONS_COLUMNS
    values = dict.fromkeys(POSITIONS_COLUMNS, '')
    values.update(ClientAccountID='A', CurrencyPrimary='EUR', AssetClass='OPT',
        Symbol='C REVIEW 20250620 50 M', Description='REVIEW 2025-06-20 50 C',
        Quantity=str(quantity), PositionValue=str(D(quantity)*200), MarkPrice='2',
        CostBasisMoney=str(D(quantity)*200), UnderlyingSymbol='REVIEW',
        Conid='880002', UnderlyingConid='880001', Multiplier='100')
    return [values[k] for k in POSITIONS_COLUMNS]


class TestOptionPremiumTaxTreatment(FifoTestCaseBase):
    def test_pdf_separates_writer_payments_and_reconciles_before_rounding(self, tmp_path):
        import fitz
        from src.engine.loss_offsetting import LossOffsettingEngine
        from src.reporting.pdf_generator import PdfReportGenerator
        written = option('A', '100', when='2025-12-27', opening=True, assigned=True, premium='2')
        buyback = option('A', '200', when='2025-12-29', assigned=True)
        buyback[TRADES_COLUMNS.index('Notes/Codes')] = ''
        buyback[TRADES_COLUMNS.index('TradePrice')] = '.01004'
        purchased = option('A', '110', when='2025-01-03', opening=True, premium='.01004', conid='880003')
        expired = option('A', '210', conid='880003')
        expired[TRADES_COLUMNS.index('Notes/Codes')] = 'Ep'
        out = self._run_pipeline(trades_data=[written, buyback, purchased, expired],
            positions_start_data=[], positions_end_data=[], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        summary = LossOffsettingEngine(out.realized_gains_losses, [], [], out.asset_resolver, 2025).calculate_reporting_figures()
        assert summary.form_line_values[TC.ANLAGE_KAP_SONSTIGE_VERLUSTE] == D('2.01')
        pdf = PdfReportGenerator(summary, [], out.realized_gains_losses, [],
                                 out.asset_resolver.assets_by_internal_id, 2025, [], data_gaps=out.data_gaps)
        path = tmp_path/'premiums.pdf'
        pdf.generate_report(str(path))
        with fitz.open(path) as doc:
            content = ' '.join(p.get_text() for p in doc)
        assert 'Negative Stillhaltereinnahmen' in content
        assert 'Prämienzufluss' in content
        assert 'Handelsdatum' in content
        assert 'Differenz zwischen der Summe der Komponenten' not in content

    def test_open_remainder_does_not_defer_any_opening_premium(self):
        opening = option('A', '100', when='2025-01-02', opening=True,
                         contracts='3', assigned=True, premium='2')
        closing = option('A', '200', when='2025-03-01', assigned=True)
        closing[TRADES_COLUMNS.index('Notes/Codes')] = ''
        closing[TRADES_COLUMNS.index('TradePrice')] = '1'
        out = self._run_pipeline(trades_data=[opening, closing], positions_start_data=[],
            positions_end_data=[_option_position('-2')], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        assert [(r.quantity_realized, r.gross_gain_loss_eur) for r in out.realized_gains_losses] == [
            (D('3'), D('600')), (D('1'), D('-100'))]

    def test_long_to_short_flip_recognises_only_the_new_writer_portion(self):
        bought = option('A', '100', when='2025-01-02', opening=True, premium='1')
        sale = option('A', '200', when='2025-03-01', opening=True,
                      assigned=True, contracts='2', premium='2')
        sale[TRADES_COLUMNS.index('Open/CloseIndicator')] = 'C;O'
        out = self._run_pipeline(trades_data=[bought, sale], positions_start_data=[],
            positions_end_data=[_option_position('-1')], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        assert [(r.is_stillhalter_income, r.quantity_realized, r.gross_gain_loss_eur)
                for r in out.realized_gains_losses] == [(False, D('1'), D('100')), (True, D('1'), D('200'))]

    def test_prior_year_opening_is_not_taxed_again_on_buyback(self):
        opening = option('A', '100', when='2024-12-20', opening=True, assigned=True, premium='2')
        closing = option('A', '200', when='2025-03-01', assigned=True)
        closing[TRADES_COLUMNS.index('Notes/Codes')] = ''
        closing[TRADES_COLUMNS.index('TradePrice')] = '1'
        out = self._run_pipeline(trades_data=[opening, closing],
            positions_start_data=[_option_position('-1')], positions_end_data=[], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        assert [(r.realization_date, r.gross_gain_loss_eur) for r in out.realized_gains_losses] == [
            ('2025-03-01', D('-100'))]

    @pytest.mark.parametrize('year', [2023, 2024, 2025])
    def test_written_premium_and_buyback_are_separate_income_events(self, year):
        opening = option('A', '100', when=f'{year}-01-02', opening=True,
                         assigned=True, premium='2')
        closing = option('A', '200', when=f'{year}-06-20', assigned=True)
        closing[TRADES_COLUMNS.index('Notes/Codes')] = ''
        closing[TRADES_COLUMNS.index('TradePrice')] = '3'
        out = self._run_pipeline(trades_data=[opening, closing],
            positions_start_data=[], positions_end_data=[], tax_year=year,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        rows = out.realized_gains_losses
        assert [(r.realization_date, r.gross_gain_loss_eur) for r in rows] == [
            (f'{year}-01-02', D('200')), (f'{year}-06-20', D('-300'))]
        assert all(r.is_stillhalter_income for r in rows)
        assert rows[1].tax_reporting_category == TC.ANLAGE_KAP_SONSTIGE_VERLUSTE
        from src.engine.loss_offsetting import LossOffsettingEngine
        figures = LossOffsettingEngine(rows, [], [], out.asset_resolver, year).calculate_reporting_figures()
        assert figures.form_line_values[TC.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT] == D('-100')
        assert figures.form_line_values[TC.ANLAGE_KAP_SONSTIGE_VERLUSTE] == D('300')
        assert figures.form_line_values[TC.ANLAGE_KAP_TERMIN_VERLUST] == D('0')
        assert figures.form_line_values[TC.ANLAGE_KAP_TERMIN_GEWINN] == (D('200') if year < 2025 else D('0'))

    def test_short_expiry_does_not_tax_the_premium_again(self):
        opening = option('A', '100', when='2025-01-02', opening=True,
                         assigned=True, premium='2')
        expiry = option('A', '200', assigned=True)
        expiry[TRADES_COLUMNS.index('Notes/Codes')] = 'Ep'
        out = self._run_pipeline(trades_data=[opening, expiry],
            positions_start_data=[], positions_end_data=[], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')))
        assert [(r.realization_date, r.gross_gain_loss_eur) for r in out.realized_gains_losses] == [
            ('2025-01-02', D('200'))]

    @pytest.mark.parametrize('kind', ['C', 'P'])
    def test_prior_year_writer_premium_does_not_change_delivered_stock(self, kind):
        # Open in the historical window, assign in 2025, then close the stock.
        # No current-year ordinary option-premium cash date is needed here.
        from tests.support.multi_account import POSITIONS_COLUMNS
        opening_option = dict.fromkeys(POSITIONS_COLUMNS, '')
        opening_option.update(ClientAccountID='A', CurrencyPrimary='EUR',
            AssetClass='OPT', Symbol=f'{kind} REVIEW 20250620 50 M',
            Description=f'REVIEW 2025-06-20 50 {kind}', Quantity='-1',
            PositionValue='-200', MarkPrice='2', CostBasisMoney='-200',
            UnderlyingSymbol='REVIEW', Conid='880002', UnderlyingConid='880001',
            Multiplier='100')
        out = self._run_pipeline(
            trades_data=[
                option('A', '100', when='2024-12-02', opening=True,
                       premium='2', kind=kind, assigned=True),
                option('A', '200', kind=kind, assigned=True),
                stock('A', '300', kind=kind, assigned=True),
                stock('A', '400', kind=kind, assigned=True, sale=True,
                      when='2025-07-01', price='70'),
            ],
            positions_start_data=[[opening_option[k] for k in POSITIONS_COLUMNS]],
            positions_end_data=[], tax_year=2025,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')),
        )
        stock_results = [r for r in out.realized_gains_losses
                         if r.asset_category_at_realization == AssetCategory.STOCK]
        assert len(stock_results) == 1
        assert stock_results[0].gross_gain_loss_eur == (D('-2000') if kind == 'C' else D('2000'))
        assert not [r for r in out.realized_gains_losses
                    if r.asset_category_at_realization == AssetCategory.OPTION]

    @pytest.mark.parametrize('historical,fund', [(False, False), (True, False), (False, True)])
    def test_purchased_call_cost_survives_exercise_and_year_end(self, historical, fund):
        if fund:
            self.seed_classification('ISIN:US000000RV88', 'INVESTMENT_FUND', 'AKTIENFONDS')
        year = 2024 if historical else 2025
        out = self._run_pipeline(
            trades_data=[
                option('A', '100', when=f'{year}-01-02', opening=True, premium='2'),
                option('A', '200', when=f'{year}-06-20'),
                stock('A', '300', when=f'{year}-06-20'),
                stock('A', '400', sale=True, when='2025-07-01', price='70'),
            ],
            positions_start_data=([position_row('A', 'US000000RV88', D('100'), D('5000'))]
                                  if historical else []),
            positions_end_data=[], tax_year=2025,
            positions_prior_start_data=[] if fund else None,
            positions_prior_end_data=[] if fund else None,
            custom_rate_provider=MockECBExchangeRateProvider(D('1')),
        )
        assert len(out.realized_gains_losses) == 1
        assert out.realized_gains_losses[0].total_cost_basis_eur == D('5200')
        assert out.realized_gains_losses[0].gross_gain_loss_eur == D('1800')


def test_writer_cash_settlement_is_a_separate_derivative_loss():
    from src.domain.assets import Option
    from src.domain.events import OptionCashSettlementEvent
    from src.engine.event_processors.option_processor import OptionCashSettlementProcessor
    from src.engine.fifo_manager import FifoLedger, ShortFifoLot
    from types import SimpleNamespace
    option_asset = Option(currency='EUR', multiplier=D('100'), ibkr_conid='SYNTHETIC_SETTLEMENT')
    ledger = FifoLedger(option_asset.internal_asset_id, AssetCategory.OPTION, D('100'),
                        None, None, 28, 'ROUND_HALF_UP')
    # Different opening premiums must not change the settlement allocation.
    ledger.short_lots = [ShortFifoLot('2024-01-01', D('1'), D('200'), D('200'), 'FIRST'),
                         ShortFifoLot('2024-02-01', D('1'), D('800'), D('800'), 'SECOND')]
    event = OptionCashSettlementEvent(option_asset.internal_asset_id, '2025-03-01',
        quantity_contracts=D('2'), cash_settlement_proceeds=D('-600'),
        gross_amount_eur=D('-600'), local_currency='EUR', commission_eur=D('2'))
    resolver = SimpleNamespace(get_asset_by_id=lambda _: option_asset)
    rows = OptionCashSettlementProcessor().process(event, ledger, {'asset_resolver': resolver})
    assert [r.gross_gain_loss_eur for r in rows] == [D('-301'), D('-301')]
    assert all(r.total_realization_value_eur == 0 and not r.is_stillhalter_income for r in rows)
    assert all(r.tax_reporting_category == TC.ANLAGE_KAP_TERMIN_VERLUST for r in rows)
    assert ledger.short_lots == []


@pytest.mark.parametrize('historical', [False, True])
@pytest.mark.parametrize('kind,writer', [('C', False), ('P', False), ('C', True), ('P', True)])
def test_fund_delivery_preserves_holder_cost_and_separates_writer_premium(historical, kind, writer):
    from types import SimpleNamespace
    from src.domain.assets import Option, InvestmentFund
    from src.domain.enums import FinancialEventType as FT, InvestmentFundType
    from src.domain.events import OptionExerciseEvent, OptionAssignmentEvent, TradeEvent
    from src.engine.fifo_manager import FifoLedger, FifoLot, ShortFifoLot
    from src.engine.option_premiums import OptionPremiumBook
    from src.engine.event_processors.option_processor import OptionExerciseProcessor, OptionAssignmentProcessor
    from src.engine.event_processors.trade_processor import TradeProcessor
    from src.engine.calculation_engine import _replay_security_with_option_costs
    from src.processing.option_trade_linker import perform_option_trade_linking
    fund = InvestmentFund(currency='EUR', ibkr_isin='LU0000000085', fund_type=InvestmentFundType.AKTIENFONDS)
    opt = Option(currency='EUR', ibkr_conid='FUND_OPTION', multiplier=D('100'),
                 underlying_asset_internal_id=fund.internal_asset_id, option_type=kind, strike_price=D('50'))
    assets = {a.internal_asset_id: a for a in (fund, opt)}
    resolver = SimpleNamespace(get_asset_by_id=assets.get)
    def ledger(asset):
        return FifoLedger(asset.internal_asset_id, asset.asset_category, D('100') if asset is opt else D('1'),
                          None, None, 28, 'ROUND_HALF_UP',
                          fund_type=InvestmentFundType.AKTIENFONDS if asset is fund else None)
    option_ledger, fund_ledger = ledger(opt), ledger(fund)
    if writer:
        option_ledger.short_lots = [ShortFifoLot('2024-01-02', D('1'), D('200'), D('200'), 'OPEN')]
    else:
        option_ledger.lots = [FifoLot('2024-01-02', D('1'), D('200'), D('200'), 'OPEN')]
    event_class = OptionAssignmentEvent if writer else OptionExerciseEvent
    event = event_class(opt.internal_asset_id, '2024-06-20', quantity_contracts=D('1'),
                        local_currency='EUR', ibkr_transaction_id='200', account_id='A')
    buy = (kind == 'C') != writer
    trade = TradeEvent(fund.internal_asset_id, '2024-06-20', quantity=D('100') if buy else D('-100'),
        price_foreign_currency=D('50'), net_proceeds_or_cost_basis_eur=D('5000'),
        event_type=FT.TRADE_BUY_LONG if buy else FT.TRADE_SELL_SHORT_OPEN,
        local_currency='EUR', ibkr_transaction_id='300', ibkr_notes_codes='A' if writer else 'Ex', account_id='A')
    perform_option_trade_linking(resolver, [event], [trade])
    assert len(trade.option_delivery_links) == 1
    book = OptionPremiumBook()
    if historical:
        _replay_security_with_option_costs(option_ledger, opt, event, 2025, book, resolver)
        _replay_security_with_option_costs(fund_ledger, fund, trade, 2025, book, resolver)
    else:
        context = {'asset_resolver': resolver, 'option_premiums': book}
        processor = OptionAssignmentProcessor() if writer else OptionExerciseProcessor()
        assert processor.process(event, option_ledger, context) == []
        assert TradeProcessor().process(trade, fund_ledger, context) == []
    expected = D('5000') if writer else D('5200') if kind == 'C' else D('4800')
    assert trade.net_proceeds_or_cost_basis_eur == expected
    assert not option_ledger.lots and not option_ledger.short_lots
    if buy:
        assert fund_ledger.lots[0].total_cost_basis_eur == expected
    else:
        assert fund_ledger.short_lots[0].total_sale_proceeds_eur == expected
    book.require_empty()


@pytest.mark.parametrize('day,warns', [('12-26', False), ('12-27', True), ('12-31', True), ('01-02', False)])
def test_year_boundary_warning_preserves_trade_date(day, warns):
    from src.domain.assets import Option
    from src.domain.events import TradeEvent
    from src.domain.enums import FinancialEventType as FT
    from src.engine.calculation_engine import _warn_option_premiums_near_year_end
    from src.processing.data_gaps import DataGapCollector
    from types import SimpleNamespace
    asset = Option(currency='EUR')
    event = TradeEvent(asset.internal_asset_id, f'2025-{day}', quantity=D('-1'),
        price_foreign_currency=D('2'), event_type=FT.TRADE_SELL_SHORT_OPEN)
    collector = DataGapCollector()
    _warn_option_premiums_near_year_end([event], SimpleNamespace(get_asset_by_id=lambda _: asset),
                                      2025, collector)
    assert bool(collector.gaps) is warns
    assert event.event_date == f'2025-{day}'

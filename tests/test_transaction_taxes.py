"""
A transaction tax charged on a share trade -- a stamp duty -- is part of the trade.

legal_basis: [GT-ESTG20-068]. § 20 Abs. 4 Satz 1 EStG measures the gain as the Einnahmen
less the Aufwendungen in unmittelbarem sachlichem Zusammenhang with the disposal, less
the Anschaffungskosten; § 255 Abs. 1 Satz 2 HGB puts the Nebenkosten of a purchase into
the Anschaffungskosten, and BMF 14.05.2025 Rz. 93 Satz 2 names both sides in one
sentence. So a tax on a buy raises the cost basis of the lot bought, and a tax on a sale
lowers the proceeds. Each leg is converted on its own date ([GT-ESTG20-022]).

The tax is also cash: a buy pays gross + tax, a sale receives gross - tax. That is one
currency movement, the trade's own, and the currency assertions below are made on the
account's balance (no cash data gap) as well as on the realised result.

No taxed foreign-currency trade here is dated on a day whose rate is 1, and no two dates
of one scenario share a rate. At a rate of 1 the tax in EUR and the tax in the foreign
currency are the same number, and a site that used the wrong one of the two -- or the
rate of the wrong day -- would pass.

Every expected value is derived from the claim, in the comment beside it. All identifiers
and amounts are invented.
"""
from decimal import Decimal

import pytest

from src.domain.enums import FinancialEventType, RealizationType
from src.domain.events import TradeEvent
from src.engine.fifo_manager import split_position_flip_event
from src.processing.enrichment import enrich_financial_events
from src.utils.currency_converter import CurrencyConverter
from tests.support.base import FifoTestCaseBase
from tests.support.mock_providers import MockECBExchangeRateProvider
from tests.support.multi_account import (
    cash_balance_row, fx_trade_row, position_row, trade_row)

ACCOUNT = "U10000001"
TAX_YEAR = 2025


class _RatePerDate(MockECBExchangeRateProvider):
    """EUR per unit of the foreign currency, per date (ECB's reciprocal is stored).

    Use rates whose reciprocal is exact -- 0.50, 0.625, 0.80 -- or the expected values
    below pick up a rounding tail that belongs to the fixture, not to the rule.
    """

    def __init__(self, eur_per_unit_by_date, default=Decimal("1.00")):
        super().__init__(default)
        self._by_date = {d: Decimal("1") / Decimal(str(r))
                         for d, r in eur_per_unit_by_date.items()}

    def get_rate(self, rate_date, currency):
        if currency and currency.upper() == "EUR":
            return Decimal("1")
        return self._by_date.get(rate_date.isoformat(),
                                 super().get_rate(rate_date, currency))


def _usd_cash_position(account, quantity, cost_basis_eur):
    """A USD cash balance in a Positions snapshot -- where a balance's cost comes from."""
    q = Decimal(str(quantity))
    unit = Decimal(str(cost_basis_eur)) / q if q else Decimal("1")
    return [account, "USD", "CASH", "", "USD", "Cash Balance USD", "", q,
            q * unit, unit, Decimal(str(cost_basis_eur)), None, None, None, Decimal("1")]


def _sales(out):
    return [r for r in out.realized_gains_losses
            if r.realization_type == RealizationType.LONG_POSITION_SALE]


def _usd_results(out):
    usd_ids = {a.internal_asset_id
               for a in out.asset_resolver.assets_by_internal_id.values()
               if a.__class__.__name__ == "CashBalance" and getattr(a, "currency", None) == "USD"}
    return [r for r in out.realized_gains_losses if r.asset_internal_id in usd_ids]


class TestATaxOnABuyJoinsTheCostBasis(FifoTestCaseBase):
    """Bought and sold inside the tax year, so no snapshot can supply the lot's cost."""

    ISIN = "DE000000TAX1"

    def test_the_gain_is_lower_by_the_purchase_tax(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O",
                          "T_BUY", commission="-1", taxes="-5"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "12", "SELL", "C",
                          "T_SELL", commission="-1"),
            ],
            positions_end_data=[],
            tax_year=TAX_YEAR,
        )
        sales = _sales(out)
        assert len(sales) == 1, out.realized_gains_losses
        # Anschaffungskosten = 100 x 10 + 1 commission + 5 tax (both Nebenkosten) = 1006
        assert sales[0].total_cost_basis_eur == Decimal("1006")
        # Einnahmen less Veraeusserungskosten = 100 x 12 - 1 = 1199; gain = 1199 - 1006
        assert sales[0].gross_gain_loss_eur == Decimal("193")


class TestATaxOnASaleLowersTheProceeds(FifoTestCaseBase):
    ISIN = "DE000000TAX3"

    def test_the_gain_is_lower_by_the_sale_tax(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "12", "SELL", "C",
                          "T_SELL", commission="-1", taxes="-3"),
            ],
            positions_end_data=[],
            tax_year=TAX_YEAR,
        )
        sales = _sales(out)
        assert len(sales) == 1, out.realized_gains_losses
        assert sales[0].total_cost_basis_eur == Decimal("1000")
        # 100 x 12 less the costs of the disposal, 1 commission + 3 tax = 1196
        assert sales[0].total_realization_value_eur == Decimal("1196")
        assert sales[0].gross_gain_loss_eur == Decimal("196")


class TestABuyPaysItsTaxOutOfTheCurrencyBalance(FifoTestCaseBase):
    """1000 USD held at 0.80 EUR. One share bought for 100 USD plus 10 USD tax on a day at
    0.50, sold for 100 USD on a day at 0.625."""

    ISIN = "US000000TAX1"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-03-01", "1", "100", "BUY", "O",
                          "T_BUY", currency="USD", taxes="-10"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "-1", "100", "SELL", "C",
                          "T_SELL", currency="USD"),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, "1000", "800")],
            positions_end_data=[_usd_cash_position(ACCOUNT, "990", "772")],
            # The broker's closing balance: 1000 - (100 + 10) + 100.
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "1000", "990", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-03-01": "0.50", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR,
        )

    def test_the_balance_the_engine_ends_on_is_the_brokers(self):
        assert self._run().data_gaps == []

    def test_the_tax_joins_the_cost_basis_at_the_purchase_days_rate(self):
        sales = _sales(self._run())
        assert len(sales) == 1
        # (100 + 10) USD x 0.50, the rate of the day of acquisition ([GT-ESTG20-022]).
        # The tax taken unconverted would give 60; at the sale day's rate, 56.25.
        assert sales[0].total_cost_basis_eur == Decimal("55")

    def test_the_tax_is_part_of_the_purchase_not_a_second_movement(self):
        fx = _usd_results(self._run())
        # 110 USD leave the balance in one movement: acquired at 0.80, given up at 0.50.
        assert [r.realization_type for r in fx] == [RealizationType.FX_IMPLICIT_SECURITY_PURCHASE]
        assert fx[0].quantity_realized == Decimal("110")
        assert fx[0].gross_gain_loss_eur == Decimal("-33")   # 110 x (0.50 - 0.80)


class TestASaleReceivesItsProceedsLessTheTax(FifoTestCaseBase):
    """No USD held. One share bought for 100 USD on a day at 0.80, which leaves the account
    100 USD short; sold for 100 USD with 10 USD tax on a day at 0.625. Only 90 USD come
    back, so 90 of the short are covered and 10 stay open."""

    ISIN = "US000000TAX3"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-03-01", "1", "100", "BUY", "O",
                          "T_BUY", currency="USD"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "-1", "100", "SELL", "C",
                          "T_SELL", currency="USD", taxes="-10"),
            ],
            positions_end_data=[_usd_cash_position(ACCOUNT, "-10", "-8")],
            # 0 - 100 + (100 - 10)
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "0", "-10", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-03-01": "0.80", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR,
        )

    def test_the_balance_the_engine_ends_on_is_the_brokers(self):
        assert self._run().data_gaps == []

    def test_the_proceeds_are_net_of_the_tax_at_the_sale_days_rate(self):
        sales = _sales(self._run())
        assert len(sales) == 1
        # (100 - 10) USD x 0.625, the rate of the day of disposal. The tax taken
        # unconverted would give 52.5; at the purchase day's rate, 54.5.
        assert sales[0].total_realization_value_eur == Decimal("56.25")

    def test_the_currency_received_is_valued_net_of_the_tax(self):
        fx = _usd_results(self._run())
        # 90 USD of the short, opened at 0.80 (72.00), are covered by 90 USD worth
        # 90 x 0.625 = 56.25. Valued with the tax unconverted they would be worth 52.50.
        assert [r.realization_type for r in fx] == [RealizationType.FX_IMPLICIT_SECURITY_SALE]
        assert fx[0].quantity_realized == Decimal("90")
        assert fx[0].gross_gain_loss_eur == Decimal("15.75")


class TestAPriorYearPurchaseTax(FifoTestCaseBase):
    """The buy lies before the tax year, so both of its effects come from the replay."""

    ISIN = "US000000TAX2"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                # 2024: 1000 USD bought for 1000 EUR; 5 shares at 100 USD plus 50 USD tax.
                fx_trade_row(ACCOUNT, "USD", "BUY", "1000", "1000", "1.00", "2024-01-15", "H_FX"),
                trade_row(ACCOUNT, self.ISIN, "2024-06-01", "5", "100", "BUY", "O",
                          "H_BUY", currency="USD", taxes="-50"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-5", "120", "SELL", "C",
                          "T_SELL", currency="USD"),
            ],
            positions_start_data=[
                position_row(ACCOUNT, self.ISIN, "5", "550", currency="USD", price="100"),
                _usd_cash_position(ACCOUNT, "450", "450"),
            ],
            positions_end_data=[_usd_cash_position(ACCOUNT, "1050", "1050")],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "450", "1050", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2024-01-15": "1.00", "2024-06-01": "1.00",
                                               "2025-06-10": "1.00"}),
            tax_year=TAX_YEAR,
        )

    def test_the_replayed_lot_carries_the_tax(self):
        sales = _sales(self._run())
        assert len(sales) == 1
        # 5 x 100 + 50 tax = 550; without the tax the replayed lot would cost 500
        assert sales[0].total_cost_basis_eur == Decimal("550")
        assert sales[0].gross_gain_loss_eur == Decimal("50")

    def test_the_replayed_balance_is_what_the_broker_opened_the_year_with(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="src.engine.calculation_engine"):
            out = self._run()
        # 1000 - 500 - 50 = 450. A replay that forgot the tax rebuilds 500 and the
        # start-of-year reconciliation has 50 USD to explain away.
        gaps = [r.message for r in caplog.records
                if "SOY reconciliation" in r.message and "USD" in r.message]
        assert gaps == [], gaps
        assert out.data_gaps == []


class TestAPriorYearSaleTax(FifoTestCaseBase):
    """A taxed sale before the tax year: the replay must rebuild the balance the sale
    actually left, gross less tax."""

    ISIN = "US000000TAX4"

    def test_the_replayed_balance_is_what_the_broker_opened_the_year_with(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="src.engine.calculation_engine"):
            out = self._run_pipeline(
                trades_data=[
                    fx_trade_row(ACCOUNT, "USD", "BUY", "1000", "1000", "1.00", "2024-01-15", "H_FX"),
                    trade_row(ACCOUNT, self.ISIN, "2024-03-01", "5", "100", "BUY", "O",
                              "H_BUY", currency="USD"),
                    trade_row(ACCOUNT, self.ISIN, "2024-06-01", "-5", "100", "SELL", "C",
                              "H_SELL", currency="USD", taxes="-50"),
                ],
                # 1000 - 500 + (500 - 50)
                positions_start_data=[_usd_cash_position(ACCOUNT, "950", "950")],
                positions_end_data=[_usd_cash_position(ACCOUNT, "950", "950")],
                cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "950", "950", year=TAX_YEAR)],
                custom_rate_provider=_RatePerDate({"2024-01-15": "1.00", "2024-03-01": "1.00",
                                                   "2024-06-01": "1.00"}),
                tax_year=TAX_YEAR,
            )
        gaps = [r.message for r in caplog.records
                if "SOY reconciliation" in r.message and "USD" in r.message]
        assert gaps == [], gaps
        assert out.data_gaps == []


class TestTheReplayValuesAPriorYearTaxInEur(FifoTestCaseBase):
    """The replay keeps a EUR value in two places only, and each needs its own shape to be
    seen: a sale creates a currency lot costed at it, and a purchase uses it solely when it
    overdraws the balance and opens a short. With enough currency on hand a replayed
    purchase consumes lots and its EUR value is never read."""

    def test_a_taxed_sale_leaves_a_lot_costed_at_the_sale_days_rate(self):
        isin = "US000000TAX5"
        out = self._run_pipeline(
            trades_data=[
                fx_trade_row(ACCOUNT, "USD", "BUY", "1000", "1000", "1.00", "2024-01-15", "H_FX"),
                trade_row(ACCOUNT, isin, "2024-03-01", "5", "100", "BUY", "O", "H_BUY",
                          currency="USD"),
                trade_row(ACCOUNT, isin, "2024-06-01", "-5", "100", "SELL", "C", "H_SELL",
                          currency="USD", taxes="-50"),
                # Tax year: the whole balance is sold for EUR at 0.625 (1.6 USD per EUR).
                fx_trade_row(ACCOUNT, "USD", "SELL", "950", "593.75", "1.6", "2025-03-01", "T_FX"),
            ],
            # 500 USD left of the 1000 bought at 1.00, and (500 - 50) received at 0.50.
            positions_start_data=[_usd_cash_position(ACCOUNT, "950", "725")],
            positions_end_data=[],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "950", "0", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2024-01-15": "1.00", "2024-03-01": "0.80",
                                               "2024-06-01": "0.50", "2025-03-01": "0.625"}),
            tax_year=TAX_YEAR,
        )
        assert out.data_gaps == []
        results = sorted(r.gross_gain_loss_eur for r in _usd_results(out))
        # 500 USD: 312.50 - 500.00.  450 USD: 281.25 - 225.00, the lot the taxed sale left.
        # Had the replay taken the tax unconverted, that lot would cost 200 and yield 81.25.
        assert results == [Decimal("-187.5"), Decimal("56.25")]

    def test_a_taxed_purchase_that_overdraws_opens_a_short_at_the_purchase_days_rate(self):
        isin = "US000000TAX6"
        out = self._run_pipeline(
            trades_data=[
                # No USD held: 5 x 100 + 50 tax leaves the account 550 USD short, at 0.50.
                trade_row(ACCOUNT, isin, "2024-06-01", "5", "100", "BUY", "O", "H_BUY",
                          currency="USD", taxes="-50"),
                # Tax year: 550 USD bought for EUR at 0.625 cover it.
                fx_trade_row(ACCOUNT, "USD", "BUY", "550", "343.75", "1.6", "2025-03-01", "T_FX"),
            ],
            positions_start_data=[
                position_row(ACCOUNT, isin, "5", "550", currency="USD", price="100"),
                _usd_cash_position(ACCOUNT, "-550", "-275"),
            ],
            positions_end_data=[
                position_row(ACCOUNT, isin, "5", "550", currency="USD", price="100")],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "-550", "0", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2024-06-01": "0.50", "2025-03-01": "0.625"}),
            tax_year=TAX_YEAR,
        )
        assert out.data_gaps == []
        results = [r.gross_gain_loss_eur for r in _usd_results(out)]
        # The short was worth 550 x 0.50 = 275 and costs 343.75 to cover. Had the replay
        # taken the tax unconverted, the short would stand at 300 and the loss at 43.75.
        assert results == [Decimal("-68.75")]


def _covers(out):
    return [r for r in out.realized_gains_losses
            if r.realization_type == RealizationType.SHORT_POSITION_COVER]


class TestAShortSaleAndItsCoverAreTaxedLikeAnyOtherSaleAndPurchase(FifoTestCaseBase):
    """The rule is about the direction of the trade, not about which one opens the position.
    A short sale is a sale: its tax lowers the proceeds and the currency received. The cover
    is a purchase: its tax raises the cost and the currency paid.

    No USD held. Sold short 1 share at 100 USD with 10 USD tax on a day at 0.50; covered at
    80 USD with 8 USD tax on a day at 0.625."""

    ISIN = "US000000TAX7"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-03-01", "-1", "100", "SELL", "O",
                          "T_OPEN", currency="USD", taxes="-10"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "1", "80", "BUY", "C",
                          "T_COVER", currency="USD", taxes="-8"),
            ],
            positions_end_data=[_usd_cash_position(ACCOUNT, "2", "1.25")],
            # 0 + (100 - 10) - (80 + 8)
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "0", "2", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-03-01": "0.50", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR,
        )

    def test_the_balance_the_engine_ends_on_is_the_brokers(self):
        assert self._run().data_gaps == []

    def test_the_tax_lowers_the_short_sales_proceeds_and_raises_the_covers_cost(self):
        covers = _covers(self._run())
        assert len(covers) == 1
        assert covers[0].total_realization_value_eur == Decimal("45")   # (100 - 10) x 0.50
        assert covers[0].total_cost_basis_eur == Decimal("55")          # (80 + 8) x 0.625
        assert covers[0].gross_gain_loss_eur == Decimal("-10")

    def test_the_cover_pays_its_tax_out_of_the_currency_the_short_sale_brought_in(self):
        fx = _usd_results(self._run())
        # 90 USD came in at 0.50. 88 of them go out at 0.625.
        assert [r.realization_type for r in fx] == [RealizationType.FX_IMPLICIT_SECURITY_PURCHASE]
        assert fx[0].quantity_realized == Decimal("88")
        assert fx[0].gross_gain_loss_eur == Decimal("11")               # 88 x (0.625 - 0.50)


class TestAPriorYearShortSaleTax(FifoTestCaseBase):
    """The same short sale, opened before the tax year: its net proceeds and the currency it
    brought in both come from the replay."""

    ISIN = "US000000TAX8"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2024-06-01", "-1", "100", "SELL", "O",
                          "H_OPEN", currency="USD", taxes="-10"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "1", "80", "BUY", "C",
                          "T_COVER", currency="USD", taxes="-8"),
            ],
            positions_start_data=[
                position_row(ACCOUNT, self.ISIN, "-1", "-90", currency="USD", price="100"),
                _usd_cash_position(ACCOUNT, "90", "45"),
            ],
            positions_end_data=[_usd_cash_position(ACCOUNT, "2", "1")],
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "90", "2", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2024-06-01": "0.50", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR,
        )

    def test_the_replayed_short_carries_proceeds_net_of_the_tax(self):
        covers = _covers(self._run())
        assert len(covers) == 1
        assert covers[0].total_realization_value_eur == Decimal("45")   # (100 - 10) x 0.50
        assert covers[0].gross_gain_loss_eur == Decimal("-10")          # 45 - (80 + 8) x 0.625

    def test_the_replayed_balance_is_the_90_usd_the_short_sale_left(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="src.engine.calculation_engine"):
            out = self._run()
        gaps = [r.message for r in caplog.records
                if "SOY reconciliation" in r.message and "USD" in r.message]
        assert gaps == [], gaps
        assert out.data_gaps == []
        fx = _usd_results(out)
        assert [r.quantity_realized for r in fx] == [Decimal("88")]
        assert fx[0].gross_gain_loss_eur == Decimal("11")


class TestAPositionFlipSplitsTheTax:
    """A flip is one trade booked as two. Each leg draws its own currency, so each carries
    its share of the tax, as it carries its share of the commission."""

    def test_each_leg_carries_its_share(self):
        import uuid
        flip = TradeEvent(
            asset_internal_id=uuid.uuid4(), event_date="2025-03-01",
            event_type=FinancialEventType.TRADE_BUY_SHORT_COVER,
            quantity=Decimal("100"), price_foreign_currency=Decimal("10"),
            transaction_tax_foreign=Decimal("10"), transaction_tax_eur=Decimal("8"),
            gross_amount_foreign_currency=Decimal("1000"), gross_amount_eur=Decimal("800"),
            commission_eur=Decimal("0"), net_proceeds_or_cost_basis_eur=Decimal("808"),
            local_currency="USD", is_position_flip=True, ibkr_transaction_id="FLIP",
            account_id=ACCOUNT,
        )
        # 40 short to cover, so 40 close and 60 open.
        close, opened = split_position_flip_event(flip, Decimal("0"), Decimal("40"))
        assert (close.transaction_tax_foreign, opened.transaction_tax_foreign) == (Decimal("4"), Decimal("6"))
        assert (close.transaction_tax_eur, opened.transaction_tax_eur) == (Decimal("3.2"), Decimal("4.8"))


class TestATaxTheEngineHasNoTreatmentForStopsTheRun(FifoTestCaseBase):
    """Only a charge on a stock trade has been seen and has a rule. Anything else is refused,
    and every refused row is named in the one error."""

    def _refused(self, rows):
        # `_run_pipeline` re-raises a pipeline error as `pytest.fail.Exception` carrying the
        # original DataIntegrityError's message.
        with pytest.raises(pytest.fail.Exception, match="data integrity") as err:
            self._run_pipeline(trades_data=rows, positions_end_data=[], tax_year=TAX_YEAR)
        return str(err.value)

    def test_a_positive_tax(self):
        msg = self._refused([trade_row(ACCOUNT, "DE000000TAX4", "2025-01-10", "10", "10",
                                       "BUY", "O", "T_POS", taxes="5")])
        assert "T_POS" in msg and "positive" in msg

    def test_a_tax_on_an_option_row(self):
        msg = self._refused([trade_row(ACCOUNT, "DE000000TAX5", "2025-01-10", "1", "2",
                                       "BUY", "O", "T_OPT", asset_class="OPT",
                                       sub_category="C", multiplier="100", taxes="-1")])
        assert "T_OPT" in msg and "OPT" in msg

    def test_a_tax_on_a_currency_pair_row(self):
        """The row kind that leaves the trade loop early: a check placed after that exit
        never sees it."""
        fx = fx_trade_row(ACCOUNT, "USD", "BUY", "100", "100", "1.00", "2025-01-15", "T_FX")
        fx[-1] = Decimal("-1")
        msg = self._refused([fx])
        assert "T_FX" in msg and "CASH" in msg

    def test_a_tax_on_a_trade_of_no_value(self):
        """Its cost side would take the tax and its currency side would draw nothing."""
        msg = self._refused([trade_row(ACCOUNT, "DE000000TAX4", "2025-01-10", "10", "0",
                                       "BUY", "O", "T_ZERO", taxes="-5")])
        assert "T_ZERO" in msg and "zero" in msg

    def test_every_refused_row_is_named(self):
        msg = self._refused([
            trade_row(ACCOUNT, "DE000000TAX4", "2025-01-10", "10", "10", "BUY", "O",
                      "T_ONE", taxes="5"),
            trade_row(ACCOUNT, "DE000000TAX4", "2025-01-11", "10", "10", "BUY", "O",
                      "T_TWO", taxes="7"),
        ])
        assert "T_ONE" in msg and "T_TWO" in msg


class TestATaxThatCannotBeConvertedStopsTheRun:
    """The gross amount and the commission have their EUR values; only the tax does not.
    The trade must not get a cost basis that silently leaves the tax out."""

    def test_the_trade_is_left_without_a_net_and_enrichment_refuses_it(self):
        import uuid

        class _NoRates(MockECBExchangeRateProvider):
            def get_rate(self, rate_date, currency):
                return None

        trade = TradeEvent(
            asset_internal_id=uuid.uuid4(), event_date="2025-03-01",
            event_type=FinancialEventType.TRADE_BUY_LONG,
            quantity=Decimal("10"), price_foreign_currency=Decimal("10"),
            transaction_tax_foreign=Decimal("5"),
            gross_amount_foreign_currency=Decimal("100"), gross_amount_eur=Decimal("80"),
            commission_foreign_currency=Decimal("0"), commission_eur=Decimal("0"),
            local_currency="USD", ibkr_transaction_id="T_NORATE", account_id=ACCOUNT,
        )
        with pytest.raises(ValueError, match="T_NORATE"):
            enrich_financial_events([trade], CurrencyConverter(_NoRates()),
                                    internal_calculation_precision=28,
                                    decimal_rounding_mode="ROUND_HALF_UP")
        assert trade.net_proceeds_or_cost_basis_eur is None


class TestATaxedPositionFlipEndToEnd(FifoTestCaseBase):
    """The unit test above pins the split; this runs one through the pipeline. Long 100,
    then one SELL of 150 marked C;O -- 100 close the long, 50 open a short -- with a tax on
    it, then a taxed cover. Three dates, three rates."""

    ISIN = "US000000TAX9"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-02-01", "100", "10", "BUY", "O", "T_BUY",
                          currency="USD"),
                trade_row(ACCOUNT, self.ISIN, "2025-04-01", "-150", "12", "SELL", "C;O", "T_FLIP",
                          currency="USD", taxes="-18"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "50", "8", "BUY", "C", "T_COVER",
                          currency="USD", taxes="-4"),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, "1000", "1000")],
            positions_end_data=[_usd_cash_position(ACCOUNT, "1378", "1000")],
            # 1000 - 1000 + (1800 - 18) - (400 + 4)
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "1000", "1378", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-02-01": "0.80", "2025-04-01": "0.50",
                                               "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR,
        )

    def test_the_balance_the_engine_ends_on_is_the_brokers(self):
        assert self._run().data_gaps == []

    def test_each_leg_carries_its_share_of_the_tax_into_its_own_gain(self):
        out = self._run()
        sale, = _sales(out)
        cover, = _covers(out)
        # Close leg, 100 of 150: proceeds (1200 - 12) x 0.50 = 594; cost 1000 x 0.80 = 800.
        assert sale.total_realization_value_eur == Decimal("594")
        assert sale.gross_gain_loss_eur == Decimal("-206")
        # Open leg, 50 of 150: proceeds (600 - 6) x 0.50 = 297; cover (400 + 4) x 0.625 = 252.5.
        assert cover.total_realization_value_eur == Decimal("297")
        assert cover.total_cost_basis_eur == Decimal("252.5")
        assert cover.gross_gain_loss_eur == Decimal("44.5")


class TestTheEventListingShowsTheTax(FifoTestCaseBase):
    """The per-event diagnostic listing. A reader checking a taxed trade against the broker's
    statement has to find the tax on it; without the line the listing still adds up to the
    wrong total and nothing says why."""

    ISIN = "DE000000TAXA"

    def test_a_taxed_trade_lists_its_tax_in_both_currencies(self, capsys):
        from src.reporting.diagnostic_reports import print_grouped_event_details
        out = self._run_pipeline(
            trades_data=[trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O",
                                   "T_BUY", taxes="-5")],
            positions_end_data=[position_row(ACCOUNT, self.ISIN, "100", "1005", price="10")],
            tax_year=TAX_YEAR)
        capsys.readouterr()
        print_grouped_event_details(out.all_financial_events_enriched, out.asset_resolver)
        listing = capsys.readouterr().out
        assert "Tax: 5" in listing and "TaxEUR: 5" in listing


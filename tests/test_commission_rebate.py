"""
A commission that comes out as a credit is part of the trade it was booked on.

legal_basis: [GT-ESTG20-069]. § 255 Abs. 1 Satz 3 HGB subtracts a reduction of the
acquisition cost that can be attributed to the asset. BFH IX R 46/03 includes third-party
reductions, provided they do not remunerate a separate service by the recipient.
These fixtures model the contemporaneous net price for executing the identified trade:
a credit lowers a purchase's cost and raises a disposal's net proceeds under § 20
Abs. 4 Satz 1. Q21 distinguishes independent reimbursements and payments for separate
services, which require their own facts and characterisation. No taxpayer election
is asserted by these tests. The execution-price credit is the mirror of a charge
([GT-ESTG20-068]) and is converted on the trade date like the rest of the trade
([GT-ESTG20-022]).

The export signs a charge negative and a credit positive. Every expected value is derived in
the comment beside it; all identifiers and amounts are invented. No foreign-currency trade
here is dated on a day whose rate is 1, and no two dates of a scenario share a rate.
"""
from decimal import Decimal

from src.domain.enums import RealizationType
from tests.support.base import FifoTestCaseBase
from tests.support.mock_providers import MockECBExchangeRateProvider
from tests.support.multi_account import cash_balance_row, position_row, trade_row

ACCOUNT = "U10000001"
TAX_YEAR = 2025


class _RatePerDate(MockECBExchangeRateProvider):
    """EUR per unit of the foreign currency, per date. Use rates with an exact reciprocal."""

    def __init__(self, eur_per_unit_by_date):
        super().__init__(Decimal("1.00"))
        self._by_date = {d: Decimal("1") / Decimal(str(r)) for d, r in eur_per_unit_by_date.items()}

    def get_rate(self, rate_date, currency):
        if currency and currency.upper() == "EUR":
            return Decimal("1")
        return self._by_date.get(rate_date.isoformat(), super().get_rate(rate_date, currency))


def _usd_cash_position(account, quantity, cost_basis_eur):
    q = Decimal(str(quantity))
    unit = Decimal(str(cost_basis_eur)) / q if q else Decimal("1")
    return [account, "USD", "CASH", "", "USD", "Cash Balance USD", "", q,
            q * unit, unit, Decimal(str(cost_basis_eur)), None, None, None, Decimal("1")]


def _of(out, kind):
    return [r for r in out.realized_gains_losses if r.realization_type == kind]


class TestACreditOnAPurchaseLowersItsCost(FifoTestCaseBase):
    ISIN = "DE000000REB1"

    def test_bought_and_sold_inside_the_year(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY",
                          commission="2"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "12", "SELL", "C", "T_SELL",
                          commission="-1"),
            ],
            positions_end_data=[], tax_year=TAX_YEAR)
        sale, = _of(out, RealizationType.LONG_POSITION_SALE)
        assert sale.total_cost_basis_eur == Decimal("998")        # 100 x 10 - 2 credit
        assert sale.total_realization_value_eur == Decimal("1199")  # 100 x 12 - 1 charge
        assert sale.gross_gain_loss_eur == Decimal("201")


class TestACreditOnASaleRaisesItsProceeds(FifoTestCaseBase):
    ISIN = "DE000000REB2"

    def test_the_proceeds_include_the_credit(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "12", "SELL", "C", "T_SELL",
                          commission="3"),
            ],
            positions_end_data=[], tax_year=TAX_YEAR)
        sale, = _of(out, RealizationType.LONG_POSITION_SALE)
        assert sale.total_realization_value_eur == Decimal("1203")  # 100 x 12 + 3 credit
        assert sale.gross_gain_loss_eur == Decimal("203")


class TestACreditInForeignCurrency(FifoTestCaseBase):
    """1000 USD held at 0.80. One share bought for 100 USD with a 4 USD credit on a day at
    0.50; sold for 100 USD with a 2 USD credit on a day at 0.625."""

    ISIN = "US000000REB3"

    def _run(self):
        return self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-03-01", "1", "100", "BUY", "O", "T_BUY",
                          currency="USD", commission="4"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "-1", "100", "SELL", "C", "T_SELL",
                          currency="USD", commission="2"),
            ],
            positions_start_data=[_usd_cash_position(ACCOUNT, "1000", "800")],
            positions_end_data=[_usd_cash_position(ACCOUNT, "1006", "800")],
            # 1000 - 100 + 4 + 100 + 2
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "1000", "1006", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-03-01": "0.50", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR)

    def test_each_credit_is_converted_on_its_own_trade_date(self):
        sale, = _of(self._run(), RealizationType.LONG_POSITION_SALE)
        assert sale.total_cost_basis_eur == Decimal("48")            # (100 - 4) x 0.50
        assert sale.total_realization_value_eur == Decimal("63.75")  # (100 + 2) x 0.625

    def test_the_balance_the_engine_ends_on_is_the_brokers(self):
        assert self._run().data_gaps == []


class TestACreditOnAShortSaleAndAChargeOnItsCover(FifoTestCaseBase):
    """Direction decides, not which trade opens the position: a short sale is a sale."""

    ISIN = "US000000REB4"

    def test_the_short_sales_proceeds_include_the_credit(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-03-01", "-1", "100", "SELL", "O", "T_OPEN",
                          currency="USD", commission="2"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-01", "1", "80", "BUY", "C", "T_COVER",
                          currency="USD", commission="-4"),
            ],
            positions_end_data=[_usd_cash_position(ACCOUNT, "18", "9")],
            # 0 + (100 + 2) - (80 + 4)
            cash_balance_data=[cash_balance_row(ACCOUNT, "USD", "0", "18", year=TAX_YEAR)],
            custom_rate_provider=_RatePerDate({"2025-03-01": "0.50", "2025-06-01": "0.625"}),
            tax_year=TAX_YEAR)
        assert out.data_gaps == []
        cover, = _of(out, RealizationType.SHORT_POSITION_COVER)
        assert cover.total_realization_value_eur == Decimal("51")    # (100 + 2) x 0.50
        assert cover.total_cost_basis_eur == Decimal("52.5")         # (80 + 4) x 0.625
        assert cover.gross_gain_loss_eur == Decimal("-1.5")


class TestACreditOnAPriorYearPurchase(FifoTestCaseBase):
    """The lot is rebuilt by the replay. The snapshot has to state a cost and states the right
    one; that it is the replayed cost and not the snapshot's which reaches the gain is what
    the mutation probe of this test establishes, not this docstring."""

    ISIN = "DE000000REB5"

    def test_the_replayed_lot_carries_the_credit(self):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2024-06-01", "100", "10", "BUY", "O", "H_BUY",
                          commission="2"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "12", "SELL", "C", "T_SELL"),
            ],
            positions_start_data=[position_row(ACCOUNT, self.ISIN, "100", "998", price="10")],
            positions_end_data=[], tax_year=TAX_YEAR)
        sale, = _of(out, RealizationType.LONG_POSITION_SALE)
        assert sale.total_cost_basis_eur == Decimal("998")
        assert sale.gross_gain_loss_eur == Decimal("202")

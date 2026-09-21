"""
A sale whose costs are larger than its price brings in less than nothing, and the loss says so.

legal_basis: [GT-ESTG20-011]. § 20 Abs. 4 Satz 1 EStG takes the Einnahmen *"nach Abzug der
Aufwendungen, die im unmittelbaren sachlichen Zusammenhang mit dem Veraeusserungsgeschaeft
stehen"* and sets nothing as a floor under the result; a commission and a transaction tax on the
sale are such Aufwendungen ([GT-ESTG20-068]). A near-worthless position sold at a minimum
commission is the ordinary way to get here.

The engine took the absolute value of the net proceeds where a sale consumes its lots, so
-3 became +3 and the loss came out smaller by twice the excess. All amounts are invented.
"""
from decimal import Decimal

import pytest

from src.domain.enums import RealizationType
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import position_row, trade_row

ACCOUNT = "U10000001"


class TestALongSaleThatCostsMoreThanItBrings(FifoTestCaseBase):
    ISIN = "DE000000NEG1"

    def _sale(self, **sell_costs):
        out = self._run_pipeline(
            trades_data=[
                trade_row(ACCOUNT, self.ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY"),
                trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-100", "0.01", "SELL", "C", "T_SELL",
                          **sell_costs),
            ],
            positions_end_data=[], tax_year=2025)
        sale, = [r for r in out.realized_gains_losses
                 if r.realization_type == RealizationType.LONG_POSITION_SALE]
        return sale

    def test_commission_and_tax_together_exceed_the_price(self):
        sale = self._sale(commission="-1", taxes="-3")
        assert sale.total_realization_value_eur == Decimal("-3")   # 100 x 0.01 - 1 - 3
        assert sale.gross_gain_loss_eur == Decimal("-1003")        # -3 - 1000

    def test_the_commission_alone_exceeds_the_price(self):
        sale = self._sale(commission="-4")
        assert sale.total_realization_value_eur == Decimal("-3")
        assert sale.gross_gain_loss_eur == Decimal("-1003")


class TestAShortSaleThatCostsMoreThanItBrings(FifoTestCaseBase):
    """A short lot records what the sale brought in, and the ledger has no place for a lot
    that brought in less than nothing. The run stops and names the trade; it does not book
    the magnitude."""

    def test_the_run_stops_and_names_the_trade(self):
        with pytest.raises(pytest.fail.Exception, match="T_OPEN"):
            self._run_pipeline(
                trades_data=[trade_row(ACCOUNT, "DE000000NEG2", "2025-03-01", "-100", "0.01",
                                       "SELL", "O", "T_OPEN", commission="-4")],
                # The short is still open at year end, so the run would otherwise complete.
                positions_end_data=[position_row(ACCOUNT, "DE000000NEG2", "-100", "-1",
                                                 price="0.01")],
                tax_year=2025)

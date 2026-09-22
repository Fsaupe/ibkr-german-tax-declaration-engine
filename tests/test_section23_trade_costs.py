"""
A gold ETC trades as AssetClass STK, so whatever the engine does with a stock trade's costs
it does to a § 23 asset too. The rule is the same one and has its own ground.

legal_basis: [GT-ESTG23-008]. § 23 Abs. 3 Satz 1 EStG subtracts the Anschaffungskosten and the
Werbungskosten from the Veraeusserungspreis; the Anschaffungskosten are those of § 255 Abs. 1
HGB, so a Nebenkosten of the purchase raises them ([GT-ESTG20-068]) and a reduction caused by
it lowers them ([GT-ESTG20-069]); a cost of the disposal is a Werbungskosten. All
identifiers and amounts are invented.
"""
from decimal import Decimal

from src.domain.enums import AssetCategory
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import trade_row

ACCOUNT = "U10000001"
DESCRIPTION = 5   # TRADES_COLUMNS index


def _gold(row):
    """The classifier reads the description; this is the wording the suite uses for § 23."""
    row[DESCRIPTION] = "GLDX XETRA-GOLD Physical Gold ETC"
    return row


class TestTheCostsOfASection23Trade(FifoTestCaseBase):
    ISIN = "DE000000GLD1"

    def _gain(self, buy, sell):
        out = self._run_pipeline(trades_data=[_gold(buy), _gold(sell)],
                                 positions_end_data=[], tax_year=2025)
        asset, = [a for a in out.asset_resolver.assets_by_internal_id.values()
                  if a.asset_category == AssetCategory.PRIVATE_SALE_ASSET]
        gain, = [r for r in out.realized_gains_losses
                 if r.asset_internal_id == asset.internal_asset_id]
        return gain

    def test_a_purchase_tax_and_a_sale_tax_both_lower_the_gain(self):
        gain = self._gain(
            trade_row(ACCOUNT, self.ISIN, "2025-01-10", "10", "100", "BUY", "O", "T_BUY",
                      commission="-1", taxes="-5"),
            trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-10", "120", "SELL", "C", "T_SELL",
                      commission="-1", taxes="-3"))
        assert gain.total_cost_basis_eur == Decimal("1006")           # 1000 + 1 + 5
        assert gain.total_realization_value_eur == Decimal("1196")    # 1200 - 1 - 3
        assert gain.gross_gain_loss_eur == Decimal("190")

    def test_a_credit_on_the_purchase_lowers_its_cost(self):
        gain = self._gain(
            trade_row(ACCOUNT, self.ISIN, "2025-01-10", "10", "100", "BUY", "O", "T_BUY",
                      commission="2"),
            trade_row(ACCOUNT, self.ISIN, "2025-06-10", "-10", "120", "SELL", "C", "T_SELL"))
        assert gain.total_cost_basis_eur == Decimal("998")            # 1000 - 2
        assert gain.gross_gain_loss_eur == Decimal("202")

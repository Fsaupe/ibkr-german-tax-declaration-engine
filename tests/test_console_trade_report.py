"""
The per-symbol trade table (`--report-stock-trades`) is a diagnostic, not a declared
figure -- but a reader checks a trade against the broker's statement with it, so its local
net has to be what the trade cost or brought in.

What a buy costs is its value plus the commission and the transaction tax; what a sale
brings in is its value less both ([GT-ESTG20-068]). The export states a commission as a
negative number and a rebate as a positive one, so the net follows the sign instead of
assuming it. All identifiers and amounts are invented.
"""
from decimal import Decimal

from src.reporting.console_reporter import generate_stock_trade_report_for_symbol
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import trade_row

ACCOUNT = "U10000001"
ISIN = "DE000000CON1"
SYMBOL = ISIN[:6]
NET_LOCAL = 8  # Date, Type, Qty, Price, Curr, Value, Comm, Tax, Net Val (Local), ...


class TestTheLocalNetOfATrade(FifoTestCaseBase):

    def _rows(self, capsys, trades):
        out = self._run_pipeline(trades_data=trades, positions_end_data=[], tax_year=2025)
        capsys.readouterr()
        generate_stock_trade_report_for_symbol(
            SYMBOL, out.all_financial_events_enriched, out.realized_gains_losses,
            out.asset_resolver, 2025)
        lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("2025-")]
        return {l.split(" | ")[1].strip(): Decimal(l.split(" | ")[NET_LOCAL].strip())
                for l in lines}

    def test_a_buy_costs_its_value_plus_commission_and_tax(self, capsys):
        nets = self._rows(capsys, [
            trade_row(ACCOUNT, ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY",
                      commission="-2", taxes="-5"),
            trade_row(ACCOUNT, ISIN, "2025-06-10", "-100", "12", "SELL", "C", "T_SELL",
                      commission="-3", taxes="-4"),
        ])
        assert nets["TRADE_BUY_LONG"] == Decimal("1007")    # 1000 + 2 + 5
        assert nets["TRADE_SELL_LONG"] == Decimal("1193")   # 1200 - 3 - 4

    def test_a_rebate_lowers_a_cost_and_raises_proceeds(self, capsys):
        nets = self._rows(capsys, [
            trade_row(ACCOUNT, ISIN, "2025-01-10", "100", "10", "BUY", "O", "T_BUY",
                      commission="2"),
            trade_row(ACCOUNT, ISIN, "2025-06-10", "-100", "12", "SELL", "C", "T_SELL",
                      commission="3"),
        ])
        assert nets["TRADE_BUY_LONG"] == Decimal("998")
        assert nets["TRADE_SELL_LONG"] == Decimal("1203")

# tests/test_withholding_link_same_day_incomes.py
"""A withholding row is measured against the income it was levied on.

DBA-USA Art. 10 Abs. 2 limits the tax on a dividend against *"des Bruttobetrags der
Dividenden"* -- that dividend's gross ([GT-CREDIT-027]); the treaty-rate guard
([GT-CREDIT-026]) therefore depends on the linker attaching each tax row to its own
income. The broker books an income and its tax as consecutive TransactionIDs. When an
instrument pays two incomes on one day -- a payment in lieu and a dividend -- a tax row
can be "sequential" (1 to 5 IDs after) to both, both score 100, and the linker took
whichever came first in the list.

Measured 2026-09-23 on data_import/Cash_Transactions-{2023,2024}.csv: four DEM dates
with a payment in lieu and a dividend, three tax rows sequential to both; the nearer
income is always the one directly before the tax row. On 2023-12-28 the dividend's
tax set against the payment in lieu reads 16.9 % -- a false cap, had the row carried a
country code.

Currency: USD at 0.90 EUR/USD (helpers shared with test_payment_in_lieu_credit_route).
"""
from decimal import Decimal

from src.domain.enums import TaxReportingCategory
from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from tests.test_payment_in_lieu_credit_route import _line, _rct, _run_loss_offsetting
from tests.test_cash_transaction_reversals import _events

Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID
_STK = dict(asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON")
PIL = "ACME(US0000000AAA) PAYMENT IN LIEU OF DIVIDEND"
DIV = "ACME(US0000000AAA) CASH DIVIDEND USD 1.00 PER SHARE"

# The DEM shape: PIL, its tax, dividend, its tax -- each tax 15 % of its own income.
# The dividend's tax (tx 525) is sequential to both incomes; against the PIL it reads 30 %.
ROWS = [
    _rct(type_="Payment In Lieu Of Dividends", description=PIL + " (Ordinary Dividend)",
         amount=Decimal("500"), tx_id="522", **_STK),
    _rct(type_="Withholding Tax", description=PIL + " - US TAX", amount=Decimal("-75"), tx_id="523", **_STK),
    _rct(type_="Dividends", description=DIV + " (Ordinary Dividend)", amount=Decimal("1000"), tx_id="524", **_STK),
    _rct(type_="Withholding Tax", description=DIV + " - US TAX", amount=Decimal("-150"), tx_id="525", **_STK),
]


def test_each_tax_row_links_to_the_income_directly_before_it(tmp_path):
    events, _ = _events(tmp_path, ROWS)
    by_id = {e.event_id: e.ibkr_transaction_id for e in events if isinstance(e, CashFlowEvent)}
    links = {e.ibkr_transaction_id: by_id.get(e.taxed_income_event_id)
             for e in events if isinstance(e, WithholdingTaxEvent)}
    assert links == {"523": "522", "525": "524"}


def test_two_incomes_at_the_treaty_rate_are_credited_in_full(tmp_path):
    """Both taxes are 15 % of their own income: 225 USD -> 202.50 EUR, no gap. Linked to
    the payment in lieu, the dividend's tax reads 30 % and is capped to 75."""
    events, resolver = _events(tmp_path, ROWS)
    form, gaps = _run_loss_offsetting(events, resolver, tmp_path)
    assert _line(form, Z41) == Decimal("202.50")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in [g.code for g in gaps.gaps]

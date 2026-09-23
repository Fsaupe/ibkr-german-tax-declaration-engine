# tests/test_withholding_link_account_local.py
"""A withholding row is linked to an income of its own account only.

DBA-USA Art. 10 Abs. 2 limits the tax on a dividend against that dividend's gross
([GT-CREDIT-027]), and the treaty-rate assessment measures all the tax linked to one
income together ([GT-CREDIT-026]). A dividend booked in another account is a different
dividend. Before this fix the linker considered every account's income, so two accounts
holding the same instrument had both taxes linked to one dividend; that dividend then
read 30 % and was capped, halving a credit that was at the treaty rate in each account.

The maintainer's reproduction (review of PR #102, F3), invented figures: the same asset,
date and currency in accounts A and B, 1,000 USD dividend and 150 USD tax each, at
0.90 EUR/USD. Correct Zeile 41: 270.00. Before the fix: 135.00.

Real data: the maintainer's exports are one account. The contributor's hold three; the
parity run of this fix (VZ 2023-2025, 2026-09-23) is identical in console and PDF, so no
real tax row was linked across accounts in a way that moved a figure or a report line.
"""
from decimal import Decimal

from src.domain.enums import TaxReportingCategory
from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from tests.test_payment_in_lieu_credit_route import _line, _rct, _run_loss_offsetting
from tests.test_cash_transaction_reversals import _events

Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID
_STK = dict(asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON")
DIV = "ACME(US0000000AAA) CASH DIVIDEND USD 1.00 PER SHARE"


def _in(account, row):
    row.client_account_id = account
    return row


ROWS = [
    _in("U0000001", _rct(type_="Dividends", description=DIV + " (Ordinary Dividend)",
                         amount=Decimal("1000"), tx_id="1001", **_STK)),
    _in("U0000002", _rct(type_="Dividends", description=DIV + " (Ordinary Dividend)",
                         amount=Decimal("1000"), tx_id="1002", **_STK)),
    _in("U0000001", _rct(type_="Withholding Tax", description=DIV + " - US TAX",
                         amount=Decimal("-150"), tx_id="1003", **_STK)),
    _in("U0000002", _rct(type_="Withholding Tax", description=DIV + " - US TAX",
                         amount=Decimal("-150"), tx_id="1004", **_STK)),
]


def test_each_tax_row_links_to_the_dividend_of_its_own_account(tmp_path):
    events, _ = _events(tmp_path, ROWS)
    by_id = {e.event_id: e.ibkr_transaction_id for e in events if isinstance(e, CashFlowEvent)}
    links = {e.ibkr_transaction_id: by_id.get(e.taxed_income_event_id)
             for e in events if isinstance(e, WithholdingTaxEvent)}
    assert links == {"1003": "1001", "1004": "1002"}


def test_two_accounts_at_the_treaty_rate_are_credited_in_full(tmp_path):
    """300 USD at 0.90 -> 270.00, no cap. Linked across accounts: 135.00."""
    events, resolver = _events(tmp_path, ROWS)
    form, gaps = _run_loss_offsetting(events, resolver, tmp_path)
    assert _line(form, Z41) == Decimal("270.00")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in [g.code for g in gaps.gaps]


def test_two_accounts_together_credit_what_each_credits_alone(tmp_path):
    """Combined versus separate: Zeile 41 of the two-account run is the sum of the two
    one-account runs."""
    def z41(rows, sub):
        d = tmp_path / sub
        d.mkdir()
        events, resolver = _events(d, rows)
        form, _ = _run_loss_offsetting(events, resolver, d)
        return _line(form, Z41)

    rows_a = [r for r in ROWS if r.client_account_id == "U0000001"]
    rows_b = [r for r in ROWS if r.client_account_id == "U0000002"]
    assert z41(ROWS, "both") == z41(rows_a, "a") + z41(rows_b, "b") == Decimal("270.00")

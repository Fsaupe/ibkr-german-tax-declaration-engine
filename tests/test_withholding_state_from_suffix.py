# tests/test_withholding_state_from_suffix.py
"""A dividend withholding row with a blank IssuerCountryCode takes its taxing state from
the broker's own "- XX Tax" suffix.

The treaty-rate guard ([GT-CREDIT-026], [GT-CREDIT-029]) needs the taxing state. The 2023
export leaves IssuerCountryCode blank on all 11 dividend and payment-in-lieu withholding
rows (7 US, 3 CA, 1 FR by suffix), so the guard could verify none of them. The suffix is on
every such row in Cash_Transactions-{2022..2025}, and agrees with the column on all 49 rows
where both are set (measured 2026-09-23).
"""
from decimal import Decimal

from src.domain.events import WithholdingTaxEvent
from src.parsers.domain_event_factory import DomainEventFactory
from tests.test_payment_in_lieu_credit_route import _rct, _resolver

_STOCK = dict(asset_class="STK", isin="FR0000000AAA", symbol="AAA")


def _states(tmp_path, description, country):
    rows = [
        _rct(type_="Dividends", description="AAA(FR0000000AAA) Cash Dividend EUR 1.00 per Share (Ordinary Dividend)",
             amount=Decimal("100"), tx_id="7001", country=country, **_STOCK),
        _rct(type_="Withholding Tax", description=description,
             amount=Decimal("-25"), tx_id="7002", country=country, **_STOCK),
    ]
    events = DomainEventFactory(_resolver(tmp_path)).create_events_from_cash_transactions(rows)
    return [e.source_country_code for e in events if isinstance(e, WithholdingTaxEvent)]


def test_a_blank_issuer_country_is_taken_from_the_tax_suffix(tmp_path):
    assert _states(tmp_path, "AAA(FR0000000AAA) Cash Dividend EUR 1.00 per Share - FR Tax", "") == ["FR"]


def test_the_issuer_country_column_is_used_where_set(tmp_path):
    assert _states(tmp_path, "AAA(FR0000000AAA) Cash Dividend EUR 1.00 per Share - FR Tax", "FR") == ["FR"]


def test_no_state_is_assumed_without_column_or_suffix(tmp_path):
    assert _states(tmp_path, "AAA(FR0000000AAA) Cash Dividend EUR 1.00 per Share", "") in ([None], [""])

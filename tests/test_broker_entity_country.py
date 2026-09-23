# tests/test_broker_entity_country.py
"""Credit-interest withholding takes the taxing state from the taxpayer's configuration.

The export names no state for "WITHHOLDING @ ...% ON CREDIT INT" rows: IssuerCountryCode
is blank on all 41 of them in Cash_Transactions-{2023..2025} (measured 2026-09-23). The
tax is levied by the country of the broker entity that pays the interest, which only the
taxpayer can state (config.BROKER_ENTITY_COUNTRY). Unset, no state is assumed -- the
parser used to write "IE" for every such row.
"""
from decimal import Decimal

from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from src.parsers.domain_event_factory import DomainEventFactory
from tests.test_payment_in_lieu_credit_route import _rct, _resolver

_CASH = dict(asset_class="CASH", isin="", symbol="")


def _rows():
    return [
        _rct(type_="Broker Interest Received", description="EUR CREDIT INT FOR JAN-2025",
             amount=Decimal("100"), tx_id="6001", country="", **_CASH),
        _rct(type_="Withholding Tax", description="WITHHOLDING @ 20% ON CREDIT INT FOR JAN-2025",
             amount=Decimal("-20"), tx_id="6002", country="", **_CASH),
    ]


def _withholding_states(tmp_path, **kwargs):
    events = DomainEventFactory(_resolver(tmp_path), **kwargs).create_events_from_cash_transactions(_rows())
    assert [e.event_type.name for e in events if isinstance(e, CashFlowEvent)] == ["INTEREST_RECEIVED"]
    return [e.source_country_code for e in events if isinstance(e, WithholdingTaxEvent)]


def test_the_configured_broker_country_is_the_interest_withholding_s_state(tmp_path):
    assert _withholding_states(tmp_path, broker_entity_country="IE") == ["IE"]


def test_no_state_is_assumed_when_none_is_configured(tmp_path):
    assert _withholding_states(tmp_path) == [None]

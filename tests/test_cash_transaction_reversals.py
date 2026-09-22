# tests/test_cash_transaction_reversals.py
"""A reversed dividend or withholding row cancels the booking it reverses.

The broker corrects a dividend by reversing it and booking it again: the dividend row
is repeated with the opposite sign and ``- REVERSAL`` in its description, the
withholding row is repeated with the opposite sign and the same description, each with
a higher TransactionID than the row it reverses. Measured on
``data_import/Cash_Transactions-{2021..2025}.csv`` (2026-09-22): one such correction,
VZ 2025 -- one negative dividend row and one positive withholding row, each matching an
earlier row of the same account, instrument, amount and description.

The parser stored every row as a magnitude, so a reversal counted as a second dividend
and a second payment of tax. The income is the dividend that was credited
(reference/tax-law/estg-20-kapitalvermoegen.md [GT-ESTG20-001]), and the credit is for
tax *"festgesetzte und gezahlte"* (reference/tax-law/estg-32d-abgeltungsteuer.md
[GT-CREDIT-004]); a reversed booking is neither. A reversal that matches no earlier row
cannot be read either way and stops the run.

Currency: USD at 0.90 EUR/USD (helpers shared with test_payment_in_lieu_credit_route),
so a foreign amount never coincides with its EUR value.
"""
from decimal import Decimal

import pytest

from src.domain.enums import FinancialEventType, TaxReportingCategory
from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from src.domain.exceptions import DataIntegrityError
from src.parsers.domain_event_factory import DomainEventFactory
from src.processing.withholding_tax_linker import WithholdingTaxLinker
from tests.test_payment_in_lieu_credit_route import (
    _enrich_eur, _line, _rct, _resolver, _run_loss_offsetting,
)

Z19 = TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT
Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID

DIV = "ACME(US0000000AAA) CASH DIVIDEND USD 1.00 PER SHARE"
_STK = dict(asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON")


def _dividend(amount, tx_id, reversal=False):
    desc = DIV + (" - REVERSAL" if reversal else "") + " (Ordinary Dividend)"
    return _rct(type_="Dividends", description=desc, amount=Decimal(amount), tx_id=tx_id, **_STK)


def _tax(amount, tx_id):
    return _rct(type_="Withholding Tax", description=DIV + " - US TAX",
                amount=Decimal(amount), tx_id=tx_id, **_STK)


def _events(tmp_path, rows):
    resolver = _resolver(tmp_path)
    events = DomainEventFactory(resolver).create_events_from_cash_transactions(rows)
    _enrich_eur(events)
    WithholdingTaxLinker().link_withholding_tax_events(events)
    return events, resolver


class TestAReversedDividendAndItsTax:

    ROWS = [
        _dividend("100", "3001"), _tax("-15", "3002"),
        _dividend("-100", "3003", reversal=True), _tax("15", "3004"),
        _dividend("100", "3005"), _tax("-15", "3006"),
    ]

    def test_leaves_one_dividend_and_one_tax_the_rebooking(self, tmp_path):
        events, _ = _events(tmp_path, self.ROWS)
        dividends = [e for e in events if isinstance(e, CashFlowEvent)]
        taxes = [e for e in events if isinstance(e, WithholdingTaxEvent)]
        assert [(e.event_type, e.ibkr_transaction_id) for e in dividends] == [
            (FinancialEventType.DIVIDEND_CASH, "3005")]
        assert [e.ibkr_transaction_id for e in taxes] == ["3006"]

    def test_declares_the_dividend_and_its_tax_once(self, tmp_path):
        """Before the fix: Zeile 19 = 270.00 and Zeile 41 = 40.50 -- three of each."""
        events, resolver = _events(tmp_path, self.ROWS)
        form, _ = _run_loss_offsetting(events, resolver, tmp_path)
        assert _line(form, Z19) == Decimal("90.00")
        assert _line(form, Z41) == Decimal("13.50")


def test_a_withholding_reversed_and_withheld_again_at_the_treaty_rate(tmp_path):
    """The lapsed-W-8BEN correction: 30 % withheld, reversed, 15 % withheld again, the
    dividend itself untouched. The tax paid is 15; nothing is above the treaty rate.
    Before the fix: Zeile 41 = 40.50 (30 + 30 + 15, each capped at 15 by the guard) and
    an ABOVE_TREATY_RATE gap telling the user that much was credited."""
    events, resolver = _events(tmp_path, [
        _dividend("100", "3001"), _tax("-30", "3002"), _tax("30", "3003"), _tax("-15", "3004"),
    ])
    form, gaps = _run_loss_offsetting(events, resolver, tmp_path)
    assert _line(form, Z41) == Decimal("13.50")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in [g.code for g in gaps.gaps]


class TestAReversalWithNothingToReverse:
    """Not a reversal of anything in the input: no reading of it is safe."""

    def test_a_positive_withholding_row_with_no_earlier_match_stops_the_run(self, tmp_path):
        with pytest.raises(DataIntegrityError, match="3003"):
            _events(tmp_path, [_dividend("100", "3001"), _tax("-30", "3002"), _tax("15", "3003")])

    def test_a_negative_dividend_row_with_no_earlier_match_stops_the_run(self, tmp_path):
        with pytest.raises(DataIntegrityError, match="3003"):
            _events(tmp_path, [_dividend("100", "3001"), _dividend("-90", "3003", reversal=True)])

    def test_a_reversal_must_follow_the_row_it_reverses(self, tmp_path):
        with pytest.raises(DataIntegrityError, match="3001"):
            _events(tmp_path, [_tax("15", "3001"), _tax("-15", "3002")])

    def test_every_unmatched_reversal_is_reported_in_one_run(self, tmp_path):
        with pytest.raises(DataIntegrityError) as exc:
            _events(tmp_path, [_tax("15", "3001"), _dividend("-90", "3002", reversal=True)])
        assert "3001" in str(exc.value) and "3002" in str(exc.value)

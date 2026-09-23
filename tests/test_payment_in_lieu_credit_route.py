# tests/test_payment_in_lieu_credit_route.py
"""Where a Payment In Lieu lands, and where its foreign tax lands.

Issue #78. A payment in lieu of a dividend on lent units is, on the § 39 AO
attribution the taxpayer asserts (branch A, [GT-INVSTG-059]), the instrument's own
income: the fund's Ausschuettung on Anlage KAP-INV Zeile 4, or the share's dividend
on Anlage KAP Zeile 19. Its foreign withholding is *anrechenbare auslaendische
Steuer* on Anlage KAP Zeile 41 at the treaty rate ([GT-CREDIT-004], [GT-CREDIT-026],
[GT-CREDIT-027]).

These tests lock the behaviour the engine already produces, on two seams the suite
did not previously assert together:

- the parser routing that makes a fund PIL a `DISTRIBUTION_FUND` and a share PIL a
  `DIVIDEND_CASH` -- branch A of [GT-INVSTG-059], whose map row read *"none --
  unguarded"* until this file;
- the aggregation that carries the fund PIL to KAP-INV Zeile 4 *and* its tax to
  KAP Zeile 41 in one run, which `docs/legal-implementation-map.md` noted was tested
  only in halves against different fixtures.

Category: fix-nonfunc (blind-spot closure). No engine code changes here. Each test
names the mutation it now catches, and the whole group is calibrated against a tree
mutated to branch B (a fund PIL routed away from `DISTRIBUTION_FUND`): the routing
test fails, and the fund PIL then lands on Zeile 19 instead of Zeile 4.

Currency: USD throughout, EUR value fixed at 1 USD = 0.90 EUR so a foreign amount
and its EUR value never coincide (CLAUDE.md, "which currency a value is in, in any
fixture whose rate is 1").
"""
import uuid
from decimal import Decimal

import pytest

from src.parsers.domain_event_factory import DomainEventFactory
from src.parsers.raw_models import RawCashTransactionRecord
from src.processing.withholding_tax_linker import WithholdingTaxLinker
from src.processing.data_gaps import DataGapCollector
from src.engine.loss_offsetting import LossOffsettingEngine
from src.identification.asset_resolver import AssetResolver
from src.classification.asset_classifier import AssetClassifier
from src.domain.assets import InvestmentFund
from src.domain.enums import (
    AssetCategory, FinancialEventType, InvestmentFundType, TaxReportingCategory,
)
from src.domain.events import CashFlowEvent, WithholdingTaxEvent


EUR_PER_USD = Decimal("0.90")


def _resolver(tmp_path):
    return AssetResolver(asset_classifier=AssetClassifier(
        cache_file_path=str(tmp_path / "cls.json")))


def _rct(*, type_, description, amount, tx_id, asset_class, isin, symbol,
         settle="2025-06-16", country="US", sub_category=None):
    """A raw cash-transaction row, built through the field aliases the parser reads."""
    return RawCashTransactionRecord(
        ClientAccountID="U1111111",
        CurrencyPrimary="USD",
        AssetClass=asset_class,
        SubCategory=sub_category,
        Symbol=symbol,
        Description=description,
        ISIN=isin,
        IssuerCountryCode=country,
        SettleDate=settle,
        Type=type_,
        Amount=amount,
        TransactionID=tx_id,
    )


def _enrich_eur(events):
    """Stand in for the ECB-conversion step: every USD amount at 0.90 EUR/USD."""
    for e in events:
        if e.gross_amount_foreign_currency is not None:
            e.gross_amount_eur = e.gross_amount_foreign_currency * EUR_PER_USD
    return events


def _run_loss_offsetting(events, resolver, tmp_path, tax_year=2025):
    gaps = DataGapCollector()
    engine = LossOffsettingEngine(
        realized_gains_losses=[],
        vorabpauschale_items=[],
        current_year_financial_events=events,
        asset_resolver=resolver,
        tax_year=tax_year,
        data_gap_collector=gaps,
    )
    return engine.calculate_reporting_figures(), gaps


def _line(form, category):
    return form.form_line_values.get(category, Decimal("0.00"))


# --------------------------------------------------------------------------- #
# Parser routing — branch A of [GT-INVSTG-059]
# --------------------------------------------------------------------------- #

class TestAPaymentInLieuTakesTheInstrumentsOwnEventKind:
    """The routing that decides the form line downstream.

    legal_basis: [GT-INVSTG-059] branch A — the substitute payment is the fund's
    Ausschuettung / the share's dividend, taken as the taxpayer's own income; and
    [GT-ESTG20-045], Rz. 12. The negative-PIL branch (booked as a fee, per the type
    table in input_data_spec.md) is asserted too so it is not swept into income.
    """

    def test_a_positive_fund_payment_in_lieu_becomes_a_fund_distribution(self, tmp_path):
        resolver = _resolver(tmp_path)
        factory = DomainEventFactory(resolver)
        events = factory.create_events_from_cash_transactions([
            _rct(type_="Payment In Lieu Of Dividends",
                 description="ISHARES CORE (US00000FUND1) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)",
                 amount=Decimal("1000.00"), tx_id="5000",
                 asset_class="FUND", isin="US00000FUND1", symbol="TF", sub_category="ETF"),
        ])
        assert len(events) == 1
        assert events[0].event_type == FinancialEventType.DISTRIBUTION_FUND, (
            "a fund PIL is the fund's Ausschuettung on branch A ([GT-INVSTG-059]); "
            "routing it to DIVIDEND_CASH would land it on KAP Zeile 19, not KAP-INV "
            "Zeile 4, and would stop it reducing the Vorabpauschale")

    def test_a_positive_share_payment_in_lieu_becomes_a_cash_dividend(self, tmp_path):
        resolver = _resolver(tmp_path)
        factory = DomainEventFactory(resolver)
        events = factory.create_events_from_cash_transactions([
            _rct(type_="Payment In Lieu Of Dividends",
                 description="ACME(US0000000AAA) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)",
                 amount=Decimal("1000.00"), tx_id="5000",
                 asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
        ])
        assert len(events) == 1
        assert events[0].event_type == FinancialEventType.DIVIDEND_CASH

    def test_a_negative_fund_payment_in_lieu_is_a_fee_not_income(self, tmp_path):
        """A negative PIL (the account pays it; booked as a fee per input_data_spec.md) is a cost,
        not an Ausschuettung — it must not add to any income line."""
        resolver = _resolver(tmp_path)
        factory = DomainEventFactory(resolver)
        events = factory.create_events_from_cash_transactions([
            _rct(type_="Payment In Lieu Of Dividends",
                 description="ISHARES CORE (US00000FUND1) PAYMENT IN LIEU OF DIVIDEND",
                 amount=Decimal("-1000.00"), tx_id="5000",
                 asset_class="FUND", isin="US00000FUND1", symbol="TF", sub_category="ETF"),
        ])
        assert len(events) == 1
        assert events[0].event_type == FinancialEventType.FEE_TRANSACTION


# --------------------------------------------------------------------------- #
# A1 / A2 — the fund PIL reaches Zeile 4 AND its tax reaches Zeile 41, in one run
# --------------------------------------------------------------------------- #

def _fund_pil_events(resolver, tmp_path, tax_usd=Decimal("150.00")):
    """A fund PIL of 1000 USD and its withholding, both routed by the parser, EUR
    enriched at 0.90, and linked. The resolved fund is pinned to AKTIENFONDS so the
    KAP-INV line is deterministic regardless of the classifier's heuristics."""
    factory = DomainEventFactory(resolver)
    events = factory.create_events_from_cash_transactions([
        _rct(type_="Payment In Lieu Of Dividends",
             description="ISHARES CORE (US00000FUND1) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)",
             amount=Decimal("1000.00"), tx_id="5000",
             asset_class="FUND", isin="US00000FUND1", symbol="TF", sub_category="ETF"),
        _rct(type_="Withholding Tax",
             description="ISHARES CORE (US00000FUND1) PAYMENT IN LIEU OF DIVIDEND - US TAX",
             amount=-tax_usd, tx_id="5001",
             asset_class="FUND", isin="US00000FUND1", symbol="TF", sub_category="ETF"),
    ])
    for e in events:
        asset = resolver.get_asset_by_id(e.asset_internal_id)
        if isinstance(asset, InvestmentFund):
            asset.fund_type = InvestmentFundType.AKTIENFONDS
    _enrich_eur(events)
    WithholdingTaxLinker().link_withholding_tax_events(events)
    return events


def _share_pil_events(resolver, tmp_path, tax_usd=Decimal("150.00")):
    factory = DomainEventFactory(resolver)
    events = factory.create_events_from_cash_transactions([
        _rct(type_="Payment In Lieu Of Dividends",
             description="ACME(US0000000AAA) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)",
             amount=Decimal("1000.00"), tx_id="5000",
             asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
        _rct(type_="Withholding Tax",
             description="ACME(US0000000AAA) PAYMENT IN LIEU OF DIVIDEND - US TAX",
             amount=-tax_usd, tx_id="5001",
             asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
    ])
    _enrich_eur(events)
    WithholdingTaxLinker().link_withholding_tax_events(events)
    return events


class TestTheFundPaymentInLieuAndItsTaxReachTheRightLines:

    def test_fund_pil_reaches_kap_inv_zeile_4_and_its_tax_reaches_kap_zeile_41(self, tmp_path):
        """legal_basis: [GT-INVSTG-059] branch A, [GT-INVSTG-057] (gross), [GT-FORM-006],
        [GT-CREDIT-004]; KAP-INV Anleitung page 1 routes fund tax to KAP Zeile 41.

        Catches: routing the fund PIL to DIVIDEND_CASH (Zeile 19 becomes 900.00 and
        Zeile 4 becomes 0); dropping the withholding sum (Zeile 41 becomes 0);
        reading the USD value where the EUR one belongs (Zeile 41 becomes 150.00).
        The tax withheld here is exactly the 15 % treaty rate, so nothing is capped.
        """
        resolver = _resolver(tmp_path)
        events = _fund_pil_events(resolver, tmp_path)
        form, gaps = _run_loss_offsetting(events, resolver, tmp_path)

        assert _line(form, TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS) == Decimal("900.00")
        assert _line(form, TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID) == Decimal("135.00")
        assert _line(form, TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT) == Decimal("0.00")
        assert len(gaps) == 0

    def test_share_pil_reaches_kap_zeile_19_and_its_tax_reaches_kap_zeile_41(self, tmp_path):
        """legal_basis: [GT-INVSTG-059] branch A / [GT-ESTG20-045] (the dividend is the
        lender's), [GT-FORM-006]. A share PIL is § 20 Abs. 1 Nr. 1 income on Zeile 19."""
        resolver = _resolver(tmp_path)
        events = _share_pil_events(resolver, tmp_path)
        form, gaps = _run_loss_offsetting(events, resolver, tmp_path)

        assert _line(form, TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT) == Decimal("900.00")
        assert _line(form, TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID) == Decimal("135.00")
        assert _line(form, TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS) == Decimal("0.00")
        assert len(gaps) == 0


# --------------------------------------------------------------------------- #
# A fund PIL reduces the Vorabpauschale like any distribution (both sides of §18)
# --------------------------------------------------------------------------- #

class TestAFundPaymentInLieuIsADistributionOnBothSidesOfParagraph18:
    """The Ausschuettung raises the Satz-3 cap and is subtracted under Satz 1
    ([GT-INVSTG-059] branch A). Here the second half — subtraction from the
    Vorabpauschale — is exercised at the engine level via the event kind the parser
    assigns.

    legal_basis: [GT-INVSTG-056], [GT-INVSTG-010]; a `DISTRIBUTION_FUND` reduces the
    Basisertrag before the twelfths. Catches a tree in which a fund PIL is not a
    distribution (branch B): the Vorabpauschale would not be reduced.
    """

    def test_a_fund_pil_distribution_reduces_the_vorabpauschale(self, tmp_path):
        from tests.test_vorabpauschale import _make_fund, _make_distribution, _run_vp

        fund = _make_fund()
        # A PIL, typed by the parser as DISTRIBUTION_FUND, is the same event kind a
        # distribution is; the Vorabpauschale engine subtracts it just the same.
        pil = _make_distribution(fund.internal_asset_id, Decimal("50"))
        assert pil.event_type == FinancialEventType.DISTRIBUTION_FUND
        with_pil = _run_vp(fund, events=[pil])
        without = _run_vp(fund, events=[])
        assert len(with_pil) == 1 and len(without) == 1
        assert with_pil[0].gross_vorabpauschale_eur == without[0].gross_vorabpauschale_eur - Decimal("50")


# --------------------------------------------------------------------------- #
# A4 — cent-rounded withholding on a small gross is not an over-withholding
# --------------------------------------------------------------------------- #

class TestCentRoundedWithholdingIsNotAnOverWithholding:
    """Withheld tax equal to 15 % of the gross rounded to the cent, on grosses under
    one currency unit, is the treaty rate — not an over-withholding.

    legal_basis: measured in the issue #78 research (§1): the off-rate rows in the
    real window are exact cent roundings of 15 %. A guard must compare |tax| with
    round(rate x gross, 2) at a one-cent tolerance, or it fires on every small
    dividend. This passes today (no guard) and pins the value the Group B guard must
    not disturb.
    """

    def test_two_small_dividends_at_the_rounded_treaty_rate(self, tmp_path):
        resolver = _resolver(tmp_path)
        factory = DomainEventFactory(resolver)
        events = factory.create_events_from_cash_transactions([
            _rct(type_="Dividends", description="ACME(US0000000AAA) CASH DIVIDEND",
                 amount=Decimal("0.30"), tx_id="6000",
                 asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
            _rct(type_="Withholding Tax", description="ACME(US0000000AAA) CASH DIVIDEND - US TAX",
                 amount=Decimal("-0.05"), tx_id="6001",
                 asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
            _rct(type_="Dividends", description="ACME(US0000000AAA) CASH DIVIDEND",
                 amount=Decimal("0.23"), tx_id="6002",
                 asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
            _rct(type_="Withholding Tax", description="ACME(US0000000AAA) CASH DIVIDEND - US TAX",
                 amount=Decimal("-0.03"), tx_id="6003",
                 asset_class="STK", isin="US0000000AAA", symbol="ACME", sub_category="COMMON"),
        ])
        _enrich_eur(events)
        WithholdingTaxLinker().link_withholding_tax_events(events)
        form, gaps = _run_loss_offsetting(events, resolver, tmp_path)

        # 0.045 EUR + 0.027 EUR = 0.072 -> 0.07
        assert _line(form, TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID) == Decimal("0.07")
        assert len(gaps) == 0

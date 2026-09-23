"""The securities-lending fee is a Leistung under § 22 Nr. 3, not interest under § 20.

legal_basis:
  - [GT-ESTG20-049] and [GT-ESTG20-050] in reference/tax-law/estg-20-kapitalvermoegen.md —
    the order of enquiry § 20 Abs. 3 → § 20 Abs. 1 Nr. 7 → § 22 Nr. 3 runs out inside
    § 20 EStG. Abs. 3 is accessory and the fee is accessory to nothing; Nr. 7's gate is a
    Kapitalforderung and a lender holds a Sachforderung. § 22 Nr. 3 takes it by its own
    subsidiarity clause.
  - [GT-FORM-024] in reference/tax-forms/anlage-so-zeilen.md — the Anlage SO *Leistungen*
    entry line, per year: **Zeile 12** in VZ 2023 and VZ 2024, **Zeile 16** in VZ 2025.

Two things make this more than a relabelling, and each has tests here rather than a
comment:

**Detection cannot key on `Type`.** IBKR books the Stock Yield Enhancement Program fee with
`Type = Broker Interest Received`, which is also the type of ordinary credit interest on a
cash balance. Measured across `Cash_Transactions-2021.csv`…`-2025.csv` on 2026-08-09: 35
rows carry the SYEP marker in the description and are the fee; every other
`Broker Interest Received` row is `<CCY> CREDIT INT FOR <MON>-<YYYY>` or
`<CCY> SHORT CREDIT INTEREST FOR <MON>-<YYYY>`, which are genuine § 20 interest and must be
left where they are. So the split is on the description, and the tests pin **both sides**.

**It must leave the § 20 pools completely.** Not merely off Zeile 19: out of the loss
offsetting between § 20 categories, out of the conceptual "Sonstige Kapitalerträge" balance,
and out of the Sparer-Pauschbetrag's reach. § 22 Nr. 3 income is a different Einkunftsart.

**And it must stay in the currency ledger.** The fee is a cash inflow like any other. A new
event type that the currency dispatch does not know about would silently stop creating
currency lots — the failure mode CLAUDE.md records for this engine, where a dispatch falls
through without an `else` and the missing lots reconcile against a reported zero. Three
tests below exercise the current-year path, the historical-replay collection and the
historical-replay application, because the suite cannot otherwise see them.

The Freigrenze of § 22 Nr. 3 Satz 2 and the loss ring-fencing of Satz 3 are deliberately not
implemented, on the same ground as [GT-ESTG23-009]: both operate on the taxpayer's total
income of that kind from every source, which one broker export cannot establish. The engine
declares gross. `test_freigrenze_is_not_applied` pins that as a decision rather than an
omission.
"""

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any, List, Optional

import pytest

from src.classification.asset_classifier import AssetClassifier
from src.domain.enums import (
    AssetCategory,
    FinancialEventType,
    RealizationType,
    TaxReportingCategory,
)
from src.domain.events import CashFlowEvent
from src.domain.exceptions import ProcessingError
from src.engine.loss_offsetting import LossOffsettingEngine
from src.identification.asset_resolver import AssetResolver
from src.parsers.domain_event_factory import DomainEventFactory
from src.parsers.raw_models import RawCashTransactionRecord

from tests.support.base import FifoTestCaseBase
from tests.support.mock_providers import MockECBExchangeRateProvider


ACCOUNT_ID = "U_SYEP_TEST"
TAX_YEAR = 2023

# Verbatim shape of the 35 rows measured in the export, month and year varying.
SYEP_DESCRIPTION = "EUR IBKR MANAGED SECURITIES (SYEP) INTEREST FOR JAN-2023"
CREDIT_INTEREST_DESCRIPTION = "EUR CREDIT INT FOR JAN-2023"
SHORT_CREDIT_INTEREST_DESCRIPTION = "EUR SHORT CREDIT INTEREST FOR JAN-2023"
BROKER_INTEREST_RECEIVED = "Broker Interest Received"


# =============================================================================
# Parsing: the split is on the description, because Type does not distinguish
# =============================================================================


@pytest.fixture
def resolver(tmp_path):
    return AssetResolver(asset_classifier=AssetClassifier(
        cache_file_path=str(tmp_path / "cls.json")))


def _raw_cash_tx(description: str, amount: str = "12.34", currency: str = "EUR",
                 tx_type: str = BROKER_INTEREST_RECEIVED,
                 tx_id: str = "TX1") -> RawCashTransactionRecord:
    return RawCashTransactionRecord(
        ClientAccountID=ACCOUNT_ID,
        CurrencyPrimary=currency,
        AssetClass="",
        SubCategory="",
        Symbol="",
        Description=description,
        SettleDate="2023-01-31",
        Amount=amount,
        Type=tx_type,
        Conid="",
        UnderlyingConid="",
        ISIN="",
        IssuerCountryCode="",
        TransactionID=tx_id,
    )


def _one_event(resolver, record: RawCashTransactionRecord):
    events = DomainEventFactory(resolver).create_events_from_cash_transactions([record])
    assert len(events) == 1, f"expected exactly one event, got {events}"
    return events[0]


def test_syep_row_becomes_a_lending_fee_not_interest(resolver):
    event = _one_event(resolver, _raw_cash_tx(SYEP_DESCRIPTION))
    assert event.event_type == FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED


def test_ordinary_credit_interest_with_the_same_type_stays_interest(resolver):
    """The half of the split that a description match could break."""
    event = _one_event(resolver, _raw_cash_tx(CREDIT_INTEREST_DESCRIPTION))
    assert event.event_type == FinancialEventType.INTEREST_RECEIVED


def test_short_credit_interest_stays_interest(resolver):
    """Credit interest on short-sale proceeds. Also § 20, also `Broker Interest Received`."""
    event = _one_event(resolver, _raw_cash_tx(SHORT_CREDIT_INTEREST_DESCRIPTION))
    assert event.event_type == FinancialEventType.INTEREST_RECEIVED


def test_the_fee_keeps_its_amount_and_currency(resolver):
    event = _one_event(resolver, _raw_cash_tx(SYEP_DESCRIPTION, amount="12.34", currency="USD"))
    assert event.gross_amount_foreign_currency == Decimal("12.34")
    assert event.local_currency == "USD"


def test_detection_is_case_insensitive(resolver):
    """The export is upper-case today; nothing guarantees it stays that way."""
    event = _one_event(resolver, _raw_cash_tx(
        "eur ibkr managed securities (syep) interest for jan-2023"))
    assert event.event_type == FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED


# =============================================================================
# The form line, per year: [GT-FORM-024]
# =============================================================================


def test_the_leistungen_entry_line_per_assessment_year():
    from src.tax_law.registry import get_anlage_so_form_rules

    assert get_anlage_so_form_rules(2023).leistungen_einnahmen_zeile == 12
    assert get_anlage_so_form_rules(2024).leistungen_einnahmen_zeile == 12
    assert get_anlage_so_form_rules(2025).leistungen_einnahmen_zeile == 16


def test_a_year_below_the_earliest_verified_form_raises():
    """Backward projection is what Validation Protocol item 4 forbids, and on this form
    the numbering demonstrably moves."""
    from src.tax_law.registry import get_anlage_so_form_rules

    with pytest.raises(ProcessingError) as excinfo:
        get_anlage_so_form_rules(2022)
    assert "2023" in str(excinfo.value)


def test_a_later_year_carries_the_latest_verified_structure_forward():
    from src.tax_law.registry import get_anlage_so_form_rules

    assert get_anlage_so_form_rules(2026).leistungen_einnahmen_zeile == 16


# =============================================================================
# Aggregation: onto Anlage SO, and out of the § 20 pools
# =============================================================================


@pytest.fixture
def cash_asset(resolver):
    return resolver.get_or_create_asset(
        raw_isin=None, raw_conid=None, raw_symbol="EUR", raw_currency="EUR",
        raw_ibkr_asset_class="CASH", raw_description="Cash Balance EUR",
        description_source_type="cash_balance_generated", raw_ibkr_sub_category=None,
    )


def _fee_event(asset, gross_eur: str, date: str = "2023-01-31") -> CashFlowEvent:
    ev = CashFlowEvent(
        asset_internal_id=asset.internal_asset_id,
        event_date=date,
        event_type=FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED,
        gross_amount_foreign_currency=Decimal(gross_eur),
        local_currency="EUR",
        ibkr_activity_description=SYEP_DESCRIPTION,
    )
    ev.gross_amount_eur = Decimal(gross_eur)
    return ev


def _interest_event(asset, gross_eur: str, date: str = "2023-02-28") -> CashFlowEvent:
    ev = CashFlowEvent(
        asset_internal_id=asset.internal_asset_id,
        event_date=date,
        event_type=FinancialEventType.INTEREST_RECEIVED,
        gross_amount_foreign_currency=Decimal(gross_eur),
        local_currency="EUR",
        ibkr_activity_description=CREDIT_INTEREST_DESCRIPTION,
    )
    ev.gross_amount_eur = Decimal(gross_eur)
    return ev


def _figures(resolver, events, tax_year: int = TAX_YEAR):
    return LossOffsettingEngine(
        realized_gains_losses=[],
        vorabpauschale_items=[],
        current_year_financial_events=events,
        asset_resolver=resolver,
        tax_year=tax_year,
    ).calculate_reporting_figures()


SO_LEISTUNGEN = TaxReportingCategory.ANLAGE_SO_LEISTUNGEN_EINNAHMEN
KAP_SONSTIGE = TaxReportingCategory.ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE
KAP_ZEILE_19 = TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT


def test_the_fee_lands_on_the_anlage_so_leistungen_line(resolver, cash_asset):
    result = _figures(resolver, [_fee_event(cash_asset, "40.00")])
    assert result.form_line_values[SO_LEISTUNGEN] == Decimal("40.00")


def test_the_fee_is_not_in_the_kap_other_income_line(resolver, cash_asset):
    result = _figures(resolver, [_fee_event(cash_asset, "40.00")])
    assert result.form_line_values[KAP_SONSTIGE] == Decimal("0.00")


def test_the_fee_is_not_in_kap_zeile_19(resolver, cash_asset):
    result = _figures(resolver, [_fee_event(cash_asset, "40.00")])
    assert result.form_line_values[KAP_ZEILE_19] == Decimal("0.00")


def test_the_fee_is_not_in_the_conceptual_paragraph_20_balance(resolver, cash_asset):
    """The § 20 pool is what the Sparer-Pauschbetrag and § 20 Abs. 6 offsetting reach.
    § 22 Nr. 3 income is a different Einkunftsart and neither applies to it."""
    result = _figures(resolver, [_fee_event(cash_asset, "40.00")])
    assert result.conceptual_net_other_income == Decimal("0.00")


def test_interest_and_the_fee_are_separated_when_both_are_present(resolver, cash_asset):
    """The one test that would fail if the split were made by summing everything twice."""
    result = _figures(resolver, [
        _fee_event(cash_asset, "40.00"),
        _interest_event(cash_asset, "7.00"),
    ])
    assert result.form_line_values[SO_LEISTUNGEN] == Decimal("40.00")
    assert result.form_line_values[KAP_SONSTIGE] == Decimal("7.00")
    assert result.form_line_values[KAP_ZEILE_19] == Decimal("7.00")


def test_several_fee_rows_are_summed(resolver, cash_asset):
    """The real shape: one row a month, not one a year."""
    result = _figures(resolver, [
        _fee_event(cash_asset, "1.10", "2023-01-31"),
        _fee_event(cash_asset, "2.20", "2023-02-28"),
        _fee_event(cash_asset, "3.30", "2023-03-31"),
    ])
    assert result.form_line_values[SO_LEISTUNGEN] == Decimal("6.60")


def test_the_line_is_present_and_zero_when_there_is_no_fee(resolver, cash_asset):
    """A line that vanishes when empty reads as "not computed" rather than "nothing".
    `form_line_values` is a defaultdict, so membership is asserted and not just the value —
    a lookup alone would pass against a line the engine never writes."""
    result = _figures(resolver, [_interest_event(cash_asset, "7.00")])
    assert SO_LEISTUNGEN in result.form_line_values
    assert result.form_line_values[SO_LEISTUNGEN] == Decimal("0.00")


def test_freigrenze_is_not_applied(resolver, cash_asset):
    """§ 22 Nr. 3 Satz 2 exempts Einkünfte aus Leistungen below 256 € **in total**, from
    every source. One broker export cannot establish that total, so the engine declares
    gross and the threshold is the filer's to apply — the same position as [GT-ESTG23-009]
    takes on the § 23 Freigrenze. A figure below 256 € must still appear."""
    result = _figures(resolver, [_fee_event(cash_asset, "40.00")])
    assert result.form_line_values[SO_LEISTUNGEN] == Decimal("40.00")


# =============================================================================
# The currency ledger: a new event type must not fall out of the FX dispatch
# =============================================================================


def _cash_balance_row(currency: str, soy: Decimal, eoy: Decimal) -> List[Any]:
    return [ACCOUNT_ID, currency, "20230101", "20231231", soy, eoy]


def _cash_transaction_row(currency: str, amount: Decimal, tx_type: str, date: str,
                          description: str, tx_id: str) -> List[Any]:
    return [
        ACCOUNT_ID, currency, "", "", "", description, date, amount, tx_type,
        "", "", "", "", tx_id,
    ]


def _fx_trade_row(currency: str, eur_amount: Decimal, trade_type: str,
                  ecb_rate: Decimal, date: str, tx_id: str) -> List[Any]:
    symbol = f"EUR.{currency}"
    quantity = -eur_amount if trade_type == "BUY" else eur_amount
    buy_sell = "SELL" if trade_type == "BUY" else "BUY"
    return [
        ACCOUNT_ID, "EUR", "CASH", "", symbol, f"FX {symbol}", "",
        None, None, None,
        date, quantity, ecb_rate, Decimal("0"), "EUR",
        buy_sell, tx_id, None, None, None, None, Decimal("1"), "O", Decimal("0"),
    ]


class _RateProvider(MockECBExchangeRateProvider):
    def __init__(self, rate_map: dict):
        super().__init__(foreign_to_eur_init_value=Decimal("1.0"))
        self._rate_map = rate_map

    def get_rate(self, date_of_conversion, currency_code: str) -> Optional[Decimal]:
        from datetime import date as date_type

        currency_upper = currency_code.upper()
        if currency_upper == "EUR":
            return Decimal("1.0")
        if isinstance(date_of_conversion, date_type):
            date_str = date_of_conversion.strftime("%Y-%m-%d")
        else:
            date_str = str(date_of_conversion)
        rate = self._rate_map.get((date_str, currency_upper))
        if rate is not None:
            return rate
        return super().get_rate(date_of_conversion, currency_code)


class TestTheFeeStillMovesTheCurrencyLedger(FifoTestCaseBase):
    """A USD lending fee is a USD inflow and has to create a USD lot, exactly as the
    identically-typed credit interest does. `test_group11_cashflow_currency.py` pins the
    interest case; this pins the fee, because the currency dispatch enumerates event types
    and a new one is invisible to it until it is listed."""

    @pytest.mark.parametrize("historical", [False, True])
    def test_fee_lots_keep_their_account_and_acquisition_basis(self, historical):
        """GT-FX-009: spending B's fee cannot consume A's older, cheaper lot."""
        from tests.support.multi_account import cash_balance_row, cash_transaction_row, fx_trade_row

        fee_year = 2022 if historical else 2023
        a_date, b_date = f"{fee_year}-03-15", f"{fee_year}-04-15"
        out = self._run_pipeline(
            cash_transactions_data=[
                cash_transaction_row("A", "USD", "10", BROKER_INTEREST_RECEIVED,
                                     a_date, description=SYEP_DESCRIPTION, tx_id="FEE_A"),
                cash_transaction_row("B", "USD", "10", BROKER_INTEREST_RECEIVED,
                                     b_date, description=SYEP_DESCRIPTION, tx_id="FEE_B"),
            ],
            trades_data=[fx_trade_row("B", "USD", "SELL", "10", "10", "1",
                                      "2023-07-01", "SPEND_B")],
            cash_balance_data=[
                cash_balance_row("A", "USD", "10" if historical else "0", "10", 2023),
                cash_balance_row("B", "USD", "10" if historical else "0", "0", 2023),
            ],
            custom_rate_provider=_RateProvider({
                (a_date, "USD"): Decimal("2"),
                (b_date, "USD"): Decimal("0.5"),
            }), tax_year=2023,
        )
        gains = [r for r in out.realized_gains_losses
                 if r.asset_category_at_realization == AssetCategory.CASH_BALANCE]
        assert len(gains) == 1
        assert gains[0].total_cost_basis_eur == Decimal("20")
        assert gains[0].gross_gain_loss_eur == Decimal("-10")
        assert str(gains[0].acquisition_date) == b_date
        assert not [g for g in out.data_gaps if g.code == "CURRENCY_EOY_MISMATCH"]

        fees = [e for e in out.processed_income_events
                if e.event_type == FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED]
        summary = _figures(out.asset_resolver, fees)
        assert summary.form_line_values[SO_LEISTUNGEN] == (
            Decimal("0") if historical else Decimal("25"))


    def test_a_foreign_currency_lending_fee_creates_a_currency_lot(self, mock_config_paths):
        rate_map = {
            ("2023-03-15", "USD"): Decimal("1.00"),
            ("2023-07-01", "USD"): Decimal("0.50"),
            ("2022-12-31", "USD"): Decimal("1.00"),
        }
        actual = self._run_pipeline(
            trades_data=[_fx_trade_row("USD", Decimal("20"), "SELL", Decimal("0.50"),
                                       "2023-07-01", "FX_001")],
            cash_transactions_data=[_cash_transaction_row(
                currency="USD", amount=Decimal("10"), tx_type=BROKER_INTEREST_RECEIVED,
                date="2023-03-15",
                description="USD IBKR MANAGED SECURITIES (SYEP) INTEREST FOR MAR-2023",
                tx_id="SYEP_001")],
            cash_balance_data=[_cash_balance_row("USD", Decimal("0"), Decimal("0"))],
            custom_rate_provider=_RateProvider(rate_map),
            tax_year=TAX_YEAR,
        )

        currency_rgls = [
            rgl for rgl in actual.realized_gains_losses
            if rgl.asset_category_at_realization == AssetCategory.CASH_BALANCE
        ]
        assert len(currency_rgls) == 1, (
            "the lending fee did not create a USD lot, so the FX sale had nothing to "
            f"consume: {currency_rgls}")
        rgl = currency_rgls[0]
        assert rgl.quantity_realized == Decimal("10")
        assert rgl.total_cost_basis_eur.quantize(Decimal("0.01")) == Decimal("10.00")
        assert rgl.total_realization_value_eur.quantize(Decimal("0.01")) == Decimal("20.00")
        assert rgl.gross_gain_loss_eur.quantize(Decimal("0.01")) == Decimal("10.00")


def test_the_fee_is_collected_for_the_historical_currency_replay():
    """The prior-year half. A fee row from before the tax year has to reach the replay,
    or the lot it created never exists and the ledger it belongs to starts short."""
    from src.engine.calculation_engine import _collect_historical_currency_event

    event = CashFlowEvent(
        asset_internal_id=uuid.uuid4(),
        event_date="2022-04-30",
        event_type=FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED,
        gross_amount_foreign_currency=Decimal("10"),
        local_currency="USD",
    )
    collected = defaultdict(list)
    _collect_historical_currency_event(event, collected)
    assert collected["USD"] == [event]


def test_the_replay_applies_the_fee_as_an_inflow(mock_config_paths):
    """The other end of the same channel: collected is not applied. The replay's dispatch
    is an if/elif with no else, so an unlisted type is counted as replayed-zero and
    silently drops the lot."""
    from decimal import Context

    from src.engine.calculation_engine import _apply_historical_currency_event
    from src.engine.fifo_manager import FifoLedger
    from src.utils.currency_converter import CurrencyConverter

    rate_provider = MockECBExchangeRateProvider(foreign_to_eur_init_value=Decimal("1.0"))
    converter = CurrencyConverter(rate_provider=rate_provider)
    asset_id = uuid.uuid4()
    ledger = FifoLedger(
        asset_internal_id=asset_id,
        asset_category=AssetCategory.CASH_BALANCE,
        asset_multiplier_from_asset=Decimal("1"),
        currency_converter=converter,
        exchange_rate_provider=rate_provider,
        internal_working_precision=28,
        decimal_rounding_mode="ROUND_HALF_EVEN",
    )

    event = CashFlowEvent(
        asset_internal_id=asset_id,
        event_date="2022-04-30",
        event_type=FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED,
        gross_amount_foreign_currency=Decimal("10"),
        local_currency="USD",
    )
    event.gross_amount_eur = Decimal("9")

    replayed = _apply_historical_currency_event(
        event, ledger, "USD", converter, Context(prec=28))

    assert replayed == 1, "the replay ignored the lending fee"
    assert sum(lot.quantity for lot in ledger.lots) == Decimal("10")


# =============================================================================
# The ends of the channel: console and PDF
# =============================================================================
#
# CLAUDE.md records that a new reporting channel's ends are where the suite is blind —
# a recording site and an entire rendering block have each been deleted here with the
# suite green. These tests render the two blocks and read the text back.


def _console_text(events, tax_year=TAX_YEAR, resolver=None):
    import contextlib
    import io

    from src.reporting.console_reporter import generate_console_tax_report

    figures = _figures(resolver, events, tax_year)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        generate_console_tax_report(
            realized_gains_losses=[],
            vorabpauschale_items=[],
            all_financial_events=events,
            asset_resolver=resolver,
            tax_year=tax_year,
            eoy_mismatch_count=0,
            loss_offsetting_summary=figures,
        )
    return buffer.getvalue()


def test_the_console_prints_the_leistungen_line_with_the_year_s_zeile(resolver, cash_asset):
    text = _console_text([_fee_event(cash_asset, "40.00")], TAX_YEAR, resolver)
    assert "Zeile 12 (Einnahmen aus Leistungen, §22 Nr. 3 EStG): 40.00" in text


def test_the_console_line_moves_to_zeile_16_in_vz_2025(resolver, cash_asset):
    """The whole reason the line number is not a constant."""
    text = _console_text([_fee_event(cash_asset, "40.00", "2025-01-31")], 2025, resolver)
    assert "Zeile 16 (Einnahmen aus Leistungen, §22 Nr. 3 EStG): 40.00" in text


def test_the_console_does_not_put_the_fee_on_kap_zeile_19(resolver, cash_asset):
    """The defect this change closes, read off the report a person actually looks at."""
    text = _console_text([_fee_event(cash_asset, "40.00")], TAX_YEAR, resolver)
    zeile_19 = [ln for ln in text.splitlines() if "Zeile 19 " in ln]
    assert zeile_19, "the Zeile 19 line vanished from the report"
    assert all("40.00" not in ln for ln in zeile_19), zeile_19


def _pdf_text(events, tax_year=TAX_YEAR, method="_add_so_details"):
    from reportlab.platypus import Paragraph

    from src.domain.results import LossOffsettingResult
    from src.reporting.pdf_generator import PdfReportGenerator

    def flatten(flowable, parts):
        if isinstance(flowable, Paragraph):
            parts.append(flowable.text)
        elif hasattr(flowable, "_cellvalues"):
            for row in flowable._cellvalues:
                for cell in row:
                    flatten(cell, parts) if hasattr(cell, "text") else parts.append(str(cell))
        for attr in ("_content", "_flowables"):
            for child in getattr(flowable, attr, None) or []:
                flatten(child, parts)

    result = LossOffsettingResult()
    result.form_line_values[SO_LEISTUNGEN] = sum(
        (ev.gross_amount_eur for ev in events), Decimal("0"))
    generator = PdfReportGenerator(
        loss_offsetting_result=result,
        all_financial_events=events,
        realized_gains_losses=[],
        vorabpauschale_items=[],
        assets_by_id={},
        tax_year=tax_year,
        eoy_mismatch_details=None,
        eoy_mismatch_count=0,
    )
    getattr(generator, method)()
    parts = []
    for flowable in generator.story:
        flatten(flowable, parts)
    return "\n".join(parts)


def test_the_pdf_detail_section_itemises_the_fee(resolver, cash_asset):
    text = _pdf_text([_fee_event(cash_asset, "40.00")])
    assert "Einnahmen aus Leistungen" in text
    assert "Zeile 12" in text
    assert "40,00" in text
    assert "SYEP" in text, "the Art der Einnahmen the form asks for is not shown"


def test_the_pdf_detail_section_says_so_when_there_is_nothing(resolver, cash_asset):
    text = _pdf_text([])
    assert "Keine Einnahmen aus Leistungen" in text


def test_the_pdf_summary_row_carries_the_figure_and_the_year_s_zeile(resolver, cash_asset):
    text = _pdf_text([_fee_event(cash_asset, "40.00")], method="_add_declared_values_summary")
    assert "Anlage SO Zeile 12 (Einnahmen aus Leistungen, §22 Nr. 3 EStG)" in text
    assert "40,00" in text


def test_the_pdf_summary_row_moves_to_zeile_16_in_vz_2025(resolver, cash_asset):
    text = _pdf_text([_fee_event(cash_asset, "40.00", "2025-01-31")], 2025,
                     method="_add_declared_values_summary")
    assert "Anlage SO Zeile 16 (Einnahmen aus Leistungen, §22 Nr. 3 EStG)" in text

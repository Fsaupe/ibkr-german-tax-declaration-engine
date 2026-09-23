"""A breakdown that does not add up has to say why.

Every amount here is carried at `INTERNAL_CALCULATION_PRECISION` and rounded once, where
it is displayed. So a breakdown rounds its parts and its total independently from the same
exact figures, and the two need not agree — each rounded term can be off by up to half a
cent. Both numbers are correct; neither is a declared figure that moves.

**What was wrong is the silence.** Measured 2026-08-09 on the maintainer's export, before
this change: the PDF's Anlage KAP Zeile 19 breakdown table missed its own total by a cent in
VZ 2024 and VZ 2025, and the console's positive-components block missed its total by a cent
in VZ 2025. A reader checking the arithmetic finds a cent unaccounted for and **cannot tell
rounding from a component the engine forgot** — which is the whole reason the breakdown is
printed. Adding a lending fee to VZ 2023 made the PDF table miss by a cent there too, which
is what surfaced this.

The fix shows the difference and labels it. No component is adjusted to absorb it, because
that would misstate a component; no total is recomputed from the rounded parts, because the
total is the figure that goes on the form.

**The label is a claim, and the guard is the point.** A gap wider than rounding can produce
is not rounding — it is a component missing from the breakdown — and calling it rounding
would tell the reader the one thing that stops them looking. `display_rounding_difference`
returns whether the gap is within `(n + 1) / 2` cents and the label follows it.
"""

from decimal import Decimal

from src.reporting.reporting_utils import (
    ROUNDING_DIFFERENCE_LABEL,
    UNEXPLAINED_DIFFERENCE_LABEL,
    display_rounding_difference,
    rounding_difference_label,
)


def test_a_breakdown_that_adds_up_reports_nothing():
    """The common case. A difference row on every table would be noise."""
    assert display_rounding_difference(
        [Decimal("1.00"), Decimal("2.00")], Decimal("3.00")) is None


def test_a_one_cent_gap_is_reported_as_rounding():
    difference = display_rounding_difference(
        [Decimal("1.00"), Decimal("2.00")], Decimal("3.01"))
    assert difference == (Decimal("0.01"), True)
    assert rounding_difference_label(True) == ROUNDING_DIFFERENCE_LABEL


def test_the_difference_is_signed_so_parts_plus_difference_equal_the_total():
    """Both directions occur in the real captures: +0.01 in VZ 2023, −0.01 in VZ 2024."""
    parts = [Decimal("1.00"), Decimal("2.00")]
    for total in (Decimal("3.01"), Decimal("2.99")):
        amount, _ = display_rounding_difference(parts, total)
        assert sum(parts) + amount == total


def test_the_bound_grows_with_the_number_of_parts():
    """Each rounded term contributes up to half a cent, **the total included** — so the
    bound is (n + 1) / 2 cents, not n / 2. One part and its total can legitimately miss by
    a whole cent; two more than that, they cannot."""
    assert display_rounding_difference(
        [Decimal("1.00"), Decimal("2.00")], Decimal("3.01"))[1] is True
    # The (n + 1) term, on its own: drop it and this single-part cent becomes a false alarm.
    assert display_rounding_difference([Decimal("1.00")], Decimal("1.01"))[1] is True
    assert display_rounding_difference([Decimal("1.00")], Decimal("1.02"))[1] is False


def test_a_gap_wider_than_rounding_is_not_labelled_rounding():
    """The guard. A missing component presented as a rounding difference is a false
    statement in the one place a reader would have caught the defect."""
    amount, is_rounding = display_rounding_difference(
        [Decimal("1.00"), Decimal("2.00")], Decimal("3.50"))
    assert amount == Decimal("0.50")
    assert is_rounding is False
    assert rounding_difference_label(False) == UNEXPLAINED_DIFFERENCE_LABEL
    assert "NICHT ERKL" in UNEXPLAINED_DIFFERENCE_LABEL


def test_the_two_labels_are_not_the_same_string():
    """They are printed, not compared, so nothing else would notice them collapsing."""
    assert ROUNDING_DIFFERENCE_LABEL != UNEXPLAINED_DIFFERENCE_LABEL


# =============================================================================
# The two rendering blocks. Deleting either leaves the rest of the suite green.
# =============================================================================

import contextlib
import io

import pytest
from reportlab.platypus import Paragraph

from src.classification.asset_classifier import AssetClassifier
from src.domain.enums import FinancialEventType, TaxReportingCategory
from src.domain.events import CashFlowEvent
from src.domain.results import LossOffsettingResult
from src.identification.asset_resolver import AssetResolver
from src.reporting.console_reporter import generate_console_tax_report
from src.reporting.pdf_generator import PdfReportGenerator


TAX_YEAR = 2023


@pytest.fixture
def resolver(tmp_path):
    return AssetResolver(asset_classifier=AssetClassifier(
        cache_file_path=str(tmp_path / "cls.json")))


@pytest.fixture
def stock(resolver):
    return resolver.get_or_create_asset(
        raw_isin="DE0007164600", raw_conid="CONSAP", raw_symbol="SAP",
        raw_currency="EUR", raw_ibkr_asset_class="STK",
        raw_description="SAP SE", raw_ibkr_sub_category="COMMON",
    )


def _cash(asset, event_type, gross_eur: str) -> CashFlowEvent:
    """A cash flow whose EUR value carries a sub-cent tail, which is what a non-EUR
    receipt converted at an ECB rate actually looks like — EUR amounts are stored at
    INTERNAL_CALCULATION_PRECISION, not rounded at conversion."""
    ev = CashFlowEvent(
        asset_internal_id=asset.internal_asset_id,
        event_date=f"{TAX_YEAR}-06-30",
        event_type=event_type,
        gross_amount_foreign_currency=Decimal(gross_eur),
        local_currency="EUR",
    )
    ev.gross_amount_eur = Decimal(gross_eur)
    return ev


def _console_text(events, resolver):
    from src.engine.loss_offsetting import LossOffsettingEngine

    figures = LossOffsettingEngine(
        realized_gains_losses=[], vorabpauschale_items=[],
        current_year_financial_events=events, asset_resolver=resolver,
        tax_year=TAX_YEAR,
    ).calculate_reporting_figures()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        generate_console_tax_report(
            realized_gains_losses=[], vorabpauschale_items=[],
            all_financial_events=events, asset_resolver=resolver,
            tax_year=TAX_YEAR, eoy_mismatch_count=0, loss_offsetting_summary=figures,
        )
    return buffer.getvalue()


def _component_block(text: str) -> str:
    return text.split("Detaillierte positive Komponenten")[1].split("Hinweis:")[0]


def test_the_console_block_shows_the_cent_it_would_otherwise_swallow(resolver, stock):
    """Two receipts of just under half a cent each: both print as 0,00 and their exact
    sum rounds to 0,01, so the parts miss the total by a cent."""
    events = [_cash(stock, FinancialEventType.INTEREST_RECEIVED, "0.004"),
              _cash(stock, FinancialEventType.DIVIDEND_CASH, "0.004")]
    block = _component_block(_console_text(events, resolver))

    assert ROUNDING_DIFFERENCE_LABEL in block, block
    assert "0.01" in block


def test_the_console_block_stays_quiet_when_it_adds_up(resolver, stock):
    events = [_cash(stock, FinancialEventType.INTEREST_RECEIVED, "1.00"),
              _cash(stock, FinancialEventType.DIVIDEND_CASH, "2.00")]
    block = _component_block(_console_text(events, resolver))

    assert ROUNDING_DIFFERENCE_LABEL not in block
    assert UNEXPLAINED_DIFFERENCE_LABEL not in block


def test_the_printed_console_parts_plus_the_difference_equal_the_printed_total(resolver, stock):
    """The property the reader checks, asserted on the rendered text rather than on the
    helper — which is the half a unit test of the helper cannot reach."""
    import re

    events = [_cash(stock, FinancialEventType.INTEREST_RECEIVED, "0.004"),
              _cash(stock, FinancialEventType.DIVIDEND_CASH, "0.004")]
    block = _component_block(_console_text(events, resolver))

    values = [Decimal(v) for v in re.findall(r":\s*(-?\d+\.\d\d)\s*$", block, re.M)]
    *parts_and_difference, total = values
    assert sum(parts_and_difference) == total


def _pdf_breakdown_text(result: LossOffsettingResult) -> str:
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

    generator = PdfReportGenerator(
        loss_offsetting_result=result, all_financial_events=[],
        realized_gains_losses=[], vorabpauschale_items=[], assets_by_id={},
        tax_year=TAX_YEAR, eoy_mismatch_details=None, eoy_mismatch_count=0,
    )
    generator._add_calculation_explanations()
    parts = []
    for flowable in generator.story:
        flatten(flowable, parts)
    return "\n".join(parts)


def _result(zeile_19: str, other_income: str = "0.00") -> LossOffsettingResult:
    """The renderer's own inputs. Its component rows come from `form_line_values`, each
    already rounded by the engine, while Zeile 19 is rounded separately from the exact
    internals — so the two can disagree, and that is what is reproduced here."""
    result = LossOffsettingResult()
    result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT] = Decimal(zeile_19)
    result.form_line_values[TaxReportingCategory.ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE] = Decimal(other_income)
    result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AKTIEN_GEWINN] = Decimal("0.00")
    result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AKTIEN_VERLUST] = Decimal("0.00")
    return result


def test_the_pdf_zeile_19_table_shows_the_cent(resolver):
    text = _pdf_breakdown_text(_result(zeile_19="0.01"))
    assert ROUNDING_DIFFERENCE_LABEL in text


def test_the_pdf_zeile_19_table_stays_quiet_when_it_adds_up(resolver):
    text = _pdf_breakdown_text(_result(zeile_19="5.00", other_income="5.00"))
    assert ROUNDING_DIFFERENCE_LABEL not in text
    assert UNEXPLAINED_DIFFERENCE_LABEL not in text


def test_the_pdf_zeile_19_table_refuses_to_call_a_missing_component_rounding(resolver):
    """The calibration this fix exists for: a gap no rounding could produce must not be
    presented as rounding."""
    text = _pdf_breakdown_text(_result(zeile_19="9.99"))
    assert UNEXPLAINED_DIFFERENCE_LABEL in text
    assert ROUNDING_DIFFERENCE_LABEL not in text

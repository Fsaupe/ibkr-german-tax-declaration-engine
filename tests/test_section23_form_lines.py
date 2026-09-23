"""GT-FORM-020: annual taxpayer allocation, distinct from the disposal subtotal.

Official sheets: 2023/2024AnlSO133NET Z54; 2025AnlSO133NET Z58.
Amounts are invented. No holding-period or gain arithmetic is changed here.
"""
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import fitz
import pytest

from src.domain.enums import AssetCategory, RealizationType
from src.domain.exceptions import ProcessingError
from src.domain.results import LossOffsettingResult, RealizedGainLoss
from src.engine.loss_offsetting import LossOffsettingEngine
from src.reporting.console_reporter import generate_console_tax_report
from src.reporting.pdf_generator import PdfReportGenerator
from src.tax_law import registry


def sale(year, gain):
    return RealizedGainLoss(
        originating_event_id=UUID(int=1), asset_internal_id=UUID(int=2),
        asset_category_at_realization=AssetCategory.PRIVATE_SALE_ASSET,
        acquisition_date=f"{year}-01-15", realization_date=f"{year}-03-15",
        realization_type=RealizationType.LONG_POSITION_SALE, quantity_realized=Decimal("1"),
        unit_cost_basis_eur=Decimal("500"),
        unit_realization_value_eur=Decimal("500") + gain,
        total_cost_basis_eur=Decimal("500"),
        total_realization_value_eur=Decimal("500") + gain,
        gross_gain_loss_eur=gain, is_taxable_under_section_23=True,
        holding_period_days=59,
    )


@pytest.mark.parametrize("year", [2023, 2024, 2025])
@pytest.mark.parametrize("gain", [Decimal("123.45"), Decimal("-67.89"), Decimal("0.00")])
def test_aggregation_uses_a_year_neutral_key_without_changing_amount(year, gain):
    result = LossOffsettingEngine(
        [sale(year, gain)], [], [], SimpleNamespace(), year,
    ).calculate_reporting_figures()
    assert result.form_line_values["ANLAGE_SO_NET_GV"] == gain
    assert "ANLAGE_SO_Z54_NET_GV" not in result.form_line_values
    assert result.conceptual_net_p23_estg == gain


def report_result(gain):
    # The legacy key is deliberately absent: reporters must read the new key.
    return LossOffsettingResult(form_line_values={"ANLAGE_SO_NET_GV": gain})


@pytest.mark.parametrize("year,line", [(2023, 54), (2024, 54), (2025, 58)])
@pytest.mark.parametrize("gain", [Decimal("123.45"), Decimal("-67.89"), Decimal("0.00")])
def test_console_places_the_unchanged_amount_on_the_annual_line(year, line, gain, capsys):
    generate_console_tax_report(
        [], [], [], SimpleNamespace(assets_by_internal_id={}), year, 0,
        report_result(gain),
    )
    output = capsys.readouterr().out
    so = output.split("Anlage SO (Sonstige Einkünfte - §23 EStG Private Sales)")[1].split("--- Zusammenfassung")[0]
    assert f"Zeile {line} (Aggregierter Gewinn/Verlust aus §23 EStG Veräußerungen): {gain:.2f}" in so
    assert so.count("Zeile ") == 1


@pytest.mark.parametrize("year,line", [(2023, 54), (2024, 54), (2025, 58)])
@pytest.mark.parametrize("gain", [Decimal("123.45"), Decimal("-67.89"), Decimal("0.00")])
def test_actual_pdf_summary_and_detail_use_the_same_annual_line(year, line, gain, tmp_path):
    generator = PdfReportGenerator(
        report_result(gain), [], [sale(year, gain)], [], {}, year, None,
    )
    target = tmp_path / "section23.pdf"
    generator.generate_report(str(target))
    with fitz.open(target) as pdf:
        text = " ".join(" ".join(page.get_text().split()) for page in pdf)
    formatted = f"{gain:.2f}".replace(".", ",")
    assert f"Anlage SO Zeile {line} (G/V §23 EStG) {formatted}" in text
    assert f"Gesamter G/V §23 EStG (Zeile {line}): {formatted}" in text
    if year == 2025:
        assert "Anlage SO Zeile 54" not in text
        assert "Gesamter G/V §23 EStG (Zeile 54)" not in text


@pytest.mark.parametrize("year,line", [(2021, 48), (2022, 48), (2023, 54), (2024, 54), (2025, 58)])
def test_independently_verified_allocation_lines(year, line):
    assert registry.get_section23_form_line(year) == line
    assert registry.section23_form_warning(year) is None


def test_no_backward_projection():
    with pytest.raises(ProcessingError, match="Anlage SO.*2020"):
        registry.get_section23_form_line(2020)


def test_future_projection_is_visibly_unverified(capsys, tmp_path):
    year = 2027
    assert registry.get_section23_form_line(year) == 58
    notice = registry.section23_form_warning(year)
    assert "2027" in notice and "2025" in notice and "Anlage SO" in notice
    generate_console_tax_report(
        [], [], [], SimpleNamespace(assets_by_internal_id={}), year, 0,
        report_result(Decimal("0.00")),
    )
    assert notice in capsys.readouterr().out
    generator = PdfReportGenerator(report_result(Decimal("0.00")), [], [], [], {}, year, None)
    generator._add_declared_values_summary()
    assert any(notice in getattr(item, "text", "") for item in generator.story)

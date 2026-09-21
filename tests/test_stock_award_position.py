"""The selected GT-ESTG20-064 application reaches both reports, including history."""
import pymupdf
import pytest

from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import position_row
from tests.test_stock_award_scenarios import grant_row, ACCOUNT, ISIN
from src.engine.loss_offsetting import LossOffsettingEngine
from src.reporting.console_reporter import generate_console_tax_report
from src.reporting.pdf_generator import PdfReportGenerator


class TestAwardPositionDisclosure(FifoTestCaseBase):
    @pytest.mark.parametrize("historical", [False, True])
    def test_position_reaches_console_and_pdf(self, historical, capsys, tmp_path):
        year = 2022 if historical else 2023
        holding = position_row(ACCOUNT, ISIN, '10', '40', price='4')
        out = self._run_pipeline(
            tax_year=2023,
            positions_start_data=[holding] if historical else [],
            positions_end_data=[holding],
            grants_data=[grant_row('Stock Award Grant for Cash Deposit',
                                   f'{year}0210', f'{year}0210',
                                   f'{year + 1}0210', '10', '4')])
        summary = LossOffsettingEngine(
            realized_gains_losses=out.realized_gains_losses,
            vorabpauschale_items=out.vorabpauschale_items,
            current_year_financial_events=out.processed_income_events,
            asset_resolver=out.asset_resolver, tax_year=2023,
            apply_conceptual_derivative_loss_capping=False).calculate_reporting_figures()
        generate_console_tax_report(
            realized_gains_losses=out.realized_gains_losses,
            vorabpauschale_items=out.vorabpauschale_items,
            all_financial_events=out.all_financial_events_enriched,
            asset_resolver=out.asset_resolver, tax_year=2023,
            eoy_mismatch_count=out.eoy_mismatch_error_count,
            loss_offsetting_summary=summary, data_gaps=out.data_gaps)
        console = capsys.readouterr().out
        path = tmp_path / 'award-position.pdf'
        PdfReportGenerator(
            loss_offsetting_result=summary,
            all_financial_events=out.processed_income_events,
            realized_gains_losses=out.realized_gains_losses,
            vorabpauschale_items=out.vorabpauschale_items,
            assets_by_id=out.asset_resolver.assets_by_internal_id,
            tax_year=2023, eoy_mismatch_details=[], data_gaps=out.data_gaps,
        ).generate_report(str(path))
        with pymupdf.open(path) as doc:
            pdf = ' '.join(page.get_text() for page in doc)
        for text in (console, pdf):
            assert 'Award-date receipt is the selected filing position' in text
            assert 'vesting-date receipt would change' in ' '.join(text.split())
            assert 'historical awards' in ' '.join(text.split())

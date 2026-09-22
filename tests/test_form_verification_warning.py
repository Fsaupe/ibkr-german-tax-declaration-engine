"""GT-FORM-012: verified reuse must not be reported as missing verification.

The source lookup may share the 2021 entry; the stored 2022/2023 form checks
still apply. Unknown future years must retain the warning in all three outputs.
"""
import logging
from types import SimpleNamespace

import pytest

from src.domain.results import LossOffsettingResult
from src.reporting.console_reporter import generate_console_tax_report
from src.reporting.pdf_generator import PdfReportGenerator
from src.tax_law import registry


@pytest.mark.parametrize('year', [2022, 2023, 2024, 2025, 2027])
def test_log_only_warns_for_an_unverified_year(year, caplog, monkeypatch):
    monkeypatch.setattr(registry, '_warned_carry_years', set())
    with caplog.at_level(logging.WARNING, logger='src.tax_law.registry'):
        rules = registry.get_form_rules(year)
    assert rules == registry.get_form_rules(2021 if year < 2024 else min(year, 2025))
    warnings = [r for r in caplog.records if 'UNGEPRUEFT' in r.getMessage()]
    assert bool(warnings) == (year == 2027)


@pytest.mark.parametrize('year', [2022, 2023, 2024, 2025, 2027])
def test_console_only_denies_verification_for_an_unverified_year(year, capsys):
    generate_console_tax_report(
        [], [], [], SimpleNamespace(assets_by_internal_id={}), year, 0,
        LossOffsettingResult(),
    )
    output = capsys.readouterr().out
    assert ('keine geprueften Formularregeln' in output) == (year == 2027)


@pytest.mark.parametrize('year', [2022, 2023, 2024, 2025, 2027])
def test_pdf_only_denies_verification_for_an_unverified_year(year):
    generator = PdfReportGenerator(LossOffsettingResult(), [], [], [], {}, year, None)
    generator._add_declared_values_summary()
    paragraphs = '\n'.join(getattr(item, 'text', '') for item in generator.story)
    assert ('keine geprüften' in paragraphs) == (year == 2027)

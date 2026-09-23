# tests/test_withholding_cn.py
"""China: 10 % on a mainland company's dividend, 0 % where China's own law exempts it.

[GT-CREDIT-031]: BZSt column C "0 / 10" in each edition 2023-2026; BMF-Schreiben vom
31.03.2022 (the DBA China decides for a company resident on the mainland, Art. 4); DBA
China Art. 10 Abs. 2 Buchst. c (10 %), Buchst. b (15 % for a real-property investment
vehicle, outside column C). The three facts are the taxpayer's, per instrument and year.
Added because the maintainer's VZ 2024 data carries a CN-taxed dividend (review of PR
#102). Currency: the fixtures' USD at 0.90 EUR (a Hong Kong H-share pays in HKD; the
currency does not enter the rate).
"""
import re
from decimal import Decimal
from pathlib import Path

import pytest

from src.tax_law import registry
from tests.test_foreign_withholding_treaty_guard import (
    Z41, _codes, _fund, _income, _resolver, _run, _stock, _stopped, _wht)
from src.domain.enums import FinancialEventType

MAINLAND = {"cn_mainland_resident": True, "cn_real_estate_investment_vehicle": False,
            "cn_exempt_under_chinese_law": False}


def _cn(tmp_path, facts, tax="100", year=2025):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="CNE000000AAA")
    stock.withholding_facts.clear()
    if facts is not None:
        stock.withholding_facts[year] = facts
    inc = _income(stock, "1000", country="CN")
    return [inc, _wht(stock, tax, country="CN", linked_to=inc)], resolver


def test_a_mainland_dividend_withheld_at_10_percent_is_credited_in_full(tmp_path):
    form, gaps = _run(*_cn(tmp_path, MAINLAND))
    assert form.form_line_values[Z41] == Decimal("90.00")
    assert not [c for c in _codes(gaps) if c.startswith("FOREIGN_WHT_")]


def test_a_mainland_dividend_withheld_at_20_percent_is_capped_at_10(tmp_path):
    """An A-share held under a month: 20 % national, 10 % creditable (Art. 10 Abs. 2 c)."""
    form, gaps = _run(*_cn(tmp_path, MAINLAND, tax="200"))
    assert form.form_line_values[Z41] == Decimal("90.00")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in _codes(gaps)


def test_a_dividend_china_exempts_is_credited_at_0(tmp_path):
    """Column C's 0: whatever was withheld is reclaimable in China, none is creditable."""
    form, gaps = _run(*_cn(tmp_path, dict(MAINLAND, cn_exempt_under_chinese_law=True)))
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal("0.00")
    g = [x for x in gaps.gaps if x.code == "FOREIGN_WHT_ABOVE_TREATY_RATE"]
    assert len(g) == 1 and "(0%)" in g[0].detail


@pytest.mark.parametrize("facts", [
    {"cn_mainland_resident": False},
    {"cn_mainland_resident": True, "cn_real_estate_investment_vehicle": True},
])
def test_outside_column_c_the_run_stops(tmp_path, facts):
    _, gaps = _stopped(*_cn(tmp_path, facts))
    assert "FOREIGN_WHT_CONDITION_NOT_MET" in _codes(gaps)


def test_unanswered_the_run_stops(tmp_path):
    _, gaps = _stopped(*_cn(tmp_path, {"cn_mainland_resident": True}))
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_a_chinese_fund_distribution_gets_no_rate(tmp_path):
    resolver = _resolver(tmp_path)
    fund = _fund(resolver, isin="CNE00000FUND")
    fund.withholding_facts.clear()
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND, country="CN")
    _, gaps = _stopped([inc, _wht(fund, "100", country="CN", linked_to=inc)], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)


@pytest.mark.parametrize("year", [2022, 2027])
def test_a_year_without_a_researched_edition_gets_no_rate(tmp_path, year):
    events, resolver = _cn(tmp_path, MAINLAND, year=year)
    for e in events:
        e.event_date = f"{year}-06-16"
    _, gaps = _stopped(events, resolver, tax_year=year)
    assert "FOREIGN_WHT_RATE_YEAR_NOT_RESEARCHED" in _codes(gaps)


def test_the_registry_matches_the_store_edition_by_edition():
    """The CN rates equal the per-edition column C of [GT-CREDIT-031]: the 10 of "0 / 10",
    the 0 being the exempt case the conditions module applies."""
    text = (Path(__file__).resolve().parent.parent / "reference" / "bmf-guidance"
            / "bzst-anrechenbare-quellensteuer.md").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("- Column C, per edition:"))
    parsed = {int(y): Decimal(high) / 100
              for y, low, high in re.findall(r"(\d{4}) \*\*(\d+) / (\d+)\*\*", line)}
    assert parsed == {y: r["CN"] for y, r in registry.CONDITIONAL_DIVIDEND_RATES.items()}
    assert set(parsed) == set(registry.CREDITABLE_DIVIDEND_RATES)

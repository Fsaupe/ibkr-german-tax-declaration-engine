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
    form, gaps = _run(*_cn(tmp_path, dict(MAINLAND, cn_exempt_under_chinese_law=True,
                                          **{"cn_exempt_dividend:2025-06-16": True})))
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


# --------------------------------------------------------------------------- #
# The exemption is a fact of each dividend ([GT-CREDIT-031]: "Three facts about the
# individual dividend"): an A-share's depends on how long it was held at payment. A year
# can hold exempt and taxed dividends of one payer, so the answer is given per dividend.
# --------------------------------------------------------------------------- #

def _two_dividends(tmp_path, facts):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="CNE000000AAA")
    stock.withholding_facts.clear()
    stock.withholding_facts[2025] = facts
    events = []
    for day in ("2025-03-14", "2025-09-12"):
        inc = _income(stock, "1000", country="CN")
        wht = _wht(stock, "100", country="CN", linked_to=inc)
        inc.event_date = wht.event_date = day
        events += [inc, wht]
    return events, resolver


def test_a_year_with_an_exempt_and_a_taxed_dividend_credits_each_at_its_own_rate(tmp_path):
    facts = dict(MAINLAND, cn_exempt_under_chinese_law=True,
                 **{"cn_exempt_dividend:2025-03-14": True, "cn_exempt_dividend:2025-09-12": False})
    form, _ = _run(*_two_dividends(tmp_path, facts))
    assert form.form_line_values[Z41] == Decimal("90.00")   # 0 on March, 10 % on September


def test_a_dividend_without_its_own_answer_stops(tmp_path):
    facts = dict(MAINLAND, cn_exempt_under_chinese_law=True,
                 **{"cn_exempt_dividend:2025-03-14": True})
    message, gaps = _stopped(*_two_dividends(tmp_path, facts))
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_the_per_dividend_question_is_asked_only_after_an_exemption_is_stated(tmp_path):
    from src.processing.withholding_facts import WithholdingFactsStore, resolve_withholding_facts
    events, resolver = _two_dividends(tmp_path, {})
    answers = dict(MAINLAND, cn_exempt_under_chinese_law=True,
                   **{"cn_exempt_dividend:2025-03-14": True, "cn_exempt_dividend:2025-09-12": False})
    asked = []

    def ask(asset, year, question):
        asked.append(question.key)
        return answers[question.key]

    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025,
                                     WithholdingFactsStore(str(tmp_path / "f.json")), True, ask)
    assert left == []
    assert asked == ["cn_mainland_resident", "cn_real_estate_investment_vehicle",
                     "cn_exempt_under_chinese_law", "cn_exempt_dividend:2025-03-14",
                     "cn_exempt_dividend:2025-09-12"]
    form, _ = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("90.00")


def test_no_exempt_dividend_needs_no_per_dividend_answer(tmp_path):
    form, _ = _run(*_two_dividends(tmp_path, MAINLAND))
    assert form.form_line_values[Z41] == Decimal("180.00")

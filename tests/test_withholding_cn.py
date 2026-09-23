# tests/test_withholding_cn.py
"""China: 10 % on a mainland company's dividend; a year with an exempt dividend is unresolved.

[GT-CREDIT-031]: BZSt column C "0 / 10" in each edition 2023-2026; BMF-Schreiben vom
31.03.2022 (the DBA China decides for a company resident on the mainland, Art. 4); DBA
China Art. 10 Abs. 2 Buchst. c (10 %), Buchst. b (15 % for a real-property investment
vehicle, outside column C). The three facts are the taxpayer's, per instrument and year.
Column C's 0 applies where China exempts the dividend; which dividends those are turns on
the holding period of the shares each was paid on, which can differ between accounts and
lots, and is not asked. So a year in which any dividend was exempt leaves the payer's rows
unresolved: not credited, listed, and not declared a 0 % (maintainer's second review, R3).
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
    Z41, _codes, _fund, _income, _not_credited, _resolver, _run, _stock, _wht)
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


def test_a_year_with_an_exempt_dividend_is_unresolved_not_a_stated_0(tmp_path):
    """Not credited and listed as unresolved -- not an ABOVE_TREATY_RATE at 0 %, which
    would state that the tax is reclaimable in China (second review, R3)."""
    message, gaps = _not_credited(*_cn(tmp_path, dict(MAINLAND, cn_exempt_under_chinese_law=True)))
    assert "FOREIGN_WHT_CONDITION_UNRESOLVED" in _codes(gaps)
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)
    assert "Haltedauer" in message


@pytest.mark.parametrize("facts", [
    {"cn_mainland_resident": False},
    {"cn_mainland_resident": True, "cn_real_estate_investment_vehicle": True},
])
def test_outside_column_c_it_is_not_credited(tmp_path, facts):
    _, gaps = _not_credited(*_cn(tmp_path, facts))
    assert "FOREIGN_WHT_CONDITION_UNRESOLVED" in _codes(gaps)


def test_unanswered_it_is_not_credited(tmp_path):
    _, gaps = _not_credited(*_cn(tmp_path, {"cn_mainland_resident": True}))
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_a_chinese_fund_distribution_gets_no_rate(tmp_path):
    resolver = _resolver(tmp_path)
    fund = _fund(resolver, isin="CNE00000FUND")
    fund.withholding_facts.clear()
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND, country="CN")
    _, gaps = _not_credited([inc, _wht(fund, "100", country="CN", linked_to=inc)], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)


@pytest.mark.parametrize("year", [2022, 2027])
def test_a_year_without_a_researched_edition_gets_no_rate(tmp_path, year):
    events, resolver = _cn(tmp_path, MAINLAND, year=year)
    for e in events:
        e.event_date = f"{year}-06-16"
    _, gaps = _not_credited(events, resolver, tax_year=year)
    assert "FOREIGN_WHT_RATE_YEAR_NOT_RESEARCHED" in _codes(gaps)


def test_the_registry_matches_the_store_edition_by_edition():
    """The CN rates equal the per-edition column C of [GT-CREDIT-031]: the 10 of "0 / 10".
    The 0 is the exempt case, which the engine leaves unresolved rather than applying."""
    text = (Path(__file__).resolve().parent.parent / "reference" / "bmf-guidance"
            / "bzst-anrechenbare-quellensteuer.md").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("- Column C, per edition:"))
    parsed = {int(y): Decimal(high) / 100
              for y, low, high in re.findall(r"(\d{4}) \*\*(\d+) / (\d+)\*\*", line)}
    assert parsed == {y: r["CN"] for y, r in registry.CONDITIONAL_DIVIDEND_RATES.items()}
    assert set(parsed) == set(registry.CREDITABLE_DIVIDEND_RATES)


# --------------------------------------------------------------------------- #
# The exemption is a fact of each dividend and holding ([GT-CREDIT-031]); the answer is
# per payer and year, so it can only say whether any dividend was exempt (R3).
# --------------------------------------------------------------------------- #

def _two_accounts(tmp_path, facts):
    """One payer, one date, two accounts' dividends: an A-share's exemption turns on each
    holding's period, so the two can differ; one answer cannot say which is which."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="CNE000000AAA")
    stock.withholding_facts.clear()
    stock.withholding_facts[2025] = facts
    events = []
    for account in ("U0000001", "U0000002"):
        inc = _income(stock, "1000", country="CN")
        wht = _wht(stock, "100", country="CN", linked_to=inc)
        inc.account_id = wht.account_id = account
        events += [inc, wht]
    return events, resolver


def test_an_exempt_dividend_in_the_year_leaves_every_account_s_rows_unresolved(tmp_path):
    """The reviewer's probe: A's holding exempt, B's not. No answer encodes that, so
    neither is credited -- not EUR 0 for both as an exemption, not EUR 180 for both."""
    events, resolver = _two_accounts(tmp_path, dict(MAINLAND, cn_exempt_under_chinese_law=True))
    form, gaps = _run(events, resolver)
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal("0.00")
    assert len(form.foreign_wht_not_credited) == 2
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)


def test_without_an_exempt_dividend_every_account_is_credited_at_10(tmp_path):
    form, _ = _run(*_two_accounts(tmp_path, MAINLAND))
    assert form.form_line_values[Z41] == Decimal("180.00")


def test_nothing_is_asked_per_dividend(tmp_path):
    from src.processing.withholding_facts import WithholdingFactsStore, resolve_withholding_facts
    events, resolver = _two_accounts(tmp_path, {})
    asked = []
    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025,
                                     WithholdingFactsStore(str(tmp_path / "f.json")), True,
                                     lambda asset, year, q: asked.append(q.key) or MAINLAND[q.key])
    assert left == []
    assert asked == ["cn_mainland_resident", "cn_real_estate_investment_vehicle",
                     "cn_exempt_under_chinese_law"]


# --------------------------------------------------------------------------- #
# The listing names the Chinese question or reason, not the US ones
# --------------------------------------------------------------------------- #

def test_the_unanswered_listing_names_the_chinese_question(tmp_path):
    message, _ = _not_credited(*_cn(tmp_path, {"cn_mainland_resident": True}))
    assert "Investmentvehikel" in message and "REIT" not in message


def test_the_unresolved_listing_names_the_chinese_reason(tmp_path):
    message, _ = _not_credited(*_cn(tmp_path, {"cn_mainland_resident": False}))
    assert "Festland" in message and "REIT" not in message

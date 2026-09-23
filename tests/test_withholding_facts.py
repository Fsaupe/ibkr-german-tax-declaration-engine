# tests/test_withholding_facts.py
"""The US 15 % is credited only where the facts it depends on have been stated.

[GT-CREDIT-027]: the 15 % holds "falls keine Befreiung" for a RIC dividend -- the exempt
part is what the RIC reports under 26 U.S.C. § 871(k) -- and for a REIT dividend only under
DBA-USA Art. 10 Abs. 4 Satz 3 (for a natural person, at most 10 % of the REIT). Neither
fact is in the export; the taxpayer states them per instrument and year (maintainer's
review of PR #102, F2). An unanswered question or a failed condition stops the run.

Currency: USD at 0.90 EUR/USD (helpers from the treaty-guard tests).
"""
import json
from datetime import date
from decimal import Decimal

import pytest

from src.domain.exceptions import ProcessingError
from src.domain.enums import FinancialEventType
from src.processing.withholding_facts import (
    WithholdingFacts, WithholdingFactsStore, resolve_withholding_facts)
from tests.test_foreign_withholding_treaty_guard import (
    Z41, _codes, _fund, _income, _resolver, _run, _stock, _stopped, _wht)


def _us_dividend(tmp_path, facts, usd_tax="150"):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    stock.withholding_facts.clear()
    if facts is not None:
        stock.withholding_facts[2025] = facts
    inc = _income(stock, "1000")
    return [inc, _wht(stock, usd_tax, linked_to=inc)], resolver, stock


def _us_fund(tmp_path, facts):
    resolver = _resolver(tmp_path)
    fund = _fund(resolver)
    fund.withholding_facts.clear()
    if facts is not None:
        fund.withholding_facts[2025] = facts
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND)
    return [inc, _wht(fund, "150", linked_to=inc)], resolver


# --------------------------------------------------------------------------- #
# The rule
# --------------------------------------------------------------------------- #

def test_a_us_dividend_with_no_stated_facts_stops_and_names_the_isin(tmp_path):
    events, resolver, stock = _us_dividend(tmp_path, None)
    message, gaps = _stopped(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)
    assert stock.ibkr_isin in message and "withholding_facts.json" in message


def test_a_us_share_that_is_not_a_reit_is_credited_at_15(tmp_path):
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": False})
    form, gaps = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")
    assert not [c for c in _codes(gaps) if c.startswith("FOREIGN_WHT_")]


def test_a_reit_held_at_no_more_than_10_percent_is_credited_at_15(tmp_path):
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": True, "us_reit_holding_at_most_10pct": True})
    form, _ = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")


def test_a_reit_held_above_10_percent_stops(tmp_path):
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": True, "us_reit_holding_at_most_10pct": False})
    message, gaps = _stopped(events, resolver)
    assert "FOREIGN_WHT_CONDITION_NOT_MET" in _codes(gaps) and "REIT" in message


def test_a_reit_without_the_holding_answer_stops_as_unanswered(tmp_path):
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": True})
    _, gaps = _stopped(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_a_us_fund_with_no_exempt_part_is_credited_at_15(tmp_path):
    events, resolver = _us_fund(tmp_path, {"us_ric_exempt_part": False})
    form, _ = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")


def test_a_us_fund_that_reported_an_exempt_part_without_its_share_stops(tmp_path):
    """Tax withheld on the exempt part is not creditable; without the share of each
    distribution the creditable amount is unknown: no figure."""
    events, resolver = _us_fund(tmp_path, {"us_ric_exempt_part": True})
    message, gaps = _stopped(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps) and "RIC" in message


# The exempt part as the RIC reports it, per distribution ([GT-CREDIT-027]: "the 15 % of
# Abs. 2 b applies to the unreported part only"; tax withheld on the reported part is
# wholly an Ermaessigungsanspruch). 1000 USD at 0.90 EUR, 25 % reported exempt: 15 % of
# the other 750 USD = 112.50 USD = EUR 101.25 is creditable.

def _exempt(percent):
    return {"us_ric_exempt_part": True, "us_ric_exempt_percent:2025-06-16": Decimal(percent)}


def test_a_us_fund_with_an_exempt_share_is_credited_at_15_percent_of_the_rest(tmp_path):
    events, resolver = _us_fund(tmp_path, _exempt("25"))
    form, gaps = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("101.25")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in _codes(gaps)


def test_tax_withheld_only_on_the_taxable_part_is_credited_in_full(tmp_path):
    events, resolver = _us_fund(tmp_path, _exempt("25"))
    events[1].gross_amount_foreign_currency = Decimal("112.50")
    events[1].gross_amount_eur = Decimal("112.50") * Decimal("0.90")
    form, gaps = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("101.25")
    assert not [c for c in _codes(gaps) if c.startswith("FOREIGN_WHT_")]


def test_a_wholly_exempt_distribution_credits_nothing(tmp_path):
    events, resolver = _us_fund(tmp_path, _exempt("100"))
    form, _ = _run(events, resolver)
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal("0.00")


def test_the_share_is_asked_per_distribution_after_the_exempt_answer(tmp_path):
    events, resolver = _us_fund(tmp_path, None)
    asked = []
    answers = {"us_ric_exempt_part": True, "us_ric_exempt_percent:2025-06-16": Decimal("25")}

    def ask(asset, year, question):
        asked.append(question.key)
        return answers[question.key]

    store = WithholdingFactsStore(str(tmp_path / "facts.json"))
    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025, store, True, ask)
    assert asked == ["us_ric_exempt_part", "us_ric_exempt_percent:2025-06-16"] and left == []
    saved = WithholdingFactsStore(store.cache_file_path).get(
        next(iter(resolver.assets_by_internal_id.values())).get_classification_key(), 2025)
    assert saved.answers["us_ric_exempt_percent:2025-06-16"] == Decimal("25")


def test_a_share_left_blank_stays_unanswered(tmp_path):
    events, resolver = _us_fund(tmp_path, None)
    answers = {"us_ric_exempt_part": True, "us_ric_exempt_percent:2025-06-16": None}
    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025,
                                     WithholdingFactsStore(str(tmp_path / "facts.json")), True,
                                     lambda asset, year, q: answers[q.key])
    assert len(left) == 1


@pytest.mark.parametrize("value", ["120", "-1", "abc", True])
def test_an_exempt_share_outside_0_to_100_is_unreadable(tmp_path, value):
    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"ISIN:X|2025": {
        "answers": {"us_ric_exempt_part": True, "us_ric_exempt_percent:2025-06-16": value},
        "date_set": "2026-09-23", "source": "x"}}), encoding="utf-8")
    with pytest.raises(ProcessingError):
        WithholdingFactsStore(str(path))


def test_the_answer_of_another_year_is_not_used(tmp_path):
    events, resolver, stock = _us_dividend(tmp_path, None)
    stock.withholding_facts[2024] = {"us_reit": False}
    _, gaps = _stopped(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_a_state_whose_rate_has_no_condition_needs_no_answer(tmp_path):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="JP0000000AAA")
    inc = _income(stock, "1000", country="JP")
    form, _ = _run([inc, _wht(stock, "150", country="JP", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")


# --------------------------------------------------------------------------- #
# The store
# --------------------------------------------------------------------------- #

def test_the_store_round_trips_answers_with_their_source(tmp_path):
    path = str(tmp_path / "facts.json")
    store = WithholdingFactsStore(path)
    store.put("ISIN:US0000000AAA", 2025, WithholdingFacts({"us_reit": False}, date(2026, 9, 23), "1042-S"))
    store.save()
    again = WithholdingFactsStore(path).get("ISIN:US0000000AAA", 2025)
    assert again == WithholdingFacts({"us_reit": False}, date(2026, 9, 23), "1042-S")
    assert WithholdingFactsStore(path).get("ISIN:US0000000AAA", 2024) is None


@pytest.mark.parametrize("content", ["{not json", json.dumps({"ISIN:X|2025": {"answers": {"us_reit": "no"},
                                                                            "date_set": "2026-09-23",
                                                                            "source": "x"}})])
def test_an_unreadable_store_raises_rather_than_starting_empty(tmp_path, content):
    path = tmp_path / "facts.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ProcessingError):
        WithholdingFactsStore(str(path))


# --------------------------------------------------------------------------- #
# Asked at the start of the run
# --------------------------------------------------------------------------- #

def _resolve(tmp_path, answers, interactive=True, store=None):
    events, resolver, stock = _us_dividend(tmp_path, None)
    store = store or WithholdingFactsStore(str(tmp_path / "facts.json"))
    asked = []

    def ask(asset, year, question):
        asked.append((asset.ibkr_isin, year, question.key))
        return answers[question.key]

    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025, store,
                                     interactive, ask)
    return stock, asked, left, store


def test_an_interactive_run_asks_and_remembers(tmp_path):
    stock, asked, left, store = _resolve(tmp_path, {"us_reit": False})
    assert asked == [("US0000000AAA", 2025, "us_reit")] and left == []
    assert stock.withholding_facts[2025] == {"us_reit": False}
    saved = WithholdingFactsStore(store.cache_file_path).get(stock.get_classification_key(), 2025)
    assert saved.answers == {"us_reit": False} and saved.source


def test_the_holding_question_follows_only_a_reit_answer(tmp_path):
    _, asked, left, _ = _resolve(tmp_path, {"us_reit": True, "us_reit_holding_at_most_10pct": True})
    assert [k for _, _, k in asked] == ["us_reit", "us_reit_holding_at_most_10pct"] and left == []


def test_a_stored_answer_is_not_asked_again(tmp_path):
    store = WithholdingFactsStore(str(tmp_path / "facts.json"))
    store.put("ISIN:US0000000AAA", 2025, WithholdingFacts({"us_reit": False}, date(2026, 9, 23), "1042-S"))
    stock, asked, left, _ = _resolve(tmp_path, {}, store=store)
    assert asked == [] and left == [] and stock.withholding_facts[2025] == {"us_reit": False}


def test_a_non_interactive_run_asks_nothing_and_reports_what_is_missing(tmp_path):
    stock, asked, left, store = _resolve(tmp_path, {}, interactive=False)
    assert asked == [] and left == [stock]
    assert not (tmp_path / "facts.json").exists()


def test_the_pipeline_resolves_the_facts_before_the_engine(monkeypatch):
    """The end of the channel: a pipeline that never asked would leave every US row
    unanswered. The call is probed where the pipeline makes it."""
    import src.pipeline_runner as pipeline_runner

    class Reached(Exception):
        pass

    def spy(**kwargs):
        assert kwargs["tax_year"] == 2025 and kwargs["interactive"] is False
        raise Reached

    class Orchestrator:
        def __init__(self, **kwargs):
            from tests.test_foreign_withholding_treaty_guard import _resolver as _r
            import tempfile
            self.asset_resolver = _r(__import__("pathlib").Path(tempfile.mkdtemp()))
            self.raw_grants, self.vorabpauschale_price_substitutions = [], []
            self.prior_soy_positions = self.prior_eoy_positions = {}

        def run_parsing_pipeline(self, **kwargs):
            return []

    monkeypatch.setattr(pipeline_runner, "ParsingOrchestrator", Orchestrator)
    monkeypatch.setattr(pipeline_runner, "resolve_year_start_prices", lambda **kw: 0)
    monkeypatch.setattr(pipeline_runner, "resolve_withholding_facts", spy)
    monkeypatch.setattr(pipeline_runner, "WithholdingFactsStore", lambda: None)
    with pytest.raises(Reached):
        pipeline_runner.run_core_processing_pipeline(
            trades_file_path="", cash_transactions_file_path="", positions_start_file_path="",
            positions_end_file_path="", corporate_actions_file_path="",
            interactive_classification_mode=False, tax_year_to_process=2025,
            custom_rate_provider=object())

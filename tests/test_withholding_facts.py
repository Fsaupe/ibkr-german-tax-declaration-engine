# tests/test_withholding_facts.py
"""The US 15 % is credited only where the facts it depends on have been stated.

[GT-CREDIT-027]: the 15 % holds "falls keine Befreiung" for a RIC distribution -- US law
leaves untaxed what the RIC reports as an interest-related, short-term capital gain
(26 U.S.C. § 871(k)) or capital gain dividend (§ 852(b)(3)), under conditions the report
does not establish, so the 15 % is settled only where the RIC reported no part as other
than an ordinary dividend -- and for a REIT dividend only under DBA-USA Art. 10 Abs. 4
Satz 3. Neither fact is in the export; the taxpayer states them per payer and year. An
unanswered question, or an answer that leaves the rate unsettled, means the rows are not
credited and are listed as unresolved (maintainer's second review of PR #102).

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
    Z41, _codes, _fund, _income, _not_credited, _resolver, _run, _stock, _wht)


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

def test_a_us_dividend_with_no_stated_facts_is_not_credited_and_names_the_isin(tmp_path):
    events, resolver, stock = _us_dividend(tmp_path, None)
    message, gaps = _not_credited(events, resolver)
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


def test_a_reit_held_above_10_percent_is_unresolved_not_without_a_ceiling(tmp_path):
    """Above 10 % Buchst. a fails, but Buchst. b (an exchange-traded class, at most 5 %) and
    c (a diversified REIT) are independent alternatives, not examined here. The reason
    says so; it does not say the treaty sets no ceiling (second review, R5)."""
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": True, "us_reit_holding_at_most_10pct": False})
    message, gaps = _not_credited(events, resolver)
    assert "FOREIGN_WHT_CONDITION_UNRESOLVED" in _codes(gaps)
    assert "Buchst. b" in message and "keinen Höchstsatz" not in message


def test_a_reit_without_the_holding_answer_is_unanswered(tmp_path):
    events, resolver, _ = _us_dividend(tmp_path, {"us_reit": True})
    _, gaps = _not_credited(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


def test_a_us_fund_with_no_non_ordinary_part_is_credited_at_15(tmp_path):
    events, resolver = _us_fund(tmp_path, {"us_ric_non_ordinary_part": False})
    form, _ = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")


def test_a_us_fund_that_reported_a_non_ordinary_part_is_not_credited(tmp_path):
    """Whatever part the RIC reported, how much of it the US leaves untaxed for this
    recipient turns on § 871(k)(1)(B), (2)(B) and the excess-reported-amount rules, which
    the report does not establish (second review, R2). Not credited, not a stated 0 %."""
    events, resolver = _us_fund(tmp_path, {"us_ric_non_ordinary_part": True})
    message, gaps = _not_credited(events, resolver)
    assert "FOREIGN_WHT_CONDITION_UNRESOLVED" in _codes(gaps)
    assert "871(k)(1)(B)" in message and "852(b)(3)" in message


def test_one_answer_per_fund_and_year_covers_every_distribution(tmp_path):
    """The question is about what the RIC reported for its year, the same for every
    account and payment; nothing is asked per distribution or keyed by date (R3)."""
    events, resolver = _us_fund(tmp_path, None)
    fund = next(iter(resolver.assets_by_internal_id.values()))
    second = _income(fund, "500", kind=FinancialEventType.DISTRIBUTION_FUND)   # same date
    events += [second, _wht(fund, "75", linked_to=second)]
    asked = []
    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025,
                                     WithholdingFactsStore(str(tmp_path / "facts.json")), True,
                                     lambda asset, year, q: asked.append(q.key) or False)
    assert asked == ["us_ric_non_ordinary_part"] and left == []
    form, _ = _run(events, resolver)
    assert form.form_line_values[Z41] == Decimal("202.50")


def test_a_question_left_blank_stays_unanswered(tmp_path):
    events, resolver = _us_fund(tmp_path, None)
    left = resolve_withholding_facts(resolver.assets_by_internal_id.values(), events, 2025,
                                     WithholdingFactsStore(str(tmp_path / "facts.json")), True,
                                     lambda asset, year, q: None)
    assert len(left) == 1
    _, gaps = _not_credited(events, resolver)
    assert "FOREIGN_WHT_FACTS_UNANSWERED" in _codes(gaps)


@pytest.mark.parametrize("key,value", [("us_ric_exempt_part", False),
                                       ("us_ric_exempt_percent:2025-06-16", "25"),
                                       ("cn_exempt_dividend:2025-06-16", True)])
def test_an_answer_to_a_retired_question_is_refused(tmp_path, key, value):
    """'us_ric_exempt_part' asked about the § 871(k) kinds only, so its 'no' does not
    answer the question that replaced it; the per-date answers are no longer asked. A file
    holding them raises, naming them, rather than being read as a current answer."""
    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"ISIN:X|2025": {"answers": {key: value}, "date_set": "2026-09-23",
                                                "source": "x"}}), encoding="utf-8")
    with pytest.raises(ProcessingError, match=key.split(":")[0]):
        WithholdingFactsStore(str(path))


def test_the_answer_of_another_year_is_not_used(tmp_path):
    events, resolver, stock = _us_dividend(tmp_path, None)
    stock.withholding_facts[2024] = {"us_reit": False}
    _, gaps = _not_credited(events, resolver)
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

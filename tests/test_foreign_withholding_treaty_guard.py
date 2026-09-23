# tests/test_foreign_withholding_treaty_guard.py
"""Zeile 41 never carries more than the creditable foreign tax on a row.

Issue #78, Group B. § 32d Abs. 5 Satz 1 credits the withheld tax reduced by the
source state's Ermäßigungsanspruch ([GT-CREDIT-026]); for a US dividend or payment in
lieu the source state keeps 15 % ([GT-CREDIT-027], DBA-USA Art. 10 Abs. 2 b / Abs. 4
Satz 2). The guard caps the anrechenbare amount on Zeile 41 to the treaty rate and
reports the excess as reclaimable in the source state (cap-and-report). The other
source states and Irish interest follow the same route ([GT-CREDIT-029], [GT-CREDIT-030]). It never defaults an
unknown source state, and it compares in the row's own currency to the cent so a
rounded 15 % on a sub-unit gross is not read as an over-withholding. A row with no
supported creditable amount (no linked income, no rate for its state, income kind or
year) is not credited: it is not on Zeile 41, and it is listed as unresolved with what
is open, while the rest of the declaration stands (maintainer's second review of PR #102:
an unresolved credit may be left unclaimed, never claimed under a warning).

Measured incidence of a US row above the treaty rate is 0 of 28 US-suffixed
dividend/PIL withholding rows VZ 2023–2025 (2026-09-22); these fixtures are the hypothetical the issue named (a lapsed W-8BEN
puts every US row at 30 %). Every over-withholding test below is red on the tree
before the guard (Zeile 41 uncapped, no gap).

Currency: USD at a fixed 0.90 EUR/USD, so a foreign amount never coincides with its
EUR value and the guard's currency handling is observable (CLAUDE.md).
"""
import io
import uuid
from contextlib import redirect_stdout
from decimal import Decimal

import pytest

from src.engine.loss_offsetting import LossOffsettingEngine
from src.processing.data_gaps import DataGapCollector, GapSeverity
from src.identification.asset_resolver import AssetResolver
from src.classification.asset_classifier import AssetClassifier
from src.domain.assets import InvestmentFund
from src.domain.enums import (
    FinancialEventType, InvestmentFundType, TaxReportingCategory,
)
from src.domain.events import CashFlowEvent, WithholdingTaxEvent

EUR = Decimal("0.90")
Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID
Z19 = TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT
Z4_AKTIEN = TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS


def _resolver(tmp_path):
    return AssetResolver(asset_classifier=AssetClassifier(cache_file_path=str(tmp_path / "c.json")))


# The taxpayer's answers the US 15 % depends on ([GT-CREDIT-027]; test_withholding_facts.py):
# the fixtures' share is not a REIT and the fund reported no non-ordinary part, in every year
# the tests use. A test of the facts themselves clears them.
_YEARS = range(2020, 2031)


def _stock(resolver, isin="US0000000AAA"):
    stock = resolver.get_or_create_asset(
        raw_isin=isin, raw_conid="C" + isin[-4:], raw_symbol="ACME", raw_currency="USD",
        raw_ibkr_asset_class="STK", raw_description="ACME", raw_ibkr_sub_category="COMMON")
    stock.withholding_facts.update({y: {"us_reit": False} for y in _YEARS})
    return stock


def _fund(resolver, isin="US00000FUND1"):
    fund = InvestmentFund(fund_type=InvestmentFundType.AKTIENFONDS, description="TF ETF",
                          currency="USD", ibkr_isin=isin, ibkr_symbol="TF")
    fund.withholding_facts.update({y: {"us_ric_non_ordinary_part": False} for y in _YEARS})
    resolver.assets_by_internal_id[fund.internal_asset_id] = fund
    return fund


_TX = iter(range(7000, 9000))


def _income(asset, usd, kind=FinancialEventType.DIVIDEND_CASH, country="US"):
    ev = CashFlowEvent(
        asset_internal_id=asset.internal_asset_id, event_date="2025-06-16",
        event_type=kind, gross_amount_foreign_currency=Decimal(usd), local_currency="USD",
        source_country_code=country, ibkr_transaction_id=str(next(_TX)))
    ev.gross_amount_eur = Decimal(usd) * EUR
    return ev


def _wht(asset, usd, country="US", linked_to=None):
    ev = WithholdingTaxEvent(
        asset_internal_id=asset.internal_asset_id, event_date="2025-06-16",
        gross_amount_foreign_currency=Decimal(usd), local_currency="USD",
        source_country_code=country, ibkr_transaction_id=str(next(_TX)))
    ev.gross_amount_eur = Decimal(usd) * EUR
    if linked_to is not None:
        ev.taxed_income_event_id = linked_to.event_id
        ev.link_confidence_score = 100  # as the linker sets it alongside the id
    return ev


def _run(events, resolver, tax_year=2025):
    gaps = DataGapCollector()
    engine = LossOffsettingEngine(
        realized_gains_losses=[], vorabpauschale_items=[],
        current_year_financial_events=events, asset_resolver=resolver,
        tax_year=tax_year, data_gap_collector=gaps)
    return engine.calculate_reporting_figures(), gaps


def _codes(gaps):
    return [g.code for g in gaps.gaps]


def _not_credited(events, resolver, tax_year=2025, z41="0.00"):
    """Run expecting the unsupported rows to be left off Zeile 41 and listed, not a stop:
    the run completes, every gap is a WARNING, Zeile 41 is `z41` (the supported rows
    only), and each unsupported row carries what is open. Return the listing's text
    and the gaps."""
    form, gaps = _run(events, resolver, tax_year)
    assert all(g.severity is GapSeverity.WARNING for g in gaps.gaps)
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal(z41)
    listed = form.foreign_wht_not_credited
    assert listed and all(listed.values())
    for e in events:
        if isinstance(e, WithholdingTaxEvent) and e.event_id in listed:
            assert form.creditable_foreign_wht_eur[e.event_id] is None
    message = " ".join(g.detail for g in gaps.gaps if "NICHT auf Zeile 41" in g.detail)
    assert "keine Feststellung" in message   # not a finding of zero, nor a refund claim
    return message, gaps


# --------------------------------------------------------------------------- #
# B1 / B2 — over-withholding is capped, on a fund and on a share alike
# --------------------------------------------------------------------------- #

def test_b1_us_fund_withholding_above_the_treaty_rate_is_capped_and_reported(tmp_path):
    """The issue's hypothetical: a fund PIL of 1000 USD withheld at 30 %.

    Zeile 4 (gross Ausschüttung) is unaffected; Zeile 41 carries only the treaty 15 %
    (EUR 135), and a WARNING gap names the withheld 270, the creditable 135, the excess
    135, and the IRS route. legal_basis: [GT-CREDIT-026], [GT-CREDIT-027]."""
    resolver = _resolver(tmp_path)
    fund = _fund(resolver)
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND)
    form, gaps = _run([inc, _wht(fund, "300", linked_to=inc)], resolver)

    assert form.form_line_values[Z4_AKTIEN] == Decimal("900.00")
    assert form.form_line_values[Z41] == Decimal("135.00")
    g = [x for x in gaps.gaps if x.code == "FOREIGN_WHT_ABOVE_TREATY_RATE"]
    assert len(g) == 1 and g[0].severity is GapSeverity.WARNING
    assert "270.00" in g[0].detail and "135.00" in g[0].detail and "IRS" in g[0].detail


def test_b1_the_gap_reaches_the_console_report_not_only_the_collector(tmp_path):
    """The ends of the channel: recording the gap is not enough — it must render.
    Deleting the report's gap section (or misrouting the assertion to the collector)
    must fail here. CLAUDE.md, 'the ends of a new channel'."""
    from src.reporting.console_reporter import generate_console_tax_report
    resolver = _resolver(tmp_path)
    fund = _fund(resolver)
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND)
    events = [inc, _wht(fund, "300", linked_to=inc)]
    form, gaps = _run(events, resolver)

    buf = io.StringIO()
    with redirect_stdout(buf):
        generate_console_tax_report(
            realized_gains_losses=[], vorabpauschale_items=[], all_financial_events=events,
            asset_resolver=resolver, tax_year=2025, eoy_mismatch_count=0,
            loss_offsetting_summary=form, data_gaps=gaps.gaps)
    out = buf.getvalue()
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in out
    assert "IRS" in out and "135.00" in out


def test_b2_us_share_dividend_at_thirty_percent_is_capped_the_same_way(tmp_path):
    """The rule is not a substitute-payment rule: an ordinary US dividend at 30 % caps
    the same way. A guard written for PILs only would pass B1 and fail here."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    form, gaps = _run([inc, _wht(stock, "300", linked_to=inc)], resolver)

    assert form.form_line_values[Z19] == Decimal("900.00")
    assert form.form_line_values[Z41] == Decimal("135.00")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in _codes(gaps)


def test_b2_the_capped_amount_keeps_the_tax_rows_own_conversion(tmp_path):
    """The Ermäßigungsanspruch reduces the withheld tax ([GT-CREDIT-026]), so the capped
    amount is that tax's own EUR value scaled to the treaty share, not 15 % of the
    income converted at the income row's rate. Income at 0.90, tax at 0.92 EUR/USD:
    withheld 300 USD = EUR 276.00, of which 150/300 creditable = EUR 138.00. Converting
    the treaty tax at the income's rate instead gives EUR 135.00."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    wht = _wht(stock, "300", linked_to=inc)
    wht.gross_amount_eur = Decimal("300") * Decimal("0.92")
    form, _ = _run([inc, wht], resolver)

    assert form.form_line_values[Z41] == Decimal("138.00")


# --------------------------------------------------------------------------- #
# B3 — the gap reports the year total, one aggregate per source state
# --------------------------------------------------------------------------- #

def test_b3_the_gap_aggregates_the_years_us_rows_into_one(tmp_path):
    """Four US dividends at 30 %. Zeile 41 = 4 x 135; one aggregate gap for the US
    naming the total excess (the shape of the IRS claim)."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    events = []
    for _ in range(4):
        inc = _income(stock, "1000")
        events += [inc, _wht(stock, "300", linked_to=inc)]
    form, gaps = _run(events, resolver)

    assert form.form_line_values[Z41] == Decimal("540.00")  # 4 x 135
    above = [g for g in gaps.gaps if g.code == "FOREIGN_WHT_ABOVE_TREATY_RATE"]
    assert len(above) == 1, "one aggregate gap per source state per year"
    assert "540.00" in above[0].detail  # total excess 4 x 135


# --------------------------------------------------------------------------- #
# B4 / B5 — no default for an unknown or absent source state: not credited
# --------------------------------------------------------------------------- #

def test_b4_a_source_state_with_no_treaty_rate_is_not_credited(tmp_path):
    """A dividend from Takatukaland, withheld at 21 %: a made-up source state, so the
    store will never have a rate for it. No figure: not the withheld EUR 189, not a
    15 % cap. Not credited, and the listing names its transaction."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="XX0000000AAA")
    inc = _income(stock, "1000", country="TAKATUKALAND")
    wht = _wht(stock, "210", country="TAKATUKALAND", linked_to=inc)
    message, gaps = _not_credited([inc, wht], resolver)

    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "TAKATUKALAND" in message and wht.ibkr_transaction_id in message


def test_b5_a_row_without_a_country_code_is_not_given_a_state_and_not_credited(tmp_path):
    """A US-ISIN row withheld at 30 % but with no issuer country code: the guard must
    NOT infer the state from the currency or the ISIN prefix and cap at the US rate."""
    resolver = _resolver(tmp_path)
    fund = _fund(resolver)
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND, country=None)
    message, gaps = _not_credited([inc, _wht(fund, "300", country=None, linked_to=inc)], resolver)

    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)
    assert "keinen Quellenstaat" in message


# --------------------------------------------------------------------------- #
# B6 / B7 — interest is outside the dividend rate; an unlinked row is reported
# --------------------------------------------------------------------------- #

def test_b6_interest_withholding_is_outside_the_dividend_ceiling(tmp_path):
    """A US interest withholding is not measured against the dividend rate (the store
    carries no US interest rate): no 15 % cap, and not credited."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000", kind=FinancialEventType.INTEREST_RECEIVED)
    _, gaps = _not_credited([inc, _wht(stock, "300", linked_to=inc)], resolver)

    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)


def test_b7_a_withholding_row_the_linker_could_not_attach_is_not_credited(tmp_path):
    """A withholding with no income row to measure against has no creditable amount:
    a rate check needs a denominator. Listed as unlinked, not credited."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    message, gaps = _not_credited([_wht(stock, "300", linked_to=None)], resolver)

    assert "FOREIGN_WHT_UNLINKED" in _codes(gaps)
    assert "keinem Ertrag" in message


def test_b7_every_unsupported_row_is_listed_and_the_supported_one_credited(tmp_path):
    """An unlinked row, an unknown state and a capped row in one run: both unsupported
    rows are listed and left off Zeile 41, and the capped row is credited at 15 %."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    unlinked = _wht(stock, "300", linked_to=None)
    other = _stock(resolver, isin="XX0000000BBB")
    inc_x = _income(other, "1000", country="TAKATUKALAND")
    unknown = _wht(other, "210", country="TAKATUKALAND", linked_to=inc_x)
    inc_us = _income(stock, "1000")
    message, gaps = _not_credited([unlinked, inc_x, unknown, inc_us, _wht(stock, "300", linked_to=inc_us)],
                                  resolver, z41="135.00")

    assert unlinked.ibkr_transaction_id in message and unknown.ibkr_transaction_id in message
    assert {"FOREIGN_WHT_UNLINKED", "FOREIGN_WHT_RATE_NOT_VERIFIED",
            "FOREIGN_WHT_ABOVE_TREATY_RATE"} <= set(_codes(gaps))


# --------------------------------------------------------------------------- #
# B8 — the treaty rate limits all the tax on one dividend, not each row
# --------------------------------------------------------------------------- #

def test_b8_two_tax_rows_on_one_dividend_are_measured_together(tmp_path):
    """Art. 10 Abs. 2 limits *"die Steuer"* on a dividend against *"des Bruttobetrags
    der Dividenden"* ([GT-CREDIT-027]): all the tax on one dividend, together. Two rows
    of 15 % each on one 1000 USD dividend are 30 %; 150 USD is creditable, 135.00 EUR.
    Measured one row at a time, each passes and 270.00 reaches Zeile 41. Measured
    2026-09-23: no income in Cash_Transactions-{2023..2025} has two tax rows linked to
    it, so this is the hypothetical of an additional withholding booked as its own row."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    first = _wht(stock, "150", linked_to=inc)
    second = _wht(stock, "150", linked_to=inc)
    form, gaps = _run([inc, first, second], resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in _codes(gaps)


@pytest.mark.parametrize("order", [("CA", "US"), ("US", "CA")])
def test_b8_rows_naming_two_states_on_one_dividend_are_not_credited_in_either_order(tmp_path, order):
    """One dividend has one source state ([GT-CREDIT-027]: the limit is on the tax of the
    state where the paying company is resident). Two rows naming different states cannot
    both be that state's tax, so neither rate applies and neither row is credited. CA and US share
    the 15 %, so comparing rates does not see it; with the CA row first the US REIT
    question was skipped and both rows were credited in full (review of PR #102, 2026-09-23)."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    stock.withholding_facts.clear()   # the US condition is unanswered
    inc = _income(stock, "1000")
    rows = [_wht(stock, "100", country=order[0], linked_to=inc),
            _wht(stock, "50", country=order[1], linked_to=inc)]
    _, gaps = _not_credited([inc, *rows], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)


# --------------------------------------------------------------------------- #
# B9 — the BZSt creditable rates for the other states in the exports
# --------------------------------------------------------------------------- #
# [GT-CREDIT-029], BZSt column C, identical in the Stand 1.1.2023 to 1.1.2026 editions:
# Frankreich 12,8 (the national rate, below the DBA's 15), Japan 15, Taiwan 10. Share
# dividends only: the table's "Dividenden" are distributions of Kapitalgesellschaften.

def test_b9_a_french_dividend_withheld_at_25_percent_is_credited_at_12_8(tmp_path):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="FR0000000AAA")
    inc = _income(stock, "1000", country="FR")
    form, gaps = _run([inc, _wht(stock, "250", country="FR", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("115.20")      # 128 USD x 0.90
    g = [x for x in gaps.gaps if x.code == "FOREIGN_WHT_ABOVE_TREATY_RATE"]
    assert len(g) == 1 and "12.8%" in g[0].detail


def test_b9_a_french_dividend_withheld_at_12_8_percent_is_credited_in_full(tmp_path):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="FR0000000AAA")
    inc = _income(stock, "1000", country="FR")
    form, gaps = _run([inc, _wht(stock, "128", country="FR", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("115.20")
    assert not [x for x in gaps.gaps if x.code.startswith("FOREIGN_WHT_")]


def test_b9_a_taiwanese_dividend_withheld_at_21_percent_is_credited_at_10(tmp_path):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="US8740391003")
    inc = _income(stock, "1000", country="TW")
    form, _ = _run([inc, _wht(stock, "210", country="TW", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("90.00")


def test_b9_a_japanese_dividend_at_15_315_percent_is_credited_at_15(tmp_path):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="JP0000000AAA")
    inc = _income(stock, "1000", country="JP")
    form, _ = _run([inc, _wht(stock, "153.15", country="JP", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")


def test_b9_a_french_fund_distribution_is_not_given_the_share_dividend_rate(tmp_path):
    """Outside the table's Dividenden: not capped at 12,8, and not credited."""
    resolver = _resolver(tmp_path)
    fund = _fund(resolver, isin="FR00000FUND1")
    inc = _income(fund, "1000", kind=FinancialEventType.DISTRIBUTION_FUND, country="FR")
    _, gaps = _not_credited([inc, _wht(fund, "250", country="FR", linked_to=inc)], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)


# --------------------------------------------------------------------------- #
# B10 — the rates are per assessment year; an unresearched year gets none
# --------------------------------------------------------------------------- #
# [GT-CREDIT-029]: each year's rates come from that year's BZSt edition only. A year
# whose edition has not been read is never given a neighbouring year's rate.

@pytest.mark.parametrize("tax_year", [2022, 2027])
def test_b10_a_year_without_a_researched_edition_is_not_given_another_year_s_rate(tmp_path, tax_year):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    message, gaps = _not_credited([inc, _wht(stock, "300", linked_to=inc)], resolver, tax_year=tax_year)
    g = [x for x in gaps.gaps if x.code == "FOREIGN_WHT_RATE_YEAR_NOT_RESEARCHED"]
    assert len(g) == 1 and str(tax_year) in g[0].detail and str(tax_year) in message
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)


@pytest.mark.parametrize("tax_year", [2023, 2024, 2025])
def test_b10_each_researched_year_caps_with_its_own_rate(tmp_path, tax_year):
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    form, _ = _run([inc, _wht(stock, "300", linked_to=inc)], resolver, tax_year=tax_year)
    assert form.form_line_values[Z41] == Decimal("135.00")


def test_b10_a_us_row_in_a_year_the_us_law_is_not_stated_for_is_not_credited(tmp_path):
    """[GT-CREDIT-027] states the US law the 15 % turns on for 2023-2025 only. VZ 2026 has
    a BZSt edition with 15 %, which alone does not establish it (second review, R1)."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    message, gaps = _not_credited([inc, _wht(stock, "150", linked_to=inc)], resolver, tax_year=2026)
    assert "FOREIGN_WHT_CONDITIONS_YEAR_NOT_RESEARCHED" in _codes(gaps) and "2026" in message


def test_b10_a_non_us_row_in_2026_keeps_its_edition_rate(tmp_path):
    """The US gate is on the US only: a Japanese dividend in 2026 keeps column C's 15 %."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="JP0000000AAA")
    inc = _income(stock, "1000", country="JP")
    form, _ = _run([inc, _wht(stock, "300", country="JP", linked_to=inc)], resolver, tax_year=2026)
    assert form.form_line_values[Z41] == Decimal("135.00")


# --------------------------------------------------------------------------- #
# B11 — Irish interest withholding: 0 % creditable ([GT-CREDIT-030])
# --------------------------------------------------------------------------- #
# The taxing state of credit-interest withholding is the broker entity's country, which
# only the taxpayer's configuration supplies (config.BROKER_ENTITY_COUNTRY).

def _interest_pair(resolver, country):
    stock = _stock(resolver)   # the asset is irrelevant to the rate; kind and state decide
    inc = _income(stock, "100", kind=FinancialEventType.INTEREST_RECEIVED, country=country)
    return inc, _wht(stock, "20", country=country, linked_to=inc)


def test_b11_irish_interest_withholding_is_not_credited(tmp_path):
    resolver = _resolver(tmp_path)
    inc, wht = _interest_pair(resolver, "IE")
    form, gaps = _run([inc, wht], resolver)
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal("0.00")
    g = [x for x in gaps.gaps if x.code == "FOREIGN_WHT_ABOVE_TREATY_RATE"]
    assert len(g) == 1 and "(0%)" in g[0].detail


def test_b11_interest_withholding_with_no_configured_state_is_not_credited_and_names_the_setting(tmp_path):
    resolver = _resolver(tmp_path)
    inc, wht = _interest_pair(resolver, None)
    message, gaps = _not_credited([inc, wht], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "BROKER_ENTITY_COUNTRY" in message


def test_b11_irish_interest_in_an_unresearched_year_is_not_credited(tmp_path):
    resolver = _resolver(tmp_path)
    inc, wht = _interest_pair(resolver, "IE")
    _, gaps = _not_credited([inc, wht], resolver, tax_year=2027)
    assert "FOREIGN_WHT_RATE_YEAR_NOT_RESEARCHED" in _codes(gaps)


def test_b11_a_one_cent_irish_interest_withholding_is_not_credited_either(tmp_path):
    """The cent tolerance absorbs a positive rate rounded up on a sub-unit gross. At a
    0 % rate there is nothing to round: any amount withheld is above it. Measured
    2026-09-23: 3 such rows in VZ 2023 (NOK, NZD), each at most 0.01."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "0.05", kind=FinancialEventType.INTEREST_RECEIVED, country="IE")
    form, gaps = _run([inc, _wht(stock, "0.01", country="IE", linked_to=inc)], resolver)
    assert form.form_line_values.get(Z41, Decimal("0.00")) == Decimal("0.00")
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" in _codes(gaps)


# --------------------------------------------------------------------------- #
# B12 — a rate applies only to the instrument it covers (maintainer's review, F2)
# --------------------------------------------------------------------------- #
# [GT-CREDIT-029]: column C of FR, JP, CA, KR, NL, TW covers a dividend on an ordinary
# share; the column-F notes take a right or share whose payment the payer deducts out of
# it. [GT-CREDIT-028]: the store establishes a payment in lieu's treaty character as a
# dividend for the US only.

def test_b12_a_french_dividend_on_an_instrument_not_classified_aktie_is_not_given_12_8(tmp_path):
    """A profit-participating right booked by the broker as a dividend: the classification
    says it is not an Aktie, so column C is not its rate, and it is not credited."""
    from src.domain.enums import AssetCategory
    resolver = _resolver(tmp_path)
    right = _stock(resolver, isin="FR0000000GEN")
    right = resolver.replace_asset_type(right.internal_asset_id, AssetCategory.SONSTIGE_KAPITALFORDERUNG,
                                        None, "Genussrecht")
    inc = _income(right, "1000", country="FR")
    _, gaps = _not_credited([inc, _wht(right, "250", country="FR", linked_to=inc)], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)
    assert "FOREIGN_WHT_ABOVE_TREATY_RATE" not in _codes(gaps)


def test_b12_a_french_payment_in_lieu_is_not_given_the_dividend_rate(tmp_path):
    """The maintainer's probe: a French payment in lieu through the parser was credited
    at 12,8 % with status OK. The store has no treaty character for it; not credited."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver, isin="FR0000000AAA")
    inc = _income(stock, "1000", country="FR")
    inc.is_payment_in_lieu = True
    _, gaps = _not_credited([inc, _wht(stock, "128", country="FR", linked_to=inc)], resolver)
    assert "FOREIGN_WHT_RATE_NOT_VERIFIED" in _codes(gaps)


def test_b12_a_us_payment_in_lieu_keeps_the_us_rate(tmp_path):
    """[GT-CREDIT-028] branch A: the US payment in lieu is on the 15 % of Art. 10."""
    resolver = _resolver(tmp_path)
    stock = _stock(resolver)
    inc = _income(stock, "1000")
    inc.is_payment_in_lieu = True
    form, _ = _run([inc, _wht(stock, "300", linked_to=inc)], resolver)
    assert form.form_line_values[Z41] == Decimal("135.00")

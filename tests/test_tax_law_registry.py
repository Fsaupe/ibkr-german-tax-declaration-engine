"""
Law-as-data registry: the engine and the tests read the SAME
tables; entries carry citations; lookups outside validity are loud.

legal_basis: GT-INVSTG-020..024 (Teilfreistellung rates), GT-INVSTG-050 and
GT-INVSTG-053 (Basiszins), GT-ESTG20-035..037 and GT-FORM-010..012 (form
structure, cap repeal) — mirrored from reference/ (see registry module
docstring).
"""
import logging
import re

import pytest
from decimal import Decimal
from pathlib import Path

from src.domain.enums import FinancialEventType, InvestmentFundType
from src.domain.exceptions import ProcessingError
from src.tax_law import registry


class TestTeilfreistellung:
    def test_rates_match_invstg_20(self):
        """§20 Abs. 1/2/3 InvStG: 30/15/60/80; Sonstige/None -> 0."""
        r = registry.teilfreistellung_rate
        assert r(InvestmentFundType.AKTIENFONDS) == Decimal("0.30")
        assert r(InvestmentFundType.MISCHFONDS) == Decimal("0.15")
        assert r(InvestmentFundType.IMMOBILIENFONDS) == Decimal("0.60")
        assert r(InvestmentFundType.AUSLANDS_IMMOBILIENFONDS) == Decimal("0.80")
        assert r(InvestmentFundType.SONSTIGE_FONDS) == Decimal("0.00")
        assert r(None) == Decimal("0.00")

    def test_shim_delegates(self):
        from src.utils.tax_utils import get_teilfreistellung_rate_for_fund_type
        assert get_teilfreistellung_rate_for_fund_type(
            InvestmentFundType.AKTIENFONDS) == Decimal("0.30")


class TestFormYearRules:
    def test_cap_repealed_for_every_configured_year(self):
        """JStG 2024 abolished the €20k cap RETROACTIVELY for all open cases
        (§52 Abs. 28 EStG n.F.) — no year may apply it."""
        for year, rules in registry._FORM_RULES_BY_YEAR.items():
            assert rules.derivative_loss_cap_applies is False, year

    def test_2024_vs_2025_form_structure(self):
        r24, r25 = registry.get_form_rules(2024), registry.get_form_rules(2025)
        assert r24.separate_derivative_lines and not r25.separate_derivative_lines
        assert not r24.z19_subtracts_derivative_losses and r25.z19_subtracts_derivative_losses
        assert not r24.z22_includes_derivative_losses and r25.z22_includes_derivative_losses

    def test_pre_2024_years_use_2024_structure(self):
        """VZ 2021-2023 share the <=2024 form structure (earliest fallback)."""
        assert registry.get_form_rules(2023) == registry.get_form_rules(2024)

    def test_every_configured_year_2021_to_2023_matches_2024(self):
        """Verified against the official forms: 2021AnlKAP051, 2022, 2023 and
        2024 carry the same Zeilen 18-25 with the same Kennzahlen."""
        for year in (2021, 2022, 2023):
            assert registry.get_form_rules(year) == registry.get_form_rules(2024), year

    def test_years_before_the_earliest_verified_form_raise(self):
        """The VZ 2020 form has no Zeile 21 and no Zeile 24 (both 'frei'), so
        the 2021+ projection must not be carried backwards onto it."""
        for year in (2020, 2019, 2018):
            with pytest.raises(ProcessingError, match="earliest verified form year"):
                registry.get_form_rules(year)

    def test_future_years_carry_the_latest_structure_forward(self):
        """Forward-carry still applies (now announced by a loud warning, not
        silent): a form structure holds until a later year changes it, and next
        year's form is not published yet."""
        assert registry.get_form_rules(2027) == registry.get_form_rules(2025)

    def test_resolved_form_year_names_the_governing_year(self):
        assert registry.resolved_form_year(2024) == 2024   # explicit
        assert registry.resolved_form_year(2025) == 2025   # explicit
        assert registry.resolved_form_year(2023) == 2021   # carried forward
        assert registry.resolved_form_year(2027) == 2025   # carried forward

    def test_form_rules_are_carried_flags_only_unconfigured_years(self):
        assert registry.form_rules_are_carried(2024) is None
        assert registry.form_rules_are_carried(2025) is None
        assert registry.form_rules_are_carried(2023) == 2021
        assert registry.form_rules_are_carried(2027) == 2025

    def test_forward_carry_emits_one_loud_warning_naming_both_years(self, caplog):
        """The carried rules drive the DECLARED Z19/Z21/Z22/Z24 figures, so a
        forward-carry must not pass unnoticed. Deleting the warning turns this
        red; deduping keeps a multi-call run from repeating it."""
        registry._warned_carry_years.discard(2027)
        with caplog.at_level(logging.WARNING, logger="src.tax_law.registry"):
            registry.get_form_rules(2027)
            registry.get_form_rules(2027)  # second call is deduped
        banners = [r.getMessage() for r in caplog.records
                   if r.levelno == logging.WARNING and "forward-carry" in r.getMessage()]
        assert len(banners) == 1
        assert "VZ 2027" in banners[0] and "VZ 2025" in banners[0]

    def test_an_explicit_year_does_not_warn_of_a_carry(self, caplog):
        registry._warned_carry_years.discard(2025)
        with caplog.at_level(logging.WARNING, logger="src.tax_law.registry"):
            registry.get_form_rules(2025)
        assert not [r for r in caplog.records if "forward-carry" in r.getMessage()]

    def test_reporting_shim_reexports(self):
        from src.reporting.form_rules import get_form_rules, FormYearRules
        assert get_form_rules is registry.get_form_rules
        assert FormYearRules is registry.FormYearRules


class TestBasiszinsLookup:
    def test_known_year(self):
        assert registry.basiszins_pct(2024) == Decimal("2.29")

    def test_negative_years_present_not_gaps(self, caplog):
        """2021/2022 are COMPUTED zero-VP years (negative rate), not config gaps."""
        with caplog.at_level(logging.WARNING):
            assert registry.basiszins_pct(2021) == Decimal("-0.45")
        assert not any("No Basiszins" in r.message for r in caplog.records)

    def test_missing_year_inside_the_regime_is_loud(self, caplog):
        """A year >= 2018 that the table lacks is a real gap: no rate, no VP,
        and deemed income may be understated. WARNING."""
        with caplog.at_level(logging.INFO):
            assert registry.basiszins_pct(2030) is None
        assert any("No Basiszins" in r.message and r.levelname == "WARNING"
                   for r in caplog.records)

    def test_pre_regime_year_is_not_reported_as_a_gap(self, caplog):
        """Before 2018 there was no Vorabpauschale at all (§56 Abs. 1 S. 1
        InvStG), so the absence is correct and must not read as a missing rate."""
        with caplog.at_level(logging.INFO):
            assert registry.basiszins_pct(2017) is None
        assert not any(r.levelname == "WARNING" for r in caplog.records)
        assert any("InvStG 2018 regime" in r.message for r in caplog.records)

    def test_bewg_basiszins_values_are_not_in_the_table(self):
        """2016/2017 once carried 1.10%/0.59% — the §203 Abs. 2 BewG Basiszins
        for the vereinfachtes Ertragswertverfahren, a different statute. No
        §18 Abs. 4 InvStG rate exists for those years."""
        assert 2016 not in registry.BASISZINS_PCT
        assert 2017 not in registry.BASISZINS_PCT
        assert min(registry.BASISZINS_PCT) == registry.INVSTG_2018_FIRST_BASISZINS_YEAR == 2018


class TestBasiszinsReferenceConsistency:
    """The registry must equal the BMF table in the knowledge store, row for
    row. Parsed from the document — not a third hand-kept copy of the numbers,
    which could not detect the drift it exists to detect.
    Source: reference/bmf-guidance/basiszins-vorabpauschale.md."""

    REFERENCE_DOC = (Path(__file__).resolve().parent.parent
                     / "reference" / "bmf-guidance" / "basiszins-vorabpauschale.md")

    @staticmethod
    def _parse_published_table(text: str) -> dict[int, Decimal]:
        """Rows of the '## Published Basiszins Values' table:
        | 2024 | 2.29% | 02.01.2024 | ... |"""
        rows: dict[int, Decimal] = {}
        in_table = False
        for line in text.splitlines():
            if line.startswith("## Published Basiszins Values"):
                in_table = True
                continue
            if in_table and line.startswith("#"):
                break
            m = re.match(r"^\|\s*(\d{4})\s*\|\s*(-?\d+\.\d+)%\s*\|", line)
            if in_table and m:
                rows[int(m.group(1))] = Decimal(m.group(2))
        return rows

    def test_parser_finds_the_table(self):
        published = self._parse_published_table(self.REFERENCE_DOC.read_text(encoding="utf-8"))
        assert len(published) >= 9, f"table not parsed (got {published})"

    def test_registry_matches_the_reference_document(self):
        published = self._parse_published_table(self.REFERENCE_DOC.read_text(encoding="utf-8"))
        assert registry.BASISZINS_PCT == published, (
            "src/tax_law/registry.py and reference/bmf-guidance/"
            "basiszins-vorabpauschale.md disagree; the reference is authoritative"
        )

    def test_no_gap_inside_the_covered_range(self):
        years = sorted(registry.BASISZINS_PCT)
        assert years == list(range(years[0], years[-1] + 1)), (
            f"missing year(s) between {years[0]} and {years[-1]}: a gap silently "
            "skips that year's Vorabpauschale"
        )


class TestCreditableDividendRatesReferenceConsistency:
    """The per-year creditable dividend rates must equal the per-edition columns of the
    BZSt table in the knowledge store, year for year and state for state. Parsed from the
    document, so a year added to one side only is caught.
    Source: reference/bmf-guidance/bzst-anrechenbare-quellensteuer.md [GT-CREDIT-029]."""

    REFERENCE_DOC = (Path(__file__).resolve().parent.parent
                     / "reference" / "bmf-guidance" / "bzst-anrechenbare-quellensteuer.md")

    @staticmethod
    def _parse(text: str) -> dict[int, dict[str, Decimal]]:
        """| Frankreich | FR | 12,8 | 15 | 12,8 | 12,8 | 12,8 | 12,8 | pages |, under a
        header naming the editions as 'C 2023 | C 2024 | ...'."""
        years: list[int] = []
        rates: dict[int, dict[str, Decimal]] = {}
        for line in text.splitlines():
            if line.startswith("| Source state | Code |"):
                years = [int(y) for y in re.findall(r"C (\d{4})", line)]
                continue
            m = re.match(r"^\|[^|]+\|\s*([A-Z]{2})\s*\|[^|]+\|[^|]+\|(.*)$", line)
            if years and m:
                cells = [c.strip() for c in m.group(2).split("|")][:len(years)]
                for year, cell in zip(years, cells):
                    rates.setdefault(year, {})[m.group(1)] = (
                        Decimal(cell.replace(",", ".")) / 100)
        return rates

    def test_parser_finds_the_table(self):
        parsed = self._parse(self.REFERENCE_DOC.read_text(encoding="utf-8"))
        assert len(parsed) >= 4 and all(len(v) >= 7 for v in parsed.values()), parsed

    def test_registry_matches_the_reference_document(self):
        parsed = self._parse(self.REFERENCE_DOC.read_text(encoding="utf-8"))
        assert registry.CREDITABLE_DIVIDEND_RATES == parsed, (
            "src/tax_law/registry.py and reference/bmf-guidance/"
            "bzst-anrechenbare-quellensteuer.md disagree; the reference is authoritative")

    def test_an_unresearched_year_has_no_rate(self):
        year = max(registry.CREDITABLE_DIVIDEND_RATES) + 1
        assert not registry.creditable_dividend_rates_researched(year)
        assert registry.creditable_dividend_rate(
            year, "US", FinancialEventType.DIVIDEND_CASH) is None


class TestCreditableInterestRatesReferenceConsistency:
    """The per-year creditable interest rates must equal the per-edition D columns of
    the store's [GT-CREDIT-030] table.
    Source: reference/bmf-guidance/bzst-anrechenbare-quellensteuer.md."""

    REFERENCE_DOC = TestCreditableDividendRatesReferenceConsistency.REFERENCE_DOC

    @staticmethod
    def _parse(text: str) -> dict[int, dict[str, Decimal]]:
        years: list[int] = []
        rates: dict[int, dict[str, Decimal]] = {}
        for line in text.splitlines():
            if line.startswith("| Source state | Code |"):
                years = [int(y) for y in re.findall(r"D (\d{4})", line)]
                continue
            m = re.match(r"^\|[^|]+\|\s*([A-Z]{2})\s*\|[^|]+\|[^|]+\|(.*)$", line)
            if years and m:
                cells = [c.strip() for c in m.group(2).split("|")][:len(years)]
                for year, cell in zip(years, cells):
                    rates.setdefault(year, {})[m.group(1)] = (
                        Decimal(cell.replace(",", ".")) / 100)
        return rates

    def test_registry_matches_the_reference_document(self):
        parsed = self._parse(self.REFERENCE_DOC.read_text(encoding="utf-8"))
        assert len(parsed) >= 4, parsed
        assert registry.CREDITABLE_INTEREST_RATES == parsed

    def test_the_two_tables_cover_the_same_years(self):
        assert set(registry.CREDITABLE_INTEREST_RATES) == set(registry.CREDITABLE_DIVIDEND_RATES)


class TestCreditableRateGroundsReferenceConsistency:
    """The national rate and DBA ceiling the report prints beside each creditable rate
    must equal columns A a)/A b) (dividends) and B a)/B b) (interest) of the store's tables.
    Source: reference/bmf-guidance/bzst-anrechenbare-quellensteuer.md [GT-CREDIT-029], [GT-CREDIT-030]."""

    REFERENCE_DOC = TestCreditableDividendRatesReferenceConsistency.REFERENCE_DOC

    @staticmethod
    def _parse(text: str, column: str) -> dict[str, tuple[str, str]]:
        """| Frankreich | FR | 12,8 | 15 | ... under a header naming '<column> a) national'."""
        grounds: dict[str, tuple[str, str]] = {}
        in_table = False
        for line in text.splitlines():
            if line.startswith("| Source state | Code |"):
                in_table = f"| {column} a) national |" in line
                continue
            m = re.match(r"^\|[^|]+\|\s*([A-Z]{2})\s*\|([^|]+)\|([^|]+)\|", line)
            if in_table and m:
                grounds[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
            elif not line.startswith("|"):
                in_table = in_table and line.startswith("|---")
        return grounds

    def test_dividend_grounds_match_the_reference_document(self):
        parsed = self._parse(self.REFERENCE_DOC.read_text(encoding="utf-8"), "A")
        assert len(parsed) >= 7, parsed
        assert registry.CREDITABLE_DIVIDEND_GROUNDS == parsed

    def test_interest_grounds_match_the_reference_document(self):
        parsed = self._parse(self.REFERENCE_DOC.read_text(encoding="utf-8"), "B")
        assert parsed, parsed
        assert registry.CREDITABLE_INTEREST_GROUNDS == parsed

    def test_every_state_with_a_rate_has_its_grounds(self):
        dividend_states = {s for rates in registry.CREDITABLE_DIVIDEND_RATES.values() for s in rates}
        interest_states = {s for rates in registry.CREDITABLE_INTEREST_RATES.values() for s in rates}
        assert dividend_states == set(registry.CREDITABLE_DIVIDEND_GROUNDS)
        assert interest_states == set(registry.CREDITABLE_INTEREST_GROUNDS)

# src/tax_law/registry.py
"""
Law-as-data registry — the SINGLE home of year-parameterized German tax-law
values. Engine and tests read the SAME tables; every entry carries its
statutory citation; lookups outside an entry's validity are LOUD, never a
silent zero.

Layering, as it actually stands: the computation core emits year-agnostic
`TaxReportingCategory` totals, and the year-specific *branching* between form
structures happens only through `get_form_rules(tax_year)` defined here. That
is not the same as being the only Zeilen-aware layer — the category enum names
carry Zeilen semantics, and `console_reporter.py` / `pdf_generator.py` print
line numbers directly. Concentrating the branching here is the property to
preserve; single-point Zeilen knowledge is not yet true.

Sources of truth mirrored here (machine-readable side of `reference/`):
- Basiszins:        reference/bmf-guidance/basiszins-vorabpauschale.md (BStBl I)
- Teilfreistellung: reference/investment-tax-law/invstg-20-teilfreistellung.md
- Form structure:   reference/tax-law/estg-20-abs6-verlustverrechnung.md,
                    reference/tax-forms/anlage-kap-zeilen.md
`tests/test_tax_law_registry.py` pins registry <-> reference consistency.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.domain.enums import InvestmentFundType
from src.domain.exceptions import ProcessingError

logger = logging.getLogger(__name__)


# =============================================================================
# Basiszins (§18 Abs. 4 InvStG) — BMF-published, percent values
# =============================================================================
# Negative years (2021/2022) are deliberately PRESENT: a negative Basiszins is
# a computed zero Vorabpauschale, not a configuration gap.
# Citation: BMF Basiszins notices, BStBl I (per-year links in the reference doc).

# The series starts in 2018: the Vorabpauschale was introduced by the InvStG
# 2018, whose provisions "sind ab dem 1. Januar 2018 anzuwenden" (§56 Abs. 1
# Satz 1 InvStG). No §18 Abs. 4 InvStG Basiszins exists for 2016 or 2017 — the
# 1.10%/0.59% once listed for those years are the §203 Abs. 2 BewG Basiszins
# (a different statute); see the reference doc.
INVSTG_2018_FIRST_BASISZINS_YEAR = 2018

BASISZINS_PCT: dict[int, Decimal] = {
    2018: Decimal("0.87"),
    2019: Decimal("0.52"),
    2020: Decimal("0.07"),
    2021: Decimal("-0.45"),  # negative -> Basisertrag <= 0 -> no Vorabpauschale
    2022: Decimal("-0.05"),  # negative -> Basisertrag <= 0 -> no Vorabpauschale
    2023: Decimal("2.55"),
    2024: Decimal("2.29"),
    2025: Decimal("2.53"),
    2026: Decimal("3.20"),
}


def basiszins_pct(year: int) -> Optional[Decimal]:
    """BMF-published Basiszins for `year` in percent, or None if unavailable.

    Two ways to be absent, logged differently because they mean opposite things:

    - `year` predates the InvStG-2018 regime (§56 Abs. 1 S. 1 InvStG): there was
      no Vorabpauschale at all. INFO — nothing is being missed.
    - `year` is 2018 or later: a rate WAS published and the table lacks it.
      WARNING — skipping understates deemed income (§18 InvStG). Add the rate."""
    value = BASISZINS_PCT.get(year)
    if value is None:
        if year < INVSTG_2018_FIRST_BASISZINS_YEAR:
            logger.info(
                f"No Vorabpauschale for year {year}: the InvStG 2018 regime "
                f"applies from 1 January {INVSTG_2018_FIRST_BASISZINS_YEAR} "
                f"(§56 Abs. 1 Satz 1 InvStG), so no Basiszins was published."
            )
        else:
            logger.warning(
                f"No Basiszins in the tax-law registry for year {year} — SKIPPING "
                f"its Vorabpauschale computation. If funds were held through "
                f"{year} and the BMF-published Basiszins for that year was "
                f"positive, deemed income is being understated. Add the rate to "
                f"src/tax_law/registry.py (source: "
                f"reference/bmf-guidance/basiszins-vorabpauschale.md)."
            )
    return value


# =============================================================================
# Teilfreistellung (§20 InvStG) — private investors, units acquired >= 2018
# =============================================================================
# §20 Abs. 1 S. 1 (Aktienfonds 30%), Abs. 2 (Mischfonds 15%),
# Abs. 3 S. 1 Nr. 1 (Immobilienfonds 60%), Nr. 2 (Auslands-Immobilien 80%).
# Sonstige Fonds / unknown: no provision -> 0%.

TEILFREISTELLUNG_RATES: dict[InvestmentFundType, Decimal] = {
    InvestmentFundType.AKTIENFONDS: Decimal("0.30"),
    InvestmentFundType.MISCHFONDS: Decimal("0.15"),
    InvestmentFundType.IMMOBILIENFONDS: Decimal("0.60"),
    InvestmentFundType.AUSLANDS_IMMOBILIENFONDS: Decimal("0.80"),
}


def teilfreistellung_rate(fund_type: Optional[InvestmentFundType]) -> Decimal:
    """Teilfreistellung rate for a fund type (0 for Sonstige/None — no
    statutory provision, full amount taxable)."""
    if fund_type is None:
        return Decimal("0.00")
    return TEILFREISTELLUNG_RATES.get(fund_type, Decimal("0.00"))


# =============================================================================
# Anlage KAP form structure per assessment year (§20 Abs. 6 EStG)
# =============================================================================
# The €20k Termingeschäft loss cap (§20 Abs. 6 S. 5/6 a.F.) was abolished by
# JStG 2024 (BGBl. I 2024 Nr. 387). Its scope comes from the application rule:
# §52 Abs. 28 Satz 25 EStG n.F. (Termingeschäfte) and Satz 26 (Forderungs-
# ausfälle) each order that the a.F. sentence "ist auf alle offenen Fälle nicht
# mehr anzuwenden" — therefore derivative_loss_cap_applies is False for EVERY
# year: a return prepared today, including VZ 2021-2024, is not subject to it.
#
# Only the FORM STRUCTURE remains year-specific:
#   VZ <= 2024: derivative gains/losses declared separately on Z21/Z24; Z19
#               does not subtract derivative losses; Z22 excludes them.
#   VZ >= 2025: Z21/Z24 removed; derivative gains AND losses flow through Z19;
#               Z22 includes derivative losses with other non-stock losses.

@dataclass(frozen=True)
class FormYearRules:
    """Year-specific differences in the Anlage KAP form projection."""
    separate_derivative_lines: bool       # Z21/Z24 exist on the form
    derivative_loss_cap_applies: bool     # repealed retroactively: always False
    z19_subtracts_derivative_losses: bool
    z22_includes_derivative_losses: bool


# GT-FORM-020, reference/tax-forms/anlage-so-zeilen.md: independently checked
# annual taxpayer allocation lines, not the individual-disposal calculation.
_SECTION23_FORM_LINES = {2021: 48, 2022: 48, 2023: 54, 2024: 54, 2025: 58}


def _section23_form_source(tax_year: int) -> int:
    years = [year for year in _SECTION23_FORM_LINES if year <= tax_year]
    if not years:
        raise ProcessingError(
            f"No Anlage SO form rules for tax year {tax_year}: earliest verified "
            f"year is {min(_SECTION23_FORM_LINES)}; backward projection is not supported."
        )
    return max(years)


def section23_form_warning(tax_year: int) -> Optional[str]:
    """Visible notice for an unverified forward carry of the SO destination."""
    source = _section23_form_source(tax_year)
    if source == tax_year:
        return None
    return (
        f"ACHTUNG: Anlage SO fuer VZ {tax_year} ist UNGEPRUEFT. "
        f"Die Formularzuordnung wird aus VZ {source} uebernommen "
        f"(forward-carry); gegen das amtliche Formular fuer VZ {tax_year} pruefen."
    )


def get_section23_form_line(tax_year: int) -> int:
    """Annual §23 taxpayer allocation destination (GT-FORM-020)."""
    warning = section23_form_warning(tax_year)
    if warning:
        logger.warning(warning)
    return _SECTION23_FORM_LINES[_section23_form_source(tax_year)]


# Verified against the official form for each year (see the verification table in
# reference/tax-law/estg-20-abs6-verlustverrechnung.md). 2021 is the EARLIEST:
# on the VZ 2020 form (Formularstand 2020AnlKAP051) Zeilen 21 and 24 are printed
# "frei" and the word "Termingeschäfte" does not occur at all — the separate
# Termingeschäft lines were introduced with the VZ 2021 form, alongside the
# (since repealed) §20 Abs. 6 S. 5 restriction.
_FORM_RULES_BY_YEAR: dict[int, FormYearRules] = {
    2021: FormYearRules(          # 2021AnlKAP051; 2022/2023 identical, incl. Kennzahlen
        separate_derivative_lines=True,
        derivative_loss_cap_applies=False,  # JStG 2024 (§52 Abs. 28 S. 25)
        z19_subtracts_derivative_losses=False,
        z22_includes_derivative_losses=False,
    ),
    2024: FormYearRules(
        separate_derivative_lines=True,
        derivative_loss_cap_applies=False,  # JStG 2024 (§52 Abs. 28 S. 25)
        z19_subtracts_derivative_losses=False,
        z22_includes_derivative_losses=False,
    ),
    2025: FormYearRules(
        separate_derivative_lines=False,
        derivative_loss_cap_applies=False,
        z19_subtracts_derivative_losses=True,
        z22_includes_derivative_losses=True,
    ),
}


# GT-FORM-012 records independent verification of the 2022 and 2023 forms,
# including their identical Kennzahlen. Reusing the 2021 rule entry for those
# years is verified reuse, not an assumption about an unpublished form.
_VERIFIED_FORM_YEAR_SOURCES: dict[int, int] = {2022: 2021, 2023: 2021}

# Unverified forward-carry is warned once per year, not per call (get_form_rules is called
# several times a run). Reset in tests that assert the warning.
_warned_carry_years: set[int] = set()


def resolved_form_year(tax_year: int) -> int:
    """The year whose FormYearRules govern `tax_year`.

    The year itself when it is explicitly configured, otherwise the nearest
    EARLIER configured year: a form structure stays in force until a later year
    changes it. A year before the earliest configured one raises — carrying one
    BACKWARD is unsound (the VZ 2020 form has no Zeile 21 and no Zeile 24 at
    all, both printed "frei"), so it is refused rather than guessed.
    See reference/tax-law/estg-20-abs6-verlustverrechnung.md."""
    if tax_year in _FORM_RULES_BY_YEAR:
        return tax_year

    available_years = sorted(_FORM_RULES_BY_YEAR.keys())
    fallback_year = None
    for year in available_years:
        if year <= tax_year:
            fallback_year = year
    if fallback_year is not None:
        return fallback_year

    earliest = available_years[0]
    raise ProcessingError(
        f"No Anlage KAP form rules for tax year {tax_year}: the earliest "
        f"verified form year is {earliest}. Earlier forms differ structurally "
        f"(the VZ 2020 form has no Zeile 21 and no Zeile 24 — both are 'frei'), "
        f"so the {earliest} projection must not be applied backwards. Add a "
        f"verified entry to src/tax_law/registry.py, checked against that "
        f"year's official form (reference/tax-law/"
        f"estg-20-abs6-verlustverrechnung.md)."
    )


def form_rules_are_carried(tax_year: int) -> Optional[int]:
    """The source year when `tax_year`'s rules are carried FORWARD from an
    earlier year (i.e. `tax_year` has no explicit entry), else None.

    This describes rule storage, not verification: GT-FORM-012 independently
    verifies years that share an earlier entry. Reports use
    unverified_form_rules_source() to decide whether to show a warning."""
    source = resolved_form_year(tax_year)
    return source if source != tax_year else None


def unverified_form_rules_source(tax_year: int) -> Optional[int]:
    """Source year of an unverified carry, or None for verified form rules.

    An explicit entry or a verified source mapping establishes verification.
    Require the mapped source to match the actual lookup, so later registry
    changes cannot silently reuse evidence for a different rule entry.
    """
    source = form_rules_are_carried(tax_year)
    if source is None or _VERIFIED_FORM_YEAR_SOURCES.get(tax_year) == source:
        return None
    return source


def get_form_rules(tax_year: int) -> FormYearRules:
    """Form rules for an assessment year (see resolved_form_year for how the
    year is chosen; a year before the earliest configured one raises).

    An unverified forward-carry is deliberately NOT silent. It drives the declared
    Z19/Z21/Z22/Z24 figures (src/engine/loss_offsetting.py), so it emits a
    prominent WARNING (once per year) and the console/PDF reports print an
    ACHTUNG banner via unverified_form_rules_source(). Verified reuse of an
    earlier entry needs no warning. For an unverified year the figures compute on
    the carried year's UNVERIFIED structure, to be checked against that year's
    official form. See reference/tax-law/estg-20-abs6-verlustverrechnung.md."""
    source = resolved_form_year(tax_year)
    if unverified_form_rules_source(tax_year) is not None and tax_year not in _warned_carry_years:
        _warned_carry_years.add(tax_year)
        bar = "=" * 74
        logger.warning(
            "\n%s\n"
            "  ACHTUNG: Keine geprueften Anlage-KAP-Formularregeln fuer VZ %d.\n"
            "  Es werden die Regeln von VZ %d uebernommen (forward-carry).\n"
            "  Die erklaerten Figuren Z19/Z21/Z22/Z24 und ihre Formularzuordnung\n"
            "  beruhen damit auf UNGEPRUEFTEN Annahmen und muessen gegen das\n"
            "  amtliche Formular fuer VZ %d geprueft werden. Fuegen Sie einen\n"
            "  geprueften Eintrag in src/tax_law/registry.py hinzu.\n"
            "%s",
            bar, tax_year, source, tax_year, bar,
        )
    return _FORM_RULES_BY_YEAR[source]

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
- Creditable foreign withholding (dividends, interest): reference/bmf-guidance/bzst-anrechenbare-quellensteuer.md
`tests/test_tax_law_registry.py` pins registry <-> reference consistency.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.domain.enums import AssetCategory, FinancialEventType, InvestmentFundType
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
# Creditable foreign withholding on dividends (§32d Abs. 5 EStG) — BZSt column C
# =============================================================================
# [GT-CREDIT-029]: the BZSt table "Anrechenbarkeit der Quellensteuer auf Dividenden
# und Zinsen", one edition per year, each stating the law at 1 January. A year's rates
# come from THAT year's edition only. A year with no entry has no rates — nothing is
# carried from a neighbouring year, even where the editions agree; research the
# edition and add the year. Fractions, not percent.
#
# US ([GT-CREDIT-027]): the 15 % holds only for a RIC dividend with no exempt part and a
# REIT dividend whose holder meets Art. 10 Abs. 4 Satz 3. Neither is in the export; the
# conditions are checked against the taxpayer's stated answers
# (src/tax_law/withholding_conditions.py), and without them the rate does not apply.

CREDITABLE_DIVIDEND_RATES: dict[int, dict[str, Decimal]] = {
    2023: {"US": Decimal("0.15"), "FR": Decimal("0.128"), "JP": Decimal("0.15"),
           "CA": Decimal("0.15"), "KR": Decimal("0.15"), "NL": Decimal("0.15"),
           "TW": Decimal("0.10")},
    2024: {"US": Decimal("0.15"), "FR": Decimal("0.128"), "JP": Decimal("0.15"),
           "CA": Decimal("0.15"), "KR": Decimal("0.15"), "NL": Decimal("0.15"),
           "TW": Decimal("0.10")},
    2025: {"US": Decimal("0.15"), "FR": Decimal("0.128"), "JP": Decimal("0.15"),
           "CA": Decimal("0.15"), "KR": Decimal("0.15"), "NL": Decimal("0.15"),
           "TW": Decimal("0.10")},
    2026: {"US": Decimal("0.15"), "FR": Decimal("0.128"), "JP": Decimal("0.15"),
           "CA": Decimal("0.15"), "KR": Decimal("0.15"), "NL": Decimal("0.15"),
           "TW": Decimal("0.10")},
}

# The income kinds a state's dividend rate governs. The table's "Dividenden" are
# distributions of Kapitalgesellschaften, so share dividends only; the US treaty puts a
# RIC's distribution on the dividend rate too (Art. 10 Abs. 4 Satz 2).
_SHARE_DIVIDEND = frozenset({FinancialEventType.DIVIDEND_CASH})
CREDITABLE_DIVIDEND_KINDS: dict[str, frozenset] = {
    "US": frozenset({FinancialEventType.DIVIDEND_CASH, FinancialEventType.DISTRIBUTION_FUND}),
    "FR": _SHARE_DIVIDEND, "JP": _SHARE_DIVIDEND, "CA": _SHARE_DIVIDEND,
    "KR": _SHARE_DIVIDEND, "NL": _SHARE_DIVIDEND, "TW": _SHARE_DIVIDEND,
}

# The instrument class each dividend kind requires. Column C holds for a dividend on an
# ordinary share; the column-F notes take a right or share whose payment the payer deducts
# out of it ([GT-CREDIT-029]), so an instrument not classified as an Aktie gets no rate. A
# fund distribution needs a fund (the US RIC route).
_KIND_ASSET = {
    FinancialEventType.DIVIDEND_CASH: AssetCategory.STOCK,
    FinancialEventType.DISTRIBUTION_FUND: AssetCategory.INVESTMENT_FUND,
}
# The states for which the store establishes a payment in lieu's treaty character as a
# dividend ([GT-CREDIT-028], via DBA-USA Art. 10 Abs. 5 and US law). For any other state
# the payment has no rate.
PAYMENT_IN_LIEU_STATES = frozenset({"US"})


# [GT-CREDIT-030]: column D, the creditable interest rate, per edition likewise. Which
# state levied an interest withholding is not in the export; the parser takes it from
# the taxpayer's configuration (the broker entity's country).
CREDITABLE_INTEREST_RATES: dict[int, dict[str, Decimal]] = {
    2023: {"IE": Decimal("0")},
    2024: {"IE": Decimal("0")},
    2025: {"IE": Decimal("0")},
    2026: {"IE": Decimal("0")},
}


def creditable_rates_researched(tax_year: int) -> bool:
    """Whether the BZSt edition for `tax_year` has been read for dividends and interest."""
    return (creditable_dividend_rates_researched(tax_year)
            and tax_year in CREDITABLE_INTEREST_RATES)


def creditable_rate(tax_year: int, source_state: Optional[str],
                    income_kind: FinancialEventType,
                    asset_category: Optional[AssetCategory] = None,
                    payment_in_lieu: bool = False) -> Optional[Decimal]:
    """The creditable rate for a state and income kind in `tax_year`: the interest rate
    for interest, the dividend rate otherwise -- and a dividend rate only for the
    instrument class it covers, and for a payment in lieu only where the store gives it
    a treaty character. None where not in the table; never another year's."""
    if income_kind is FinancialEventType.INTEREST_RECEIVED:
        if not source_state:
            return None
        return CREDITABLE_INTEREST_RATES.get(tax_year, {}).get(source_state.strip().upper())
    if asset_category is not _KIND_ASSET.get(income_kind):
        return None
    if payment_in_lieu and (source_state or "").strip().upper() not in PAYMENT_IN_LIEU_STATES:
        return None
    return creditable_dividend_rate(tax_year, source_state, income_kind)


def creditable_dividend_rates_researched(tax_year: int) -> bool:
    """Whether the BZSt edition for `tax_year` has been read into the table."""
    return tax_year in CREDITABLE_DIVIDEND_RATES


def creditable_dividend_rate(tax_year: int, source_state: Optional[str],
                             income_kind: FinancialEventType) -> Optional[Decimal]:
    """The creditable rate for a state and income kind in `tax_year`, or None where the
    year's edition, the state or the kind is not in the table. Never another year's."""
    if not source_state:
        return None
    state = source_state.strip().upper()
    rate = CREDITABLE_DIVIDEND_RATES.get(tax_year, {}).get(state)
    if rate is None or income_kind not in CREDITABLE_DIVIDEND_KINDS.get(state, frozenset()):
        return None
    return rate


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

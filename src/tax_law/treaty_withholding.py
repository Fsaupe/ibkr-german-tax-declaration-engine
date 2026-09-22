# src/tax_law/treaty_withholding.py
"""Is a foreign withholding row creditable in full, or only up to the treaty rate?

§ 32d Abs. 5 Satz 1 credits foreign tax *um einen entstandenen Ermaessigungsanspruch
gekuerzt* — the withheld tax reduced by what can be reclaimed in the source state under
its own law or a DBA (reference/tax-law/estg-32d-abgeltungsteuer.md [GT-CREDIT-026];
BMF Rn. 207a, BZSt Erlaeuterungen). For a US dividend, and a payment in lieu on branch A,
the two grounds coincide: the US keeps 15 % and refunds the rest
(reference/tax-law/dba-usa.md [GT-CREDIT-027], [GT-CREDIT-028], Art. 10 Abs. 2 b /
Abs. 4 Satz 2). Anything withheld above that is not creditable in Germany; it is claimed
back from the IRS. Branch B (Art. 21), where the two grounds diverge, is open (Q22) and
not reached: the parser takes branch A ([GT-INVSTG-059]).

This module supplies the treaty rate and the per-row decision. It does NOT cap silently
and it does NOT default an unknown source state: only source states with a rate in the
store are checked, and a row it cannot verify keeps the amount that was actually
withheld while telling the caller to flag it. The caller (loss_offsetting) routes the
flags through the data-gap channel and never past it.

Scope, deliberately narrow (issue #78): dividends only, US only. Measured 2026-09-22: 28
dividend/PIL withholding rows VZ 2023-2025 carry the "- US TAX" suffix, 0 of them above
15 % + 1 cent of their paired income; the guard exists for the future case (a lapsed
W-8BEN puts every US row at 30 %). The source state is read from `source_country_code`
(IssuerCountryCode), which is blank on 7 of those 28 (all VZ 2023): they are reported
rate-not-verified and kept as withheld, never guessed. Interest treaty
rates and every source state other than the US are not in the store, so a row of that
kind is reported as rate-not-verified, not capped. Adding another state or interest is a
store extension plus a table row, not a code change here.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

from src.domain.enums import FinancialEventType
from src.domain.events import CashFlowEvent, WithholdingTaxEvent

# [GT-CREDIT-027] DBA D-USA Art. 10 Abs. 2 Buchst. b (Abs. 4 Satz 2 for a RIC/fund):
# 15 % of the gross on a dividend to a German private investor. Dividends only — the
# BZSt table gives US interest 0 anrechenbar, but interest treaty rates are not carried
# in the store, so interest is not checked here (reported rate-not-verified instead).
_TREATY_DIVIDEND_RATES = {
    "US": Decimal("0.15"),
}

# The event kinds whose foreign withholding the dividend rate governs. A payment in lieu
# reaches this set as its instrument's own income on branch A ([GT-INVSTG-059]):
# DISTRIBUTION_FUND for a fund, DIVIDEND_CASH for a share.
#
# Assumed, not checked: the dividend is not an exempt RIC dividend. [GT-CREDIT-027]'s
# 15 % holds *falls keine Befreiung*; where the exemption applies nothing is creditable,
# and this table would still let 15 % through. Nothing in the export marks a RIC
# exemption. Measured 2026-09-22: of the 28 US-suffixed withholding rows VZ 2023-2025,
# 0 are paired to income described as exempt.
_DIVIDEND_LIKE = frozenset({
    FinancialEventType.DIVIDEND_CASH,
    FinancialEventType.DISTRIBUTION_FUND,
})

_CENT = Decimal("0.01")


class WithholdingStatus(Enum):
    OK = "OK"                              # at or below the treaty rate; credit in full
    ABOVE_TREATY_RATE = "ABOVE_TREATY_RATE"  # over-withheld; credit capped, excess is an IRS matter
    RATE_NOT_VERIFIED = "RATE_NOT_VERIFIED"  # no treaty rate in the store for this row
    UNLINKED = "UNLINKED"                  # no income row to measure the rate against


@dataclass(frozen=True)
class WithholdingAssessment:
    status: WithholdingStatus
    creditable_eur: Decimal      # what belongs on Zeile 41 for this row
    withheld_eur: Decimal        # what was actually withheld
    source_state: Optional[str]  # the taxing authority, "" if the broker gave none
    treaty_rate: Optional[Decimal] = None

    @property
    def excess_eur(self) -> Decimal:
        return (self.withheld_eur - self.creditable_eur).quantize(_CENT, rounding=ROUND_HALF_UP)


def treaty_dividend_rate(source_state: Optional[str]) -> Optional[Decimal]:
    """The creditable dividend rate for a source state, or None if the store has none."""
    if not source_state:
        return None
    return _TREATY_DIVIDEND_RATES.get(source_state.strip().upper())


def assess_withholding(wht: WithholdingTaxEvent,
                       income_event: Optional[CashFlowEvent]) -> WithholdingAssessment:
    """Decide the creditable amount for one foreign (non-German-KESt) withholding row.

    The over-withholding test is done in the row's own currency and to the cent, so a
    15 % withholding rounded up on a sub-unit gross is not read as an over-withholding
    (issue #78 research: those exact cent roundings are the real off-rate rows). The
    amount put on Zeile 41 stays in EUR, and is the withheld tax's own EUR value scaled
    down to the treaty share: the Ermaessigungsanspruch reduces that tax
    ([GT-CREDIT-026]), so no second conversion (the income row's) enters.
    """
    withheld_eur = _abs(wht.gross_amount_eur)
    state = (wht.source_country_code or "").strip().upper()

    if income_event is None:
        return WithholdingAssessment(WithholdingStatus.UNLINKED, withheld_eur, withheld_eur, state or None)

    rate = treaty_dividend_rate(state)
    if rate is None or income_event.event_type not in _DIVIDEND_LIKE:
        # No treaty rate in the store for this (state, income kind): keep what was
        # withheld, and let the caller flag it. Never default to a rate.
        return WithholdingAssessment(WithholdingStatus.RATE_NOT_VERIFIED, withheld_eur, withheld_eur, state or None)

    income_foreign = _abs(income_event.gross_amount_foreign_currency)
    withheld_foreign = _abs(wht.gross_amount_foreign_currency)
    if income_foreign is None or income_foreign <= 0 or withheld_foreign is None:
        return WithholdingAssessment(WithholdingStatus.RATE_NOT_VERIFIED, withheld_eur, withheld_eur, state or None)

    treaty_tax_foreign = (rate * income_foreign).quantize(_CENT, rounding=ROUND_HALF_UP)
    if withheld_foreign - treaty_tax_foreign > _CENT:
        creditable_eur = (withheld_eur * treaty_tax_foreign / withheld_foreign).quantize(
            _CENT, rounding=ROUND_HALF_UP)
        return WithholdingAssessment(
            WithholdingStatus.ABOVE_TREATY_RATE, creditable_eur, withheld_eur, state, rate)

    return WithholdingAssessment(WithholdingStatus.OK, withheld_eur, withheld_eur, state, rate)


def _abs(value: Optional[Decimal]) -> Optional[Decimal]:
    return value.copy_abs() if value is not None else None

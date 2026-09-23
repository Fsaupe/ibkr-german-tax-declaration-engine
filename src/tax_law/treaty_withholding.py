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

This module supplies the treaty rate and the decision for all the rows on one income. It does NOT cap silently
and it does NOT default an unknown source state: only source states with a rate in the
store are checked, and a row it cannot verify keeps the amount that was actually
withheld while telling the caller to flag it. The caller (loss_offsetting) routes the
flags through the data-gap channel and never past it.

Scope (issue #78): dividends only. The rates are per assessment year, from that year's
BZSt edition ([GT-CREDIT-029]), held in `src/tax_law/registry.py`; a year whose edition
has not been read has no rates and every row is reported, never given another year's
rate. The US rate covers a US fund's distribution too (the treaty covers RICs); the
others cover share dividends only -- the table's "Dividenden" are distributions of
Kapitalgesellschaften. Measured 2026-09-22: 28 dividend/PIL withholding
rows VZ 2023-2025 carry the "- US TAX" suffix, 0 of them above 15 % + 1 cent of their
paired income. The source state is read from `source_country_code` (IssuerCountryCode),
which is blank on 11 dividend/PIL withholding rows, all VZ 2023 (7 US, 3 CA, 1 FR by
their suffix): they are reported rate-not-verified and kept as withheld, never guessed.
Interest rates and every other source state are not in the store, so such a row is
reported as rate-not-verified, not capped. Adding another state or interest is a store
extension plus a table row, not a code change here.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional

from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from src.tax_law.registry import creditable_dividend_rate, creditable_dividend_rates_researched

_CENT = Decimal("0.01")


class WithholdingStatus(Enum):
    OK = "OK"                              # at or below the treaty rate; credit in full
    ABOVE_TREATY_RATE = "ABOVE_TREATY_RATE"  # over-withheld; credit capped, excess reclaimable in the source state
    RATE_NOT_VERIFIED = "RATE_NOT_VERIFIED"  # no creditable rate in the store for this row
    RATE_YEAR_NOT_RESEARCHED = "RATE_YEAR_NOT_RESEARCHED"  # no rates read for this tax year at all
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


def assess_withholdings(whts: List[WithholdingTaxEvent],
                        income_event: Optional[CashFlowEvent],
                        tax_year: int) -> List[WithholdingAssessment]:
    """Decide the creditable amount of every foreign (non-German-KESt) withholding row
    linked to one income, one assessment per row in the order given.

    The treaty limits all the tax on one dividend against that dividend's gross
    ([GT-CREDIT-027], Art. 10 Abs. 2), so the rows are measured together: their sum
    against the treaty share of the income. The over-withholding test is done in the
    rows' own currency and to the cent, so a 15 % withholding rounded up on a sub-unit
    gross is not read as an over-withholding (issue #78 research: those exact cent
    roundings are the real off-rate rows). The amount put on Zeile 41 stays in EUR, and
    is each row's own EUR value scaled down to the treaty share: the
    Ermaessigungsanspruch reduces that tax ([GT-CREDIT-026]), so no second conversion
    (the income row's) enters.
    """
    withheld = [_abs(w.gross_amount_eur) for w in whts]
    states = [(w.source_country_code or "").strip().upper() for w in whts]

    def _each(status, rate=None, creditable=None):
        return [WithholdingAssessment(status, creditable[i] if creditable else withheld[i],
                                      withheld[i], states[i] or None, rate)
                for i in range(len(whts))]

    if income_event is None:
        return _each(WithholdingStatus.UNLINKED)
    if not creditable_dividend_rates_researched(tax_year):
        return _each(WithholdingStatus.RATE_YEAR_NOT_RESEARCHED)

    rates = {creditable_dividend_rate(tax_year, state, income_event.event_type) for state in states}
    rate = rates.pop() if len(rates) == 1 else None
    if rate is None:
        # No treaty rate in the store for this (state, income kind), or rows naming
        # different states: keep what was withheld, and let the caller flag it. Never
        # default to a rate.
        return _each(WithholdingStatus.RATE_NOT_VERIFIED)

    income_foreign = _abs(income_event.gross_amount_foreign_currency)
    withheld_foreign = [_abs(w.gross_amount_foreign_currency) for w in whts]
    if income_foreign is None or income_foreign <= 0 or any(v is None for v in withheld_foreign):
        return _each(WithholdingStatus.RATE_NOT_VERIFIED)

    total_foreign = sum(withheld_foreign, Decimal("0"))
    treaty_tax_foreign = (rate * income_foreign).quantize(_CENT, rounding=ROUND_HALF_UP)
    if total_foreign - treaty_tax_foreign > _CENT:
        creditable = [(withheld[i] * treaty_tax_foreign / total_foreign).quantize(_CENT, rounding=ROUND_HALF_UP)
                      for i in range(len(whts))]
        return _each(WithholdingStatus.ABOVE_TREATY_RATE, rate, creditable)

    return _each(WithholdingStatus.OK, rate)


def _abs(value: Optional[Decimal]) -> Optional[Decimal]:
    return value.copy_abs() if value is not None else None

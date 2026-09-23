# src/tax_law/treaty_withholding.py
"""Is a foreign withholding row creditable in full, or only up to the treaty rate?

§ 32d Abs. 5 Satz 1 credits foreign tax *um einen entstandenen Ermaessigungsanspruch
gekuerzt* — the withheld tax reduced by what can be reclaimed in the source state under
its own law or a DBA (reference/tax-law/estg-32d-abgeltungsteuer.md [GT-CREDIT-026];
BMF Rn. 207a, BZSt Erlaeuterungen). For a US dividend, and a payment in lieu on branch A,
the two grounds coincide: the US keeps 15 % and refunds the rest
(reference/tax-law/dba-usa.md [GT-CREDIT-027], [GT-CREDIT-028], Art. 10 Abs. 2 b /
Abs. 4 Satz 2; a RIC's only where it reported no part as other than an ordinary dividend,
a REIT's only under the holding conditions of Abs. 4 Satz 3 -- facts the taxpayer states,
src/tax_law/withholding_conditions.py). Anything withheld above that is not creditable in
Germany; it is claimed back from the IRS. Branch B (Art. 21), where the US does not apply the treaty's allocation, is open (Q23) and
not reached: the parser takes branch A ([GT-INVSTG-059]).

This module supplies the treaty rate and the decision for all the rows on one income. It does NOT cap silently
and it does NOT default an unknown source state: only source states with a rate in the
store are checked. A row it cannot verify is not credited: it gets no creditable amount,
and the caller (loss_offsetting) lists it as unresolved, with the reason, while the rest
of the declaration continues (maintainer's review of PR #102: an unresolved credit may be
left unclaimed, never claimed under a warning). Not crediting it is a reporting decision,
not a finding that nothing is creditable or that the tax is refundable abroad.

Scope (issue #78): dividends, and interest where the store has a rate (Irland, 0 %:
[GT-CREDIT-030]). The rates are per assessment year, from that year's
BZSt edition ([GT-CREDIT-029]), held in `src/tax_law/registry.py`; a year whose edition
has not been read has no rates and every row is unresolved, never given another year's
rate; likewise a US row in a year for which the store does not state the US law the 15 %
turns on (`registry.US_CONDITIONS_STATED_YEARS`). The US rate covers a US fund's distribution too (the treaty covers RICs); the
others cover share dividends only -- the table's "Dividenden" are distributions of
Kapitalgesellschaften. Measured 2026-09-22: 28 dividend/PIL withholding
rows VZ 2023-2025 carry the "- US TAX" suffix, 0 of them above 15 % + 1 cent of their
paired income. The source state is read from `source_country_code`: IssuerCountryCode,
or where that is blank (11 dividend/PIL withholding rows, all VZ 2023) the broker's
"- XX Tax" suffix, filled in by the parser. A row with neither is
rate-not-verified, never guessed. Every other source state, and interest from a state without a rate, are not in the
store, so such a row is rate-not-verified and unresolved, not capped. Adding another state or interest is a store
extension plus a table row, not a code change here.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional

from src.domain.enums import AssetCategory
from src.domain.events import CashFlowEvent, WithholdingTaxEvent
from src.tax_law.registry import US_CONDITIONS_STATED_YEARS, creditable_rate, creditable_rates_researched
from src.tax_law.withholding_conditions import Verdict, verdict

_CENT = Decimal("0.01")


class WithholdingStatus(Enum):
    OK = "OK"                              # at or below the treaty rate; credit in full
    ABOVE_TREATY_RATE = "ABOVE_TREATY_RATE"  # over-withheld; credit capped, excess reclaimable in the source state
    RATE_NOT_VERIFIED = "RATE_NOT_VERIFIED"  # no creditable rate in the store for this row
    RATE_YEAR_NOT_RESEARCHED = "RATE_YEAR_NOT_RESEARCHED"  # no rates read for this tax year at all
    UNLINKED = "UNLINKED"                  # no income row to measure the rate against
    CONDITIONS_YEAR_NOT_RESEARCHED = "CONDITIONS_YEAR_NOT_RESEARCHED"  # the law the rate's conditions rest on is not stated for the year
    FACTS_UNANSWERED = "FACTS_UNANSWERED"  # the rate depends on a fact the taxpayer has not stated
    CONDITION_UNRESOLVED = "CONDITION_UNRESOLVED"  # stated, and the store does not settle the rate under the answers


# The statuses with no supported creditable amount: the row is not credited and is
# listed as unresolved.
UNSUPPORTED = frozenset({WithholdingStatus.RATE_NOT_VERIFIED,
                         WithholdingStatus.RATE_YEAR_NOT_RESEARCHED,
                         WithholdingStatus.UNLINKED,
                         WithholdingStatus.CONDITIONS_YEAR_NOT_RESEARCHED,
                         WithholdingStatus.FACTS_UNANSWERED,
                         WithholdingStatus.CONDITION_UNRESOLVED})


@dataclass(frozen=True)
class WithholdingAssessment:
    status: WithholdingStatus
    creditable_eur: Optional[Decimal]  # what belongs on Zeile 41 for this row; None where unsupported
    withheld_eur: Decimal        # what was actually withheld
    source_state: Optional[str]  # the taxing authority, "" if the broker gave none
    treaty_rate: Optional[Decimal] = None
    reason: str = ""             # for FACTS_UNANSWERED / CONDITION_UNRESOLVED: what is open

    @property
    def excess_eur(self) -> Decimal:
        return (self.withheld_eur - self.creditable_eur).quantize(_CENT, rounding=ROUND_HALF_UP)


def assess_withholdings(whts: List[WithholdingTaxEvent],
                        income_event: Optional[CashFlowEvent],
                        tax_year: int,
                        income_asset_category: Optional[AssetCategory] = None,
                        facts: Optional[Dict[str, bool]] = None) -> List[WithholdingAssessment]:
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

    def _each(status, rate=None, creditable=None, reason=""):
        return [WithholdingAssessment(status, creditable[i] if creditable else None,
                                      withheld[i], states[i] or None, rate, reason)
                for i in range(len(whts))]

    if income_event is None:
        return _each(WithholdingStatus.UNLINKED)
    if not creditable_rates_researched(tax_year):
        return _each(WithholdingStatus.RATE_YEAR_NOT_RESEARCHED)

    if len(set(states)) != 1:
        # One dividend has one source state; rows naming different states cannot all be
        # its tax, even where their rates agree. Not credited.
        return _each(WithholdingStatus.RATE_NOT_VERIFIED)
    rate = creditable_rate(tax_year, states[0], income_event.event_type, income_asset_category,
                           income_event.is_payment_in_lieu)
    if rate is None:
        # No treaty rate in the store for this (state, income kind): not credited.
        # Never default to a rate.
        return _each(WithholdingStatus.RATE_NOT_VERIFIED)

    # The US 15 % turns on US law the store states for some years only ([GT-CREDIT-027],
    # applicable years); the BZSt edition's rate alone does not establish it.
    if states[0] == "US" and tax_year not in US_CONDITIONS_STATED_YEARS:
        return _each(WithholdingStatus.CONDITIONS_YEAR_NOT_RESEARCHED)
    # The rate holds only where its conditions do ([GT-CREDIT-027], [GT-CREDIT-031]):
    # facts the export does not carry, stated by the taxpayer per instrument and year.
    met, reason = verdict(states[0], income_asset_category, facts)
    if met is Verdict.UNANSWERED:
        return _each(WithholdingStatus.FACTS_UNANSWERED, reason=reason)
    if met is Verdict.UNRESOLVED:
        return _each(WithholdingStatus.CONDITION_UNRESOLVED, reason=reason)

    income_foreign = _abs(income_event.gross_amount_foreign_currency)
    withheld_foreign = [_abs(w.gross_amount_foreign_currency) for w in whts]
    if income_foreign is None or income_foreign <= 0 or any(v is None for v in withheld_foreign):
        return _each(WithholdingStatus.RATE_NOT_VERIFIED)

    total_foreign = sum(withheld_foreign, Decimal("0"))
    treaty_tax_foreign = (rate * income_foreign).quantize(_CENT, rounding=ROUND_HALF_UP)
    # The cent absorbs a positive rate rounded up on a sub-unit gross; at a 0 % rate
    # there is nothing to round, and any amount withheld is above it.
    tolerance = _CENT if rate > 0 else Decimal("0")
    if total_foreign - treaty_tax_foreign > tolerance:
        creditable = [(withheld[i] * treaty_tax_foreign / total_foreign).quantize(_CENT, rounding=ROUND_HALF_UP)
                      for i in range(len(whts))]
        return _each(WithholdingStatus.ABOVE_TREATY_RATE, rate, creditable)

    return _each(WithholdingStatus.OK, rate, withheld)


def _abs(value: Optional[Decimal]) -> Optional[Decimal]:
    return value.copy_abs() if value is not None else None

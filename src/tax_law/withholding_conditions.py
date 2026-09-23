# src/tax_law/withholding_conditions.py
"""The facts a creditable rate is conditional on, which no export contains.

A rate in `registry.CREDITABLE_DIVIDEND_RATES` holds only where the conditions the
store attaches to it are met. For a US payer they are facts of the individual payer and
year ([GT-CREDIT-027]):

- a US fund (RIC): the 15 % holds *"falls keine Befreiung"*. The exempt part of a RIC
  dividend is whatever part the RIC reports as an interest-related or short-term
  capital gain dividend (26 U.S.C. § 871(k)); tax withheld on it is wholly an
  Ermaessigungsanspruch ([GT-CREDIT-026]).
- a US share: a REIT's dividend is on the 15 % only if the holder meets Art. 10 Abs. 4
  Satz 3 -- for a natural person, not more than 10 % of the REIT. REIT status is held per
  taxable year (§ 856(c)(1)).

The facts come from the taxpayer, per instrument and year (src/processing/withholding_facts.py).
An unanswered question gives no rate; an answer under which the condition fails gives no
rate either, since the store then states none this engine applies. Both stop the run.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.domain.enums import AssetCategory


@dataclass(frozen=True)
class Question:
    key: str
    text: str


US_RIC_EXEMPT_PART = Question(
    "us_ric_exempt_part",
    "Hat der Fonds einen Teil seiner Ausschüttungen dieses Jahres als 'interest-related dividend' "
    "oder 'short-term capital gain dividend' ausgewiesen (Form 1042-S; 26 U.S.C. § 871(k))?")
US_REIT = Question(
    "us_reit",
    "War der Zahler in diesem Jahr ein Real Estate Investment Trust (REIT) der Vereinigten Staaten "
    "(26 U.S.C. § 856(c)(1))?")
US_REIT_AT_MOST_10 = Question(
    "us_reit_holding_at_most_10pct",
    "Waren Sie in diesem Jahr mit nicht mehr als 10 % an dem REIT beteiligt "
    "(DBA-USA Art. 10 Abs. 4 Satz 3 Buchst. a)?")


class Verdict(Enum):
    MET = "MET"                  # the rate applies
    UNANSWERED = "UNANSWERED"    # a question the rate depends on has no answer
    NOT_MET = "NOT_MET"          # answered, and the condition fails: no rate this engine applies


def questions(state: Optional[str], category: Optional[AssetCategory],
              answers: Dict[str, bool]) -> List[Question]:
    """The questions the rate for this state and instrument class depends on, given the
    answers so far (a follow-up is asked only where an earlier answer calls for it)."""
    state = (state or "").strip().upper()
    if state == "US" and category is AssetCategory.INVESTMENT_FUND:
        return [US_RIC_EXEMPT_PART]
    if state == "US" and category is AssetCategory.STOCK:
        return [US_REIT, US_REIT_AT_MOST_10] if answers.get(US_REIT.key) else [US_REIT]
    return []


def verdict(state: Optional[str], category: Optional[AssetCategory],
            answers: Optional[Dict[str, bool]]) -> Tuple[Verdict, str]:
    """Whether the conditions of the rate are met, with the reason where they are not."""
    answers = answers or {}
    asked = questions(state, category, answers)
    if any(q.key not in answers for q in asked):
        return Verdict.UNANSWERED, "; ".join(q.text for q in asked if q.key not in answers)
    if answers.get(US_RIC_EXEMPT_PART.key) and US_RIC_EXEMPT_PART in asked:
        return Verdict.NOT_MET, ("ein Teil der Ausschüttungen ist nach 26 U.S.C. § 871(k) steuerbefreit; "
                                 "die darauf einbehaltene Steuer ist nicht anrechenbar, der befreite Teil "
                                 "ist nicht bekannt")
    if answers.get(US_REIT.key) and not answers.get(US_REIT_AT_MOST_10.key):
        return Verdict.NOT_MET, ("REIT-Beteiligung über 10 %: DBA-USA Art. 10 Abs. 4 Satz 3 setzt dann "
                                 "keinen Höchstsatz")
    return Verdict.MET, ""

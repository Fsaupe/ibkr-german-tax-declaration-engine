# src/tax_law/withholding_conditions.py
"""The facts a creditable rate is conditional on, which no export contains.

A rate in `registry.CREDITABLE_DIVIDEND_RATES` holds only where the conditions the
store attaches to it are met. For a US payer they are facts of the payer and year
([GT-CREDIT-027]):

- a US fund (RIC): the 15 % holds *"falls keine Befreiung"*. US law leaves untaxed what
  the RIC reports as an interest-related or short-term capital gain dividend (26 U.S.C.
  § 871(k)) or as a capital gain dividend (§ 852(b)(3)), each under conditions of its own
  that the report does not establish. Where the RIC reports no part of the year's
  distributions as anything other than an ordinary dividend, the 15 % applies to the
  whole. Where it reports any part otherwise, the store does not settle the creditable
  amount, and the fund's tax rows for the year are not credited.
- a US share: a REIT's dividend is on the 15 % only if the holder meets one of the three
  alternatives of Art. 10 Abs. 4 Satz 3. Only Buchst. a (a natural person with not more
  than 10 % of the REIT) is asked; a REIT held above 10 % is not credited, since
  Buchst. b and c are not examined. REIT status is held per taxable year (§ 856(c)(1)).

Every question is about the payer, or about the taxpayer's holding as a whole, so one
answer per payer and year holds for every account and payment.

For a Chinese payer ([GT-CREDIT-031]: BZSt column C "0 / 10", BMF-Schreiben vom 31.03.2022,
DBA China Art. 10 Abs. 2): the company must be resident in mainland China (Art. 4) and not
an Art. 10 Abs. 2 Buchst. b investment vehicle; then the rate is 10 %, or 0 % where
China's own law exempts the dividend. The exemption is a fact of each dividend and, for an
A-share, of how long the shares it is paid on were held -- which can differ between
accounts and lots. It is therefore asked only whether any dividend of the year was
exempt. Where one was, the payer's tax rows for the year are not credited.

The facts come from the taxpayer, per instrument and year (src/processing/withholding_facts.py).
An unanswered question, and an answer that leaves the rate unsettled, give no rate: the
rows are not credited and are listed as unresolved, with the reason. That is not a finding
that nothing is creditable, nor that anything is refundable abroad.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.domain.enums import AssetCategory


@dataclass(frozen=True)
class Question:
    key: str
    text: str


US_RIC_NON_ORDINARY_PART = Question(
    "us_ric_non_ordinary_part",
    "Hat der Fonds einen Teil seiner Ausschüttungen dieses Jahres anders als als gewöhnliche Dividende "
    "ausgewiesen -- als 'interest-related dividend', 'short-term capital gain dividend' "
    "(26 U.S.C. § 871(k)), 'capital gain dividend' (§ 852(b)(3)) oder sonst (z. B. 'return of capital')? "
    "Siehe die Steuerbescheinigung des Fonds (Tax Supplement) bzw. Form 1042-S.")
US_REIT = Question(
    "us_reit",
    "War der Zahler in diesem Jahr ein Real Estate Investment Trust (REIT) der Vereinigten Staaten "
    "(26 U.S.C. § 856(c)(1))?")
US_REIT_AT_MOST_10 = Question(
    "us_reit_holding_at_most_10pct",
    "Waren Sie in diesem Jahr mit nicht mehr als 10 % an dem REIT beteiligt "
    "(DBA-USA Art. 10 Abs. 4 Satz 3 Buchst. a)?")
CN_MAINLAND_RESIDENT = Question(
    "cn_mainland_resident",
    "Ist die ausschüttende Gesellschaft auf dem chinesischen Festland ansässig (Art. 4 DBA China; "
    "nicht Hongkong oder Macau)?")
CN_INVESTMENT_VEHICLE = Question(
    "cn_real_estate_investment_vehicle",
    "Ist die Gesellschaft ein Investmentvehikel für unbewegliches Vermögen im Sinne von Art. 10 "
    "Abs. 2 Buchst. b DBA China (ausgeschüttete, steuerbefreite Immobilienerträge)?")
CN_EXEMPT = Question(
    "cn_exempt_under_chinese_law",
    "War mindestens eine Dividende dieser Gesellschaft in diesem Jahr nach chinesischem Recht "
    "steuerfrei (B-Aktie; A-Aktie länger als ein Jahr gehalten; befreites Unternehmen "
    "ausländischer Investoren -- BMF-Schreiben vom 31.03.2022)?")

# Keys of an earlier version of these questions. Their answers meant something else (a
# narrower US question; per-date answers shared across accounts), so a file holding them
# is not read as if they answered the questions above.
RETIRED_KEYS = ("us_ric_exempt_part",)
RETIRED_KEY_PREFIXES = ("us_ric_exempt_percent:", "cn_exempt_dividend:")


class Verdict(Enum):
    MET = "MET"                  # the rate applies
    UNANSWERED = "UNANSWERED"    # a question the rate depends on has no answer
    UNRESOLVED = "UNRESOLVED"    # answered, and the store does not settle the rate under the answers


def questions(state: Optional[str], category: Optional[AssetCategory],
              answers: Dict[str, bool]) -> List[Question]:
    """The questions the rate for this state and instrument class depends on, given the
    answers so far (a follow-up is asked only where an earlier answer calls for it)."""
    state = (state or "").strip().upper()
    if state == "US" and category is AssetCategory.INVESTMENT_FUND:
        return [US_RIC_NON_ORDINARY_PART]
    if state == "US" and category is AssetCategory.STOCK:
        return [US_REIT, US_REIT_AT_MOST_10] if answers.get(US_REIT.key) else [US_REIT]
    if state == "CN" and category is AssetCategory.STOCK:
        if answers.get(CN_MAINLAND_RESIDENT.key) is False:
            return [CN_MAINLAND_RESIDENT]
        if answers.get(CN_INVESTMENT_VEHICLE.key) is True:
            return [CN_MAINLAND_RESIDENT, CN_INVESTMENT_VEHICLE]
        return [CN_MAINLAND_RESIDENT, CN_INVESTMENT_VEHICLE, CN_EXEMPT]
    return []


def verdict(state: Optional[str], category: Optional[AssetCategory],
            answers: Optional[Dict[str, bool]]) -> Tuple[Verdict, str]:
    """Whether the conditions of the rate are met, and the reason where they are not."""
    answers = answers or {}
    asked = questions(state, category, answers)
    if any(q.key not in answers for q in asked):
        return Verdict.UNANSWERED, "; ".join(q.text for q in asked if q.key not in answers)
    if answers.get(US_RIC_NON_ORDINARY_PART.key):
        return Verdict.UNRESOLVED, (
            "der Fonds hat einen Teil anders als als gewöhnliche Dividende ausgewiesen; wie viel davon "
            "in den USA für Sie unbesteuert bleibt, hängt von Bedingungen ab, die nicht geprüft sind "
            "(26 U.S.C. § 871(k)(1)(B), (2)(B), die Kürzung zu hoch ausgewiesener Beträge, § 852(b)(3)(C)(ii))")
    if answers.get(US_REIT.key) and not answers.get(US_REIT_AT_MOST_10.key):
        return Verdict.UNRESOLVED, (
            "REIT-Beteiligung über 10 %: DBA-USA Art. 10 Abs. 4 Satz 3 Buchst. a nicht erfüllt; ob "
            "Buchst. b (börsengehandelte Gattung, höchstens 5 %) oder c (diversifizierter REIT) "
            "erfüllt ist, wird nicht geprüft")
    if CN_MAINLAND_RESIDENT in asked:
        if not answers[CN_MAINLAND_RESIDENT.key]:
            return Verdict.UNRESOLVED, "Gesellschaft nicht auf dem chinesischen Festland ansässig: Spalte C für China gilt nicht"
        if answers[CN_INVESTMENT_VEHICLE.key]:
            return Verdict.UNRESOLVED, "Investmentvehikel nach Art. 10 Abs. 2 Buchst. b DBA China: kein Satz der Spalte C"
        if answers[CN_EXEMPT.key]:
            return Verdict.UNRESOLVED, (
                "mindestens eine Dividende des Jahres nach chinesischem Recht steuerfrei; welche, hängt "
                "je Dividende von der Haltedauer der Aktien ab, auf die sie gezahlt wurde, und wird "
                "nicht je Konto und Zahlung erfasst")
    return Verdict.MET, ""

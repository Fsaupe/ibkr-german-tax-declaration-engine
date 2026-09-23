# src/tax_law/withholding_conditions.py
"""The facts a creditable rate is conditional on, which no export contains.

A rate in `registry.CREDITABLE_DIVIDEND_RATES` holds only where the conditions the
store attaches to it are met. For a US payer they are facts of the individual payer and
year ([GT-CREDIT-027]):

- a US fund (RIC): the 15 % holds *"falls keine Befreiung"*. The exempt part of a RIC
  dividend is whatever part the RIC reports as an interest-related or short-term
  capital gain dividend (26 U.S.C. § 871(k)); tax withheld on it is wholly an
  Ermaessigungsanspruch ([GT-CREDIT-026]), and the 15 % applies to the rest only. Where
  the taxpayer states that the fund reported an exempt part in the year, the share of
  each distribution is asked by its date, in percent of the gross.
- a US share: a REIT's dividend is on the 15 % only if the holder meets Art. 10 Abs. 4
  Satz 3 -- for a natural person, not more than 10 % of the REIT. REIT status is held per
  taxable year (§ 856(c)(1)).

For a Chinese payer ([GT-CREDIT-031]: BZSt column C "0 / 10", BMF-Schreiben vom 31.03.2022,
DBA China Art. 10 Abs. 2): the company must be resident in mainland China (Art. 4) and not
an Art. 10 Abs. 2 Buchst. b investment vehicle (15 % ceiling, outside column C); then the
rate is 10 %, or 0 % where China's own law exempts the dividend. The exemption is a fact of
each dividend (an A-share's turns on how long it was held at payment), so where the
taxpayer states that any dividend of the year was exempt, each dividend is asked by its
date.

The facts come from the taxpayer, per instrument and year (per dividend where the law says so) (src/processing/withholding_facts.py).
An unanswered question gives no rate; an answer under which the condition fails gives no
rate either, since the store then states none this engine applies. Both stop the run.
"""
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from src.domain.enums import AssetCategory


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    kind: str = "yes_no"   # or "percent": a number from 0 to 100


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


def us_ric_exempt_percent(income_date: str) -> Question:
    """Asked per distribution once US_RIC_EXEMPT_PART is answered yes ([GT-CREDIT-027])."""
    return Question(f"{US_RIC_EXEMPT_PERCENT_PREFIX}{income_date}",
                    f"Welcher Anteil (in %) der Ausschüttung vom {income_date} wurde vom Fonds (RIC) als "
                    "'interest-related dividend' oder 'short-term capital gain dividend' ausgewiesen "
                    "(Steuerbescheinigung des Fonds bzw. Form 1042-S)? Leer lassen, wenn unbekannt.",
                    kind="percent")


US_RIC_EXEMPT_PERCENT_PREFIX = "us_ric_exempt_percent:"


def cn_exempt_dividend(income_date: str) -> Question:
    """Asked per dividend once CN_EXEMPT is answered yes ([GT-CREDIT-031])."""
    return Question(f"cn_exempt_dividend:{income_date}",
                    f"War die Dividende vom {income_date} nach chinesischem Recht steuerfrei?")


class Verdict(Enum):
    MET = "MET"                  # the rate applies
    UNANSWERED = "UNANSWERED"    # a question the rate depends on has no answer
    NOT_MET = "NOT_MET"          # answered, and the condition fails: no rate this engine applies


def questions(state: Optional[str], category: Optional[AssetCategory],
              answers: Dict[str, bool], income_dates: Iterable[str] = ()) -> List[Question]:
    """The questions the rate for this state and instrument class depends on, given the
    answers so far (a follow-up is asked only where an earlier answer calls for it).
    `income_dates`: the dates of the incomes concerned, for a question asked per dividend."""
    state = (state or "").strip().upper()
    if state == "US" and category is AssetCategory.INVESTMENT_FUND:
        if answers.get(US_RIC_EXEMPT_PART.key):
            return [US_RIC_EXEMPT_PART] + [us_ric_exempt_percent(d) for d in sorted(set(income_dates))]
        return [US_RIC_EXEMPT_PART]
    if state == "US" and category is AssetCategory.STOCK:
        return [US_REIT, US_REIT_AT_MOST_10] if answers.get(US_REIT.key) else [US_REIT]
    if state == "CN" and category is AssetCategory.STOCK:
        if answers.get(CN_MAINLAND_RESIDENT.key) is False:
            return [CN_MAINLAND_RESIDENT]
        if answers.get(CN_INVESTMENT_VEHICLE.key) is True:
            return [CN_MAINLAND_RESIDENT, CN_INVESTMENT_VEHICLE]
        asked = [CN_MAINLAND_RESIDENT, CN_INVESTMENT_VEHICLE, CN_EXEMPT]
        if answers.get(CN_EXEMPT.key):
            asked += [cn_exempt_dividend(d) for d in sorted(set(income_dates))]
        return asked
    return []


def verdict(state: Optional[str], category: Optional[AssetCategory],
            answers: Optional[Dict[str, bool]],
            income_date: Optional[str] = None) -> Tuple[Verdict, str, Optional[Decimal]]:
    """Whether the conditions of the rate are met for the income of `income_date`, the
    reason where they are not, and a rate that replaces the table's where the answers fix
    a different one (None: the table's rate stands)."""
    answers = answers or {}
    asked = questions(state, category, answers, [income_date] if income_date else [])
    if any(q.key not in answers for q in asked):
        return Verdict.UNANSWERED, "; ".join(q.text for q in asked if q.key not in answers), None
    if CN_MAINLAND_RESIDENT in asked:
        if not answers[CN_MAINLAND_RESIDENT.key]:
            return Verdict.NOT_MET, "Gesellschaft nicht auf dem chinesischen Festland ansässig: DBA China nicht anwendbar", None
        if answers[CN_INVESTMENT_VEHICLE.key]:
            return Verdict.NOT_MET, "Investmentvehikel nach Art. 10 Abs. 2 Buchst. b DBA China: kein Satz der Spalte C", None
        if answers[CN_EXEMPT.key] and income_date and answers[cn_exempt_dividend(income_date).key]:
            return Verdict.MET, "", Decimal("0")
    if answers.get(US_REIT.key) and not answers.get(US_REIT_AT_MOST_10.key):
        return Verdict.NOT_MET, ("REIT-Beteiligung über 10 %: DBA-USA Art. 10 Abs. 4 Satz 3 setzt dann "
                                 "keinen Höchstsatz"), None
    return Verdict.MET, "", None


def taxable_share(state: Optional[str], category: Optional[AssetCategory],
                  answers: Optional[Dict[str, object]], income_date: Optional[str]) -> Decimal:
    """The part of the income the treaty rate applies to: 1, less the exempt part a US
    fund reported for this distribution ([GT-CREDIT-027]). Call only where `verdict` is
    MET, so a stated exemption has its share."""
    answers = answers or {}
    if (state or "").strip().upper() == "US" and category is AssetCategory.INVESTMENT_FUND \
            and answers.get(US_RIC_EXEMPT_PART.key):
        return 1 - answers[us_ric_exempt_percent(income_date).key] / Decimal("100")
    return Decimal("1")

# src/processing/withholding_facts.py
"""Facts about a payer that a creditable withholding rate depends on, per instrument and year.

The US rate of 15 % holds only for a RIC dividend with no exempt part and for a REIT
dividend whose holder meets the treaty's holding condition ([GT-CREDIT-027]; the questions
are in src/tax_law/withholding_conditions.py). The export carries neither fact, so the
taxpayer states them.

Fourth instance of the pattern `AssetClassifier`, `FundPriceStore` and
`VorabpauschaleDeclarationStore` follow: a JSON file of answers to something nothing can
derive, keyed by classification key and year. Per year, not per instrument, because both
facts are facts of a year: a RIC reports its exempt part dividend by dividend, and REIT
status is elected per taxable year. So an answer is never carried to another year.

- **Written only from an answer**, with where it came from and when.
- **Nothing is inferred.** An absent entry is not a "no"; the rate then does not apply and
  the run stops, naming the instrument.
- **A file that cannot be read raises** rather than starting empty.

Asked at the start of the run, after classification -- the same phase as the fund type and
the Vorabpauschale price -- and only for an instrument that has a tax row in the tax year
from a state whose rate depends on such a fact.
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, Iterable, List, Optional

from src.domain.assets import Asset
from src.domain.events import FinancialEvent, WithholdingTaxEvent
from src.domain.exceptions import ProcessingError
from src.tax_law.withholding_conditions import Question, questions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WithholdingFacts:
    answers: Dict[str, bool]
    date_set: date
    source: str


class WithholdingFactsStore:
    """The taxpayer's answers, keyed by classification key and tax year."""

    def __init__(self, cache_file_path: Optional[str] = None):
        if cache_file_path is None:
            import src.config as app_config
            # A config.py written before this setting existed lacks it: the file then
            # sits beside the classification cache, the same directory.
            cache_file_path = getattr(app_config, "WITHHOLDING_FACTS_STORE_PATH", None) or os.path.join(
                os.path.dirname(app_config.CLASSIFICATION_CACHE_FILE_PATH), "withholding_facts.json")
        self.cache_file_path = cache_file_path
        self._entries: Dict[str, WithholdingFacts] = {}
        self._load()

    @staticmethod
    def _key(classification_key: str, year: int) -> str:
        return f"{classification_key}|{year}"

    def _load(self) -> None:
        if not os.path.exists(self.cache_file_path):
            return
        try:
            with open(self.cache_file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            raise ProcessingError(
                f"The withholding facts store at {self.cache_file_path} could not be read: {e}. "
                "It holds the taxpayer's answers on which a Zeile 41 credit depends; treating it "
                "as empty would discard them silently. Fix or remove the file.") from e
        for key, entry in raw.items():
            try:
                answers = entry["answers"]
                if not all(isinstance(v, bool) for v in answers.values()):
                    raise TypeError("every answer must be true or false")
                self._entries[key] = WithholdingFacts(
                    answers=dict(answers), date_set=date.fromisoformat(entry["date_set"]),
                    source=entry["source"])
            except (KeyError, ValueError, TypeError) as e:
                raise ProcessingError(
                    f"Withholding facts entry {key!r} in {self.cache_file_path} is unreadable: {e}. "
                    "An answer cannot be guessed at.") from e

    def get(self, classification_key: str, year: int) -> Optional[WithholdingFacts]:
        return self._entries.get(self._key(classification_key, year))

    def put(self, classification_key: str, year: int, facts: WithholdingFacts) -> None:
        self._entries[self._key(classification_key, year)] = facts

    def save(self) -> None:
        directory = os.path.dirname(self.cache_file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {key: {"answers": f.answers, "date_set": f.date_set.isoformat(), "source": f.source}
                   for key, f in sorted(self._entries.items())}
        with open(self.cache_file_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)


def _ask_yes_no(asset: Asset, year: int, question: Question) -> bool:
    print(f"\n--- Angabe zur Quellensteuer: {asset.ibkr_symbol} ({asset.ibkr_isin}), {asset.description}, {year}")
    print(f"  {question.text}")
    while True:
        answer = input("  j/n: ").strip().lower()
        if answer in ("j", "ja", "y", "yes"):
            return True
        if answer in ("n", "nein", "no"):
            return False
        print("  Bitte j oder n eingeben.")


def resolve_withholding_facts(assets: Iterable[Asset], events: Iterable[FinancialEvent], tax_year: int,
                              store: WithholdingFactsStore, interactive: bool,
                              ask: Optional[Callable[[Asset, int, Question], bool]] = None) -> List[Asset]:
    """Attach to each asset the answers the rate of its tax rows in `tax_year` depends on.

    Asks for what is missing in an interactive run and saves the answers. Returns the
    assets left with a question unanswered; the engine stops on their tax rows."""
    ask = ask or _ask_yes_no
    states_by_asset: Dict[object, set] = {}
    for e in events:
        if isinstance(e, WithholdingTaxEvent) and e.event_date[:4] == str(tax_year):
            states_by_asset.setdefault(e.asset_internal_id, set()).add(
                (e.source_country_code or "").strip().upper())
    unanswered: List[Asset] = []
    changed = False
    for asset in assets:
        for state in sorted(states_by_asset.get(asset.internal_asset_id, ())):
            key = asset.get_classification_key()
            stored = store.get(key, tax_year)
            answers = dict(stored.answers) if stored else {}
            before = dict(answers)
            while True:
                missing = [q for q in questions(state, asset.asset_category, answers) if q.key not in answers]
                if not missing or not interactive:
                    break
                answers[missing[0].key] = ask(asset, tax_year, missing[0])
            if answers != before:
                store.put(key, tax_year, WithholdingFacts(
                    answers=answers, date_set=date.today(),
                    source="Angabe des Steuerpflichtigen im interaktiven Lauf"))
                changed = True
            asset.withholding_facts[tax_year] = answers
            if any(q.key not in answers for q in questions(state, asset.asset_category, answers)):
                unanswered.append(asset)
    if changed:
        store.save()
    return unanswered

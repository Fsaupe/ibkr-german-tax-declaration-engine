# src/engine/event_processors/stock_award_processor.py
"""Shares a broker awarded for capital placed with it, in the tax year.

**This file exists because an award or a reversal can fall inside the declared year.**
The historical replay applies awards dated before the tax year
(`FifoLedger.apply_historical_event`), and for a while that was the only dispatch there
was. An award event dated inside the year then reached the current-year table, found no
processor, and produced a log line -- and the run continued.

For an award or a reversal that is loud: the quantity is wrong and the end-of-year
reconciliation refuses it. A vesting moves no shares, so an unhandled one would reconcile
clean while the lot stayed without a cost; it is dispatched here, and an award kind nobody
has classified raises instead of being dropped in silence.

The three kinds do here what they do in the replay, and the two paths call the same
`FifoLedger` methods so they cannot disagree about what an award means.

**One programme only.** Everything here applies the store's result for Interactive Brokers'
Refer-A-Friend share award ([GT-ESTG20-063] to [GT-ESTG20-067]); `grants_parser` refuses rows
of anything else, and the user confirms the programme in config.

**The vesting is the receipt.** The programme's terms declare a premature disposal "void"
and the custodian refuses one, so the recipient cannot dispose of the shares while the
restriction runs, and Zufluss falls on the day it lapses ([GT-ESTG20-064], BFH VI R 37/09
Rn. 15 and 20). That is the store's application of the German test to the published terms,
approved by the maintainer on 2026-09-20; its limits are stated there. This processor
implements it:

* the **award** books the shares as a holding without cost or acquisition date;
* the **vesting** is the § 22 Nr. 3 receipt ([GT-ESTG20-063]) at the vesting row's price and
  that day's ECB rate, and that value is the lot's Anschaffungskosten ([GT-ESTG20-065]);
* a **return** takes unvested shares back, and since nothing had zugeflossen there is
  neither a receipt nor a negative Einnahme ([GT-ESTG20-067], Boundary).

The receipt belongs on Anlage SO, a category the reporting layer does not have (issue #76),
so it is handed to the reader with amount, year and destination.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from src.domain.enums import FinancialEventType
from src.domain.events import FinancialEvent, StockAwardEvent
from src.domain.exceptions import ProcessingError
from src.domain.results import RealizedGainLoss
from src.engine.fifo_manager import FifoLedger
from src.processing.data_gaps import GapSeverity

from .base_processor import EventProcessor

logger = logging.getLogger(__name__)

STOCK_AWARD_RECEIPT_NOT_DECLARED = "STOCK_AWARD_RECEIPT_NOT_DECLARED"


class StockAwardProcessor(EventProcessor):
    """The tax year's half of an award. The historical replay applies the same methods."""

    def process(self, event: FinancialEvent, ledger: FifoLedger,
                context: Dict[str, Any]) -> List[RealizedGainLoss]:
        if not isinstance(event, StockAwardEvent):
            raise ProcessingError(
                f"StockAwardProcessor received {type(event).__name__}, which carries no "
                f"award date -- part of the key (with the grant account) an award has to "
                f"its lot.")

        if event.event_type == FinancialEventType.STOCK_AWARD_GRANTED:
            ledger.add_lot_for_stock_award(event)
        elif event.event_type == FinancialEventType.STOCK_AWARD_REVERSED:
            ledger.reverse_stock_award_lot(event)
        elif event.event_type == FinancialEventType.STOCK_AWARD_VESTED:
            ledger.vest_stock_award_lot(event)
            self._record_undeclared_receipt(event, context)
        else:
            # A fourth kind must stop the run rather than fall through. Falling through
            # is what once left the vesting unapplied, and the cost of it was a wrong
            # cost basis nothing reported.
            raise ProcessingError(
                f"StockAwardProcessor has no handler for {event.event_type.name} on "
                f"{event.event_date}. It reached the current-year dispatch, so it is "
                f"expected to affect the ledger; leaving it unapplied would leave a "
                f"holding or a cost basis that a later disposal is measured against.")

        # No RealizedGainLoss from any of the three. See the module docstring: the
        # receipt is Anlage SO income this engine does not yet declare, and the effect on
        # a declared figure runs through the lot's cost basis.
        return []

    @staticmethod
    def _record_undeclared_receipt(event: StockAwardEvent,
                                   context: Dict[str, Any]) -> None:
        """Say, in the report, that a taxable receipt fell in this year and is not in it.

        **The gap exists because the omission is otherwise invisible and points one way.**
        The engine takes the vesting-day value as the lot's Anschaffungskosten, which LOWERS
        the declared gain on a later disposal, and omits the matching § 22 Nr. 3 receipt
        ([GT-ESTG20-063]) because the reporting layer has no Anlage SO *Einkuenfte aus
        Leistungen* category -- issue #76. Taking the half that reduces a figure and
        dropping the half that adds one is understatement, and a run that did it in
        silence would produce a complete-looking declaration that is not complete.

        WARNING and not FAIL_FAST: the figures the engine does emit are correct under the
        reading taken at [GT-ESTG20-064], and every other Kapitalertrag in the year is unaffected.
        Refusing the year would withhold sound figures over a line the engine has never
        been able to produce. What the severity asserts is exactly that -- the declared
        figures are safe, and something outside them is not computed here.

        The amount is stated so the reader can enter it themselves rather than recompute
        it from the export.
        """
        collector = context.get('data_gap_collector')
        if collector is None:
            return
        gross = None
        if event.unit_cost_basis_eur is not None:
            # Rounded to cents: the message exists so the reader can enter this on Anlage SO,
            # and the full-precision product is a figure nobody can type. The internal cost
            # basis the ledger carries is unaffected -- this is the display of it.
            gross = (event.quantity * event.unit_cost_basis_eur).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
        collector.record(
            STOCK_AWARD_RECEIPT_NOT_DECLARED,
            f"Anlage SO (Einkuenfte aus Leistungen), {event.event_date}",
            f"The transfer restriction on shares awarded under Interactive Brokers' "
            f"Refer-A-Friend programme on {event.award_date} lapsed on {event.event_date}, "
            f"which is where Zufluss falls ([GT-ESTG20-064]). That receipt "
            f"is a Leistung under § 22 Nr. 3 EStG ([GT-ESTG20-063]) and belongs on Anlage SO for {event.event_date[:4]}; this "
            f"engine has no line for it and has NOT declared it (issue #76). Its value at "
            f"Zufluss is "
            f"{'EUR ' + str(gross) if gross is not None else 'not computable here'}, "
            f"which is also the acquisition cost the engine has used for these units "
            f"([GT-ESTG20-065]) -- so the gain declared on their later disposal is reduced "
            f"by it while the receipt itself is absent. Declare it yourself, or the return "
            f"understates. § 22 Nr. 3 Satz 2's Freigrenze ([GT-ESTG20-062]) is not applied "
            f"here -- out of scope for the same reason as the § 23 Freigrenze "
            f"([GT-ESTG23-009]): a per-Kalenderjahr total across all Leistungen that one "
            f"broker's files cannot establish.",
            severity=GapSeverity.WARNING,
        )

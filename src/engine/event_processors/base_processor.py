# src/engine/event_processors/base_processor.py
import abc
import logging
from typing import List, Dict, Any # Added Dict, Any
import uuid # Added uuid
from decimal import Decimal # Added Decimal

from src.domain.events import FinancialEvent
from src.domain.results import RealizedGainLoss
from src.engine.fifo_manager import FifoLedger
from src.identification.asset_resolver import AssetResolver # Added

logger = logging.getLogger(__name__)

class EventProcessor(abc.ABC):
    """Abstract base class for processing specific financial event types against a FIFO ledger."""

    @abc.abstractmethod
    def process(self, event: FinancialEvent, ledger: FifoLedger, context: Dict[str, Any]) -> List[RealizedGainLoss]:
        """
        Processes a financial event, modifying the ledger and returning any realized gains/losses.

        Args:
            event: The specific FinancialEvent subtype to process.
            ledger: The FifoLedger associated with the event's asset.
            context: A dictionary containing additional context required by the processor,
                     e.g., {'asset_resolver': AssetResolver, 'pending_option_adjustments': Dict}.

        Returns:
            A list of RealizedGainLoss objects generated by this event processing.
            Returns an empty list if no gains/losses are realized by this event type.
        """
        pass

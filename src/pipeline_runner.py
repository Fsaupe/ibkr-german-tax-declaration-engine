# src/pipeline_runner.py
import logging
from decimal import Decimal, getcontext
from typing import Any, Optional, Tuple, List, Dict # Python 3.8 compatibility for List, Dict

# Configuration
import src.config as config

# Domain objects and Enums (assuming they are accessible)
from src.domain.assets import Asset # For type hinting if needed
from src.domain.events import FinancialEvent
from src.domain.results import RealizedGainLoss, VorabpauschaleData

# Core components
from src.parsers.parsing_orchestrator import ParsingOrchestrator
from src.classification.asset_classifier import AssetClassifier
from src.processing.enrichment import enrich_financial_events
from src.processing.vp_nav_resolution import resolve_year_start_navs
from src.processing.declared_vp_resolution import resolve_declared_vp
from src.identification.fund_soy_nav_provider import FundSoyNavProvider
from src.identification.declared_vp_provider import DeclaredVpProvider
from src.utils.currency_converter import CurrencyConverter
from src.utils.exchange_rate_provider import ECBExchangeRateProvider, ExchangeRateProvider # Added base for custom provider
from src.engine.calculation_engine import run_main_calculations
from src.identification.asset_resolver import AssetResolver

logger = logging.getLogger(__name__)

class ProcessingOutput:
    """
    Encapsulates the results of the core processing pipeline.
    """
    def __init__(self,
                 realized_gains_losses: List[RealizedGainLoss],
                 vorabpauschale_items: List[VorabpauschaleData],
                 processed_income_events: List[FinancialEvent], # Assuming this is the third item from run_main_calculations
                 all_financial_events_enriched: List[FinancialEvent],
                 asset_resolver: AssetResolver,
                 eoy_mismatch_error_count: int,
                 vorabpauschale_gaps: Optional[List[Any]] = None):
        self.realized_gains_losses = realized_gains_losses
        self.vorabpauschale_items = vorabpauschale_items
        self.processed_income_events = processed_income_events
        self.all_financial_events_enriched = all_financial_events_enriched
        self.asset_resolver = asset_resolver
        self.eoy_mismatch_error_count = eoy_mismatch_error_count
        self.vorabpauschale_gaps = vorabpauschale_gaps or []
        # For EOY state checks in tests, final assets can be fetched from asset_resolver
        self.final_assets_by_id: Dict[Any, Asset] = asset_resolver.assets_by_internal_id


def run_core_processing_pipeline(
    trades_file_path: str,
    cash_transactions_file_path: str,
    positions_start_file_path: str,
    positions_end_file_path: str,
    corporate_actions_file_path: str,
    interactive_classification_mode: bool,
    tax_year_to_process: int = config.TAX_YEAR, # Allow override for testing
    custom_rate_provider: Optional[ExchangeRateProvider] = None, # For testing ECB mock
    cash_balance_file_path: Optional[str] = None,  # For currency FIFO processing
    options_eae_file_path: Optional[str] = None,  # For cash-settled option processing
    positions_prior_start_file_path: Optional[str] = None  # Prior-year SoY for Vorabpauschale
) -> ProcessingOutput:
    """
    Runs the core data processing pipeline: parsing, enrichment, and calculations.
    Returns a ProcessingOutput object containing all relevant results.
    """
    logger.info("Initializing system components for pipeline...")
    asset_classifier = AssetClassifier(
        cache_file_path=config.CLASSIFICATION_CACHE_FILE_PATH, # Renamed from CLASSIFICATION_CACHE_FILE
    )
    asset_resolver = AssetResolver(asset_classifier=asset_classifier)
    orchestrator = ParsingOrchestrator(
        asset_resolver=asset_resolver,
        asset_classifier=asset_classifier,
        interactive_classification=interactive_classification_mode
    )

    logger.info("Starting parsing pipeline...")
    try:
        all_financial_events_raw = orchestrator.run_parsing_pipeline(
            trades_file=trades_file_path,
            cash_transactions_file=cash_transactions_file_path,
            positions_start_file=positions_start_file_path,
            positions_end_file=positions_end_file_path,
            corporate_actions_file=corporate_actions_file_path,
            cash_balance_file=cash_balance_file_path,
            options_eae_file=options_eae_file_path,
            tax_year=tax_year_to_process
        )
    except ValueError as e:
        logger.critical(f"Parsing pipeline failed: {e}. Check input data and configuration.")
        # Re-raise or handle as per application's error strategy for pipeline failures
        raise  # Or sys.exit(1) if this function is allowed to terminate
    except Exception as e:
        logger.critical(f"Parsing pipeline failed with unexpected error: {e}", exc_info=True)
        raise

    logger.info(f"Parsing pipeline completed. Discovered {len(asset_resolver.assets_by_internal_id)} unique assets.")
    logger.info(f"Generated {len(all_financial_events_raw)} raw financial event objects.")

    if custom_rate_provider:
        rate_provider = custom_rate_provider
        logger.info("Using custom exchange rate provider.")
    else:
        rate_provider = ECBExchangeRateProvider(
            cache_file_path=config.ECB_RATES_CACHE_FILE_PATH, # Renamed from ECB_RATES_CACHE_FILE
            max_fallback_days_override=config.MAX_FALLBACK_DAYS_EXCHANGE_RATES,
            currency_code_mapping_override=config.CURRENCY_CODE_MAPPING_ECB,
            pegged_currency_rates=config.PEGGED_CURRENCY_RATES
        )
        try:
            logger.info("ECB exchange rates provider initialized.")
        except Exception as e:
            logger.error(f"Failed to load ECB exchange rates: {e}. Currency conversions might fail.")
            # Decide on error strategy: raise, or continue with potential failures later?
            # For now, logging error and continuing.

    currency_converter = CurrencyConverter(rate_provider=rate_provider)

    logger.info("Enriching financial events (e.g., EUR conversion)...")
    financial_events_enriched = enrich_financial_events(
        financial_events=all_financial_events_raw,
        currency_converter=currency_converter,
        internal_calculation_precision=config.INTERNAL_CALCULATION_PRECISION, # Renamed parameter
        decimal_rounding_mode=config.DECIMAL_ROUNDING_MODE
    )
    logger.info(f"Enrichment completed. {len(financial_events_enriched)} events processed.")

    # Resolve start-of-year NAVs for the §18 InvStG Vorabpauschale: the current year
    # (preview of next year's return) and the prior year (the VP that flows into and is
    # declared on this year's return, §18 Abs. 3). Warn-only — gaps become a report callout.
    prior_year_soy_positions = _load_prior_year_soy_positions(positions_prior_start_file_path)
    fund_nav_provider = FundSoyNavProvider(cache_file_path=config.FUND_SOY_NAV_CACHE_FILE_PATH)
    vorabpauschale_gaps = resolve_year_start_navs(
        asset_resolver=orchestrator.asset_resolver,
        events=financial_events_enriched,
        tax_year=tax_year_to_process,
        interactive=interactive_classification_mode,
        provider=fund_nav_provider,
        prior_year_soy_positions=prior_year_soy_positions,
    )

    # §19 Abs. 1 S. 3 InvStG: for funds disposed this year, resolve the VP declared in prior
    # years (interactive, cached) so the disposal gain is reduced by the held-period VP.
    declared_vp_provider = DeclaredVpProvider(cache_file_path=config.DECLARED_VP_CACHE_FILE_PATH)
    vorabpauschale_gaps += resolve_declared_vp(
        asset_resolver=orchestrator.asset_resolver,
        events=financial_events_enriched,
        tax_year=tax_year_to_process,
        interactive=interactive_classification_mode,
        provider=declared_vp_provider,
        currency_converter=currency_converter,
    )

    logger.info(f"Running calculation engine for tax year {tax_year_to_process}...")
    eoy_mismatch_error_count_calc = 0
    try:
        # Ensure run_main_calculations uses the passed tax_year_to_process
        realized_gains_losses, vorabpauschale_items, processed_income_events, eoy_mismatch_error_count_calc = run_main_calculations(
            financial_events=financial_events_enriched,
            asset_resolver=orchestrator.asset_resolver, # Use the resolver from the orchestrator
            currency_converter=currency_converter,
            exchange_rate_provider=rate_provider,
            tax_year=tax_year_to_process,
            internal_calculation_precision=config.INTERNAL_CALCULATION_PRECISION, # Renamed parameter
            decimal_rounding_mode=config.DECIMAL_ROUNDING_MODE
        )
    except Exception as e:
        logger.critical(f"Calculation engine failed with unexpected error: {e}", exc_info=True)
        raise # Re-raise for higher level handling or test assertion

    logger.info("Calculation engine run completed.")
    if eoy_mismatch_error_count_calc > 0:
         logger.warning(f"Calculation engine reported {eoy_mismatch_error_count_calc} EOY quantity mismatch errors.")


    return ProcessingOutput(
        realized_gains_losses=realized_gains_losses,
        vorabpauschale_items=vorabpauschale_items,
        processed_income_events=processed_income_events,
        all_financial_events_enriched=financial_events_enriched,
        asset_resolver=orchestrator.asset_resolver,
        eoy_mismatch_error_count=eoy_mismatch_error_count_calc,
        vorabpauschale_gaps=vorabpauschale_gaps,
    )


def _load_prior_year_soy_positions(path: Optional[str]):
    """Parse a prior-year SoY positions export into {ISIN: (nav_per_unit, currency)}.

    Returns None if no file was provided (so the resolver knows the bulk export is
    absent and warns accordingly); an empty/partial dict otherwise.
    """
    if not path:
        return None
    from src.parsers.positions_parser import parse_positions_csv
    try:
        records = parse_positions_csv(path)
    except Exception as e:
        logger.warning(f"Could not parse prior-year SoY positions '{path}': {e}")
        return None
    out: Dict[str, Any] = {}
    for r in records:
        if r.isin and r.mark_price is not None:
            out[r.isin] = (r.mark_price, r.currency_primary)
    return out

"""Writer premium receipt, separate from its later disposition (GT-ESTG20-004).

The maintainer retains the existing trade-date/FX convention. Near-year-end
executions are disclosed by calculation_engine; no settlement date is invented.
"""
from decimal import Decimal

from src.domain.enums import AssetCategory, RealizationType, TaxReportingCategory
from src.domain.results import RealizedGainLoss


def writer_premium_receipt(event, ctx):
    amount = event.net_proceeds_or_cost_basis_eur
    quantity = event.quantity.copy_abs()
    return RealizedGainLoss(
        originating_event_id=event.event_id, asset_internal_id=event.asset_internal_id,
        asset_category_at_realization=AssetCategory.OPTION,
        acquisition_date=event.event_date, realization_date=event.event_date,
        realization_type=RealizationType.OPTION_PREMIUM_RECEIPT,
        quantity_realized=quantity, unit_cost_basis_eur=Decimal('0'),
        unit_realization_value_eur=ctx.divide(amount, quantity),
        total_cost_basis_eur=Decimal('0'), total_realization_value_eur=amount,
        gross_gain_loss_eur=amount, is_stillhalter_income=True,
        tax_reporting_category=(TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN
            if amount >= 0 else TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE))

"""Export reconciled securities-short portions for GT-ESTG20-074 disclosure.

Do not replay trades in a reporter: the account ledgers already applied FIFO,
splits, transfers and position flips. Take immutable values after reconciliation.
"""
from src.domain.enums import AssetCategory, RealizationType
from src.domain.results import ShortSaleDisclosure


SECURITIES = frozenset({AssetCategory.STOCK, AssetCategory.BOND,
                        AssetCategory.SONSTIGE_KAPITALFORDERUNG,
                        AssetCategory.INVESTMENT_FUND})


def build_short_sale_disclosures(ledgers, realized_gains_losses, tax_year):
    rows = []
    open_lot_keys = set()
    for (account, asset_id), ledger in ledgers.items():
        if ledger.asset_category not in SECURITIES:
            continue
        for lot in ledger.short_lots:
            if lot.quantity_shorted <= 0:
                continue
            open_lot_keys.add((account, asset_id, lot.source_transaction_id))
            rows.append(ShortSaleDisclosure(
                account, asset_id,
                lot.opening_date if lot.acquisition_date_is_known else None,
                lot.source_transaction_id, lot.quantity_shorted,
                lot.total_sale_proceeds_eur if lot.acquisition_date_is_known else None))

    for gain in realized_gains_losses:
        if (gain.realization_type != RealizationType.SHORT_POSITION_COVER
                or gain.asset_category_at_realization not in SECURITIES
                or gain.realization_date[:4] != str(tax_year)):
            continue
        # Include prior-year covers even if everything is now closed; otherwise
        # the cover-year deviation would disappear from the covering return.
        # Same-year covered portions are useful only beside an open remainder
        # of this opening lot, not an unrelated round trip in the same security.
        if (gain.acquisition_date[:4] >= str(tax_year)
                and (gain.short_account_id, gain.asset_internal_id,
                     gain.short_opening_transaction_id) not in open_lot_keys):
            continue
        rows.append(ShortSaleDisclosure(
            gain.short_account_id, gain.asset_internal_id, gain.acquisition_date,
            gain.short_opening_transaction_id, gain.quantity_realized,
            gain.total_realization_value_eur, gain.realization_date,
            gain.total_cost_basis_eur, gain.short_cover_transaction_id))
    # Asset UUIDs vary between runs. Source/account/date ordering stays stable.
    return sorted(rows, key=lambda r: (r.account_id, r.opening_date or "",
                                      r.source_transaction_id or "", r.cover_date or "",
                                      r.cover_transaction_id or ""))

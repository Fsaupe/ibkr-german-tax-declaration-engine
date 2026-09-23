# src/engine/loss_offsetting.py
import logging
import uuid
from decimal import Decimal, Context
from collections import defaultdict
from typing import List, Dict, Optional

from src.domain.results import RealizedGainLoss, VorabpauschaleData, LossOffsettingResult
from src.domain.events import FinancialEvent, CashFlowEvent, WithholdingTaxEvent
from src.domain.enums import AssetCategory, FinancialEventType, InvestmentFundType, TaxReportingCategory
from src.domain.assets import Asset, InvestmentFund
from src.domain.exceptions import ProcessingError
from src.identification.asset_resolver import AssetResolver
from src.utils.tax_utils import get_teilfreistellung_rate_for_fund_type
from src.reporting.form_rules import get_form_rules
from src.processing.data_gaps import DataGapCollector, GapSeverity
from src.tax_law.treaty_withholding import (
    assess_withholdings, WithholdingAssessment, WithholdingStatus, UNSUPPORTED,
)
import src.config as global_config

logger = logging.getLogger(__name__)

class LossOffsettingEngine:
    def __init__(self,
                 realized_gains_losses: List[RealizedGainLoss],
                 vorabpauschale_items: List[VorabpauschaleData],
                 current_year_financial_events: List[FinancialEvent],
                 asset_resolver: AssetResolver,
                 tax_year: int,
                 apply_conceptual_derivative_loss_capping: Optional[bool] = None,
                 # Optional so existing callers keep working. When absent, a gap recorded
                 # here is logged but not collected into the report.
                 data_gap_collector: Optional["DataGapCollector"] = None):
        # None -> read the user config AT CALL TIME (the previous module-global
        # default was bound at import time — ambient mutable state).
        if apply_conceptual_derivative_loss_capping is None:
            apply_conceptual_derivative_loss_capping = global_config.APPLY_CONCEPTUAL_DERIVATIVE_LOSS_CAPPING
        self.realized_gains_losses = realized_gains_losses
        self.vorabpauschale_items = vorabpauschale_items
        self.current_year_financial_events = current_year_financial_events
        self.asset_resolver = asset_resolver
        self.tax_year = tax_year
        self.apply_conceptual_derivative_loss_capping = apply_conceptual_derivative_loss_capping
        self.data_gap_collector = data_gap_collector
        # Built lazily by _income_gross_eur_by_event_id for the German-KESt rate test.
        self._income_gross_cache: Optional[Dict[uuid.UUID, Decimal]] = None

        self.ctx = Context(prec=global_config.INTERNAL_CALCULATION_PRECISION, rounding=global_config.DECIMAL_ROUNDING_MODE) # Renamed INTERNAL_WORKING_PRECISION
        self.TWO_PLACES = global_config.OUTPUT_PRECISION_AMOUNTS # Renamed from PRECISION_TOTAL_AMOUNTS

    def _calculate_net_fund_distribution(self, event: CashFlowEvent, asset: InvestmentFund) -> Decimal:
        if not isinstance(event, CashFlowEvent) or event.event_type != FinancialEventType.DISTRIBUTION_FUND:
            return self.ctx.create_decimal(Decimal('0'))
        if not isinstance(asset, InvestmentFund):
            logger.error(f"Asset {asset.internal_asset_id} for fund distribution event {event.event_id} is not of type InvestmentFund.")
            return event.gross_amount_eur if event.gross_amount_eur is not None else self.ctx.create_decimal(Decimal('0'))

        gross_dist_eur = event.gross_amount_eur
        if gross_dist_eur is None:
            return self.ctx.create_decimal(Decimal('0'))

        tf_rate = get_teilfreistellung_rate_for_fund_type(asset.fund_type)

        tf_amount = self.ctx.multiply(gross_dist_eur.copy_abs(), tf_rate)
        if gross_dist_eur >= Decimal('0'):
            net_dist_eur = self.ctx.subtract(gross_dist_eur, tf_amount)
        else:
            net_dist_eur = self.ctx.add(gross_dist_eur, tf_amount)

        return net_dist_eur.quantize(self.TWO_PLACES, context=self.ctx)


    # The German composite rate, 25% KESt x 1.055 SolZ = 26.375%
    # (reference/tax-law/estg-36-45a-kapitalertragsteuer-anrechnung.md [GT-CREDIT-025]).
    # The band around it is EMPIRICAL, not derived. Measured against real broker data, the
    # withheld amount is not reproducible from the paired gross by any simple rounding rule:
    # one-step round(gross x 0.26375, 2), two-step KESt-then-SolZ half-up, and two-step
    # round-down each reproduced exactly half of the known-German rows, with observed
    # deviations up to two cents. Rationale for the width is recorded in
    # docs/legal-implementation-map.md under GT-CREDIT-025; do not restate it as derived.
    _KEST_RATE_LOW = Decimal("26.30")
    _KEST_RATE_HIGH = Decimal("26.45")
    # IBKR emits this as a country code but it denotes "unknown/multiple", not a jurisdiction.
    _NON_COUNTRY_CODES = frozenset({"XX"})

    def _is_german_kest(self, event: WithholdingTaxEvent) -> bool:
        """Is this withholding German Kapitalertragsteuer rather than foreign tax?

        legal_basis: [GT-FORM-007] — German KESt on a German issuer's dividend is not an
        auslaendische Steuer and does not belong on Zeile 41. [GT-CREDIT-025] gives the
        26.375% composite that identifies it.

        Two signals, in order of authority. The issuer country decides when the broker
        supplies one; its availability depends on export vintage, so older data falls back
        to the rate composite. Both limits are recorded against GT-CREDIT-025 in
        docs/legal-implementation-map.md.

        A row that matches neither is treated as foreign, which is the pre-existing
        behaviour: this method narrows Zeile 41, it never widens it.
        """
        code = (event.source_country_code or "").strip().upper()
        if code and code not in self._NON_COUNTRY_CODES:
            return code == "DE"

        # No usable country code: fall back to the rate composite against the linked income.
        if event.taxed_income_event_id is None or event.gross_amount_eur is None:
            return False
        gross = self._income_gross_eur_by_event_id().get(event.taxed_income_event_id)
        if gross is None or gross <= 0:
            return False
        rate_pct = abs(event.gross_amount_eur) / gross * Decimal("100")
        return self._KEST_RATE_LOW <= rate_pct <= self._KEST_RATE_HIGH

    def _income_gross_eur_by_event_id(self) -> Dict[uuid.UUID, Decimal]:
        """Gross EUR income per event id, for the rate test. Built once per run."""
        if self._income_gross_cache is None:
            self._income_gross_cache = {
                e.event_id: e.gross_amount_eur
                for e in self.current_year_financial_events
                if isinstance(e, CashFlowEvent) and e.gross_amount_eur is not None
            }
        return self._income_gross_cache

    def _income_event_by_event_id(self) -> Dict[uuid.UUID, CashFlowEvent]:
        """The income CashFlowEvent a withholding row is linked to, by event id.

        The treaty-rate guard needs the linked income's kind (dividend vs interest)
        and its gross in the row's own currency, which the id→EUR map above does not
        carry."""
        return {
            e.event_id: e
            for e in self.current_year_financial_events
            if isinstance(e, CashFlowEvent)
        }

    def _record_german_kest_gap(self, count: int, total_eur: Decimal) -> None:
        """Report German KESt that was excluded from Zeile 41 and cannot be declared for you.

        [GT-FORM-007] routes the credit to Zeile 7 with Zeilen 37/38/39. The engine does not
        fill those: Zeilen 7-15 are the figures *taken from* the Steuerbescheinigung of the
        inlaendische auszahlende Stelle, and 36 Abs. 2 Satz 2 bars the credit outright when no
        certificate is presented ([GT-CREDIT-022]). Zeile 7 transcribes a document the taxpayer
        holds; computing it here would fabricate the one figure the form defines as copied.

        Severity is WARNING, and the direction is what makes that honest: removing the amount
        from Zeile 41 *reduces* the credit claimed, so the declaration becomes more
        conservative, not income-understating. The taxpayer must obtain the certificate and
        fill Zeilen 7/37/38 by hand to recover the credit.
        """
        if count == 0:
            return
        detail = (
            f"{count} withholding row(s) totalling EUR {total_eur.quantize(self.TWO_PLACES, context=self.ctx)} "
            f"were identified as German Kapitalertragsteuer (25% KESt plus 5.5% SolZ) rather than "
            f"foreign withholding tax, and have been EXCLUDED from Anlage KAP Zeile 41, which is "
            f"for anrechenbare auslaendische Steuer only. This tax is creditable, but through "
            f"Zeile 7 with Zeilen 37/38/39 — and only on presentation of a Steuerbescheinigung "
            f"(36 Abs. 2 Satz 2 EStG). Those lines are transcribed from that certificate, so the "
            f"engine cannot fill them. Request the Steuerbescheinigung from the German custodian "
            f"via your broker and complete Zeilen 7/37/38 by hand, or the credit is lost."
        )
        if self.data_gap_collector is not None:
            self.data_gap_collector.record(
                code="ANLAGE_KAP_GERMAN_KEST_NOT_DECLARABLE",
                subject=f"Anlage KAP Zeilen 7/37/38 ({self.tax_year})",
                detail=detail,
                severity=GapSeverity.WARNING,
            )
        else:
            logger.warning(
                "Data gap [ANLAGE_KAP_GERMAN_KEST_NOT_DECLARABLE] "
                "Anlage KAP Zeilen 7/37/38 (%d): %s", self.tax_year, detail
            )

    def _record_treaty_withholding_gaps(self, treaty_flags: Dict[tuple, List[tuple]]) -> None:
        """Surface every foreign withholding row the treaty-rate guard could not credit
        in full: one gap per (status, source state), listing the rows.

        legal_basis: [GT-CREDIT-026] (Ermäßigungsanspruch), [GT-CREDIT-027] (US 15 %),
        [GT-CREDIT-029] (other states' dividend rates), [GT-CREDIT-030] (Irish interest).
        An over-treaty-rate row is capped and reported (WARNING): Zeile 41 carries the
        creditable amount and the report says what to reclaim abroad. A row with no
        supported creditable amount -- no linked income, no rate for its state or income
        kind, no researched edition for the year -- is itemised here as a WARNING and
        then stops the run: one FAIL_FAST gap names every such row, so one run lists the
        whole problem (maintainer's review of PR #102, F1). Neither the withheld amount
        nor zero may stand in for the credit.
        """
        unsupported = {k: v for k, v in treaty_flags.items() if k[0] in UNSUPPORTED}
        if self.data_gap_collector is None:
            for (status, state), rows in treaty_flags.items():
                logger.warning("Data gap [FOREIGN_WHT_%s] %s (%d rows)", status.value, state or "unknown", len(rows))
            if unsupported:
                raise ProcessingError(self._unsupported_credit_detail(unsupported))
            return

        def _rowlist(rows):
            return "; ".join(
                f"{ev.event_date} tx {ev.ibkr_transaction_id or '—'}: "
                f"withheld EUR {a.withheld_eur.quantize(self.TWO_PLACES, context=self.ctx)}"
                + (f", anrechenbar EUR {a.creditable_eur.quantize(self.TWO_PLACES, context=self.ctx)}"
                   f", nicht anrechenbar EUR {a.excess_eur.quantize(self.TWO_PLACES, context=self.ctx)}"
                   if a.status is WithholdingStatus.ABOVE_TREATY_RATE else "")
                for ev, a in rows
            )

        for (status, state), rows in sorted(treaty_flags.items(), key=lambda kv: (kv[0][0].value, kv[0][1])):
            state_label = state or "unbekannter Quellenstaat"
            if status is WithholdingStatus.ABOVE_TREATY_RATE:
                withheld = sum((a.withheld_eur for _, a in rows), Decimal("0"))
                creditable = sum((a.creditable_eur for _, a in rows), Decimal("0"))
                excess = sum((a.excess_eur for _, a in rows), Decimal("0"))
                rate = rows[0][1].treaty_rate
                detail = (
                    f"{len(rows)} Quellensteuerzeile(n) aus {state_label} wurden ÜBER dem "
                    f"anrechenbaren Satz ({(rate * 100).normalize():f}%) einbehalten. Nur die Steuer "
                    f"bis zu diesem Satz ist "
                    f"anrechenbar (§ 32d Abs. 5 Satz 1, Ermäßigungsanspruch): von einbehaltenen "
                    f"EUR {withheld.quantize(self.TWO_PLACES, context=self.ctx)} sind EUR "
                    f"{creditable.quantize(self.TWO_PLACES, context=self.ctx)} auf Zeile 41 "
                    f"angerechnet; EUR {excess.quantize(self.TWO_PLACES, context=self.ctx)} sind "
                    f"in Deutschland NICHT anrechenbar und im Quellenstaat zu erstatten (für die "
                    f"USA über das IRS-Erstattungsverfahren). Nachweis der einbehaltenen Steuer und "
                    f"des anrechenbaren Satzes ist erforderlich (§ 90 Abs. 2 AO). Zeilen: {_rowlist(rows)}."
                )
            else:
                detail = f"{self._unsupported_reason(status, state, rows)} Zeilen: {_rowlist(rows)}."
            self.data_gap_collector.record(
                code=f"FOREIGN_WHT_{status.value}",
                subject=f"Anlage KAP Zeile 41 / {state_label} ({self.tax_year})",
                detail=detail,
                severity=GapSeverity.WARNING,
            )
        if unsupported:
            self.data_gap_collector.record(
                code="FOREIGN_WHT_CREDIT_UNSUPPORTED",
                subject=f"Anlage KAP Zeile 41 ({self.tax_year})",
                detail=self._unsupported_credit_detail(unsupported),
                severity=GapSeverity.FAIL_FAST,
            )

    def _unsupported_reason(self, status: WithholdingStatus, state: str, rows) -> str:
        """Why these rows have no supported creditable amount, and what resolves it."""
        count = len(rows)
        reasons = "; ".join(sorted({a.reason for _, a in rows if a.reason}))
        state_label = state or "unbekannter Quellenstaat"
        if status is WithholdingStatus.RATE_NOT_VERIFIED and not state:
            return (f"{count} Quellensteuerzeile(n) ohne Quellenstaat: der Export nennt keinen. "
                    f"Bei Quellensteuer auf Habenzinsen ist es das Land der IBKR-Gesellschaft, die "
                    f"die Zinsen zahlt: BROKER_ENTITY_COUNTRY in src/config.py setzen (siehe README).")
        if status is WithholdingStatus.RATE_NOT_VERIFIED:
            return (f"{count} Quellensteuerzeile(n) aus {state_label}: für diesen Quellenstaat bzw. "
                    f"diese Ertragsart ist im Referenzbestand kein anrechenbarer Satz hinterlegt. "
                    f"Den Satz in reference/ recherchieren (docs/knowledge-store.md), dann ergänzen.")
        if status is WithholdingStatus.RATE_YEAR_NOT_RESEARCHED:
            return (f"{count} Quellensteuerzeile(n) aus {state_label}: für das Steuerjahr "
                    f"{self.tax_year} ist die BZSt-Übersicht (Stand 1. Januar {self.tax_year}) nicht "
                    f"eingelesen; Sätze anderer Jahre werden nicht übernommen.")
        if status is WithholdingStatus.FACTS_UNANSWERED:
            return (f"{count} Quellensteuerzeile(n) aus {state_label}: der anrechenbare Satz hängt von "
                    f"Angaben ab, die der Export nicht enthält. Offen: {reasons} Im interaktiven Lauf "
                    f"beantworten (--interactive) oder in cache/withholding_facts.json eintragen "
                    f"(siehe README).")
        if status is WithholdingStatus.CONDITION_NOT_MET:
            return (f"{count} Quellensteuerzeile(n) aus {state_label}: nach Ihren Angaben gilt der "
                    f"anrechenbare Satz nicht ({reasons}); der anrechenbare Betrag ist nicht ermittelbar.")
        return (f"{count} Quellensteuerzeile(n) konnten keinem Ertrag desselben Kontos zugeordnet "
                f"werden, sodass der einbehaltene Satz nicht gegen den anrechenbaren Satz geprüft "
                f"werden kann.")

    def _isins(self, rows) -> str:
        isins = sorted({getattr(self.asset_resolver.get_asset_by_id(ev.asset_internal_id), "ibkr_isin", None) or "—"
                        for ev, _ in rows})
        return " (ISIN: " + ", ".join(isins) + ")"

    def _unsupported_credit_detail(self, unsupported: Dict[tuple, List[tuple]]) -> str:
        """The one fatal message naming every row with no supported creditable amount."""
        parts = [self._unsupported_reason(status, state, rows)
                 + " Transaktionen: " + ", ".join(ev.ibkr_transaction_id or "—" for ev, _ in rows)
                 + self._isins(rows) + "."
                 for (status, state), rows in sorted(unsupported.items(), key=lambda kv: (kv[0][0].value, kv[0][1]))]
        return ("Für Anlage KAP Zeile 41 ist nicht jede ausländische Quellensteuer belegbar anrechenbar. "
                "Weder der einbehaltene Betrag noch null darf an ihre Stelle treten; es werden keine "
                "Zahlen ausgegeben. " + " ".join(parts))

    def calculate_reporting_figures(self) -> LossOffsettingResult:
        result = LossOffsettingResult()

        stock_gains_gross = self.ctx.create_decimal(Decimal('0'))
        stock_losses_abs = self.ctx.create_decimal(Decimal('0'))
        derivative_gains_gross = self.ctx.create_decimal(Decimal('0'))
        derivative_losses_abs = self.ctx.create_decimal(Decimal('0'))
        kap_other_income_positive = self.ctx.create_decimal(Decimal('0'))
        kap_other_losses_abs = self.ctx.create_decimal(Decimal('0'))

        fund_income_net_taxable = self.ctx.create_decimal(Decimal('0'))

        p23_net_total = self.ctx.create_decimal(Decimal('0'))

        # Anlage SO, Leistungen (22 Nr. 3 EStG). Deliberately its own accumulator and not
        # one of the 20 EStG pools above: a different Einkunftsart, so it is outside
        # 20 Abs. 6 offsetting and outside the Sparer-Pauschbetrag.
        so_leistungen_einnahmen = self.ctx.create_decimal(Decimal('0'))

        for rgl in self.realized_gains_losses:
            gross_gl_eur = rgl.gross_gain_loss_eur if rgl.gross_gain_loss_eur is not None else self.ctx.create_decimal(Decimal('0'))

            cat = rgl.asset_category_at_realization
            if cat == AssetCategory.STOCK:
                if gross_gl_eur > Decimal('0'):
                    stock_gains_gross = self.ctx.add(stock_gains_gross, gross_gl_eur)
                else:
                    stock_losses_abs = self.ctx.add(stock_losses_abs, gross_gl_eur.copy_abs())
            elif cat in [AssetCategory.OPTION, AssetCategory.CFD, AssetCategory.FUTURE]:
                if gross_gl_eur > Decimal('0'):
                    derivative_gains_gross = self.ctx.add(derivative_gains_gross, gross_gl_eur)
                elif rgl.is_stillhalter_income:
                    # Negative Nr. 11 income is not a Termingeschaeft loss.
                    # GT-ESTG20-004; in 2023/24 this reaches Z19/Z22, not Z24.
                    kap_other_losses_abs = self.ctx.add(kap_other_losses_abs, gross_gl_eur.copy_abs())
                else:
                    derivative_losses_abs = self.ctx.add(derivative_losses_abs, gross_gl_eur.copy_abs())
            elif cat in [AssetCategory.BOND, AssetCategory.SONSTIGE_KAPITALFORDERUNG]:
                # Both are 20 Abs. 2 Satz 1 Nr. 7 income: Zeile 19 for a gain, Zeile 22 for
                # a loss. SONSTIGE_KAPITALFORDERUNG carries the Nr. 7 instruments that are
                # not bonds -- unbacked commodity ETCs ([GT-ESTG23-011], Rz. 57),
                # Zertifikate and unallocated spot metal ([GT-ESTG20-038], Rz. 9).
                if gross_gl_eur > Decimal('0'):
                    kap_other_income_positive = self.ctx.add(kap_other_income_positive, gross_gl_eur)
                else:
                    kap_other_losses_abs = self.ctx.add(kap_other_losses_abs, gross_gl_eur.copy_abs())
            elif cat == AssetCategory.INVESTMENT_FUND:
                net_gl_eur_after_tf = rgl.net_gain_loss_after_teilfreistellung_eur
                if net_gl_eur_after_tf is None:
                     logger.warning(f"RGL {rgl.originating_event_id} for fund {rgl.asset_internal_id} has no net_gain_loss_after_teilfreistellung_eur. Using gross_gain_loss_eur.")
                     net_gl_eur_after_tf = gross_gl_eur

                fund_income_net_taxable = self.ctx.add(fund_income_net_taxable, net_gl_eur_after_tf)

            elif cat == AssetCategory.PRIVATE_SALE_ASSET:
                if rgl.is_taxable_under_section_23:
                    p23_net_total = self.ctx.add(p23_net_total, gross_gl_eur)

            elif cat == AssetCategory.CASH_BALANCE:
                # FX gains/losses go to "Other Capital Income" under Section 20 EStG
                # Per BMF circular May 2022 (para. 131): IBKR FX reserves are interest-bearing
                if gross_gl_eur > Decimal('0'):
                    kap_other_income_positive = self.ctx.add(kap_other_income_positive, gross_gl_eur)
                else:
                    kap_other_losses_abs = self.ctx.add(kap_other_losses_abs, gross_gl_eur.copy_abs())

        stueckzinsen_paid_sum = self.ctx.create_decimal(Decimal('0')) # Only used for logging/future explicit handling

        for event in self.current_year_financial_events:
            asset_resolved = self.asset_resolver.get_asset_by_id(event.asset_internal_id)
            if not asset_resolved:
                raise ProcessingError(f"LossOffsettingEngine: could not resolve asset ID {event.asset_internal_id} for financial event {event.event_id} ({event.event_type.name}).")

            event_gross_eur = event.gross_amount_eur if event.gross_amount_eur is not None else self.ctx.create_decimal(Decimal('0'))

            if event.event_type == FinancialEventType.DIVIDEND_CASH and isinstance(asset_resolved, Asset) and asset_resolved.asset_category == AssetCategory.STOCK:
                if event_gross_eur > Decimal('0'):
                    kap_other_income_positive = self.ctx.add(kap_other_income_positive, event_gross_eur)
            elif event.event_type == FinancialEventType.INTEREST_RECEIVED:
                 if event_gross_eur > Decimal('0'):
                    kap_other_income_positive = self.ctx.add(kap_other_income_positive, event_gross_eur)
            elif event.event_type == FinancialEventType.SECURITIES_LENDING_FEE_RECEIVED:
                # 22 Nr. 3 EStG, not 20 EStG: [GT-ESTG20-049], [GT-ESTG20-050]. It must not
                # touch kap_other_income_positive, or it re-enters Zeile 19 and the 20 Abs. 6
                # pools through the back door. Declared GROSS — 22 Nr. 3 Satz 2's 256 EUR
                # Freigrenze and Satz 3's ring-fencing both operate on the taxpayer's total
                # income of that kind from every source, which one broker export cannot
                # establish; same position as GT-ESTG23-009 takes on the 23 EStG Freigrenze.
                if event_gross_eur > Decimal('0'):
                    so_leistungen_einnahmen = self.ctx.add(so_leistungen_einnahmen, event_gross_eur)
            elif event.event_type == FinancialEventType.INTEREST_PAID_STUECKZINSEN:
                 stueckzinsen_paid_sum = self.ctx.add(stueckzinsen_paid_sum, event_gross_eur.copy_abs())
                 # According to PRD Section 2.6, paid Stückzinsen reduce "Other Capital Income".
                 # If they are reliably parsed as negative amounts, this would be:
                 # kap_other_income_positive = self.ctx.add(kap_other_income_positive, event_gross_eur)
                 # Or if always positive cost:
                 if event_gross_eur.copy_abs() > Decimal('0'): # ensure non-zero before adding to losses
                    kap_other_losses_abs = self.ctx.add(kap_other_losses_abs, event_gross_eur.copy_abs())

            elif event.event_type == FinancialEventType.DISTRIBUTION_FUND and isinstance(asset_resolved, InvestmentFund):
                net_dist_eur = self._calculate_net_fund_distribution(event, asset_resolved)
                fund_income_net_taxable = self.ctx.add(fund_income_net_taxable, net_dist_eur)
            elif event.event_type == FinancialEventType.CORP_STOCK_DIVIDEND:
                 if isinstance(asset_resolved, Asset) and asset_resolved.asset_category == AssetCategory.STOCK and event_gross_eur > Decimal('0'):
                    kap_other_income_positive = self.ctx.add(kap_other_income_positive, event_gross_eur)
            elif event.event_type == FinancialEventType.CAPITAL_REPAYMENT:
                 # Capital repayments themselves don't create taxable income
                 # Excess amounts are now handled as separate DIVIDEND_CASH events
                 pass

        for vp_item in self.vorabpauschale_items:
            # `declaration_year` is the VZ this Vorabpauschale belongs on: the VP for calendar
            # X flows on the first working day of X+1 (18 Abs. 3 InvStG). The engine builds the
            # items for calendar `tax_year - 1`, so this selects them.
            if vp_item.declaration_year == self.tax_year:
                net_vp_eur = vp_item.net_taxable_vorabpauschale_eur
                if net_vp_eur is None:
                    logger.warning(f"Vorabpauschale item for asset {vp_item.asset_internal_id} has no net_taxable_vorabpauschale_eur. Assuming 0.")
                    net_vp_eur = self.ctx.create_decimal(Decimal('0'))

                fund_income_net_taxable = self.ctx.add(fund_income_net_taxable, net_vp_eur)

        result.conceptual_fund_income_net_taxable = fund_income_net_taxable.quantize(self.TWO_PLACES, context=self.ctx)

        # --- Anlage KAP-INV Zeile 53 ---
        # "Waehrend der Besitzzeit angesetzte Vorabpauschalen", before Teilfreistellung
        # (19 Abs. 1 S. 3-4 InvStG). The Vorabpauschale accumulated over the holding period OF
        # THE UNITS DISPOSED OF, across every year they were held, and only so far as it was
        # actually declared -- which the FIFO ledger has already attributed lot by lot, from
        # the record of what was declared (src/processing/vorabpauschale_declarations.py).
        # Summed here, and nothing more: this is a memo figure. The gain lines below are
        # already net of it, because the form's Zeile 54 subtracts Zeile 53 before the result
        # is carried to Zeilen 14/17/20/23/26 (GT-FORM-032, GT-FORM-033).
        #
        # Until 2026-08-03 this line carried the sum of the CURRENT year's gross
        # Vorabpauschalen under the label "Z55" -- wrong line, wrong quantity, and plausible
        # enough to file. Between then and #63 it carried nothing and reported a gap.
        # See reference/investment-tax-law/invstg-19-veraeusserungsgewinne.md.
        vorabpauschale_deduction_total = self.ctx.create_decimal(Decimal('0'))
        for rgl in self.realized_gains_losses:
            if rgl.asset_category_at_realization != AssetCategory.INVESTMENT_FUND:
                continue
            if rgl.vorabpauschale_deduction_eur:
                vorabpauschale_deduction_total = self.ctx.add(
                    vorabpauschale_deduction_total, rgl.vorabpauschale_deduction_eur)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_INV_VORABPAUSCHALE_ABZUG_Z53] = (
            vorabpauschale_deduction_total.quantize(self.TWO_PLACES, context=self.ctx))

        # Calculate foreign tax paid (Zeile 41). German KESt is not an auslaendische Steuer and
        # is excluded here -- see _is_german_kest and _record_german_kest_gap.
        # legal_basis: reference/tax-forms/anlage-kap-zeilen.md [GT-FORM-007].
        foreign_tax_total = self.ctx.create_decimal(Decimal('0'))
        german_kest_total = self.ctx.create_decimal(Decimal('0'))
        german_kest_count = 0
        income_by_id = self._income_event_by_event_id()
        # Rows the treaty-rate guard could not credit in full, grouped for one gap per
        # (status, source state). A capped row is reported; a row with no supported
        # creditable amount stops the run once all are collected (F1).
        treaty_flags: Dict[tuple, List[tuple]] = defaultdict(list)
        # The treaty limits all the tax on one income ([GT-CREDIT-027]), so the foreign
        # rows are assessed per linked income; a row with no income in this year stands alone.
        foreign_rows: List[WithholdingTaxEvent] = []
        rows_by_income: Dict[object, List[WithholdingTaxEvent]] = defaultdict(list)
        for event in self.current_year_financial_events:
            if isinstance(event, WithholdingTaxEvent):
                tax_amount = event.gross_amount_eur if event.gross_amount_eur is not None else self.ctx.create_decimal(Decimal('0'))
                if self._is_german_kest(event):
                    german_kest_total = self.ctx.add(german_kest_total, tax_amount)
                    german_kest_count += 1
                    continue
                foreign_rows.append(event)
                income_event = income_by_id.get(event.taxed_income_event_id)
                rows_by_income[income_event.event_id if income_event else id(event)].append(event)
        assessments: Dict[int, WithholdingAssessment] = {}
        for rows in rows_by_income.values():
            income = income_by_id.get(rows[0].taxed_income_event_id)
            # The rate depends on what the instrument is ([GT-CREDIT-029], column F).
            income_asset = self.asset_resolver.get_asset_by_id(income.asset_internal_id) if income else None
            category = income_asset.asset_category if income_asset else None
            facts = income_asset.withholding_facts.get(self.tax_year) if income_asset else None
            for row, assessment in zip(rows, assess_withholdings(rows, income, self.tax_year, category, facts)):
                assessments[id(row)] = assessment
        for event in foreign_rows:
            assessment = assessments[id(event)]
            # Only the anrechenbare amount reaches Zeile 41: the withheld tax reduced
            # by the source state's Ermäßigungsanspruch ([GT-CREDIT-026]). For a row at
            # or below the treaty rate this equals what was withheld, so no figure
            # moves; measured 0 US rows above the rate VZ 2023–2025 (issue #78).
            if assessment.creditable_eur is not None:
                foreign_tax_total = self.ctx.add(foreign_tax_total, assessment.creditable_eur)
            result.creditable_foreign_wht_eur[event.event_id] = assessment.creditable_eur
            result.foreign_wht_status[event.event_id] = (assessment.status.value, assessment.treaty_rate)
            if assessment.status is not WithholdingStatus.OK:
                treaty_flags[(assessment.status, assessment.source_state or "")].append((event, assessment))
        self._record_german_kest_gap(german_kest_count, german_kest_total)
        self._record_treaty_withholding_gaps(treaty_flags)

        # Store raw component values for reporters (always available regardless of form year)
        result.raw_derivative_gains_gross = derivative_gains_gross.quantize(self.TWO_PLACES, context=self.ctx)
        result.raw_derivative_losses_abs = derivative_losses_abs.quantize(self.TWO_PLACES, context=self.ctx)
        result.raw_other_losses_abs = kap_other_losses_abs.quantize(self.TWO_PLACES, context=self.ctx)

        # Year-specific form rules
        form_rules = get_form_rules(self.tax_year)

        # Anlage KAP Line Calculations (as per PRD Sec 2.7, year-dependent)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AKTIEN_GEWINN] = stock_gains_gross.quantize(self.TWO_PLACES, context=self.ctx)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AKTIEN_VERLUST] = stock_losses_abs.quantize(self.TWO_PLACES, context=self.ctx)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE] = kap_other_income_positive.quantize(self.TWO_PLACES, context=self.ctx)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID] = foreign_tax_total.quantize(self.TWO_PLACES, context=self.ctx)

        if form_rules.separate_derivative_lines:
            # <= 2024: Separate Z21 (derivative gains) and Z24 (derivative losses)
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN] = derivative_gains_gross.quantize(self.TWO_PLACES, context=self.ctx)
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_TERMIN_VERLUST] = derivative_losses_abs.quantize(self.TWO_PLACES, context=self.ctx)
            # Z22: only non-stock, non-derivative losses
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE] = kap_other_losses_abs.quantize(self.TWO_PLACES, context=self.ctx)
        else:
            # >= 2025: No separate derivative lines; derivative losses fold into Z22
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN] = Decimal('0.00')
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_TERMIN_VERLUST] = Decimal('0.00')
            z22_combined = self.ctx.add(kap_other_losses_abs, derivative_losses_abs)
            result.form_line_values[TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE] = z22_combined.quantize(self.TWO_PLACES, context=self.ctx)

        # Zeile 19 Calculation
        zeile_19_amount = self.ctx.add(stock_gains_gross, derivative_gains_gross)
        zeile_19_amount = self.ctx.add(zeile_19_amount, kap_other_income_positive)
        zeile_19_amount = self.ctx.subtract(zeile_19_amount, stock_losses_abs)
        zeile_19_amount = self.ctx.subtract(zeile_19_amount, kap_other_losses_abs)
        if form_rules.z19_subtracts_derivative_losses:
            # >= 2025: Derivative losses are no longer restricted, subtract them in Z19
            zeile_19_amount = self.ctx.subtract(zeile_19_amount, derivative_losses_abs)
        result.form_line_values[TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT] = zeile_19_amount.quantize(self.TWO_PLACES, context=self.ctx)


        # GT-FORM-020: the annual destination is resolved by the reporters.
        result.form_line_values["ANLAGE_SO_NET_GV"] = p23_net_total.quantize(self.TWO_PLACES, context=self.ctx)
        # Leistungen (22 Nr. 3), written unconditionally so an empty year reads as "nothing
        # to declare" rather than "not computed". The Zeile is year-dependent and lives in
        # the registry, not in this key: [GT-FORM-024].
        result.form_line_values[TaxReportingCategory.ANLAGE_SO_LEISTUNGEN_EINNAHMEN] = (
            so_leistungen_einnahmen.quantize(self.TWO_PLACES, context=self.ctx))

        # Anlage KAP-INV (Gross Figures)
        kap_inv_gross_dist_collector = defaultdict(lambda: self.ctx.create_decimal(Decimal('0')))
        kap_inv_gross_gl_collector = defaultdict(lambda: self.ctx.create_decimal(Decimal('0')))
        kap_inv_gross_vop_collector = defaultdict(lambda: self.ctx.create_decimal(Decimal('0'))) # Should be 0 for 2023

        for event in self.current_year_financial_events:
            if isinstance(event, CashFlowEvent) and event.event_type == FinancialEventType.DISTRIBUTION_FUND:
                asset = self.asset_resolver.get_asset_by_id(event.asset_internal_id)
                if isinstance(asset, InvestmentFund) and event.gross_amount_eur is not None:
                    from src.reporting.reporting_utils import get_kap_inv_category_for_reporting
                    reporting_cat = get_kap_inv_category_for_reporting(asset.fund_type, is_distribution=True, is_gain=False) # For distributions
                    if reporting_cat:
                        kap_inv_gross_dist_collector[reporting_cat] = self.ctx.add(kap_inv_gross_dist_collector[reporting_cat], event.gross_amount_eur)

        for key, val in kap_inv_gross_dist_collector.items():
            result.form_line_values[key] = val.quantize(self.TWO_PLACES, context=self.ctx)

        for rgl in self.realized_gains_losses:
            if rgl.asset_category_at_realization == AssetCategory.INVESTMENT_FUND and rgl.gross_gain_loss_eur is not None:
                from src.reporting.reporting_utils import get_kap_inv_category_for_reporting
                reporting_cat = get_kap_inv_category_for_reporting(rgl.fund_type_at_sale, is_distribution=False, is_gain=True)
                # The Veraeusserungsgewinn of Zeile 54, which is what these lines carry: the
                # gain AFTER the Zeile 53 deduction (19 Abs. 1 S. 3). Identical to the gross
                # figure wherever no Vorabpauschale was declared over the holding period.
                gain_for_the_form = rgl.gain_after_vorabpauschale_eur
                if gain_for_the_form is None:
                    gain_for_the_form = rgl.gross_gain_loss_eur
                if reporting_cat:
                     if rgl.tax_reporting_category:
                         kap_inv_gross_gl_collector[rgl.tax_reporting_category] = self.ctx.add(kap_inv_gross_gl_collector[rgl.tax_reporting_category], gain_for_the_form)
                     else:
                         logger.warning(f"RGL for fund {rgl.asset_internal_id} missing tax_reporting_category. Using derived category {reporting_cat}.")
                         kap_inv_gross_gl_collector[reporting_cat] = self.ctx.add(kap_inv_gross_gl_collector[reporting_cat], gain_for_the_form)


        for key, val in kap_inv_gross_gl_collector.items():
            result.form_line_values[key] = val.quantize(self.TWO_PLACES, context=self.ctx)

        # Gross Vorabpauschale onto Zeilen 9-13, selected by DECLARATION year: the VP for
        # calendar X is declared in VZ X+1 (18 Abs. 3 InvStG).
        for vp_item in self.vorabpauschale_items:
             if vp_item.declaration_year == self.tax_year and vp_item.gross_vorabpauschale_eur != Decimal(0):
                if vp_item.tax_reporting_category_gross:
                     kap_inv_gross_vop_collector[vp_item.tax_reporting_category_gross] = self.ctx.add(kap_inv_gross_vop_collector[vp_item.tax_reporting_category_gross], vp_item.gross_vorabpauschale_eur)

        for key, val in kap_inv_gross_vop_collector.items():
            result.form_line_values[key] = val.quantize(self.TWO_PLACES, context=self.ctx)

        # Conceptual Net Balances (as per PRD Sec 2.8)
        result.conceptual_net_stocks = (self.ctx.subtract(stock_gains_gross, stock_losses_abs)).quantize(self.TWO_PLACES, context=self.ctx)
        result.conceptual_net_other_income = (self.ctx.subtract(kap_other_income_positive, kap_other_losses_abs)).quantize(self.TWO_PLACES, context=self.ctx)
        result.conceptual_net_p23_estg = p23_net_total.quantize(self.TWO_PLACES, context=self.ctx)

        net_derivatives_uncapped = self.ctx.subtract(derivative_gains_gross, derivative_losses_abs)
        result.conceptual_net_derivatives_uncapped = net_derivatives_uncapped.quantize(self.TWO_PLACES, context=self.ctx)

        if form_rules.derivative_loss_cap_applies and self.apply_conceptual_derivative_loss_capping and net_derivatives_uncapped < Decimal('0'):
            capped_net_derivative_loss = max(net_derivatives_uncapped, self.ctx.create_decimal(Decimal('-20000')))
            result.conceptual_net_derivatives_capped = capped_net_derivative_loss.quantize(self.TWO_PLACES, context=self.ctx)
        else:
            result.conceptual_net_derivatives_capped = net_derivatives_uncapped.quantize(self.TWO_PLACES, context=self.ctx)

        return result

# src/reporting/pdf_generator.py
import logging
from decimal import Decimal, ROUND_HALF_UP # Added ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from src.domain.results import LossOffsettingResult, RealizedGainLoss, VorabpauschaleData
from src.domain.events import FinancialEvent, CashFlowEvent, WithholdingTaxEvent, CorporateActionEvent, \
    CorpActionSplitForward, CorpActionMergerCash, CorpActionStockDividend, CorpActionMergerStock
from src.domain.assets import Asset, InvestmentFund, Stock, Bond, Derivative
from src.domain.enums import AssetCategory, InvestmentFundType, FinancialEventType, RealizationType, TaxReportingCategory
from src.reporting.reporting_utils import _q, _q_price, _q_qty, format_date_german
import src.config as app_config 
from src.utils.tax_utils import get_teilfreistellung_rate_for_fund_type

logger = logging.getLogger(__name__)

class PdfReportGenerator:
    def __init__(self,
                 loss_offsetting_result: LossOffsettingResult,
                 all_financial_events: List[FinancialEvent],
                 realized_gains_losses: List[RealizedGainLoss],
                 vorabpauschale_items: List[VorabpauschaleData],
                 assets_by_id: Dict[uuid.UUID, Asset],
                 tax_year: int,
                 eoy_mismatch_details: Optional[List[Dict[str, Any]]],
                 report_version: str = "v1.0"):
        self.loss_offsetting_result = loss_offsetting_result
        self.all_financial_events = all_financial_events
        self.realized_gains_losses = realized_gains_losses
        self.vorabpauschale_items = vorabpauschale_items
        self.assets_by_id = assets_by_id
        self.tax_year = tax_year
        self.eoy_mismatch_details = eoy_mismatch_details if eoy_mismatch_details else []
        self.report_version = report_version

        self.styles = self._generate_styles()
        self.story: List[Any] = []
        self.prepared_wht_details_for_table: Optional[Dict[str, Dict[str, Decimal]]] = None


    def _generate_styles(self):
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(name='H1', fontSize=16, leading=20, spaceAfter=10, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='H2', fontSize=14, leading=18, spaceAfter=8, spaceBefore=12, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='H3', fontSize=12, leading=16, spaceAfter=6, spaceBefore=10, fontName='Helvetica-Bold'))

        body_text_style = styles['BodyText']
        body_text_style.fontSize = 10
        body_text_style.leading = 12
        body_text_style.spaceAfter = 6
        body_text_style.fontName = 'Helvetica'

        styles.add(ParagraphStyle(name='SmallText', fontSize=8, leading=10, spaceAfter=4, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='Disclaimer', fontSize=8, leading=10, spaceAfter=12, alignment=TA_JUSTIFY, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='TableHeader', alignment=TA_CENTER, fontSize=8, fontName='Helvetica-Bold', textColor=colors.black))
        styles.add(ParagraphStyle(name='TableCell', alignment=TA_LEFT, fontSize=8, fontName='Helvetica', textColor=colors.black))
        styles.add(ParagraphStyle(name='TableCellRight', alignment=TA_RIGHT, fontSize=8, fontName='Helvetica', textColor=colors.black))
        
        return styles

    def _format_taxed_transaction_description(self, income_event: FinancialEvent, wht_date: str) -> str:
        """Format a description of the taxed transaction for the PDF report."""
        from src.reporting.reporting_utils import format_date_german
        
        # Get transaction type description
        type_descriptions = {
            FinancialEventType.DIVIDEND_CASH: "Dividende",
            FinancialEventType.DISTRIBUTION_FUND: "Fondsausschüttung", 
            FinancialEventType.INTEREST_RECEIVED: "Zinszahlung",
            FinancialEventType.PAYMENT_IN_LIEU_DIVIDEND: "Dividendenersatz",
            FinancialEventType.CAPITAL_REPAYMENT: "Kapitalrückzahlung"
        }
        
        transaction_type = type_descriptions.get(income_event.event_type, income_event.event_type.name)
        
        # Get asset information
        asset = self.assets_by_id.get(income_event.asset_internal_id)
        asset_symbol = ""
        if asset:
            if hasattr(asset, 'ibkr_symbol') and asset.ibkr_symbol:
                asset_symbol = asset.ibkr_symbol
            elif hasattr(asset, 'description') and asset.description:
                # Extract symbol from description if available
                desc = asset.description
                if '(' in desc and ')' in desc:
                    # Try to extract symbol from description like "Apple Inc (AAPL)"
                    import re
                    symbol_match = re.search(r'\(([A-Z]{1,5})\)', desc)
                    if symbol_match:
                        asset_symbol = symbol_match.group(1)
                    else:
                        asset_symbol = desc[:10]  # First 10 chars as fallback
                else:
                    asset_symbol = desc[:10]  # First 10 chars as fallback
        
        # Format the transaction date
        transaction_date = format_date_german(income_event.event_date)
        
        # Combine into description
        parts = [transaction_type]
        if asset_symbol:
            parts.append(f"({asset_symbol})")
        if income_event.event_date != wht_date:  # Only show date if different from WHT date
            parts.append(f"vom {transaction_date}")
        
        return " ".join(parts)

    def _format_decimal(self, value: Optional[Decimal | float | int | str], precision_type: str = "total") -> str:
        if value is None:
            return ""
        
        # Ensure dec_value is a Decimal
        if not isinstance(value, Decimal):
            try:
                dec_value = Decimal(str(value))
            except Exception:
                logger.warning(f"Could not convert value '{value}' type {type(value)} to Decimal in _format_decimal. Returning empty string.")
                return ""
        else:
            dec_value = value # It's already a Decimal

        if precision_type == "price":
            return str(_q_price(dec_value)) 
        elif precision_type == "integer_quantity":
             return str(dec_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)) 
        elif precision_type == "quantity": 
            return str(_q_qty(dec_value)) 
        # Default is "total" for monetary amounts
        return str(_q(dec_value))


    def _create_styled_table(self, data: List[List[Any]], col_widths: Optional[List[float]] = None, extra_styles: Optional[List[Any]] = None, repeatRows=1) -> Table:
        styled_data = []
        for i, row_content in enumerate(data):
            styled_row = []
            for j, cell_content in enumerate(row_content):
                current_style_name = 'TableCell'
                if i < repeatRows: # Header rows
                    current_style_name = 'TableHeader'
                # Check original data type for alignment hint, not the potentially pre-formatted string/paragraph
                original_cell_data = data[i][j] if isinstance(data[i][j], (Decimal, float, int)) else None
                if isinstance(data[i][j], Paragraph) and hasattr(data[i][j], 'meta_is_numeric'): # Custom attribute if needed
                    original_cell_data = data[i][j].meta_is_numeric # Assuming Paragraph could carry a hint

                if original_cell_data is not None : # If original was numeric
                     current_style_name = 'TableCellRight'


                if isinstance(cell_content, Paragraph):
                    styled_row.append(cell_content)
                elif isinstance(cell_content, (Decimal, float, int, str)):
                    text_content = str(cell_content) # Default to string
                    # Format if it's a number, but use a consistent style (TableCell or TableCellRight for numbers)
                    # The alignment is better handled by the Paragraph style itself.
                    # Let's try to make cell_content a Paragraph if it's not one already.
                    
                    # If it's a number, format it and align right by default
                    if isinstance(cell_content, (Decimal, float, int)):
                        # Apply default formatting if not already a string from _format_decimal
                        # This path is usually taken if _format_decimal wasn't called before putting in table data
                        text_content = self._format_decimal(Decimal(str(cell_content))) 
                        text_content = text_content.replace('.', ',') # German format for display
                        styled_row.append(Paragraph(text_content, self.styles['TableCellRight']))
                    elif isinstance(cell_content, str): # If it's a string
                        # If it looks like a number already formatted (e.g. "1.234,56"), align right
                        if cell_content and (cell_content[0].isdigit() or (cell_content.startswith('-') and len(cell_content) > 1 and cell_content[1].isdigit())):
                             styled_row.append(Paragraph(cell_content, self.styles['TableCellRight']))
                        else: # Align left for other strings
                             styled_row.append(Paragraph(text_content, self.styles['TableCell']))
                    else: # Fallback for other types
                        styled_row.append(Paragraph(str(cell_content), self.styles['TableCell']))

                else: # Other types (e.g. None, could be Spacer etc.)
                     styled_row.append(cell_content)
            styled_data.append(styled_row)
        
        tbl = Table(styled_data, colWidths=col_widths, repeatRows=repeatRows)
        
        base_ts_cmds = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]
        if repeatRows > 0:
            base_ts_cmds.append(('BACKGROUND', (0, 0), (-1, repeatRows -1), colors.lightgrey))
            # Ensure header text is styled via Paragraph styles, not TableStyle for font
        
        if extra_styles:
            base_ts_cmds.extend(extra_styles)
        
        tbl.setStyle(TableStyle(base_ts_cmds))
        return tbl

    def _add_title_page(self):
        self.story.append(Paragraph(f"Detaillierter Bericht zur Steuererklärung für Kapitaleinkünfte {self.tax_year}", self.styles['H1']))
        self.story.append(Spacer(1, 1*cm))
        self.story.append(Paragraph(f"Steuerjahr: {self.tax_year}", self.styles['BodyText']))
        self.story.append(Paragraph(f"Name des Steuerpflichtigen: {app_config.TAXPAYER_NAME}", self.styles['BodyText']))
        self.story.append(Paragraph(f"Konto-ID: {app_config.ACCOUNT_ID}", self.styles['BodyText'])) 
        self.story.append(Paragraph(f"Datum der Reporterstellung: {datetime.now().strftime('%d.%m.%Y')}", self.styles['BodyText']))
        self.story.append(Paragraph(f"Tool-Name und Version: IBKR German Tax Declaration Engine {self.report_version}", self.styles['BodyText']))
        self.story.append(Spacer(1, 0.5*cm))
        disclaimer_text = ("Dieser Bericht wurde automatisch auf Basis der bereitgestellten IBKR-Daten generiert. "
                           "Er dient der Unterstützung bei der Steuererklärung und stellt keine Steuerberatung dar. "
                           "Alle Zahlen sollten auf ihre Richtigkeit überprüft werden.")
        self.story.append(Paragraph(disclaimer_text, self.styles['Disclaimer']))

    def _add_declared_values_summary(self):
        self.story.append(Paragraph("Zusammenfassung der erklärten Werte", self.styles['H2']))
        
        data = [["Steuerformular Zeile", "Wert (EUR)"]]

        kap_lines_map = {
            "ANLAGE_KAP_ZEILE_19": "Anlage KAP Zeile 19 (Ausl. Kapitalerträge n. Sald.)",
            "ANLAGE_KAP_ZEILE_20": "Anlage KAP Zeile 20 (Gewinne Aktienveräußerungen)",
            "ANLAGE_KAP_ZEILE_21": "Anlage KAP Zeile 21 (Gewinne Termingeschäfte)",
            "ANLAGE_KAP_ZEILE_22": "Anlage KAP Zeile 22 (Sonstige Verluste)",
            "ANLAGE_KAP_ZEILE_23": "Anlage KAP Zeile 23 (Verluste Aktienveräußerungen)",
            "ANLAGE_KAP_ZEILE_24": "Anlage KAP Zeile 24 (Verluste Termingeschäfte)",
            "ANLAGE_KAP_ZEILE_41": "Anlage KAP Zeile 41 (Anrech. ausl. Steuern)"
        }
        kap_inv_lines_map = {
            "ANLAGE_KAP_INV_ZEILE_4_AKTIENFONDS_AUSSCHUETTUNG_GROSS": "KAP-INV Z4 (Brutto Auss. Aktienfonds)",
            "ANLAGE_KAP_INV_ZEILE_5_MISCHFONDS_AUSSCHUETTUNG_GROSS": "KAP-INV Z5 (Brutto Auss. Mischfonds)",
            "ANLAGE_KAP_INV_ZEILE_6_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS": "KAP-INV Z6 (Brutto Auss. Immofonds)",
            "ANLAGE_KAP_INV_ZEILE_7_AUSLANDS_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS": "KAP-INV Z7 (Brutto Auss. Ausl. Immofonds)",
            "ANLAGE_KAP_INV_ZEILE_8_SONSTIGE_FONDS_AUSSCHUETTUNG_GROSS": "KAP-INV Z8 (Brutto Auss. Sonstige Fonds)",
            "ANLAGE_KAP_INV_ZEILE_14_AKTIENFONDS_GEWINN_VERLUST_GROSS": "KAP-INV Z14 (Brutto G/V Aktienfonds)",
            "ANLAGE_KAP_INV_ZEILE_17_MISCHFONDS_GEWINN_VERLUST_GROSS": "KAP-INV Z17 (Brutto G/V Mischfonds)",
            "ANLAGE_KAP_INV_ZEILE_20_IMMOBILIENFONDS_GEWINN_VERLUST_GROSS": "KAP-INV Z20 (Brutto G/V Immofonds)",
            "ANLAGE_KAP_INV_ZEILE_23_AUSLANDS_IMMOBILIENFONDS_GEWINN_VERLUST_GROSS": "KAP-INV Z23 (Brutto G/V Ausl. Immofonds)",
            "ANLAGE_KAP_INV_ZEILE_26_SONSTIGE_FONDS_GEWINN_VERLUST_GROSS": "KAP-INV Z26 (Brutto G/V Sonstige Fonds)",
            "ANLAGE_KAP_INV_ZEILE_9_AKTIENFONDS_VORABPAUSCHALE_BRUTTO": "KAP-INV Z9 (Brutto VOP Aktienfonds)",
            "ANLAGE_KAP_INV_ZEILE_10_MISCHFONDS_VORABPAUSCHALE_BRUTTO": "KAP-INV Z10 (Brutto VOP Mischfonds)",
        }
        so_lines_map = {
             "ANLAGE_SO_Z54_NET_GV": "Anlage SO Zeile 54 (G/V §23 EStG)"
        }
        
        declared_values_map = {
            TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT: kap_lines_map["ANLAGE_KAP_ZEILE_19"],
            TaxReportingCategory.ANLAGE_KAP_AKTIEN_GEWINN: kap_lines_map["ANLAGE_KAP_ZEILE_20"],
            TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN: kap_lines_map["ANLAGE_KAP_ZEILE_21"],
            TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE: kap_lines_map["ANLAGE_KAP_ZEILE_22"],
            TaxReportingCategory.ANLAGE_KAP_AKTIEN_VERLUST: kap_lines_map["ANLAGE_KAP_ZEILE_23"],
            TaxReportingCategory.ANLAGE_KAP_TERMIN_VERLUST: kap_lines_map["ANLAGE_KAP_ZEILE_24"],
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_4_AKTIENFONDS_AUSSCHUETTUNG_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_AUSSCHUETTUNG_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_5_MISCHFONDS_AUSSCHUETTUNG_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_6_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_7_AUSLANDS_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_AUSSCHUETTUNG_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_8_SONSTIGE_FONDS_AUSSCHUETTUNG_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_GEWINN_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_14_AKTIENFONDS_GEWINN_VERLUST_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_GEWINN_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_17_MISCHFONDS_GEWINN_VERLUST_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_GEWINN_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_20_IMMOBILIENFONDS_GEWINN_VERLUST_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_GEWINN_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_23_AUSLANDS_IMMOBILIENFONDS_GEWINN_VERLUST_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_GEWINN_GROSS: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_26_SONSTIGE_FONDS_GEWINN_VERLUST_GROSS"],
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_VORABPAUSCHALE_BRUTTO: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_9_AKTIENFONDS_VORABPAUSCHALE_BRUTTO"],
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_VORABPAUSCHALE_BRUTTO: kap_inv_lines_map["ANLAGE_KAP_INV_ZEILE_10_MISCHFONDS_VORABPAUSCHALE_BRUTTO"],
            "ANLAGE_SO_Z54_NET_GV": so_lines_map["ANLAGE_SO_Z54_NET_GV"],
            "TOTAL_ANRECHENBARE_AUSL_STEUERN": kap_lines_map["ANLAGE_KAP_ZEILE_41"]
        }
        
        form_values = self.loss_offsetting_result.form_line_values
        # Order by line numbers (KAP 19-24, then KAP 41, then KAP-INV 4-26, then SO 54)
        key_order = [
            TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT,  # Zeile 19
            TaxReportingCategory.ANLAGE_KAP_AKTIEN_GEWINN,  # Zeile 20
            TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN,  # Zeile 21
            TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE,  # Zeile 22
            TaxReportingCategory.ANLAGE_KAP_AKTIEN_VERLUST,  # Zeile 23
            TaxReportingCategory.ANLAGE_KAP_TERMIN_VERLUST,  # Zeile 24
            "TOTAL_ANRECHENBARE_AUSL_STEUERN",  # Zeile 41
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS,  # KAP-INV Zeile 4
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_AUSSCHUETTUNG_GROSS,  # KAP-INV Zeile 5
            TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS,  # KAP-INV Zeile 6
            TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS,  # KAP-INV Zeile 7
            TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_AUSSCHUETTUNG_GROSS,  # KAP-INV Zeile 8
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_VORABPAUSCHALE_BRUTTO,  # KAP-INV Zeile 9
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_VORABPAUSCHALE_BRUTTO,  # KAP-INV Zeile 10
            TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_GEWINN_GROSS,  # KAP-INV Zeile 14
            TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_GEWINN_GROSS,  # KAP-INV Zeile 17
            TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_GEWINN_GROSS,  # KAP-INV Zeile 20
            TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_GEWINN_GROSS,  # KAP-INV Zeile 23
            TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_GEWINN_GROSS,  # KAP-INV Zeile 26
            "ANLAGE_SO_Z54_NET_GV"  # SO Zeile 54
        ]

        for key_to_lookup in key_order:
            description = declared_values_map.get(key_to_lookup)
            if not description:
                logger.warning(f"Description not found for key {key_to_lookup} in declared_values_map during PDF generation.")
                continue

            value = form_values.get(key_to_lookup, Decimal('0.00'))
            # Show all lines including zeros
            data.append([description, self._format_decimal(value).replace('.',',')]) # German format for display
        
        if len(data) > 1:
            table = self._create_styled_table(data, col_widths=[12*cm, 4*cm])
            self.story.append(table)
            
            # Add explanations of how summary values are calculated
            self._add_calculation_explanations()
        else:
            self.story.append(Paragraph("Keine Werte zu deklarieren.", self.styles['BodyText']))

    def _add_calculation_explanations(self):
        """Add explanations of how summary values are calculated based on detailed sections."""
        logger.info("Adding calculation explanations to PDF")
        self.story.append(Spacer(1, 0.5*cm))
        self.story.append(Paragraph("Erläuterung der Berechnungen", self.styles['H3']))
        
        self.story.append(Paragraph(
            "Die nachfolgenden Erläuterungen zeigen, wie die oben zusammengefassten Werte aus den "
            "detaillierten Aufstellungen in den späteren Abschnitten berechnet werden:",
            self.styles['BodyText']
        ))
        
        # Explanation for Anlage KAP Zeile 19 (Foreign capital income)
        form_values = self.loss_offsetting_result.form_line_values
        kap_zeile_19_value = form_values.get(TaxReportingCategory.ANLAGE_KAP_AUSLAENDISCHE_KAPITALERTRAEGE_GESAMT, Decimal('0.00'))
        
        # Always show Zeile 19 breakdown (even if total is 0)
        logger.info(f"Adding Anlage KAP Zeile 19 explanation for value: {kap_zeile_19_value}")
        self.story.append(Paragraph(
            f"<b>Anlage KAP Zeile 19 (Ausl. Kapitalerträge n. Sald.): {self._format_decimal(kap_zeile_19_value).replace('.', ',')} EUR</b>",
            self.styles['BodyText']
        ))
        
        self.story.append(Paragraph(
            "Dieser Wert setzt sich zusammen aus:",
            self.styles['BodyText']
        ))
        
        # Create breakdown table with actual values from existing calculations
        breakdown_data = [["Komponente", "Betrag (EUR)", "Verweis"]]
        
        # Get individual component values from form_line_values
        stock_gains = form_values.get(TaxReportingCategory.ANLAGE_KAP_AKTIEN_GEWINN, Decimal('0.00'))
        derivative_gains = form_values.get(TaxReportingCategory.ANLAGE_KAP_TERMIN_GEWINN, Decimal('0.00'))
        other_income_positive = form_values.get(TaxReportingCategory.ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE, Decimal('0.00'))
        stock_losses = form_values.get(TaxReportingCategory.ANLAGE_KAP_AKTIEN_VERLUST, Decimal('0.00'))
        other_losses = form_values.get(TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE, Decimal('0.00'))
        
        # Add all positive components (even if 0)
        breakdown_data.append([
            "Gewinne aus Aktienveräußerungen",
            self._format_decimal(stock_gains).replace('.', ','),
            "siehe Abschnitt 7.1"
        ])
        
        breakdown_data.append([
            "Gewinne aus Termingeschäften",
            self._format_decimal(derivative_gains).replace('.', ','),
            "siehe Abschnitt 7.2"
        ])
        
        breakdown_data.append([
            "Sonstige Kapitalerträge (Zinsen, Dividenden, etc.)",
            self._format_decimal(other_income_positive).replace('.', ','),
            "siehe Abschnitt 7.3"
        ])
        
        # Add all negative components (even if 0) - losses are subtracted
        breakdown_data.append([
            "Verluste aus Aktienveräußerungen (Abzug)",
            f"-{self._format_decimal(stock_losses).replace('.', ',')}",
            "siehe Abschnitt 7.1"
        ])
        
        breakdown_data.append([
            "Sonstige Verluste (Abzug)",
            f"-{self._format_decimal(other_losses).replace('.', ',')}",
            "siehe Abschnitt 7.3"
        ])
        
        # Add total row
        breakdown_data.append([
            Paragraph("<b>Summe (Anlage KAP Zeile 19)</b>", self.styles['TableHeader']),
            Paragraph(f"<b>{self._format_decimal(kap_zeile_19_value).replace('.', ',')}</b>", self.styles['TableCellRight']),
            ""
        ])
        
        # Always create the table
        table = self._create_styled_table(breakdown_data, col_widths=[8*cm, 3*cm, 4*cm])
        self.story.append(table)
        
        self.story.append(Paragraph(
            "Die Berechnung erfolgt durch Summierung aller positiven ausländischen Kapitalerträge "
            "abzüglich der negativen Komponenten (Verluste werden separat in anderen Zeilen ausgewiesen). "
            "Detaillierte Einzelpositionen finden Sie in den entsprechenden Abschnitten weiter unten.",
            self.styles['BodyText']
        ))
        
        self.story.append(Spacer(1, 0.3*cm))

    def _add_data_sources_notes(self):
        self.story.append(Paragraph("Datenquellen und Verarbeitungshinweise", self.styles['H2']))
        self.story.append(Paragraph("Verwendete IBKR Eingabedateien (Beispiele): trades.csv, cash_transactions.csv, positions_start_file.csv, positions_end_file.csv, corporate_actions.csv", self.styles['BodyText']))
        self.story.append(Paragraph("Methodik:", self.styles['H3']))
        notes = [
            "FIFO-Methode für Kapitalgewinne.",
            "Tägliche EZB-Wechselkurse für Währungsumrechnungen.",
            f"Verwendung von `Decimal`-Arithmetik mit interner Arbeitspräzision von {app_config.INTERNAL_CALCULATION_PRECISION} Stellen und Rundungsmodus '{app_config.DECIMAL_ROUNDING_MODE}'. Endbeträge werden für die Berichterstattung quantisiert.",
            f"Teilfreistellung gemäß deutschem Steuerrecht für {self.tax_year} (keine Alt-Anteile berücksichtigt).",
            f"Vorabpauschale für {self.tax_year} beträgt 0,00 EUR.",
        ]
        for note in notes:
            self.story.append(Paragraph(f"• {note}", self.styles['BodyText']))

    def _add_eoy_reconciliation(self):
        self.story.append(Paragraph("Abstimmung der Endbestände (EOY)", self.styles['H2']))

        if not self.eoy_mismatch_details:
            self.story.append(Paragraph("Alle berechneten Endbestände stimmen mit den gemeldeten Endbeständen überein.", self.styles['BodyText']))
            return

        data = [["Asset Beschreibung", "ISIN/Symbol", "Ber. EOY Menge (FIFO)", "Gem. EOY Menge (IBKR)", "Differenz"]]
        for mismatch in self.eoy_mismatch_details:
            desc = mismatch.get('asset_description', "N/A")
            identifier = mismatch.get('asset_identifier', "N/A")

            data.append([
                desc,
                identifier,
                self._format_decimal(mismatch.get('calculated_eoy_quantity'), "integer_quantity"),
                self._format_decimal(mismatch.get('reported_eoy_quantity'), "integer_quantity"),
                self._format_decimal(mismatch.get('difference'), "integer_quantity")
            ])
        
        if len(data) > 1:
            # Adjusted col_widths slightly to accommodate potentially wider integer quantity strings if numbers are large
            table = self._create_styled_table(data, col_widths=[5*cm, 3*cm, 3.5*cm, 3.5*cm, 2*cm])
            self.story.append(table)
        else: 
            self.story.append(Paragraph("Keine Abweichungen bei den Endbeständen festgestellt.", self.styles['BodyText']))
            
    def _get_asset_details(self, asset_id: uuid.UUID) -> Tuple[str, str, Optional[InvestmentFundType]]:
        asset = self.assets_by_id.get(asset_id)
        if not asset:
            return "Unbekanntes Asset", "N/A", None
        
        name = asset.description or asset.ibkr_symbol or "N/A"
        isin_symbol = asset.ibkr_isin or asset.ibkr_symbol or "N/A"
        fund_type = getattr(asset, 'fund_type', None) if isinstance(asset, InvestmentFund) else None
        return name, isin_symbol, fund_type

    def _add_kap_inv_details(self):
        self.story.append(Paragraph("Detaillierte Aufstellung: Anlage KAP-INV (Investmenterträge)", self.styles['H2']))

        fund_rgls = [
            rgl for rgl in self.realized_gains_losses 
            if rgl.asset_category_at_realization == AssetCategory.INVESTMENT_FUND
        ]
        fund_distributions = [
            event for event in self.all_financial_events 
            if isinstance(event, CashFlowEvent) and event.event_type == FinancialEventType.DISTRIBUTION_FUND
        ]
        fund_vorabpauschale_items = [vp for vp in self.vorabpauschale_items]

        self.story.append(Paragraph("6.1 Ausschüttungen (Investmentfonds)", self.styles['H3']))
        dist_data_exists = False
        unique_fund_dist_ids = sorted(list(set(fe.asset_internal_id for fe in fund_distributions)))

        for asset_id in unique_fund_dist_ids:
            asset_name, asset_isin_symbol, fund_type_enum = self._get_asset_details(asset_id)
            fund_type_str = fund_type_enum.name if fund_type_enum else "N/A"
            
            current_fund_dists = sorted([d for d in fund_distributions if d.asset_internal_id == asset_id], key=lambda x: x.event_date)
            if not current_fund_dists: continue
            dist_data_exists = True

            self.story.append(Paragraph(f"Fonds: {asset_name} ({asset_isin_symbol}) - Typ: {fund_type_str}", self.styles['SmallText']))
            data = [["Trans. Datum", "Brutto (Fremdw.)", "Kurs", "Brutto (EUR)", "TF-Satz (%)", "TF-Betrag (EUR)", "Netto Steuerpfl. (EUR)"]]
            fund_dist_total_gross_eur = Decimal(0)
            fund_dist_total_tf_eur = Decimal(0)
            fund_dist_total_net_eur = Decimal(0)

            for dist_event in current_fund_dists:
                tf_rate = get_teilfreistellung_rate_for_fund_type(fund_type_enum)
                gross_eur = dist_event.gross_amount_eur or Decimal(0)
                tf_amount_eur = (gross_eur.copy_abs() * tf_rate).quantize(app_config.OUTPUT_PRECISION_AMOUNTS)
                net_taxable_eur = gross_eur - tf_amount_eur if gross_eur >= Decimal(0) else gross_eur + tf_amount_eur
                
                fund_dist_total_gross_eur += gross_eur
                fund_dist_total_tf_eur += tf_amount_eur
                fund_dist_total_net_eur += net_taxable_eur

                ex_rate = Decimal(0)
                if dist_event.gross_amount_foreign_currency and dist_event.gross_amount_eur and dist_event.gross_amount_foreign_currency != 0:
                    try:
                        ex_rate = dist_event.gross_amount_eur / dist_event.gross_amount_foreign_currency
                    except ZeroDivisionError: 
                        ex_rate = Decimal(0)

                data.append([
                    format_date_german(dist_event.event_date),
                    f"{self._format_decimal(dist_event.gross_amount_foreign_currency)} {dist_event.local_currency}" if dist_event.gross_amount_foreign_currency else "",
                    self._format_decimal(ex_rate, "price") if ex_rate !=0 else "",
                    self._format_decimal(gross_eur).replace('.',','),
                    self._format_decimal(tf_rate*100).replace('.',','),
                    self._format_decimal(tf_amount_eur).replace('.',','),
                    self._format_decimal(net_taxable_eur).replace('.',',')
                ])
            data.append([Paragraph("Summe Fonds:", self.styles['TableHeader']), "", "",
                         Paragraph(self._format_decimal(fund_dist_total_gross_eur).replace('.',','), self.styles['TableCellRight']), "",
                         Paragraph(self._format_decimal(fund_dist_total_tf_eur).replace('.',','), self.styles['TableCellRight']),
                         Paragraph(self._format_decimal(fund_dist_total_net_eur).replace('.',','), self.styles['TableCellRight'])])

            table = self._create_styled_table(data, col_widths=[2*cm, 2.5*cm, 1.5*cm, 2*cm, 2*cm, 2.2*cm, 2.8*cm])
            self.story.append(KeepTogether(table))
            self.story.append(Spacer(1, 0.2*cm))
        if not dist_data_exists:
             self.story.append(Paragraph("Keine Ausschüttungen von Investmentfonds in diesem Steuerjahr.", self.styles['BodyText']))

        self.story.append(Paragraph("6.2 Veräußerungsgewinne/-verluste (Investmentfonds)", self.styles['H3']))
        gl_data_exists = False
        unique_fund_gl_ids = sorted(list(set(rgl.asset_internal_id for rgl in fund_rgls)))

        for asset_id in unique_fund_gl_ids:
            asset_name, asset_isin_symbol, _ = self._get_asset_details(asset_id)
            
            current_fund_rgls = sorted([rgl for rgl in fund_rgls if rgl.asset_internal_id == asset_id], key=lambda x: x.realization_date)
            if not current_fund_rgls: continue
            gl_data_exists = True
            
            fund_type_str_from_rgl = current_fund_rgls[0].fund_type_at_sale.name if current_fund_rgls[0].fund_type_at_sale else "N/A"
            self.story.append(Paragraph(f"Fonds: {asset_name} ({asset_isin_symbol}) - Typ: {fund_type_str_from_rgl}", self.styles['SmallText']))
            data = [["Verk. Datum", "Menge", "Erlös EUR", "Ansch. Datum", "Kosten EUR", "G/V Brutto EUR", "TF-Satz (%)", "TF-Betrag EUR", "Netto G/V EUR"]]
            fund_gl_total_gross_eur = Decimal(0)
            fund_gl_total_tf_eur = Decimal(0)
            fund_gl_total_net_eur = Decimal(0)
            
            for rgl in current_fund_rgls:
                fund_gl_total_gross_eur += rgl.gross_gain_loss_eur
                fund_gl_total_tf_eur += rgl.teilfreistellung_amount_eur or Decimal(0)
                fund_gl_total_net_eur += rgl.net_gain_loss_after_teilfreistellung_eur or Decimal(0)

                data.append([
                    format_date_german(rgl.realization_date),
                    self._format_decimal(rgl.quantity_realized, "integer_quantity"), # Changed precision_type
                    self._format_decimal(rgl.total_realization_value_eur).replace('.',','),
                    format_date_german(rgl.acquisition_date),
                    self._format_decimal(rgl.total_cost_basis_eur).replace('.',','), 
                    self._format_decimal(rgl.gross_gain_loss_eur).replace('.',','),
                    self._format_decimal((rgl.teilfreistellung_rate_applied or 0)*100).replace('.',','),
                    self._format_decimal(rgl.teilfreistellung_amount_eur).replace('.',','),
                    self._format_decimal(rgl.net_gain_loss_after_teilfreistellung_eur).replace('.',',')
                ])
            data.append([Paragraph("Summe Fonds:", self.styles['TableHeader']), "", "", "", "",
                        Paragraph(self._format_decimal(fund_gl_total_gross_eur).replace('.',','), self.styles['TableCellRight']), "",
                        Paragraph(self._format_decimal(fund_gl_total_tf_eur).replace('.',','), self.styles['TableCellRight']),
                        Paragraph(self._format_decimal(fund_gl_total_net_eur).replace('.',','), self.styles['TableCellRight'])])
            # Adjusted col_widths slightly for quantity column
            table = self._create_styled_table(data, col_widths=[1.8*cm, 1.8*cm, 2*cm, 1.8*cm, 2*cm, 2.2*cm, 1.8*cm, 2.2*cm, 2.2*cm])
            self.story.append(KeepTogether(table))
            self.story.append(Spacer(1, 0.2*cm))
        if not gl_data_exists:
             self.story.append(Paragraph("Keine Veräußerungen von Investmentfonds in diesem Steuerjahr.", self.styles['BodyText']))

        self.story.append(Paragraph("6.3 Vorabpauschale (Investmentfonds)", self.styles['H3']))
        if not fund_vorabpauschale_items or all(vp.gross_vorabpauschale_eur == Decimal(0) for vp in fund_vorabpauschale_items):
            self.story.append(Paragraph(f"Vorabpauschale für das Steuerjahr {self.tax_year} beträgt 0,00 EUR für alle Fonds.", self.styles['BodyText']))
        else: 
            data = [["Fonds Name", "ISIN", "Wert Anfang", "Wert Ende", "Aussch.", "Basiszinssatz (%)", "Basisertrag", "Brutto VOP", "TF-Satz (%)", "TF-Betrag", "Netto VOP"]]
            total_gross_vop = Decimal(0)
            total_tf_vop = Decimal(0)
            total_net_vop = Decimal(0)
            for vp_item in fund_vorabpauschale_items:
                asset_name, asset_isin_symbol, _ = self._get_asset_details(vp_item.asset_internal_id)
                data.append([
                    asset_name, asset_isin_symbol,
                    self._format_decimal(vp_item.fund_value_start_year_eur).replace('.',','),
                    self._format_decimal(vp_item.fund_value_end_year_eur).replace('.',','),
                    self._format_decimal(vp_item.distributions_during_year_eur).replace('.',','),
                    self._format_decimal(vp_item.base_return_rate * 100).replace('.',','), 
                    self._format_decimal(vp_item.calculated_base_return_eur).replace('.',','),
                    self._format_decimal(vp_item.gross_vorabpauschale_eur).replace('.',','),
                    self._format_decimal(vp_item.teilfreistellung_rate_applied * 100).replace('.',','),
                    self._format_decimal(vp_item.teilfreistellung_amount_eur).replace('.',','),
                    self._format_decimal(vp_item.net_taxable_vorabpauschale_eur).replace('.',',')
                ])
                total_gross_vop += vp_item.gross_vorabpauschale_eur
                total_tf_vop += vp_item.teilfreistellung_amount_eur
                total_net_vop += vp_item.net_taxable_vorabpauschale_eur
            
            if any(vp.gross_vorabpauschale_eur != Decimal(0) for vp in fund_vorabpauschale_items):
                data.append([Paragraph("Summen:", self.styles['TableHeader']), "", "", "", "", "", "",
                            Paragraph(self._format_decimal(total_gross_vop).replace('.',','), self.styles['TableCellRight']), "",
                            Paragraph(self._format_decimal(total_tf_vop).replace('.',','), self.styles['TableCellRight']),
                            Paragraph(self._format_decimal(total_net_vop).replace('.',','), self.styles['TableCellRight'])])
                table = self._create_styled_table(data, col_widths=[2.5*cm, 2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])
                self.story.append(KeepTogether(table))
            else:
                 self.story.append(Paragraph(f"Vorabpauschale für das Steuerjahr {self.tax_year} beträgt 0,00 EUR für alle Fonds (Tabelle nicht angezeigt, da alle Werte Null).", self.styles['BodyText']))

        self.story.append(Paragraph("Zusammenfassung für Anlage KAP-INV Zeilen (Bruttobeträge)", self.styles['H3']))
        kap_inv_summary_data = [["KAP-INV Zeile", "Fondsart", "Betrag (EUR)"]]
        
        form_values = self.loss_offsetting_result.form_line_values
        
        kap_inv_gross_reporting_map = [
            (TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_AUSSCHUETTUNG_GROSS, "Zeile 4", "Aktienfonds Ausschüttung"),
            (TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_AUSSCHUETTUNG_GROSS, "Zeile 5", "Mischfonds Ausschüttung"),
            (TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS, "Zeile 6", "Immobilienfonds Ausschüttung"),
            (TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_AUSSCHUETTUNG_GROSS, "Zeile 7", "Ausl. Immobilienfonds Ausschüttung"),
            (TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_AUSSCHUETTUNG_GROSS, "Zeile 8", "Sonstige Fonds Ausschüttung"),
            (TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_GEWINN_GROSS, "Zeile 14", "Aktienfonds Gewinn/Verlust"),
            (TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_GEWINN_GROSS, "Zeile 17", "Mischfonds Gewinn/Verlust"),
            (TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_GEWINN_GROSS, "Zeile 20", "Immobilienfonds Gewinn/Verlust"),
            (TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_GEWINN_GROSS, "Zeile 23", "Ausl. Immobilienfonds Gewinn/Verlust"),
            (TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_GEWINN_GROSS, "Zeile 26", "Sonstige Fonds Gewinn/Verlust"),
            (TaxReportingCategory.ANLAGE_KAP_INV_AKTIENFONDS_VORABPAUSCHALE_BRUTTO, "Zeile 9", "Aktienfonds Vorabpauschale"),
            (TaxReportingCategory.ANLAGE_KAP_INV_MISCHFONDS_VORABPAUSCHALE_BRUTTO, "Zeile 10", "Mischfonds Vorabpauschale"),
            (TaxReportingCategory.ANLAGE_KAP_INV_IMMOBILIENFONDS_VORABPAUSCHALE_BRUTTO, "Zeile 11", "Immobilienfonds Vorabpauschale"),
            (TaxReportingCategory.ANLAGE_KAP_INV_AUSLANDS_IMMOBILIENFONDS_VORABPAUSCHALE_BRUTTO, "Zeile 12", "Ausl. Immo. Vorabpauschale"),
            (TaxReportingCategory.ANLAGE_KAP_INV_SONSTIGE_FONDS_VORABPAUSCHALE_BRUTTO, "Zeile 13", "Sonstige Fonds Vorabpauschale"),
        ]
        
        has_kap_inv_summary_data = False
        for trc_enum, line_desc, fund_type_desc in kap_inv_gross_reporting_map:
            amount = form_values.get(trc_enum, Decimal('0.00')) 
            if amount != Decimal(0) or "Vorabpauschale" in fund_type_desc: 
                kap_inv_summary_data.append([line_desc, fund_type_desc, self._format_decimal(amount).replace('.',',')])
                has_kap_inv_summary_data = True
        
        if has_kap_inv_summary_data and len(kap_inv_summary_data) > 1 :
            table = self._create_styled_table(kap_inv_summary_data, col_widths=[3*cm, 7*cm, 3*cm])
            self.story.append(table)
        else:
            self.story.append(Paragraph("Keine Bruttowerte für KAP-INV Zeilen vorhanden oder alle Werte Null.", self.styles['BodyText']))


    def _add_kap_details(self):
        self.story.append(Paragraph("Detaillierte Aufstellung: Anlage KAP (Kapitalerträge)", self.styles['H2']))

        self.story.append(Paragraph("7.1 Gewinne/Verluste aus Aktienveräußerungen (§20 Abs. 2 S. 1 Nr. 1 EStG)", self.styles['H3']))
        stock_rgls = [rgl for rgl in self.realized_gains_losses if rgl.asset_category_at_realization == AssetCategory.STOCK]
        if stock_rgls:
            data = [["Asset Name", "ISIN/Symbol", "Verk. Datum", "Menge", "Erlös EUR", "Ansch. Datum", "Kosten EUR", "G/V Brutto EUR"]]
            total_gains = Decimal(0)
            total_losses_abs = Decimal(0)
            for rgl in sorted(stock_rgls, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.realization_date)):
                name, isin_symbol, _ = self._get_asset_details(rgl.asset_internal_id)
                data.append([
                    name, isin_symbol, format_date_german(rgl.realization_date),
                    self._format_decimal(rgl.quantity_realized, "integer_quantity"), # Changed precision_type
                    self._format_decimal(rgl.total_realization_value_eur).replace('.',','),
                    format_date_german(rgl.acquisition_date),
                    self._format_decimal(rgl.total_cost_basis_eur).replace('.',','),
                    self._format_decimal(rgl.gross_gain_loss_eur).replace('.',',')
                ])
                if rgl.gross_gain_loss_eur > 0: total_gains += rgl.gross_gain_loss_eur
                else: total_losses_abs += rgl.gross_gain_loss_eur.copy_abs()
            
            data.append([Paragraph("Summe Gewinne (Zeile 20):", self.styles['TableHeader']), "", "", "", "", "", "", Paragraph(self._format_decimal(total_gains).replace('.',','), self.styles['TableCellRight'])])
            data.append([Paragraph("Summe Verluste (Zeile 23):", self.styles['TableHeader']), "", "", "", "", "", "", Paragraph(self._format_decimal(total_losses_abs).replace('.',','), self.styles['TableCellRight'])])
            # Adjusted quantity col width
            table = self._create_styled_table(data, col_widths=[3*cm, 2.5*cm, 1.8*cm, 1.8*cm, 2*cm, 1.8*cm, 2*cm, 2.2*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine Aktienveräußerungen in diesem Steuerjahr.", self.styles['BodyText']))

        self.story.append(Paragraph("7.2 Gewinne/Verluste aus Termingeschäften (§20 Abs. 2 S. 1 Nr. 3 EStG)", self.styles['H3']))
        derivative_rgls = [rgl for rgl in self.realized_gains_losses if rgl.asset_category_at_realization in [AssetCategory.OPTION, AssetCategory.CFD]]
        if derivative_rgls:
            data = [["Instrument", "Underlying", "Real. Datum", "Real. Typ", "Menge", "G/V Brutto EUR", "Stillhalter?"]]
            total_gains = Decimal(0)
            total_losses_abs = Decimal(0)
            for rgl in sorted(derivative_rgls, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.realization_date)):
                name, _, _ = self._get_asset_details(rgl.asset_internal_id)
                asset_obj = self.assets_by_id.get(rgl.asset_internal_id)
                underlying_symbol = ""
                if isinstance(asset_obj, Derivative) and getattr(asset_obj, 'underlying_asset_internal_id', None):
                    underlying_id = getattr(asset_obj, 'underlying_asset_internal_id')
                    if underlying_id:
                       underlying_name_detail, underlying_isin_sym_detail, _ = self._get_asset_details(underlying_id)
                       underlying_symbol = underlying_isin_sym_detail or underlying_name_detail

                data.append([
                    name, underlying_symbol, format_date_german(rgl.realization_date),
                    rgl.realization_type.name, 
                    self._format_decimal(rgl.quantity_realized, "integer_quantity"), # Changed precision_type
                    self._format_decimal(rgl.gross_gain_loss_eur).replace('.',','),
                    "Ja" if rgl.is_stillhalter_income else "Nein" 
                ])
                if rgl.gross_gain_loss_eur > 0: total_gains += rgl.gross_gain_loss_eur
                else: total_losses_abs += rgl.gross_gain_loss_eur.copy_abs()
            
            data.append([Paragraph("Summe Gewinne (Zeile 21):", self.styles['TableHeader']), "", "", "", "", Paragraph(self._format_decimal(total_gains).replace('.',','), self.styles['TableCellRight']), ""])
            data.append([Paragraph("Summe Verluste (Zeile 24):", self.styles['TableHeader']), "", "", "", "", Paragraph(self._format_decimal(total_losses_abs).replace('.',','), self.styles['TableCellRight']), ""])
            # Adjusted quantity col width
            table = self._create_styled_table(data, col_widths=[3.5*cm, 2.5*cm, 1.8*cm, 2.5*cm, 1.5*cm, 2.2*cm, 2*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine Realisierungen aus Termingeschäften in diesem Steuerjahr.", self.styles['BodyText']))

        self.story.append(Paragraph("7.3 Sonstige Kapitalerträge (Zinsen, Dividenden, etc.)", self.styles['H3']))
        
        all_other_income_positive_components = []
        all_other_income_negative_components_abs = [] 

        self.story.append(Paragraph("7.3.1 Zinserträge", self.styles['SmallText']))
        interest_events = [ev for ev in self.all_financial_events if isinstance(ev, CashFlowEvent) and ev.event_type == FinancialEventType.INTEREST_RECEIVED]
        if interest_events:
            data = [["Quelle", "Datum", "Brutto Zins (EUR)"]]
            total_interest = Decimal(0)
            total_positive_interest = Decimal(0)
            total_negative_interest = Decimal(0)
            
            # Separate positive and negative events for display
            positive_events = []
            negative_events = []
            
            for event in sorted(interest_events, key=lambda x: x.event_date):
                name, _, _ = self._get_asset_details(event.asset_internal_id)
                gross_eur = event.gross_amount_eur or Decimal(0)
                total_interest += gross_eur
                
                if gross_eur > 0:
                    positive_events.append((name, event.event_date, gross_eur))
                    total_positive_interest += gross_eur
                    all_other_income_positive_components.append(gross_eur)
                elif gross_eur < 0:
                    negative_events.append((name, event.event_date, gross_eur))
                    total_negative_interest += gross_eur
                    all_other_income_negative_components_abs.append(gross_eur.copy_abs())
            
            # Add positive interest events
            if positive_events:
                for name, event_date, gross_eur in positive_events:
                    data.append([name, format_date_german(event_date), self._format_decimal(gross_eur).replace('.',',')])
                data.append([Paragraph("Zwischensumme positive Zinsen:", self.styles['TableHeader']), "", 
                           Paragraph(self._format_decimal(total_positive_interest).replace('.',','), self.styles['TableCellRight'])])
            
            # Add negative interest events  
            if negative_events:
                for name, event_date, gross_eur in negative_events:
                    data.append([name, format_date_german(event_date), self._format_decimal(gross_eur).replace('.',',')])
                data.append([Paragraph("Zwischensumme negative Zinsen:", self.styles['TableHeader']), "", 
                           Paragraph(self._format_decimal(total_negative_interest).replace('.',','), self.styles['TableCellRight'])])
            
            # Add net total
            data.append([Paragraph("Summe Zinsen:", self.styles['TableHeader']), "", 
                        Paragraph(self._format_decimal(total_interest).replace('.',','), self.styles['TableCellRight'])])
            
            table = self._create_styled_table(data, col_widths=[8*cm, 3*cm, 4*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine Zinserträge.", self.styles['BodyText']))

        self.story.append(Paragraph("7.3.2 Dividenden (Nicht-Investmentfonds)", self.styles['SmallText']))
        stock_dividend_events_list = []
        for ev in self.all_financial_events:
            if isinstance(ev, CashFlowEvent) and ev.event_type == FinancialEventType.DIVIDEND_CASH:
                asset = self.assets_by_id.get(ev.asset_internal_id)
                if asset and asset.asset_category == AssetCategory.STOCK: 
                    stock_dividend_events_list.append(ev)
        
        if stock_dividend_events_list:
            data = [["Aktie", "ISIN/Symbol", "Datum", "Brutto Dividende (EUR)"]] # Removed WHT column
            total_dividends = Decimal(0)
            for event in sorted(stock_dividend_events_list, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.event_date)):
                name, isin_symbol, _ = self._get_asset_details(event.asset_internal_id)
                gross_eur = event.gross_amount_eur or Decimal(0)
                data.append([name, isin_symbol, format_date_german(event.event_date), self._format_decimal(gross_eur).replace('.',',')]) # Removed WHT data
                total_dividends += gross_eur
                if gross_eur > 0: all_other_income_positive_components.append(gross_eur)
            data.append([Paragraph("Summe Dividenden:", self.styles['TableHeader']), "", "", Paragraph(self._format_decimal(total_dividends).replace('.',','), self.styles['TableCellRight'])]) # Adjusted for removed column
            table = self._create_styled_table(data, col_widths=[5*cm, 3*cm, 2.5*cm, 4.5*cm]) # Adjusted col_widths
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine Bardividenden von Nicht-Investmentfonds.", self.styles['BodyText']))

        self.story.append(Paragraph("7.3.3 Erträge aus steuerpflichtigen Stockdividenden", self.styles['SmallText']))
        taxable_stock_dividends = [
            ev for ev in self.all_financial_events 
            if isinstance(ev, CorpActionStockDividend) and (ev.fmv_per_new_share_eur is not None and ev.fmv_per_new_share_eur > 0 or (ev.gross_amount_eur is not None and ev.gross_amount_eur > 0))
        ]
        if taxable_stock_dividends:
            data = [["Aktie", "ISIN/Symbol", "Datum", "Anz. Neue Aktien", "FMV/Aktie EUR", "Steuerpfl. Ertrag EUR"]]
            total_taxable_sd_income = Decimal(0)
            for event_sd in sorted(taxable_stock_dividends, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.event_date)):
                name, isin_symbol, _ = self._get_asset_details(event_sd.asset_internal_id)
                taxable_income = event_sd.gross_amount_eur 
                if taxable_income is None and event_sd.fmv_per_new_share_eur is not None and event_sd.quantity_new_shares_received is not None:
                    taxable_income = event_sd.quantity_new_shares_received * event_sd.fmv_per_new_share_eur
                
                if taxable_income and taxable_income > 0:
                    fmv_per_share_display = event_sd.fmv_per_new_share_eur
                    if fmv_per_share_display is None and event_sd.quantity_new_shares_received and event_sd.quantity_new_shares_received != 0:
                        fmv_per_share_display = taxable_income / event_sd.quantity_new_shares_received

                    data.append([
                        name, isin_symbol, format_date_german(event_sd.event_date),
                        self._format_decimal(event_sd.quantity_new_shares_received, "integer_quantity"), # Changed precision_type
                        self._format_decimal(fmv_per_share_display, "price").replace('.',','),
                        self._format_decimal(taxable_income).replace('.',',')
                    ])
                    total_taxable_sd_income += taxable_income
                    all_other_income_positive_components.append(taxable_income)
            if total_taxable_sd_income > 0:
                data.append([Paragraph("Summe:", self.styles['TableHeader']),"", "", "", "", Paragraph(self._format_decimal(total_taxable_sd_income).replace('.',','), self.styles['TableCellRight'])])
                # Adjusted quantity col width
                table = self._create_styled_table(data, col_widths=[3.5*cm, 2.5*cm, 2*cm, 2.3*cm, 2.5*cm, 2.5*cm])
                self.story.append(KeepTogether(table))
            else:
                self.story.append(Paragraph("Keine steuerpflichtigen Erträge aus Stockdividenden.", self.styles['BodyText']))
        else:
            self.story.append(Paragraph("Keine steuerpflichtigen Erträge aus Stockdividenden.", self.styles['BodyText']))

        self.story.append(Paragraph("7.3.4 Gewinne/Verluste aus Anleihenveräußerungen", self.styles['SmallText']))
        bond_rgls = [rgl for rgl in self.realized_gains_losses if rgl.asset_category_at_realization == AssetCategory.BOND]
        if bond_rgls:
            data = [["Asset Name", "ISIN/Symbol", "Verk. Datum", "Menge", "Erlös EUR", "Ansch. Datum", "Kosten EUR", "G/V Brutto EUR"]]
            total_bond_gl = Decimal(0)
            for rgl in sorted(bond_rgls, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.realization_date)):
                name, isin_symbol, _ = self._get_asset_details(rgl.asset_internal_id)
                gross_gl = rgl.gross_gain_loss_eur or Decimal(0)
                data.append([
                    name, isin_symbol, format_date_german(rgl.realization_date),
                    self._format_decimal(rgl.quantity_realized, "integer_quantity"), # Changed precision_type
                    self._format_decimal(rgl.total_realization_value_eur).replace('.',','),
                    format_date_german(rgl.acquisition_date),
                    self._format_decimal(rgl.total_cost_basis_eur).replace('.',','), 
                    self._format_decimal(gross_gl).replace('.',',')
                ])
                total_bond_gl += gross_gl
                if gross_gl > 0: all_other_income_positive_components.append(gross_gl)
                elif gross_gl < 0: all_other_income_negative_components_abs.append(gross_gl.copy_abs())
            data.append([Paragraph("Summe G/V Anleihen:", self.styles['TableHeader']), "", "", "", "", "", "", Paragraph(self._format_decimal(total_bond_gl).replace('.',','), self.styles['TableCellRight'])])
            # Adjusted quantity col width
            table = self._create_styled_table(data, col_widths=[3*cm, 2.5*cm, 1.8*cm, 1.8*cm, 2*cm, 1.8*cm, 2*cm, 2.2*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine Anleihenveräußerungen in diesem Steuerjahr.", self.styles['BodyText']))
        
        self.story.append(Paragraph("7.3.5 Stückzinsen", self.styles['SmallText']))
        accrued_interest_events = [ev for ev in self.all_financial_events if isinstance(ev, CashFlowEvent) and ev.event_type == FinancialEventType.INTEREST_PAID_STUECKZINSEN]
        
        stueckzinsen_data_exists = False
        stueckzinsen_table_data = [["Asset Name", "Datum", "Typ", "Betrag (EUR)"]]
        
        total_stueckzinsen_paid_abs = Decimal(0) 

        for event in sorted(accrued_interest_events, key=lambda x: x.event_date):
            name, _, _ = self._get_asset_details(event.asset_internal_id)
            amount_eur_positive_cost = event.gross_amount_eur or Decimal(0)
            stueckzinsen_table_data.append([name, format_date_german(event.event_date), "Gezahlt", self._format_decimal(amount_eur_positive_cost).replace('.',',')])
            total_stueckzinsen_paid_abs += amount_eur_positive_cost # This is already a cost (negative income component)
            stueckzinsen_data_exists = True
        
        if stueckzinsen_data_exists:
            if total_stueckzinsen_paid_abs > 0:
                 all_other_income_negative_components_abs.append(total_stueckzinsen_paid_abs)
            
            stueckzinsen_table_data.append([Paragraph("Summe gezahlter Stückzinsen (als neg. Ertrag):", self.styles['TableHeader']), "", "", Paragraph(self._format_decimal(total_stueckzinsen_paid_abs).replace('.',','), self.styles['TableCellRight'])])
            table = self._create_styled_table(stueckzinsen_table_data, col_widths=[7*cm, 3*cm, 2*cm, 3*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine expliziten Stückzinsen-Transaktionen (gezahlt/erhalten) erfasst.", self.styles['BodyText']))

        self.story.append(Paragraph("7.3.6 Nettoerträge aus Investmentfonds (nach Teilfreistellung, als Komponente sonst. Erträge)", self.styles['SmallText']))
        fund_net_income_data_rows = []
        
        fund_distributions_for_kap = [
            event for event in self.all_financial_events 
            if isinstance(event, CashFlowEvent) and event.event_type == FinancialEventType.DISTRIBUTION_FUND
        ]
        fund_rgls_for_kap = [
            rgl for rgl in self.realized_gains_losses 
            if rgl.asset_category_at_realization == AssetCategory.INVESTMENT_FUND
        ]
        fund_vop_for_kap = [vp for vp in self.vorabpauschale_items if vp.tax_year == self.tax_year]

        for dist_event in fund_distributions_for_kap:
            asset_id = dist_event.asset_internal_id
            asset_name, asset_isin_symbol, fund_type_enum = self._get_asset_details(asset_id)
            tf_rate = get_teilfreistellung_rate_for_fund_type(fund_type_enum)
            gross_eur = dist_event.gross_amount_eur or Decimal(0)
            tf_amount_eur = (gross_eur.copy_abs() * tf_rate).quantize(app_config.OUTPUT_PRECISION_AMOUNTS)
            net_taxable_eur = gross_eur - tf_amount_eur if gross_eur >= Decimal(0) else gross_eur + tf_amount_eur
            if net_taxable_eur !=0:
                fund_net_income_data_rows.append([asset_name, asset_isin_symbol, "Ausschüttung (Netto)", self._format_decimal(net_taxable_eur).replace('.',',')])

        for rgl in fund_rgls_for_kap:
            asset_name, asset_isin_symbol, _ = self._get_asset_details(rgl.asset_internal_id)
            net_gl = rgl.net_gain_loss_after_teilfreistellung_eur or Decimal(0)
            if net_gl != 0:
                fund_net_income_data_rows.append([asset_name, asset_isin_symbol, "Veräußerung G/V (Netto)", self._format_decimal(net_gl).replace('.',',')])

        for vp_item in fund_vop_for_kap:
            if vp_item.net_taxable_vorabpauschale_eur != Decimal(0): 
                asset_name, asset_isin_symbol, _ = self._get_asset_details(vp_item.asset_internal_id)
                net_vp = vp_item.net_taxable_vorabpauschale_eur
                fund_net_income_data_rows.append([asset_name, asset_isin_symbol, "Vorabpauschale (Netto)", self._format_decimal(net_vp).replace('.',',')])

        if fund_net_income_data_rows:
            data = [["Fonds Name", "ISIN/Symbol", "Typ", "Netto Steuerpfl. Betrag (EUR)"]] + sorted(fund_net_income_data_rows, key=lambda x: (x[0], x[2]))
            # Calculate sum based on the already formatted strings by converting back to Decimal
            total_net_fund_income_display = sum(Decimal(row[3].replace(',','.')) for row in data[1:])
            data.append([Paragraph("Summe Netto Investmenterträge (für Verrechnung):", self.styles['TableHeader']), "", "", Paragraph(self._format_decimal(total_net_fund_income_display).replace('.',','), self.styles['TableCellRight'])])
            table = self._create_styled_table(data, col_widths=[5*cm, 3*cm, 4*cm, 3.5*cm])
            self.story.append(KeepTogether(table))
            self.story.append(Paragraph("Hinweis: Diese Netto-Investmenterträge werden gemäß InvStG versteuert und fließen in die Gesamtverrechnung ein; die Bruttozahlen sind in KAP-INV zu deklarieren.", self.styles['SmallText']))
        else:
            self.story.append(Paragraph("Keine Nettoerträge aus Investmentfonds für 'Sonstige Kapitalerträge'.", self.styles['BodyText']))

        self.story.append(Spacer(1, 0.5*cm))
        self.story.append(Paragraph("Zusammenfassung Sonstige Kapitalerträge (ohne Fonds):", self.styles['H3']))
        
        # Use pre-calculated values from calculation engine to ensure consistency
        final_total_positive_other_income_non_fund = self.loss_offsetting_result.form_line_values.get(TaxReportingCategory.ANLAGE_KAP_SONSTIGE_KAPITALERTRAEGE, Decimal('0'))
        final_total_negative_other_income_abs_non_fund = self.loss_offsetting_result.form_line_values.get(TaxReportingCategory.ANLAGE_KAP_SONSTIGE_VERLUSTE, Decimal('0'))

        # Create detailed breakdown showing calculation components
        detailed_summary_data = [
            [Paragraph("Komponente", self.styles['TableHeader']), 
             Paragraph("Referenz (Abschnitt)", self.styles['TableHeader']), 
             Paragraph("Betrag EUR", self.styles['TableHeader'])]
        ]
        
        # Positive components breakdown
        detailed_summary_data.append([
            Paragraph("POSITIVE KOMPONENTEN:", self.styles['TableHeader']), "", ""
        ])
        
        # Calculate totals for each component type
        total_interest = sum(gross_eur for gross_eur in all_other_income_positive_components 
                           if any(isinstance(ev, CashFlowEvent) and ev.event_type == FinancialEventType.INTEREST_RECEIVED 
                                  and (ev.gross_amount_eur or Decimal(0)) == gross_eur 
                                  for ev in self.all_financial_events))
        
        total_dividends = sum(gross_eur for gross_eur in all_other_income_positive_components 
                            if any(isinstance(ev, CashFlowEvent) and ev.event_type == FinancialEventType.DIVIDEND_CASH 
                                   and (ev.gross_amount_eur or Decimal(0)) == gross_eur 
                                   and (asset := self.assets_by_id.get(ev.asset_internal_id)) is not None
                                   and asset.asset_category == AssetCategory.STOCK
                                   for ev in self.all_financial_events))
        
        total_stock_dividends = sum(taxable_income for taxable_income in all_other_income_positive_components 
                                  if any(isinstance(ev, CorpActionStockDividend) and 
                                         ((ev.gross_amount_eur or Decimal(0)) == taxable_income or 
                                          (ev.fmv_per_new_share_eur and ev.quantity_new_shares_received and 
                                           ev.quantity_new_shares_received * ev.fmv_per_new_share_eur == taxable_income))
                                         for ev in self.all_financial_events))
        
        total_bond_gains = sum(gross_gl for gross_gl in all_other_income_positive_components 
                             if any(rgl for rgl in self.realized_gains_losses 
                                    if rgl.asset_category_at_realization == AssetCategory.BOND 
                                    and (rgl.gross_gain_loss_eur or Decimal(0)) == gross_gl 
                                    and gross_gl > 0))
        
        # Show all positive components (even if 0 EUR)
        detailed_summary_data.append([
            "• Zinserträge (positiv)", "7.3.1", 
            self._format_decimal(total_interest).replace('.',',')
        ])
        
        detailed_summary_data.append([
            "• Dividenden (Nicht-Investmentfonds)", "7.3.2", 
            self._format_decimal(total_dividends).replace('.',',')
        ])
        
        detailed_summary_data.append([
            "• Erträge aus steuerpflichtigen Stockdividenden", "7.3.3", 
            self._format_decimal(total_stock_dividends).replace('.',',')
        ])
        
        detailed_summary_data.append([
            "• Gewinne aus Anleihenveräußerungen", "7.3.4", 
            self._format_decimal(total_bond_gains).replace('.',',')
        ])
        
        detailed_summary_data.append([
            Paragraph("Summe positive 'Sonstige Kapitalerträge':", self.styles['TableHeader']), 
            "", 
            Paragraph(self._format_decimal(final_total_positive_other_income_non_fund).replace('.',','), self.styles['TableCellRight'])
        ])
        
        # Negative components breakdown  
        detailed_summary_data.append([
            Paragraph("NEGATIVE KOMPONENTEN (absolut):", self.styles['TableHeader']), "", ""
        ])
        
        total_bond_losses = sum(gross_gl_abs for gross_gl_abs in all_other_income_negative_components_abs 
                              if any(rgl for rgl in self.realized_gains_losses 
                                     if rgl.asset_category_at_realization == AssetCategory.BOND 
                                     and (rgl.gross_gain_loss_eur or Decimal(0)) < 0
                                     and (rgl.gross_gain_loss_eur or Decimal(0)).copy_abs() == gross_gl_abs))
        
        total_stueckzinsen = sum(stueck_abs for stueck_abs in all_other_income_negative_components_abs 
                               if stueck_abs == sum(event.gross_amount_eur or Decimal(0) 
                                                   for event in self.all_financial_events 
                                                   if isinstance(event, CashFlowEvent) 
                                                   and event.event_type == FinancialEventType.INTEREST_PAID_STUECKZINSEN))
        
        # Show all negative components (even if 0 EUR)
        detailed_summary_data.append([
            "• Verluste aus Anleihenveräußerungen", "7.3.4", 
            self._format_decimal(total_bond_losses).replace('.',',')
        ])
        
        detailed_summary_data.append([
            "• Stückzinsen (gezahlt)", "7.3.5", 
            self._format_decimal(total_stueckzinsen).replace('.',',')
        ])
        
        detailed_summary_data.append([
            Paragraph("Summe (absolute) negative 'Sonstige Kapitalerträge':", self.styles['TableHeader']), 
            "", 
            Paragraph(self._format_decimal(final_total_negative_other_income_abs_non_fund).replace('.',','), self.styles['TableCellRight'])
        ])
        
        table = self._create_styled_table(detailed_summary_data, col_widths=[8*cm, 3*cm, 4.5*cm])
        self.story.append(table)
        
        # Add explanatory note
        self.story.append(Spacer(1, 0.3*cm))
        self.story.append(Paragraph("Hinweis: Die positiven Beträge entsprechen 'kap_other_income_positive' und fließen in Zeile 19 ein. Die negativen Beträge entsprechen 'kap_other_losses_abs' und fließen in Zeile 22 ein. Negative Zinserträge werden nicht in die Steuerberechnung einbezogen.", self.styles['SmallText']))


    def _add_so_details(self):
        self.story.append(Paragraph("Detaillierte Aufstellung: Anlage SO (Sonstige Einkünfte - §23 EStG)", self.styles['H2']))
        
        sec23_rgls_taxable = [
            rgl for rgl in self.realized_gains_losses 
            if rgl.asset_category_at_realization == AssetCategory.PRIVATE_SALE_ASSET 
            and rgl.is_taxable_under_section_23 
        ]
        sec23_rgls_nontaxable = [
            rgl for rgl in self.realized_gains_losses 
            if rgl.asset_category_at_realization == AssetCategory.PRIVATE_SALE_ASSET 
            and not rgl.is_taxable_under_section_23 
        ]

        if sec23_rgls_taxable:
            self.story.append(Paragraph("Steuerpflichtige Veräußerungen nach §23 EStG", self.styles['H3']))
            data = [["Bezeichnung", "Veräuß. am", "Anschaff. am", "Veräuß.preis EUR", "Ansch.kosten EUR", "Werbungsk. EUR", "G/V EUR", "Haltefrist"]]
            total_net_gain_loss_so = Decimal(0)
            for rgl in sorted(sec23_rgls_taxable, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.realization_date)):
                name, _, _ = self._get_asset_details(rgl.asset_internal_id)
                werbungskosten_eur = Decimal(0) 
                data.append([
                    name, format_date_german(rgl.realization_date), format_date_german(rgl.acquisition_date),
                    self._format_decimal(rgl.total_realization_value_eur).replace('.',','),
                    self._format_decimal(rgl.total_cost_basis_eur).replace('.',','), 
                    self._format_decimal(werbungskosten_eur).replace('.',','),
                    self._format_decimal(rgl.gross_gain_loss_eur).replace('.',','), 
                    str(rgl.holding_period_days or "") + " Tage"
                ])
                total_net_gain_loss_so += rgl.gross_gain_loss_eur or Decimal(0)
            data.append([Paragraph("Gesamter G/V §23 EStG (Zeile 54):", self.styles['TableHeader']), "", "", "", "", "", Paragraph(self._format_decimal(total_net_gain_loss_so).replace('.',','), self.styles['TableCellRight']), ""])
            table = self._create_styled_table(data, col_widths=[3*cm, 1.8*cm, 1.8*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2*cm])
            self.story.append(KeepTogether(table))
        else:
            self.story.append(Paragraph("Keine steuerpflichtigen Veräußerungen nach §23 EStG in diesem Steuerjahr.", self.styles['BodyText']))

        if sec23_rgls_nontaxable: 
            self.story.append(Paragraph("Nicht steuerpflichtige Veräußerungen nach §23 EStG (Haltefrist > 1 Jahr)", self.styles['H3']))
            data = [["Bezeichnung", "Veräuß. am", "Anschaff. am", "G/V EUR", "Haltefrist"]]
            for rgl in sorted(sec23_rgls_nontaxable, key=lambda x: (self._get_asset_details(x.asset_internal_id)[0], x.realization_date)):
                name, _, _ = self._get_asset_details(rgl.asset_internal_id)
                data.append([
                    name, format_date_german(rgl.realization_date), format_date_german(rgl.acquisition_date),
                    self._format_decimal(rgl.gross_gain_loss_eur).replace('.',','),
                    str(rgl.holding_period_days or "") + " Tage"
                ])
            if len(data) > 1:
                table = self._create_styled_table(data, col_widths=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
                self.story.append(KeepTogether(table))
            else: 
                self.story.append(Paragraph("Keine nicht steuerpflichtigen Veräußerungen nach §23 EStG zu berichten.", self.styles['BodyText']))

    def _prepare_wht_data(self):
        wht_by_country_data: Dict[str, Dict[str, Decimal]] = {}
        wht_individual_transactions = []
        withholding_tax_events = [evt for evt in self.all_financial_events if isinstance(evt, WithholdingTaxEvent)]

        for wht_event in withholding_tax_events:
            if not wht_event.source_country_code or wht_event.gross_amount_eur is None:
                continue
            
            country = wht_event.source_country_code
            tax_amount = wht_event.gross_amount_eur
            
            income_subject_to_wht = Decimal(0)
            if wht_event.taxed_income_event_id:
                income_event = next((evt for evt in self.all_financial_events if evt.event_id == wht_event.taxed_income_event_id), None)
                if income_event and isinstance(income_event, CashFlowEvent) and income_event.gross_amount_eur is not None:
                    income_subject_to_wht = income_event.gross_amount_eur
            
            # Store individual transaction details including linking information
            linking_confidence = wht_event.link_confidence_score if hasattr(wht_event, 'link_confidence_score') else None
            effective_tax_rate = wht_event.effective_tax_rate if hasattr(wht_event, 'effective_tax_rate') else None
            
            # Generate description of the taxed transaction
            taxed_transaction_desc = ""
            if wht_event.taxed_income_event_id:
                income_event = next((evt for evt in self.all_financial_events if evt.event_id == wht_event.taxed_income_event_id), None)
                if income_event:
                    taxed_transaction_desc = self._format_taxed_transaction_description(income_event, wht_event.event_date)
                else:
                    taxed_transaction_desc = "Verknüpft (Event nicht gefunden)"
            else:
                taxed_transaction_desc = "Nicht verknüpft"
            
            wht_individual_transactions.append({
                'date': wht_event.event_date,
                'country': country,
                'income': income_subject_to_wht,
                'tax': tax_amount,
                'taxed_transaction': taxed_transaction_desc,
                'confidence': linking_confidence,
                'tax_rate': effective_tax_rate
            })
            
            if country not in wht_by_country_data:
                wht_by_country_data[country] = {"income": Decimal(0), "tax": Decimal(0)}
            
            wht_by_country_data[country]["income"] += income_subject_to_wht
            wht_by_country_data[country]["tax"] += tax_amount
        
        self.prepared_wht_details_for_table = wht_by_country_data
        self.prepared_wht_individual_transactions = sorted(wht_individual_transactions, key=lambda x: x['date'])
        
        # Use centralized calculation instead of recalculating
        centralized_total = self.loss_offsetting_result.form_line_values.get(TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID, Decimal('0.00'))
        self.loss_offsetting_result.form_line_values["TOTAL_ANRECHENBARE_AUSL_STEUERN"] = centralized_total

    def _add_wht_summary(self):
        self.story.append(Paragraph("Anrechenbare ausländische Quellensteuern (Anlage KAP Zeile 41)", self.styles['H2']))

        wht_data_for_table = self.prepared_wht_details_for_table
        wht_transactions = getattr(self, 'prepared_wht_individual_transactions', [])
        total_anrechenbare_ausl_steuern = self.loss_offsetting_result.form_line_values.get("TOTAL_ANRECHENBARE_AUSL_STEUERN", Decimal('0.00'))
        
        has_data_to_display = False
        if wht_data_for_table:
            for amounts in wht_data_for_table.values():
                if amounts["income"] != Decimal('0.00') or amounts["tax"] != Decimal('0.00'):
                    has_data_to_display = True
                    break
            
        if has_data_to_display:
            # Add individual transactions table first
            if wht_transactions:
                self.story.append(Paragraph("Einzelne Transaktionen:", self.styles['H3']))
                transaction_data = [["Datum", "Land", "Bruttoeinkünfte (EUR)", "Gezahlte QSt (EUR)", "Besteuerte Transaktion", "Steuersatz", "Konfidenz"]]
                
                for transaction in wht_transactions:
                    if transaction['income'] != Decimal('0.00') or transaction['tax'] != Decimal('0.00'):
                        # Format tax rate
                        tax_rate_str = ""
                        if transaction['tax_rate'] is not None:
                            tax_rate_pct = transaction['tax_rate'] * 100
                            # Format to 1 decimal place
                            tax_rate_str = f"{tax_rate_pct.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"
                        
                        # Format confidence
                        confidence_str = ""
                        if transaction['confidence'] is not None:
                            confidence_str = f"{transaction['confidence']}%"
                        
                        transaction_data.append([
                            format_date_german(transaction['date']),
                            transaction['country'],
                            self._format_decimal(transaction['income']).replace('.',','),
                            self._format_decimal(transaction['tax']).replace('.',','),
                            transaction['taxed_transaction'],
                            tax_rate_str,
                            confidence_str
                        ])
                
                if len(transaction_data) > 1:  # More than just header
                    transaction_table = self._create_styled_table(transaction_data, col_widths=[2.2*cm, 1.2*cm, 2.5*cm, 2.2*cm, 3.5*cm, 1.3*cm, 1.3*cm])
                    self.story.append(transaction_table)
                    self.story.append(Paragraph("", self.styles['BodyText']))  # Add spacing
                    
                    # Add legend for linking information
                    legend_text = "Besteuerte Transaktion: Art und Details der zugrunde liegenden Einkommenstransaktion | Konfidenz: Sicherheit der Verknüpfung (0-100%)"
                    self.story.append(Paragraph(legend_text, self.styles['SmallText']))
                    self.story.append(Paragraph("", self.styles['BodyText']))  # Add spacing
            
            # Add country summary table
            self.story.append(Paragraph("Zusammenfassung nach Ländern:", self.styles['H3']))
            data = [["Quellenland", "Gesamte Bruttoeinkünfte unter QSt (EUR)", "Gezahlte QSt (EUR)"]]
            for country_code, amounts in sorted(wht_data_for_table.items()):
                 if amounts["income"] != Decimal('0.00') or amounts["tax"] != Decimal('0.00'):
                    data.append([
                        country_code, 
                        self._format_decimal(amounts["income"]).replace('.',','),
                        self._format_decimal(amounts["tax"]).replace('.',',')
                    ])
            
            data.append([Paragraph("Summe anrechenbare Quellensteuern (für KAP Z. 41):", self.styles['TableHeader']), "", Paragraph(self._format_decimal(total_anrechenbare_ausl_steuern).replace('.',','), self.styles['TableCellRight'])])
            table = self._create_styled_table(data, col_widths=[4*cm, 7*cm, 4*cm])
            self.story.append(table)
        else:
            self.story.append(Paragraph("Keine anrechenbaren ausländischen Quellensteuern erfasst.", self.styles['BodyText']))


    def _add_corporate_actions_summary(self):
        self.story.append(Paragraph("Verarbeitete Kapitalmaßnahmen", self.styles['H2']))
        
        corp_actions = [event for event in self.all_financial_events if isinstance(event, CorporateActionEvent)]
        
        if corp_actions:
            data = [["Asset Name", "ISIN/Symbol", "Datum", "IBKR Action ID", "Typ", "Beschreibung (IBKR)", "Auswirkung Zusammenfassung"]]
            for ca_event in sorted(corp_actions, key=lambda x: x.event_date):
                name, isin_symbol, _ = self._get_asset_details(ca_event.asset_internal_id)
                impact_summary = "N/A"
                
                if isinstance(ca_event, CorpActionSplitForward):
                    impact_summary = f"Forward Split: 1 alte Aktie -> {self._format_decimal(ca_event.new_shares_per_old_share, 'integer_quantity')} neue. AK pro Aktie angepasst."
                elif isinstance(ca_event, CorpActionMergerCash):
                    total_cash = ca_event.gross_amount_eur
                    if total_cash is None and ca_event.cash_per_share_eur is not None and ca_event.quantity_disposed is not None:
                        total_cash = ca_event.cash_per_share_eur * ca_event.quantity_disposed
                    
                    cash_per_share_info = f"{self._format_decimal(ca_event.cash_per_share_eur, 'price').replace('.',',')} EUR/Aktie" if ca_event.cash_per_share_eur else ""
                    total_cash_info = f"{self._format_decimal(total_cash).replace('.',',')} EUR gesamt" if total_cash else ""
                    qty_info = self._format_decimal(ca_event.quantity_disposed, 'integer_quantity') if ca_event.quantity_disposed else "Unbekannte Menge"

                    impact_summary = (f"Barabfindung Fusion: Veräußerung von {qty_info} Aktien "
                                      f"({cash_per_share_info}{' / ' if cash_per_share_info and total_cash_info else ''}{total_cash_info}).")
                elif isinstance(ca_event, CorpActionStockDividend):
                    taxable_income_info = ""
                    fmv_income = ca_event.gross_amount_eur
                    if fmv_income is None and ca_event.fmv_per_new_share_eur and ca_event.quantity_new_shares_received:
                        fmv_income = ca_event.fmv_per_new_share_eur * ca_event.quantity_new_shares_received
                    
                    if fmv_income and fmv_income > 0:
                        taxable_income_info = f" FMV von {self._format_decimal(fmv_income).replace('.',',')} EUR als Ertrag behandelt."
                    qty_received = self._format_decimal(ca_event.quantity_new_shares_received, 'integer_quantity') if ca_event.quantity_new_shares_received else "N/A"
                    impact_summary = f"Stockdividende: {qty_received} neue Aktien erhalten.{taxable_income_info}"
                elif isinstance(ca_event, CorpActionMergerStock):
                    new_asset_id = getattr(ca_event, 'new_asset_internal_id', None)
                    new_asset_name, new_asset_isin = "N/A", "N/A"
                    if new_asset_id:
                        new_asset_name, new_asset_isin, _ = self._get_asset_details(new_asset_id)
                    ratio_info = self._format_decimal(ca_event.new_shares_received_per_old, 'integer_quantity') if ca_event.new_shares_received_per_old else "N/A"
                    impact_summary = (f"Aktientausch Fusion: -> {new_asset_name} ({new_asset_isin}). "
                                      f"Verhältnis: {ratio_info} neue für 1 alte. AK-Fortf.")
                else: 
                    impact_summary = "FIFO-Anpassung oder Ertragsrealisierung."

                ibkr_desc_paragraph = Paragraph(ca_event.ibkr_activity_description or "", self.styles['SmallText'])
                impact_summary_paragraph = Paragraph(impact_summary, self.styles['SmallText'])

                data.append([
                    name, isin_symbol, format_date_german(ca_event.event_date),
                    ca_event.ca_action_id_ibkr or "",
                    ca_event.event_type.name, 
                    ibkr_desc_paragraph,
                    impact_summary_paragraph
                ])
            
            table = self._create_styled_table(data, col_widths=[2.5*cm, 2*cm, 1.8*cm, 2*cm, 2.2*cm, 3.5*cm, 3.5*cm])
            self.story.append(table)
        else:
            self.story.append(Paragraph("Keine relevanten Kapitalmaßnahmen in diesem Steuerjahr verarbeitet.", self.styles['BodyText']))

    def _add_capital_repayments_summary(self):
        """Add section for tax-free capital repayments (Einlagenrückgewähr)"""
        self.story.append(Spacer(1, 0.5*cm))
        self.story.append(Paragraph("Steuerfreie Kapitalrückgewähr (Einlagenrückgewähr)", self.styles['H2']))
        self.story.append(Paragraph(
            "Übersicht über erhaltene steuerfreie Kapitalrückgewähr und deren Auswirkung auf die Anschaffungskosten.",
            self.styles['BodyText']
        ))
        self.story.append(Spacer(1, 0.3*cm))

        # Table 1: Tax-free dividends received
        capital_repayment_events = [
            event for event in self.all_financial_events 
            if event.event_type == FinancialEventType.CAPITAL_REPAYMENT
        ]

        if capital_repayment_events:
            self.story.append(Paragraph("Erhaltene steuerfreie Kapitalrückgewähr", self.styles['H3']))
            
            # Create table for received capital repayments
            headers = [
                "Datum", "Wertpapier", "ISIN/Symbol", 
                "Rückgewähr (EUR)", "Davon steuerpflichtig (EUR)", "Beschreibung"
            ]
            data = [headers]

            for event in capital_repayment_events:
                asset = self.assets_by_id.get(event.asset_internal_id)
                asset_name, isin_symbol, _ = self._get_asset_details(event.asset_internal_id)
                
                repayment_amount = self._format_decimal(event.gross_amount_eur, "total")
                excess_amount = "0,00"
                if hasattr(event, '_excess_taxable_amount_eur') and event._excess_taxable_amount_eur:
                    excess_amount = self._format_decimal(event._excess_taxable_amount_eur, "total")
                
                description = event.ibkr_activity_description or ""
                
                data.append([
                    format_date_german(event.event_date),
                    asset_name,
                    isin_symbol,
                    repayment_amount,
                    excess_amount,
                    Paragraph(description[:100], self.styles['TableCell']) if len(description) > 100 else description
                ])

            table = self._create_styled_table(data, col_widths=[2*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 4*cm])
            self.story.append(table)
            self.story.append(Spacer(1, 0.4*cm))

            # Table 2: Cost basis adjustments
            self.story.append(Paragraph("Anpassung der Anschaffungskosten", self.styles['H3']))
            self.story.append(Paragraph(
                "Die Rückgewähr reduziert die Anschaffungskosten der Wertpapiere nach dem FIFO-Prinzip (älteste Positionen zuerst). "
                "Überschreitet die Rückgewähr die vorhandenen Anschaffungskosten, wird der Überschuss als steuerpflichtiger Dividendenertrag behandelt.",
                self.styles['BodyText']
            ))
            self.story.append(Spacer(1, 0.2*cm))

            # Group by asset for cost basis adjustment summary
            asset_adjustments = {}
            for event in capital_repayment_events:
                asset_id = event.asset_internal_id
                if asset_id not in asset_adjustments:
                    asset_adjustments[asset_id] = {
                        'total_repayment': Decimal('0'),
                        'total_excess': Decimal('0'),
                        'asset_name': self._get_asset_details(asset_id)[0],
                        'isin_symbol': self._get_asset_details(asset_id)[1]
                    }
                
                if event.gross_amount_eur:
                    asset_adjustments[asset_id]['total_repayment'] += event.gross_amount_eur
                
                if hasattr(event, '_excess_taxable_amount_eur') and event._excess_taxable_amount_eur:
                    asset_adjustments[asset_id]['total_excess'] += event._excess_taxable_amount_eur

            headers = [
                "Wertpapier", "ISIN/Symbol", "Gesamte Rückgewähr (EUR)", 
                "Kostenbasis-Reduktion (EUR)", "Überschuss als Dividende (EUR)"
            ]
            data = [headers]

            for asset_id, adj in asset_adjustments.items():
                cost_reduction = adj['total_repayment'] - adj['total_excess']
                
                data.append([
                    adj['asset_name'],
                    adj['isin_symbol'],
                    self._format_decimal(adj['total_repayment'], "total"),
                    self._format_decimal(cost_reduction, "total"),
                    self._format_decimal(adj['total_excess'], "total")
                ])

            table = self._create_styled_table(data, col_widths=[3.5*cm, 2.5*cm, 3*cm, 3*cm, 3*cm])
            self.story.append(table)

            # Add summary note
            total_repayments = sum(adj['total_repayment'] for adj in asset_adjustments.values())
            total_excess = sum(adj['total_excess'] for adj in asset_adjustments.values())
            total_cost_reduction = total_repayments - total_excess

            self.story.append(Spacer(1, 0.3*cm))
            summary_text = (
                f"<b>Zusammenfassung:</b> Gesamte Kapitalrückgewähr: {self._format_decimal(total_repayments, 'total')} EUR, "
                f"davon Kostenbasis-Reduktion: {self._format_decimal(total_cost_reduction, 'total')} EUR, "
                f"als steuerpflichtige Dividende: {self._format_decimal(total_excess, 'total')} EUR."
            )
            self.story.append(Paragraph(summary_text, self.styles['BodyText']))

        else:
            self.story.append(Paragraph("Keine steuerfreien Kapitalrückgewähr in diesem Steuerjahr erhalten.", self.styles['BodyText']))

    def generate_report(self, output_file_path: str):
        logger.info(f"PDF-Bericht wird erstellt: {output_file_path}")
        doc = SimpleDocTemplate(output_file_path)
        
        final_doc_story: List[Any] = []

        self.story = [] 
        self._add_title_page()
        self._add_data_sources_notes()
        self._add_eoy_reconciliation()
        final_doc_story.extend(self.story)
        
        final_doc_story.append(PageBreak())

        self.story = [] 
        self._prepare_wht_data() 
        self._add_declared_values_summary()       
        self._add_kap_details()                   
        self._add_wht_summary()                   
        self._add_kap_inv_details()               
        self._add_so_details()                    
        self._add_corporate_actions_summary()
        self._add_capital_repayments_summary()     
        
        final_doc_story.extend(self.story)
        
        try:
            # Simplified table creation just to ensure numbers are correctly formatted for PDF
            # The _create_styled_table method handles making numbers into Paragraphs with TableCellRight style
            # For display of numbers, I've added .replace('.',',') to use German locale for decimals.
            
            # Before building, iterate through final_doc_story and convert raw numbers to German-formatted strings
            # This is now mostly handled within the _format_decimal calls combined with .replace('.', ',')
            # and the table cell preparation logic.
            
            doc.build(final_doc_story)
            logger.info(f"PDF-Bericht erfolgreich erstellt: {output_file_path}")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des PDF-Berichts: {e}", exc_info=True)

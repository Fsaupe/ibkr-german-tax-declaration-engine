# tests/test_pdf_foreign_withholding.py
"""PDF section 2.4 agrees with the Zeile 41 it explains, and says why a row is not credited.

Since the treaty-rate guard ([GT-CREDIT-026], [GT-CREDIT-029], [GT-CREDIT-030]) credits
less than was withheld on some rows, the section's per-country table summed the
*withheld* tax under a total that is the *credited* one, and the two disagreed with no
explanation: the guard's gaps, and the German-KESt gap, reached only the console. A row
without a source state (interest with BROKER_ENTITY_COUNTRY unset) was left out of the
table altogether. No declared figure changes here.
"""
from decimal import Decimal

from reportlab.platypus import Paragraph, Table

from src.domain.enums import TaxReportingCategory
from src.reporting.pdf_generator import PdfReportGenerator
from tests.test_foreign_withholding_treaty_guard import _income, _resolver, _run, _stock, _wht

Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID


def _section(tmp_path):
    resolver = _resolver(tmp_path)
    us, de, xx = (_stock(resolver, isin) for isin in ("US0000000AAA", "DE0000000BBB", "XS0000000CCC"))
    us_div, de_div, xx_div = _income(us, "100"), _income(de, "100", country="DE"), _income(xx, "100", country="")
    events = [us_div, _wht(us, "30", linked_to=us_div),                    # capped: 30 -> 15 USD
              de_div, _wht(de, "26.375", country="DE", linked_to=de_div),  # German KESt, not Zeile 41
              xx_div, _wht(xx, "5", country="", linked_to=xx_div)]         # no state: kept, reported
    result, gaps = _run(events, resolver)
    generator = PdfReportGenerator(
        loss_offsetting_result=result, all_financial_events=events, realized_gains_losses=[],
        vorabpauschale_items=[], assets_by_id=resolver.assets_by_internal_id, tax_year=2025,
        eoy_mismatch_details=None, data_gaps=gaps.gaps)
    generator._prepare_wht_data()
    generator._add_wht_summary()
    tables = [t._cellvalues for t in generator.story if isinstance(t, Table)]
    text = "\n".join(p.text for p in generator.story if isinstance(p, Paragraph))
    return result, tables, text, gaps.gaps


def _text(cell):
    return cell.text if isinstance(cell, Paragraph) else str(cell)


def _country_rows(tables):
    summary = [[_text(c) for c in row] for row in tables[-1]]
    header = summary[0]
    return header, {row[0]: row for row in summary[1:-1]}, summary[-1]


def _eur(cell):
    return Decimal(cell.replace(",", ".")) if cell not in ("–", "") else None


def test_the_country_table_carries_the_creditable_amount_and_sums_to_zeile_41(tmp_path):
    result, tables, _, _ = _section(tmp_path)
    header, rows, total = _country_rows(tables)
    creditable = header.index("Anrechenbar (EUR)")
    assert _eur(rows["US"][creditable]) == Decimal("13.50")
    assert _eur(rows["US"][header.index("Gezahlte QSt (EUR)")]) == Decimal("27.00")
    shown = sum(_eur(r[creditable]) or Decimal("0") for r in rows.values())
    assert shown == result.form_line_values[Z41]
    assert _eur(total[creditable]) == result.form_line_values[Z41]


def test_a_row_without_a_source_state_is_listed_not_dropped(tmp_path):
    _, tables, _, _ = _section(tmp_path)
    _, rows, _ = _country_rows(tables)
    assert "unbekannt" in rows


def test_german_kest_is_listed_as_not_creditable_on_zeile_41(tmp_path):
    _, tables, _, _ = _section(tmp_path)
    header, rows, _ = _country_rows(tables)
    assert rows["DE"][header.index("Anrechenbar (EUR)")] == "–"


def test_the_zeile_41_gaps_reach_the_pdf(tmp_path):
    _, _, text, gaps = _section(tmp_path)
    codes = {g.code for g in gaps}
    assert {"FOREIGN_WHT_ABOVE_TREATY_RATE", "FOREIGN_WHT_RATE_NOT_VERIFIED",
            "ANLAGE_KAP_GERMAN_KEST_NOT_DECLARABLE"} <= codes
    for gap in gaps:
        if gap.code.startswith("FOREIGN_WHT_") or gap.code == "ANLAGE_KAP_GERMAN_KEST_NOT_DECLARABLE":
            assert gap.subject in text and gap.detail in text, gap.code

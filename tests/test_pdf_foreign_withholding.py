# tests/test_pdf_foreign_withholding.py
"""PDF section 2.4 agrees with the Zeile 41 it explains, and says why a row is not credited.

Since the treaty-rate guard ([GT-CREDIT-026], [GT-CREDIT-029], [GT-CREDIT-030]) credits
less than was withheld on some rows, the section's per-country table summed the
*withheld* tax under a total that is the *credited* one, and the two disagreed with no
explanation. Each row now shows the creditable rate it was limited to, and the section
derives each rate from the BZSt table of the year; German KESt is explained in one line.
A row without a source state was left out of the table altogether; the one in the fixture
below is German KESt found by its rate. A foreign row with no supported creditable amount
is not credited: it is marked in the table and listed with what is open (maintainer's second
review of PR #102). No declared figure changes here.
"""
from decimal import Decimal

from reportlab.platypus import KeepTogether, Paragraph, Table

from src.domain.enums import TaxReportingCategory
from src.reporting.pdf_generator import PdfReportGenerator
from tests.test_foreign_withholding_treaty_guard import _income, _resolver, _run, _stock, _wht

Z41 = TaxReportingCategory.ANLAGE_KAP_FOREIGN_TAX_PAID


def _section(tmp_path):
    resolver = _resolver(tmp_path)
    us, de, xx = (_stock(resolver, isin) for isin in ("US0000000AAA", "DE0000000BBB", "DE0000000CCC"))
    us_div, de_div, xx_div = _income(us, "100"), _income(de, "100", country="DE"), _income(xx, "100", country="")
    events = [us_div, _wht(us, "30", linked_to=us_div),                    # capped: 30 -> 15 USD
              de_div, _wht(de, "26.375", country="DE", linked_to=de_div),  # German KESt, not Zeile 41
              xx_div, _wht(xx, "26.375", country="", linked_to=xx_div)]    # KESt by its rate, no state
    return _render(events, resolver)


def _render(events, resolver):
    result, gaps = _run(events, resolver)
    generator = PdfReportGenerator(
        loss_offsetting_result=result, all_financial_events=events, realized_gains_losses=[],
        vorabpauschale_items=[], assets_by_id=resolver.assets_by_internal_id, tax_year=2025,
        eoy_mismatch_details=None, data_gaps=gaps.gaps)
    generator._prepare_wht_data()
    generator._add_wht_summary()
    flowables = [f for item in generator.story
                 for f in (item._content if isinstance(item, KeepTogether) else [item])]
    tables = [t._cellvalues for t in flowables if isinstance(t, Table)]
    text = "\n".join(p.text for p in flowables if isinstance(p, Paragraph))
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
    """Changed for PR #102 F1 (approved): the row is German KESt found by its rate; a
    foreign row without a state now stops the run and never reaches the report."""
    _, tables, _, _ = _section(tmp_path)
    header, rows, _ = _country_rows(tables)
    assert rows["unbekannt"][header.index("Anrechenbar (EUR)")] == "–"


def test_german_kest_is_listed_as_not_creditable_on_zeile_41(tmp_path):
    _, tables, _, _ = _section(tmp_path)
    header, rows, _ = _country_rows(tables)
    assert rows["DE"][header.index("Anrechenbar (EUR)")] == "–"


def _rows_by_country(table):
    rows = [[_text(c) for c in row] for row in table]
    return rows[0], {row[1]: row for row in rows[1:]}


def test_each_row_shows_the_rate_its_amount_was_limited_to(tmp_path):
    """The "Anr. Satz" column says why "Anrechenbar" is what it is, row by row."""
    _, tables, _, _ = _section(tmp_path)
    header, rows = _rows_by_country(tables[0])
    rate = header.index("Anr. Satz")
    assert rows["US"][rate] == "15 %"
    assert rows["unbekannt"][rate] == "–"   # KESt by its rate (changed for PR #102 F1)
    assert rows["DE"][rate] == "–"


def test_the_rates_used_are_derived_from_the_bzst_table_of_the_year(tmp_path):
    """Below the rows: per state and income kind, the rate the BZSt table of the year makes
    creditable ([GT-CREDIT-029]), and where it comes from."""
    _, tables, text, _ = _section(tmp_path)
    grounds = [[_text(c) for c in row] for row in tables[1]]
    assert grounds[0] == ["Land", "Ertragsart", "Anrechenbar bis zu", "Hinweis"]
    assert grounds[1][:3] == ["US", "Dividenden", "15 %"]
    assert len(grounds) == 2  # only the states the rows above use
    assert "Stand 1. Januar 2025" in text and "§ 32d Abs. 5 Satz 1" in text


def test_the_legend_explains_german_kest_and_no_unrated_status(tmp_path):
    """Changed for PR #102 F1 (approved): no 'ungeprüft' / 'nicht recherchiert' legend.
    An unrated row is marked 'ungeklärt' and listed instead (second review)."""
    _, _, text, _ = _section(tmp_path)
    assert "deutsche Kapitalertragsteuer" in text and "7/37/38" in text
    assert "ungeprüft" not in text and "nicht recherchiert" not in text


def test_there_is_no_separate_notes_section(tmp_path):
    """The per-row rate and its derivation replace the gap texts (they stay on the console)."""
    _, _, text, gaps = _section(tmp_path)
    assert "2.4.3" not in text
    assert not any(g.detail in text for g in gaps)


# --------------------------------------------------------------------------- #
# A foreign row with no supported creditable amount: marked and listed, not "–"
# --------------------------------------------------------------------------- #

def _unresolved(tmp_path):
    """A capped US row beside a Takatukaland row: no rate in the store, so not credited."""
    resolver = _resolver(tmp_path)
    us, xx = _stock(resolver, "US0000000AAA"), _stock(resolver, "XX0000000BBB")
    us_div, xx_div = _income(us, "100"), _income(xx, "100", country="TAKATUKALAND")
    xx_wht = _wht(xx, "21", country="TAKATUKALAND", linked_to=xx_div)
    return _render([us_div, _wht(us, "30", linked_to=us_div), xx_div, xx_wht], resolver), xx_wht


def test_an_unresolved_row_is_marked_not_credited_not_as_german_kest(tmp_path):
    (result, tables, text, _), _ = _unresolved(tmp_path)
    header, rows = _rows_by_country(tables[0])
    assert rows["TAKATUKALAND"][header.index("Anr. Satz")] == "ungeklärt"
    assert rows["TAKATUKALAND"][header.index("Anrechenbar (EUR)")] == "nicht angerechnet"
    c_header, c_rows, total = _country_rows(tables)
    assert c_rows["TAKATUKALAND"][c_header.index("Anrechenbar (EUR)")] == "nicht angerechnet"
    assert _eur(total[c_header.index("Anrechenbar (EUR)")]) == result.form_line_values[Z41] == Decimal("13.50")
    assert "deutsche Kapitalertragsteuer" not in text


def test_an_unresolved_row_is_listed_with_what_is_open(tmp_path):
    """Not a finding of zero, not a refund claim: the listing says so and names the open point."""
    (_, tables, text, _), wht = _unresolved(tmp_path)
    listing = next([_text(c) for c in row] for t in tables for row in t[1:] if _text(t[0][0]) == "Datum"
                   and len(t[0]) == 5 and _text(row[3]) == wht.ibkr_transaction_id)
    assert listing[1] == "TAKATUKALAND" and "kein anrechenbarer Satz" in listing[4]
    assert "Nicht angerechnete Quellensteuer (ungeklärt)" in text and "keine Feststellung" in text

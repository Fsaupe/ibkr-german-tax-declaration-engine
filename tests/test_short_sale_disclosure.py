"""Selected disclosed position, not a timing-law holding: GT-ESTG20-071–074.

All accounts, securities and amounts are invented. The inventory comes from
the reconciled account lots, including a remaining portion after partial cover.
"""
from decimal import Decimal as D
from types import SimpleNamespace
import uuid

import fitz
import pytest

from src.domain.enums import AssetCategory, RealizationType
from src.engine.fifo_manager import ShortFifoLot
from src.engine.short_sale_disclosure import build_short_sale_disclosures
from src.engine.loss_offsetting import LossOffsettingEngine
from src.reporting.console_reporter import generate_console_tax_report
from src.reporting.pdf_generator import PdfReportGenerator
from tests.support.base import FifoTestCaseBase
from tests.support.multi_account import position_row, trade_row

A, B = "U10000001", "U10000002"
ISIN = "DE000000SH11"


class TestShortSaleDisclosure(FifoTestCaseBase):
    def opening(self, year=2025, account=A, quantity="-100", tx="OPEN"):
        return trade_row(account, ISIN, f"{year}-03-10", quantity, "100", "SELL", "O", tx,
                         commission="-20")

    def cover(self, quantity="40", year=2025, account=A):
        return trade_row(account, ISIN, f"{year}-06-10", quantity, "110", "BUY", "C", "COVER",
                         commission="-10")

    def partial(self):
        return self._run_pipeline(
            trades_data=[self.opening(), self.cover()],
            positions_end_data=[position_row(A, ISIN, "-60", "5988")], tax_year=2025)

    def test_partial_cover_keeps_the_exact_open_remainder_and_its_zero_contribution(self):
        out = self.partial()
        opened = [r for r in out.short_sale_disclosures if r.cover_date is None]
        assert len(opened) == 1
        row = opened[0]
        assert (row.account_id, row.opening_date, row.source_transaction_id) == (A, "2025-03-10", "OPEN")
        assert (row.quantity, row.net_proceeds_eur, row.declared_gain_eur) == (D(60), D(5988), D(0))
        covered = [r for r in out.short_sale_disclosures if r.cover_date]
        assert len(covered) == 1
        assert (covered[0].quantity, covered[0].net_proceeds_eur, covered[0].cover_cost_eur,
                covered[0].declared_gain_eur) == (D(40), D(3992), D(4410), D(-418))
        assert sum(r.gross_gain_loss_eur for r in out.realized_gains_losses
                   if r.realization_type == RealizationType.SHORT_POSITION_COVER) == D(-418)

    def test_prior_year_position_without_any_current_trades_is_listed(self):
        out = self._run_pipeline(
            trades_data=[self.opening(2024)],
            positions_start_data=[position_row(A, ISIN, "-100", "9980")],
            positions_end_data=[position_row(A, ISIN, "-100", "9980")], tax_year=2025)
        assert len(out.short_sale_disclosures) == 1
        row = out.short_sale_disclosures[0]
        assert (row.opening_date, row.quantity, row.net_proceeds_eur) == ("2024-03-10", D(100), D(9980))
        assert row.declared_gain_eur == 0

    def test_same_security_in_two_accounts_is_not_netted(self):
        out = self._run_pipeline(
            trades_data=[self.opening(account=A), self.opening(account=B, tx="OPEN-B"),
                         self.cover(quantity="100", account=B)],
            positions_end_data=[position_row(A, ISIN, "-100", "9980")],
            transfers_data=[], tax_year=2025)
        assert [(r.account_id, r.quantity) for r in out.short_sale_disclosures] == [(A, D(100))]

    def test_same_year_round_trip_has_no_annex(self):
        out = self._run_pipeline(trades_data=[self.opening(), self.cover("100")],
                                 positions_end_data=[], tax_year=2025)
        assert out.short_sale_disclosures == []

    def test_an_unrelated_same_year_round_trip_in_the_same_security_is_not_repeated(self):
        out = self._run_pipeline(trades_data=[self.opening(), self.cover("100"),
            trade_row(A, ISIN, "2025-12-10", "-10", "120", "SELL", "O", "LATER")],
            positions_end_data=[position_row(A, ISIN, "-10", "1200")], tax_year=2025)
        row, = out.short_sale_disclosures
        assert row.source_transaction_id == "LATER"

    def test_prior_year_cover_remains_visible_even_without_a_new_open_position(self):
        out = self._run_pipeline(trades_data=[self.opening(2024), self.cover("100")],
                                 positions_start_data=[position_row(A, ISIN, "-100", "9980")],
                                 positions_end_data=[], tax_year=2025)
        assert len(out.short_sale_disclosures) == 1
        row = out.short_sale_disclosures[0]
        assert (row.cover_date, row.cover_transaction_id, row.declared_gain_eur) == (
            "2025-06-10", "COVER", D(-1030))

    def test_position_flip_exposes_only_the_short_portion(self):
        out = self._run_pipeline(trades_data=[
            trade_row(A, ISIN, "2025-01-10", "20", "80", "BUY", "O", "BUY"),
            trade_row(A, ISIN, "2025-03-10", "-100", "100", "SELL", "C;O", "FLIP",
                      commission="-20")],
            positions_end_data=[position_row(A, ISIN, "-80", "7984")], tax_year=2025)
        row, = out.short_sale_disclosures
        assert (row.source_transaction_id, row.quantity, row.net_proceeds_eur) == ("FLIP", D(80), D(7984))

    def summary(self, out):
        return LossOffsettingEngine(out.realized_gains_losses, out.vorabpauschale_items,
                                   out.processed_income_events, out.asset_resolver, 2025).calculate_reporting_figures()

    def test_console_and_actual_pdf_disclose_the_amount_and_the_disagreement(self, capsys, tmp_path):
        out = self.partial()
        summary = self.summary(out)
        generate_console_tax_report(out.realized_gains_losses, [], out.all_financial_events_enriched,
                                    out.asset_resolver, 2025, 0, summary,
                                    short_sale_disclosures=out.short_sale_disclosures)
        console = capsys.readouterr().out
        pdf = PdfReportGenerator(summary, out.processed_income_events, out.realized_gains_losses,
                                 [], out.asset_resolver.assets_by_internal_id, 2025, [],
                                 short_sale_disclosures=out.short_sale_disclosures)
        path = tmp_path / "shorts.pdf"
        pdf.generate_report(str(path))
        with fitz.open(path) as doc:
            content = " ".join(page.get_text() for page in doc)
        for text in (console, content):
            normalized = " ".join(text.split())
            for wanted in ("31.12.2025", "5988", "OPEN", A, "5 StR 221/99", "196",
                           "Abweichende Rechtsauffassung", "0,00", "Ersatzbemessungsgrundlage"):
                assert wanted in normalized
            assert "keine Änderung der Steuerlast" not in normalized

    def test_no_open_or_prior_year_short_emits_no_legal_text(self, capsys):
        out = self._run_pipeline(trades_data=[self.opening(), self.cover("100")],
                                 positions_end_data=[], tax_year=2025)
        summary = self.summary(out)
        generate_console_tax_report(out.realized_gains_losses, [], out.all_financial_events_enriched,
                                    out.asset_resolver, 2025, 0, summary,
                                    short_sale_disclosures=out.short_sale_disclosures)
        assert "Abweichende Rechtsauffassung" not in capsys.readouterr().out
        pdf = PdfReportGenerator(summary, out.processed_income_events, out.realized_gains_losses,
                                 [], out.asset_resolver.assets_by_internal_id, 2025, [],
                                 short_sale_disclosures=out.short_sale_disclosures)
        pdf._add_short_sale_disclosure()
        assert pdf.story == []


@pytest.mark.parametrize("category", [AssetCategory.OPTION, AssetCategory.CFD,
                                      AssetCategory.FUTURE, AssetCategory.CASH_BALANCE])
def test_short_exposure_in_other_products_does_not_trigger_the_securities_annex(category):
    ledger = SimpleNamespace(asset_category=category, short_lots=[
        ShortFifoLot("2024-12-01", D(10), D(100), D(1000), "DERIVATIVE")])
    assert build_short_sale_disclosures({(A, uuid.uuid4()): ledger}, [], 2025) == []


def test_snapshot_preserves_split_quantities_and_never_exposes_unknown_history_as_fact():
    aid = uuid.uuid4()
    lot = ShortFifoLot("2024-12-01", D(200), D(50), D(10000), "SPLIT-OPEN")
    unknown = ShortFifoLot("2024-12-31", D(5), D(40), D(200), "SOY_FALLBACK_SHORT",
                          acquisition_date_is_known=False)
    ledger = SimpleNamespace(asset_category=AssetCategory.STOCK, short_lots=[lot, unknown])
    rows = build_short_sale_disclosures({(A, aid): ledger}, [], 2025)
    known = next(r for r in rows if r.source_transaction_id == "SPLIT-OPEN")
    missing = next(r for r in rows if r.source_transaction_id == "SOY_FALLBACK_SHORT")
    assert (known.quantity, known.net_proceeds_eur) == (D(200), D(10000))
    assert missing.opening_date is None and missing.net_proceeds_eur is None
    lot.quantity_shorted = D(1)
    assert known.quantity == D(200)

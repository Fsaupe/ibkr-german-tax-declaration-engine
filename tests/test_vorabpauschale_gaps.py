"""
Gap-coverage tests for Vorabpauschale (§18 InvStG).

This file is ADDITIVE — it does not modify or replace any test in
test_vorabpauschale.py. It covers requirements the existing suite misses and
documents known gaps where the implementation does not yet match the statute.

Requirements (verbatim §18 InvStG, https://www.gesetze-im-internet.de/invstg_2018/__18.html):
  R1 (Abs. 1 S. 1): VP = max(0, Basisertrag − Ausschüttungen)
  R2 (Abs. 1 S. 2): Basisertrag = Rücknahmepreis(Jahresbeginn) × 0.70 × Basiszins
  R3 (Abs. 1 S. 3): Basisertrag capped at (letzter − erster Rücknahmepreis) + Ausschüttungen
  R4 (Abs. 2):      In the acquisition year, VP is reduced by 1/12 for each full
                    month preceding the month of acquisition.
  R5 (Abs. 3):      VP is deemed to flow on the first business day of the
                    FOLLOWING calendar year (taxed in year X+1).

Tests marked xfail document confirmed gaps: the behaviour is required by the
statute but not implemented. strict=True means they will report XPASS (a
failure) once implemented, forcing the marker to be removed.
"""
import pytest
from decimal import Decimal

from tests.test_vorabpauschale import (
    _make_fund,
    _make_distribution,
    _run_vp,
)


# Basiszins 2024 = 2.29% -> Basisertrag factor 0.0229 * 0.7 = 0.01603
# Default fund: SoY=10000, EoY=11000 -> full-year Basisertrag = 160.30
FULL_YEAR_VP = Decimal("160.30")


# ---------------------------------------------------------------------------
# Coverage gap: R3 cap AND distributions active simultaneously.
#
# The code computes  VP = min(Basisertrag − Dist, max(0, EoY − SoY))
# the statute computes VP = max(0, min(Basisertrag, (EoY−SoY)+Dist) − Dist).
# These are algebraically equivalent; the existing suite never exercises the
# path where the value-gain cap binds AND a distribution is present, so the
# equivalence is unverified. These tests pin it. They PASS on current code.
# ---------------------------------------------------------------------------

class TestCapAndDistributionsCombined:

    def test_cap_binds_with_small_distribution(self):
        """Gain 50, dist 30, Basisertrag 160.30 -> VP 50 (cap binds after dist)."""
        fund = _make_fund(eoy_position_value=Decimal("10050"))
        dist = _make_distribution(fund.internal_asset_id, Decimal("30"))
        results = _run_vp(fund, events=[dist])
        assert len(results) == 1
        # statute: min(160.30, 50+30) − 30 = 80 − 30 = 50
        assert results[0].gross_vorabpauschale_eur == Decimal("50.00")

    def test_cap_binds_with_large_distribution(self):
        """Gain 20, dist 100, Basisertrag 160.30 -> VP 20."""
        fund = _make_fund(eoy_position_value=Decimal("10020"))
        dist = _make_distribution(fund.internal_asset_id, Decimal("100"))
        results = _run_vp(fund, events=[dist])
        assert len(results) == 1
        # statute: min(160.30, 20+100) − 100 = 120 − 100 = 20
        assert results[0].gross_vorabpauschale_eur == Decimal("20.00")

    def test_cap_not_binding_distribution_reduces_basisertrag(self):
        """Large gain, dist 60.30 -> VP = 160.30 − 60.30 = 100.00."""
        fund = _make_fund(eoy_position_value=Decimal("11000"))
        dist = _make_distribution(fund.internal_asset_id, Decimal("60.30"))
        results = _run_vp(fund, events=[dist])
        assert len(results) == 1
        assert results[0].gross_vorabpauschale_eur == Decimal("100.00")


# ---------------------------------------------------------------------------
# GAP — R4: partial-year acquisition (Abs. 2 monthly reduction).
#
# A fund acquired during the tax year and held at year-end must receive a
# Vorabpauschale reduced by 1/12 for each full month preceding the acquisition
# month. Retained fraction for acquisition month M = (13 − M) / 12.
#
# The engine sources the year-start NAV externally (here: soy_position_value),
# learns the acquisition month from acquisition_date, and applies the fraction.
# Current code skips any fund with soy_quantity <= 0, so it produces no record.
# ---------------------------------------------------------------------------

class TestPartialYearAcquisitionReduction:

    @pytest.mark.parametrize("acq_month, retained_twelfths", [
        (1, 12),   # acquired January -> no full month precedes -> full VP
        (6, 7),    # acquired June -> 5 months precede -> 7/12
        (11, 2),   # acquired November -> 10 months precede -> 2/12
        (12, 1),   # acquired December -> 11 months precede -> 1/12
    ])
    @pytest.mark.xfail(strict=True, reason="§18 Abs. 2 monthly pro-rata not implemented")
    def test_acquisition_month_reduces_vp(self, acq_month, retained_twelfths):
        """VP for a mid-year acquisition = full-year VP × (13 − M)/12."""
        fund = _make_fund(
            soy_qty=Decimal("0"),                  # not held at SoY
            soy_position_value=Decimal("10000"),   # year-start NAV (externally sourced)
            eoy_position_value=Decimal("11000"),
            eoy_qty=Decimal("100"),
            description="Mid-year fund",
        )
        fund.acquisition_date = f"2024-{acq_month:02d}-15"

        results = _run_vp(fund)
        assert len(results) == 1
        expected = (FULL_YEAR_VP * Decimal(retained_twelfths) / Decimal(12)).quantize(Decimal("0.01"))
        assert abs(results[0].gross_vorabpauschale_eur - expected) <= Decimal("0.01")


# ---------------------------------------------------------------------------
# BROKEN-TEST COUNTERPART.
#
# test_vorabpauschale.py::test_no_soy_position_no_vp asserts that a fund with
# soy_quantity == 0 yields NO Vorabpauschale. That is correct only when the
# fund is genuinely not held during the year. For a fund ACQUIRED mid-year and
# still held at year-end, §18 Abs. 2 requires a (pro-rated) VP. This test
# asserts the correct opposite behaviour for that case. It does not delete or
# modify the existing test.
# ---------------------------------------------------------------------------

class TestMidYearAcquisitionNotDropped:

    @pytest.mark.xfail(strict=True, reason="§18 Abs. 2 mid-year acquisitions are silently dropped")
    def test_mid_year_acquisition_held_at_eoy_produces_vp(self):
        fund = _make_fund(
            soy_qty=Decimal("0"),                  # not held at SoY (bought during year)
            soy_position_value=Decimal("10000"),   # year-start NAV (externally sourced)
            eoy_position_value=Decimal("11000"),
            eoy_qty=Decimal("100"),
            description="Acquired mid-year, held at EoY",
        )
        fund.acquisition_date = "2024-06-15"

        results = _run_vp(fund)
        assert len(results) == 1
        assert results[0].gross_vorabpauschale_eur > Decimal("0")


# ---------------------------------------------------------------------------
# GAP — value-gain cap with intra-year quantity change.
#
# R3's cap is per-share (erster vs. letzter Rücknahmepreis). The code caps on
# the TOTAL position value (EoY value − SoY value). When units are bought
# mid-year, the total-value delta includes the cost of the new units, inflating
# the cap even when the per-share price did not move.
#
# Construction: 100 units held all year at a constant price of 100/unit, plus
# 100 units bought mid-year at the same price. Per-share gain is zero, so the
# correct Vorabpauschale is zero. The code uses (20000 − 10000) = 10000 as the
# cap and returns the full Basisertrag instead.
# ---------------------------------------------------------------------------

class TestCapWithIntraYearQuantityChange:

    @pytest.mark.xfail(strict=True, reason="value-gain cap uses total position value, not per-share price")
    def test_zero_per_share_gain_yields_zero_vp(self):
        fund = _make_fund(
            soy_qty=Decimal("100"),
            soy_position_value=Decimal("10000"),   # 100 units @ 100
            eoy_qty=Decimal("200"),
            eoy_position_value=Decimal("20000"),   # 200 units @ 100 (price unchanged)
            description="Intra-year purchase, flat price",
        )
        results = _run_vp(fund)
        total_gross_vp = sum((r.gross_vorabpauschale_eur for r in results), Decimal("0"))
        # Per-share price did not move -> no value increase -> VP must be zero.
        assert total_gross_vp == Decimal("0")


# ---------------------------------------------------------------------------
# GAP — R5: deemed inflow timing (Abs. 3).
#
# The VP computed for calendar year X is deemed to flow on the first business
# day of year X+1 and is taxed in the X+1 assessment. The engine stamps
# VorabpauschaleData.tax_year = computation year and reports it on that year's
# return, with no representation of the deemed inflow year.
#
# strict=False: the precise reporting convention is an open product decision;
# this test documents the strict statutory interpretation (inflow = X+1) and
# the absence of any field expressing it.
# ---------------------------------------------------------------------------

class TestDeemedInflowTiming:

    @pytest.mark.xfail(strict=False, reason="§18 Abs. 3 deemed-inflow year (X+1) is not represented; reporting convention undecided")
    def test_vp_deemed_inflow_year_is_following_year(self):
        fund = _make_fund(description="Full-year fund")
        results = _run_vp(fund, tax_year=2024)
        assert len(results) == 1
        # The 2024 Vorabpauschale flows 2 Jan 2025 -> belongs to the 2025 return.
        assert getattr(results[0], "deemed_inflow_year", None) == 2025

"""The two ends of an optional export's path into the engine.

legal_basis: infrastructure. No declared figure is asserted here. What depends on these
assertions is whether an optional export -- Options_EAE, Transfers, Grants -- reaches the
pipeline at all, and whether a hole in its window reaches the check that stops the run.

**Why this file exists.** A cold review deleted `"grants": "Grants"` from
`prepare_data_for_tax_year`, and separately the two Grants arguments from `main.py`, and
the whole suite stayed green each time -- the scenario harness hands a Grants path and a
missing-years string straight to the pipeline, so neither production end was observed.
The same deletion for Transfers turned four tests red in data preparation, and none in
`main.py`. Both ends are asserted here for every optional export alike, so the next one
added to `optional_transaction_types` is covered by adding it to `OPTIONAL_EXPORTS`.

Calibration, measured against a deliberately broken tree (each reverted, file re-run green):

| mutation | red |
|---|---|
| delete `"grants": "Grants"` from `optional_transaction_types` | 4 (its three cases and the listing check) |
| delete `"transfers": "Transfers"` | 4 here (plus the 4 in test_transfers_parser.py) |
| delete `"options_eae": "Options_EAE"` | 4 |
| delete `grants_file_path=` from `main.py` | 1 |
| delete `grants_missing_years=` from `main.py` | 1 |
| delete `transfers_file_path=` / `transfers_missing_years=` from `main.py` | 1 each |
| delete `options_eae_file_path=` from `main.py` | 1 |
"""
import sys

import pytest

from src.parsers import column_validator as cv
from tests.support.multi_account import write_csv

# (key in the prepared paths, file prefix in data_import/, header of the export)
OPTIONAL_EXPORTS = [
    ("options_eae", "Options_EAE", cv.OPTIONS_EAE_COLUMNS),
    ("transfers", "Transfers", cv.TRANSFERS_COLUMNS),
    ("grants", "Grants", cv.GRANTS_COLUMNS),
]
_IDS = [key for key, _, _ in OPTIONAL_EXPORTS]


def test_every_optional_export_of_data_preparation_is_listed_here():
    """So a fourth optional export cannot be added without its two ends being asserted."""
    import inspect
    import src.data_preparation as dp
    source = inspect.getsource(dp.prepare_data_for_tax_year)
    block = source.split("optional_transaction_types = {", 1)[1].split("}", 1)[0]
    declared = {line.split('"')[1] for line in block.splitlines() if '"' in line}
    assert declared == set(_IDS)


def _prepare(tmp_path, monkeypatch, prefix, columns, years, tax_year=2025):
    import src.data_preparation as dp

    imports = tmp_path / "data_import"
    imports.mkdir()
    monkeypatch.setattr(dp, "IMPORT_DIR", imports)
    monkeypatch.setattr(dp, "WORKING_DIR", tmp_path / "data")

    required = {"Trades": cv.TRADES_COLUMNS,
                "Cash_Transactions": cv.CASH_TRANSACTIONS_COLUMNS,
                "Corporate_Actions": cv.CORPORATE_ACTIONS_COLUMNS}
    for required_prefix, required_columns in required.items():
        for year in (2023, 2024, 2025):
            write_csv(str(imports / f"{required_prefix}-{year}.csv"), required_columns, [])
    for year in (2024, 2025):
        for suffix in ("-EoY.csv", "-SoY.csv"):
            write_csv(str(imports / f"Positions-{year}{suffix}"), cv.POSITIONS_COLUMNS, [])
    for year in years:
        write_csv(str(imports / f"{prefix}-{year}.csv"), columns, [])
    return dp.prepare_data_for_tax_year(tax_year)


@pytest.mark.parametrize("key,prefix,columns", OPTIONAL_EXPORTS, ids=_IDS)
class TestDataPreparationReturnsEveryOptionalExport:

    def test_a_complete_window_is_returned_with_nothing_missing(
            self, tmp_path, monkeypatch, key, prefix, columns):
        result = _prepare(tmp_path, monkeypatch, prefix, columns, (2023, 2024, 2025))
        assert result[key], "the export exists, so its prepared path must be returned"
        assert result[f"{key}_missing_years"] == ""

    def test_a_hole_in_the_window_is_named(self, tmp_path, monkeypatch, key, prefix, columns):
        result = _prepare(tmp_path, monkeypatch, prefix, columns, (2023, 2025))
        assert result[key], "the years that do exist are still read"
        assert result[f"{key}_missing_years"] == "2024"

    def test_an_export_never_made_is_an_absence_not_a_gap(
            self, tmp_path, monkeypatch, key, prefix, columns):
        result = _prepare(tmp_path, monkeypatch, prefix, columns, ())
        assert result[key] == ""
        assert result[f"{key}_missing_years"] == ""


class _Handed(Exception):
    """Raised by the stand-in pipeline so `main_application` stops once it has called it."""


# What data preparation returns for an optional export, and the pipeline argument it has
# to arrive as. A missing-years string has no argument for Options_EAE: nothing consumes it.
_HANDOVER = [
    ("options_eae", "options_eae_file_path"),
    ("transfers", "transfers_file_path"),
    ("transfers_missing_years", "transfers_missing_years"),
    ("grants", "grants_file_path"),
    ("grants_missing_years", "grants_missing_years"),
]


@pytest.mark.parametrize("prepared_key,pipeline_argument", _HANDOVER,
                         ids=[a for _, a in _HANDOVER])
def test_main_hands_each_optional_export_to_the_pipeline(
        monkeypatch, prepared_key, pipeline_argument):
    """`main.py` is the only production caller of the pipeline. An argument dropped there
    switches the export off -- or, for a missing-years string, switches off the check that
    stops a run on a window with a hole -- and no scenario test would notice, because the
    harness calls the pipeline itself."""
    import src.main as main_module

    prepared = {
        "trades": "t.csv", "cash_transactions": "c.csv", "corporate_actions": "ca.csv",
        "positions_start": "ps.csv", "positions_end": "pe.csv",
        "options_eae": "prepared/options_eae.csv",
        "transfers": "prepared/transfers.csv", "transfers_missing_years": "2024",
        "grants": "prepared/grants.csv", "grants_missing_years": "2023",
    }
    handed = {}

    def pipeline(**kwargs):
        handed.update(kwargs)
        raise _Handed()

    monkeypatch.setattr(main_module, "prepare_data_for_tax_year", lambda year: dict(prepared))
    monkeypatch.setattr(main_module, "run_core_processing_pipeline", pipeline)
    monkeypatch.setattr(sys, "argv", ["main", "--tax-year", "2023", "--no-interactive"])

    with pytest.raises(SystemExit):
        main_module.main_application()

    assert handed, "main never reached the pipeline"
    assert handed.get(pipeline_argument) == prepared[prepared_key]

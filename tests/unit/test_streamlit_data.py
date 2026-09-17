"""
Unit tests for Streamlit Data Validator, Loader, and Freshness Calculation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import io
import numpy as np
import openpyxl
import pytest

from streamlit_app.data_validator import WorkbookDataValidator
from streamlit_app.data_loader import compute_freshness
from streamlit_app.config import load_config


def test_validator_with_production_workbook():
    validator = WorkbookDataValidator()
    parsed = validator.parse_workbook("Test_BI_Analysis_Report_2026.xlsx")

    assert parsed.is_valid is True
    assert parsed.incomer_col == "Old LT Panel Main Incomer"
    assert len(parsed.submeter_cols) == 14
    assert len(parsed.meter_cols) == 15
    assert len(parsed.df_daily) >= 18

    # Ensure Row 4 'Cum.  (YTD)' is NOT present in df_daily dates
    dates = [str(d) for d in parsed.df_daily["Date"]]
    assert not any("cum" in d.lower() for d in dates)

    # Invariant: Total column must be populated (either evaluated or from Excel)
    assert not parsed.df_daily["Total"].isna().any()

    # Invariant: First active date is 2026-08-29 or sorted correctly
    first_date = str(parsed.df_daily["Date"].iloc[0])
    assert "2026-08-29" in first_date


def test_validator_na_invariant_never_coerced_to_zero():
    """Verify that 'N/A' or missing meter values are preserved as NaN, NEVER coerced to 0.0."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EMS Monitoring Report"

    # Row 1-2 empty
    ws.append([])
    ws.append([])
    # Row 3 headers
    ws.append(["", "Date", "Main Incomer", "Meter A", "Meter B", "Total"])
    # Row 4 YTD
    ws.append(["", "Cum.  (YTD)", None, None, None, None])
    # Row 5 Daily with N/A and 0.0
    ws.append(["", "2026-09-01", 1000.0, "N/A", 0.0, 1000.0])
    # Row 6 Daily with None
    ws.append(["", "2026-09-02", 1100.0, None, 50.0, 1150.0])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    validator = WorkbookDataValidator(
        header_row=3,
        date_column=2,
        first_data_row=5,
        total_column=6,
    )
    parsed = validator.parse_workbook(buf.getvalue())
    assert parsed.is_valid is True
    assert len(parsed.df_daily) == 2

    # Row 1: Meter A must be NaN, Meter B must be 0.0 (preserved difference)
    row0 = parsed.df_daily.iloc[0]
    assert np.isnan(row0["Meter A"])
    assert row0["Meter B"] == 0.0
    assert row0["Meter B"] is not np.nan

    # Row 2: Meter A must be NaN, Meter B must be 50.0
    row1 = parsed.df_daily.iloc[1]
    assert np.isnan(row1["Meter A"])
    assert row1["Meter B"] == 50.0


def test_freshness_computation():
    now = datetime.now(timezone.utc)
    status, label = compute_freshness(now)
    assert status == "LIVE"
    assert "LIVE" in label

    # 30 minutes ago
    from datetime import timedelta
    past_30m = now - timedelta(minutes=30)
    status_recent, label_recent = compute_freshness(past_30m)
    assert status_recent == "RECENT"
    assert "RECENT" in label_recent

    # 3 hours ago
    past_3h = now - timedelta(hours=3)
    status_stale, label_stale = compute_freshness(past_3h)
    assert status_stale == "STALE"
    assert "STALE" in label_stale


def test_config_loader():
    config = load_config()
    assert config.company_name == "Savera MS"
    assert "Test_BI_Analysis_Report_2026.xlsx" in config.local_excel_path
    assert config.worksheet_name == "EMS Monitoring Report"
    assert config.header_row == 3
    assert config.first_data_row == 5

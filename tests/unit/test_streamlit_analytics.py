"""
Unit tests for Streamlit Analytics Engine.
"""

from __future__ import annotations

import pytest

from streamlit_app.data_validator import WorkbookDataValidator
from streamlit_app.analytics import EnergyAnalytics


@pytest.fixture
def analytics_engine() -> EnergyAnalytics:
    validator = WorkbookDataValidator()
    parsed = validator.parse_workbook("Test_BI_Analysis_Report_2026.xlsx")
    return EnergyAnalytics(parsed)


def test_executive_kpis(analytics_engine: EnergyAnalytics):
    kpis = analytics_engine.get_executive_kpis()

    assert kpis.latest_date is not None
    assert str(kpis.latest_date) == "2026-09-15"
    assert kpis.latest_total_kwh > 0
    assert kpis.previous_date is not None
    assert str(kpis.previous_date) == "2026-09-14"
    assert kpis.mtd_days_count == 15
    assert kpis.mtd_total_kwh > 100000.0
    assert kpis.active_meters_count == 15
    assert kpis.total_meters_count == 15
    assert kpis.peak_kwh >= kpis.min_kwh
    assert kpis.submeters_kwh > 0


def test_meter_rankings(analytics_engine: EnergyAnalytics):
    rankings = analytics_engine.get_meter_rankings(include_incomer=False)

    assert not rankings.empty
    assert len(rankings) == 14  # 14 submeters excluding incomer
    # First row should be highest consumer
    assert rankings.iloc[0]["Total kWh"] >= rankings.iloc[1]["Total kWh"]
    # Cumulative % of last row should be 100.0%
    assert pytest.approx(rankings.iloc[-1]["Cumulative %"], rel=1e-2) == 100.0
    # Sum of shares should be ~100.0%
    assert pytest.approx(rankings["Share %"].sum(), rel=1e-2) == 100.0


def test_plant_zones_breakdown(analytics_engine: EnergyAnalytics):
    zones = analytics_engine.get_zone_breakdown()

    assert len(zones) == 7
    zone_ids = {z["zone_id"] for z in zones}
    expected_ids = {"plating", "coating", "fabrication", "compressors", "water_treatment", "packaging", "main_power"}
    assert zone_ids == expected_ids

    for z in zones:
        assert "name" in z
        assert "total_kwh" in z
        assert "nominal_kwh" in z
        assert z["status"] in ("NORMAL", "WARNING", "HIGH", "INACTIVE")


def test_weekday_vs_weekend(analytics_engine: EnergyAnalytics):
    ww = analytics_engine.get_weekday_vs_weekend()

    assert ww["weekday_avg"] > 0
    assert ww["weekend_avg"] > 0
    assert len(ww["by_day"]) > 0
    for day_name, info in ww["by_day"].items():
        assert "avg_kwh" in info
        assert "days_count" in info


def test_data_quality_audit(analytics_engine: EnergyAnalytics):
    audit = analytics_engine.get_audit_report()

    assert audit["total_days_audited"] == 18
    assert audit["incomer_monitored"] is True
    assert len(audit["loss_records"]) == 18
    assert isinstance(audit["avg_distribution_loss_pct"], float)

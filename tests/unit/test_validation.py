from datetime import datetime
import pytest
from app.services.validation.service import ValidationService


@pytest.fixture
def validator():
    return ValidationService(
        minimum_active_energy=0.0,
        maximum_active_energy=100_000_000.0,
        expected_unit="kWh",
        fail_on_unmapped_numeric_meter=False,
    )


def test_valid_report(validator):
    report = {
        "report_date": datetime(2026, 9, 12),
        "readings": [
            {"meter_name": "M1", "active_energy": 120.5, "unit": "kWh", "status": "VALID"},
            {"meter_name": "M2", "active_energy": None, "unit": "kWh", "status": "N/A"},
        ],
    }
    res = validator.validate_report(report)
    assert res["valid"] is True
    assert res["valid_reading_count"] == 1
    assert res["na_reading_count"] == 1


def test_na_reading_is_never_zero(validator):
    res = validator.validate_reading({"meter_name": "M1", "active_energy": None, "status": "N/A"})
    assert res["valid"] is True
    assert res["status"] == "N/A"
    assert res["value"] is None


def test_negative_energy_rejected(validator):
    res = validator.validate_reading({"meter_name": "M1", "active_energy": -5.0, "unit": "kWh", "status": "VALID"})
    assert res["valid"] is False
    assert any("below the minimum" in e for e in res["errors"])


def test_extreme_energy_rejected(validator):
    res = validator.validate_reading({"meter_name": "M1", "active_energy": 200_000_000.0, "unit": "kWh", "status": "VALID"})
    assert res["valid"] is False
    assert any("exceeds the maximum" in e for e in res["errors"])


def test_duplicate_meter_detection(validator):
    report = {
        "report_date": datetime(2026, 9, 12),
        "readings": [
            {"meter_name": "Chiller Plant", "active_energy": 100.0, "unit": "kWh", "status": "VALID"},
            {"meter_name": "Chiller Plant", "active_energy": 120.0, "unit": "kWh", "status": "VALID"},
        ],
    }
    res = validator.validate_report(report)
    assert res["valid"] is False
    assert any("Duplicate meter" in e for e in res["errors"])


def test_wrong_unit_rejected(validator):
    res = validator.validate_reading({"meter_name": "M1", "active_energy": 10.0, "unit": "kVAh", "status": "VALID"})
    assert res["valid"] is False
    assert any("Unexpected energy unit" in e for e in res["errors"])

from app.services.powerbi.service import PowerBIService


def test_powerbi_service_disabled_by_default():
    pbi = PowerBIService()
    assert not pbi.enabled
    assert not pbi.is_configured()

    res_publish = pbi.publish([{"meter": "M1", "val": 100}])
    assert res_publish["status"] == "disabled"

    res_refresh = pbi.refresh()
    assert res_refresh["status"] == "disabled"


def test_prepare_executive_dataset():
    pbi = PowerBIService()
    readings = [
        {"meter_name": "M1", "value": 3000.0, "status": "VALID"},
        {"meter_name": "M2", "value": 2000.0, "status": "VALID"},
        {"meter_name": "M3", "value": 1000.0, "status": "VALID"},
        {"meter_name": "M4", "value": None, "status": "N/A"},
    ]
    history = [
        {"report_date": "2026-09-11", "total_energy": 5500.0},
        {"report_date": "2026-08-31", "total_energy": 5200.0},
    ]

    dataset = pbi.prepare_executive_dataset(readings, "2026-09-12", history)
    assert dataset["today_energy"] == 6000.0
    assert dataset["yesterday_energy"] == 5500.0
    assert dataset["active_meters_count"] == 3
    assert dataset["total_meters_count"] == 4
    assert dataset["top_5_meters"][0]["meter_name"] == "M1"
    assert dataset["top_5_meters"][0]["value"] == 3000.0

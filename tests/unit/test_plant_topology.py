import pytest
from app.services.analytics.plant_topology import PlantTopologyService

SAMPLE_READINGS = [
    {"meter_name": "Chiller Plating Plant", "active_energy": 141.35, "status": "OK"},
    {"meter_name": "Old LT Panel Main Incomer", "active_energy": 3165.92, "status": "OK"},
    {"meter_name": "Packing & Stiching Line", "active_energy": 477.82, "status": "OK"},
    {"meter_name": "Rigga Line Fabrication", "active_energy": 179.22, "status": "OK"},
    {"meter_name": "Press & Fabrication", "active_energy": 1009.43, "status": "OK"},
    {"meter_name": "Powder Coating", "active_energy": 2018.03, "status": "OK"},
    {"meter_name": "New Plating Plant", "active_energy": 1.21, "status": "OK"},
    {"meter_name": "Old Plating Plant", "active_energy": 2.60, "status": "OK"},
    {"meter_name": "Kaeser ASD 60 40HP Air Compressor", "active_energy": 776.61, "status": "OK"},
    {"meter_name": "ELGI E18 25HP Air Compressor", "active_energy": 0.04, "status": "OK"},
    {"meter_name": "ELGI E45 60HP Air Compressor", "active_energy": 1012.75, "status": "OK"},
    {"meter_name": "DIPP_PT_PANEĹ", "active_energy": 0.17, "status": "OK"},
    {"meter_name": "Annealing Furnance", "active_energy": 0.00, "status": "OK"},
    {"meter_name": "RO Plant", "active_energy": 418.96, "status": "OK"},
    {"meter_name": "DM Plant", "active_energy": 2.72, "status": "OK"},
    {"meter_name": "RASKOG", "active_energy": None, "status": "N/A"},
]


def test_plant_topology_calculation():
    service = PlantTopologyService()
    result = service.calculate_topology(SAMPLE_READINGS)

    assert result["plant_name"] == "Savera MS Manufacturing Facility"
    assert pytest.approx(result["plant_total_kwh"], rel=1e-4) == 9206.83

    # Check specific zones
    zones = {z["zone_id"]: z for z in result["zones"]}

    # Coating zone
    coating = zones["coating"]
    assert pytest.approx(coating["total_energy"], rel=1e-4) == 2018.03
    assert coating["active_meters_count"] == 1
    assert coating["status"] in {"NORMAL", "WARNING", "HIGH"}

    # Compressors zone (776.61 + 0.04 + 1012.75 = 1789.4)
    compressors = zones["compressors"]
    assert pytest.approx(compressors["total_energy"], rel=1e-4) == 1789.40
    assert compressors["active_meters_count"] == 3

    # Plating zone (141.35 + 1.21 + 2.60 + 0.17 = 145.33)
    plating = zones["plating"]
    assert pytest.approx(plating["total_energy"], rel=1e-4) == 145.33

    # Fabrication zone (179.22 + 1009.43 + 0.00 = 1188.65, plus RASKOG inactive)
    fab = zones["fabrication"]
    assert pytest.approx(fab["total_energy"], rel=1e-4) == 1188.65
    assert fab["inactive_meters_count"] >= 1

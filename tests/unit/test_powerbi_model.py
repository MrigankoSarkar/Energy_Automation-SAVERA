from pathlib import Path
from app.services.powerbi.model_generator import PowerBIModelGenerator


def test_powerbi_star_schema_export(tmp_path: Path):
    generator = PowerBIModelGenerator(repository=None)
    output_dir = tmp_path / "powerbi_export"

    exported = generator.export_star_schema(output_dir)

    # Verify all expected artifacts are generated
    assert "measures_dax" in exported
    assert "dataset_schema_json" in exported
    assert "report_template_json" in exported
    assert "dim_meter_csv" in exported
    assert "dim_area_csv" in exported
    assert "dim_date_csv" in exported
    assert "fact_energy_csv" in exported
    assert "dim_report_csv" in exported

    # Check files exist
    for key, file_path in exported.items():
        assert Path(file_path).exists(), f"File {key} does not exist at {file_path}"
        assert Path(file_path).stat().st_size > 0

    # Verify DAX file contents
    dax_content = Path(exported["measures_dax"]).read_text(encoding="utf-8")
    assert "[Total Energy (kWh)]" in dax_content
    assert "[MTD Energy (kWh)]" in dax_content
    assert "[YTD Energy (kWh)]" in dax_content
    assert "[Yesterday Energy]" in dax_content
    assert "[Day-over-Day Growth %]" in dax_content
    assert "[Weekend vs Weekday Ratio]" in dax_content

    # Verify Dim_Meter contents
    meter_csv = Path(exported["dim_meter_csv"]).read_text(encoding="utf-8")
    assert "Powder Coating" in meter_csv
    assert "Chiller Plating Plant" in meter_csv
    assert "Kaeser ASD 60" in meter_csv

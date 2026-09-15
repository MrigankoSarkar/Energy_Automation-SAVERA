from pathlib import Path
import pytest
from app.services.pdf.parser import NBSensePDFParser


@pytest.fixture
def parser():
    return NBSensePDFParser()


def test_sample_pdf_parsing(parser):
    pdf_path = Path("data/pdfs/report_2026-09-11_2026-09-12.pdf")
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")

    res = parser.parse(pdf_path)
    assert res["report_date_iso"] == "2026-09-12"
    assert res["meter_count"] == 18
    assert len(res["readings"]) == 18

    # Verify no meter name has 'Avg PF' appended
    for r in res["readings"]:
        assert "Avg PF" not in r["meter_name"]

    # Verify known sample readings
    lookup = {r["meter_name"]: r for r in res["readings"]}

    assert lookup["RASKOG NEW PANL"]["status"] == "N/A"
    assert lookup["RASKOG NEW PANL"]["value"] is None

    assert lookup["Chiller Plating Plant"]["value"] == 141.35
    assert lookup["Chiller Plating Plant"]["status"] == "VALID"

    assert lookup["Main Incomer Meter"]["value"] == 0.0
    assert lookup["Old LT Panel Main Incomer"]["value"] == 3165.92
    assert lookup["Kaeser ASD 60 40HP Air Compressor"]["value"] == 776.61
    assert lookup["ELGI E18 25HP Air Compressor"]["value"] == 0.04
    assert lookup["ELGI E45 60HP Air Compressor"]["value"] == 1012.75
    assert lookup["DIPP_PT_PANEĹ"]["value"] == 0.17
    assert lookup["DUST_ COLLECTOR"]["value"] == 251.50
    assert lookup["SPRAY_PT_PANEL"]["value"] == 9.19
    assert lookup["DM Plant"]["value"] == 160.99

    # Verify exact numeric total
    total = sum(r["value"] for r in res["readings"] if r["value"] is not None)
    assert round(total, 2) == 9206.83


def test_sample_pdf_second_report(parser):
    pdf_path = Path("data/pdfs/report_2026-09-10_2026-09-11.pdf")
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")

    res = parser.parse(pdf_path)
    assert res["report_date_iso"] == "2026-09-11"
    assert res["meter_count"] == 18
    total = sum(r["value"] for r in res["readings"] if r["value"] is not None)
    assert round(total, 2) == 8927.61


def test_missing_pdf(parser):
    with pytest.raises(FileNotFoundError):
        parser.parse("data/pdfs/non_existent_report.pdf")


def test_na_energy_normalization(parser):
    # Ensure N/A is never parsed as 0.0
    val, unit, status = parser._parse_energy_value("N/A kWh")
    assert status == "N/A"
    assert val is None

    val, unit, status = parser._parse_energy_value("Not Available")
    assert status == "N/A"
    assert val is None


def test_mwh_conversion(parser):
    val, unit, status = parser._parse_energy_value("1.5 MWh")
    assert status == "VALID"
    assert val == 1500.0
    assert unit == "kwh"

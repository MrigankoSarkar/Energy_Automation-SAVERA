from app.services.pdf.parser import parse_date, normalize_meter_name
from app.services.excel.mapper import ExcelMapper
from app.services.validation.service import ValidationService


def test_date():
    assert parse_date("12 Sep 2026").strftime("%Y-%m-%d") == "2026-09-12"


def test_meter():
    assert normalize_meter_name(" ELGI   E18 25HP Air Compressor ") == "elgi e18 25hp air compressor"


def test_mapper():
    m = ExcelMapper()
    h = m.build_header_map(["Date", "Powder Coating"])
    assert m.find(" POWDER   COATING ", h)[1] == "Powder Coating"


def test_validation():
    vs = ValidationService()
    assert vs.minimum_active_energy == 0.0


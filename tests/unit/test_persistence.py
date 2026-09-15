import pytest
from app.persistence.database import Database
from app.persistence.repositories.report_repository import ReportRepository


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_persistence.db"
    db = Database(str(db_file))
    db.initialize()
    return db


def test_save_and_query_report(test_db):
    repo = ReportRepository(test_db)
    report_data = {"message_id": "msg_001", "path": "test.pdf"}
    parsed_data = {
        "report_date_iso": "2026-09-12",
        "readings": [
            {"meter_name": "M1", "value": 150.25, "unit": "kWh", "status": "VALID"},
            {"meter_name": "M2", "value": None, "unit": "kWh", "status": "N/A"},
        ],
    }

    report_id = repo.record_processed_report(report_data, parsed_data)
    assert report_id is not None

    reports = repo.get_reports()
    assert len(reports) == 1
    assert reports[0]["message_id"] == "msg_001"
    assert reports[0]["report_date"] == "2026-09-12"
    assert reports[0]["status"] == "COMPLETED"

    readings = repo.get_readings_for_report(report_id)
    assert len(readings) == 2
    lookup = {r["meter_name"]: r for r in readings}
    assert lookup["M1"]["active_energy"] == 150.25
    assert lookup["M2"]["active_energy"] is None


def test_idempotent_duplicate_report(test_db):
    repo = ReportRepository(test_db)
    report_data = {"message_id": "msg_dup", "path": "test.pdf"}
    parsed_data = {"report_date_iso": "2026-09-12", "readings": []}

    id1 = repo.record_processed_report(report_data, parsed_data)
    id2 = repo.record_processed_report(report_data, parsed_data)

    assert id1 == id2
    reports = repo.get_reports()
    assert len(reports) == 1


def test_audit_trail_columns_and_stats(test_db):
    repo = ReportRepository(test_db)
    report_data = {"message_id": "msg_audit", "path": "test_audit.pdf", "received_at": "2026-09-12T08:00:00"}
    parsed_data = {
        "report_date_iso": "2026-09-12",
        "readings": [
            {"meter_name": "M1", "value": 100.0, "unit": "kWh", "status": "VALID"},
            {"meter_name": "M2", "value": 200.0, "unit": "kWh", "status": "VALID"},
            {"meter_name": "M3", "value": None, "unit": "kWh", "status": "N/A"},
        ],
    }

    report_id = repo.record_processed_report(report_data, parsed_data)
    assert report_id is not None

    rep = repo.get_report_by_date("2026-09-12")
    assert rep is not None
    assert rep["meter_count"] == 3
    assert rep["total_energy"] == 300.0
    assert rep["validation_status"] == "VALID"
    assert rep["excel_status"] == "UPDATED"

    stats = repo.get_stats()
    assert stats["total_reports"] == 1
    assert stats["successful_reports"] == 1
    assert stats["failed_reports"] == 0
    assert stats["total_energy"] == 300.0

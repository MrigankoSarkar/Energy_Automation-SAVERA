from datetime import date
import pytest
from app.services.reconciliation.service import ReconciliationService


@pytest.fixture
def recon():
    return ReconciliationService(expected_days_back=5)


def test_reconcile_with_dict(recon):
    report = {"report_date": "2026-09-12"}
    res = recon.reconcile(report, reference_date=date(2026, 9, 13))
    assert res["success"] is True
    assert "2026-09-12" in res["available_dates"]


def test_missing_dates_detection(recon):
    # Only 10th and 12th are available; reference is 13th, lookback is 3 days (12th, 11th, 10th)
    available = [date(2026, 9, 10), date(2026, 9, 12)]
    res = recon.reconcile(available, reference_date=date(2026, 9, 13), days_back=3)
    assert res["missing_dates"] == ["2026-09-11"]


def test_weekend_and_sunday_classification(recon):
    # 2026-09-13 is Sunday, 2026-09-12 is Saturday, 2026-09-11 is Friday
    assert recon.is_sunday(date(2026, 9, 13)) is True
    assert recon.is_weekend(date(2026, 9, 13)) is True
    assert recon.is_weekend(date(2026, 9, 12)) is True
    assert recon.is_weekend(date(2026, 9, 11)) is False


def test_date_classifier(recon):
    ref = date(2026, 9, 13)
    assert recon.classify_date(date(2026, 9, 13), ref) == "today"
    assert recon.classify_date(date(2026, 9, 12), ref) == "yesterday"
    assert recon.classify_date(date(2026, 9, 6), ref) == "sunday"


def test_friday_to_monday_gap_detection(recon):
    # Reference is Monday, 2026-09-14. Only Friday 2026-09-11 is available.
    available = [date(2026, 9, 11)]
    res = recon.reconcile(available, reference_date=date(2026, 9, 14), days_back=3)
    # Expected: 2026-09-13 (Sunday), 2026-09-12 (Saturday)
    assert "2026-09-13" in res["missing_dates"]
    assert "2026-09-12" in res["missing_dates"]
    assert "2026-09-13" in res["weekend_missing"]
    assert "2026-09-12" in res["weekend_missing"]

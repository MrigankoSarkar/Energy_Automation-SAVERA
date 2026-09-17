from app.services.alert.service import AlertCategory, AlertService


def test_alert_service_raise_and_acknowledge():
    service = AlertService()

    alert1 = service.raise_alert(
        category=AlertCategory.WARNING,
        title="Test Alert",
        message="This is a test warning message.",
        source="test",
    )
    assert alert1.category == "WARNING"
    assert not alert1.acknowledged

    # Verify counts
    counts = service.get_counts()
    assert counts["total"] == 1
    assert counts["WARNING"] == 1

    # Verify deduplication: raising identical unacknowledged alert returns existing
    alert2 = service.raise_alert(
        category=AlertCategory.WARNING,
        title="Test Alert",
        message="Duplicate message attempt",
    )
    assert alert2.alert_id == alert1.alert_id
    assert service.get_counts()["total"] == 1

    # Acknowledge
    success = service.acknowledge(alert1.alert_id)
    assert success is True
    assert service.get_counts()["total"] == 0


def test_alert_service_workflow_evaluation():
    service = AlertService()

    mock_result = {
        "success": True,
        "processed": [
            {
                "excel": None,
                "ai": {"status": "attention_required", "explanation": "Spike in Powder Coating."},
            }
        ],
    }

    missing_dates = ["2026-09-10", "2026-09-11"]
    alerts = service.evaluate_workflow_result(mock_result, missing_dates=missing_dates)

    assert len(alerts) >= 2
    categories = [a.category for a in alerts]
    assert AlertCategory.WARNING.value in categories
    assert AlertCategory.AI_INSIGHT.value in categories

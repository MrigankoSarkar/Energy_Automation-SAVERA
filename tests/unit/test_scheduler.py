import threading
import time
from unittest.mock import MagicMock
import pytest

from app.orchestration.scheduler import AutomationScheduler
from app.orchestration.workflow import AutomationWorkflow


def test_scheduler_init_and_state():
    workflow = MagicMock()
    scheduler = AutomationScheduler(workflow=workflow, interval_minutes=10)
    assert not scheduler.is_running()
    assert scheduler.interval_minutes == 10


def test_scheduler_run_now():
    workflow = MagicMock()
    workflow.run.return_value = {"success": True, "status": "completed"}
    scheduler = AutomationScheduler(workflow=workflow, interval_minutes=5)

    res = scheduler.run_now()
    assert res["success"] is True
    assert res["status"] == "completed"
    workflow.run.assert_called_once()


def test_scheduler_start_stop():
    workflow = MagicMock()
    workflow.run.return_value = {"success": True, "status": "completed"}
    scheduler = AutomationScheduler(workflow=workflow, interval_minutes=1)

    scheduler.start()
    assert scheduler.is_running()

    # Calling start again while running should be a no-op
    scheduler.start()
    assert scheduler.is_running()

    scheduler.stop()
    assert not scheduler.is_running()


def test_workflow_concurrency_lock():
    """Verify AutomationWorkflow prevents overlapping runs."""
    workflow = AutomationWorkflow(
        gmail_service=MagicMock(),
        pdf_service=MagicMock(),
        validation_service=MagicMock(),
        reconciliation_service=MagicMock(),
        excel_service=MagicMock(),
        energy_analyzer=MagicMock(),
        ai_decision_engine=MagicMock(),
        powerbi_service=MagicMock(),
        powerbi_publisher=MagicMock(),
        powerbi_refresh=MagicMock(),
        notification_service=MagicMock(),
    )

    started_event = threading.Event()
    finish_event = threading.Event()

    def slow_find_reports():
        started_event.set()
        finish_event.wait(timeout=5)
        return []

    workflow.gmail.find_reports = slow_find_reports

    # Run in background thread
    t = threading.Thread(target=workflow.run)
    t.start()

    # Wait until slow_find_reports has acquired lock and is executing
    assert started_event.wait(timeout=2)

    # Attempt second concurrent run (non-blocking)
    second_result = workflow.run()
    assert second_result["status"] == "already_running"
    assert second_result["success"] is False

    # Allow first to finish
    finish_event.set()
    t.join(timeout=3)

    # Now that the first completed, a new run should acquire lock normally
    workflow.gmail.find_reports = lambda: []
    third_result = workflow.run()
    assert third_result["status"] == "no_new_reports"
    assert third_result["success"] is True

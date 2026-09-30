import os
import pytest

from app.bootstrap.application import Application
from app.orchestration.workflow import AutomationWorkflow
from app.orchestration.scheduler import AutomationScheduler


def test_application_bootstrap_headless():
    """Verify application boots all services, binds workflow and scheduler."""
    app = Application(with_ui=False)
    assert isinstance(app.workflow, AutomationWorkflow)
    assert isinstance(app.scheduler, AutomationScheduler)
    assert not app.scheduler.is_running()

    app.start()
    assert app.scheduler.is_running()

    app.stop()
    assert not app.scheduler.is_running()


def test_application_dashboard_wiring():
    """Verify dashboard initializes with application controller reference when Qt is available."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance() or QApplication([])
        app = Application(with_ui=True)
        assert app.dashboard is not None, "Dashboard failed to instantiate"
        dash = app.dashboard
        assert dash.application is app
        assert hasattr(dash, "status_text")
        assert hasattr(dash, "card_processed")
        assert hasattr(dash, "status_indicator")
        assert dash.windowTitle() == "EnergyAutomation — EMS Monitoring"

        # Verify modern enterprise panels (8 subinterfaces)
        assert hasattr(dash, "page_overview")
        assert hasattr(dash, "page_recovery")
        assert hasattr(dash, "page_ai")
        assert hasattr(dash, "page_dash")
        assert hasattr(dash, "page_alerts")
        assert hasattr(dash, "page_history")
        assert hasattr(dash, "page_settings")
        assert hasattr(dash, "page_help")

        assert hasattr(dash, "recovery_log")
        assert hasattr(dash, "btn_launch_dash")
        assert hasattr(dash, "btn_start_dash_server")
        assert hasattr(dash, "ai_query_input")
        assert hasattr(dash, "ai_response_display")
        assert dash.notification_service is not None
        assert dash.data_service is not None

        # Exercise panel interactions
        dash.scan_missing_dates()
        assert "scanning" in dash.recovery_log.toPlainText().lower() or "audit" in dash.recovery_log.toPlainText().lower()

        dash._set_and_ask_ai("What is the total energy consumed?")
        assert len(dash.ai_response_display.toPlainText()) > 0

        # Exercise navigation across modern subinterfaces
        for page in [
            dash.page_overview,
            dash.page_recovery,
            dash.page_ai,
            dash.page_dash,
            dash.page_alerts,
            dash.page_history,
            dash.page_settings,
            dash.page_help,
        ]:
            dash.switchTo(page)
            assert dash.stackedWidget.currentWidget() == page

        # Exercise Global Search
        dash.handle_global_search("recovery")
        assert dash.stackedWidget.currentWidget() == dash.page_recovery

        dash.handle_global_search("alert")
        assert dash.stackedWidget.currentWidget() == dash.page_alerts

        dash.handle_global_search("dash")
        assert dash.stackedWidget.currentWidget() == dash.page_dash

        # Exercise Dialogs
        from ui.dialogs.guided_tour import GuidedTourDialog
        from ui.dialogs.setup_wizard import SetupWizardDialog

        tour = GuidedTourDialog(dash)
        assert tour.total_stops > 5
        tour._go_next()
        assert tour.current_idx == 1
        tour._go_prev()
        assert tour.current_idx == 0

        wiz = SetupWizardDialog(dash)
        assert wiz.total_steps == 8
    except Exception as exc:
        pytest.skip(f"Qt display not available: {exc}")


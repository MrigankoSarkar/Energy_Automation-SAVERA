"""
Unit tests for EnergyAutomation enhancements:
1. Back buttons in GuidedTourDialog and SetupWizardDialog
2. Dynamic Google Gemini AI API Key configuration & testing
3. Socket.IO Real-Time Alert Event Hub & Client Streaming
"""

import time
import pytest
from PySide6.QtWidgets import QApplication

from app.services.ai.gemini_service import GeminiService
from app.services.alert.service import AlertCategory, AlertService
from app.services.alert.socket_hub import AlertSocketHub
from ui.dialogs.guided_tour import GuidedTourDialog
from ui.dialogs.setup_wizard import SetupWizardDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_guided_tour_back_buttons(qapp):
    """Verify GuidedTourDialog top and bottom back buttons."""
    dialog = GuidedTourDialog()
    assert hasattr(dialog, "btn_top_back"), "Top header Back to Dashboard button must exist"
    assert hasattr(dialog, "btn_prev"), "Bottom Back button must exist"
    assert dialog.btn_prev.isEnabled(), "Bottom Back button must be enabled on step 0"
    assert "Back" in dialog.btn_prev.text()

    # Step forward
    dialog._go_next()
    assert dialog.current_idx == 1
    assert dialog.btn_prev.text() == "← Back"

    # Step back
    dialog._go_prev()
    assert dialog.current_idx == 0
    assert "Back to Dashboard" in dialog.btn_prev.text()

    # Back on step 0 rejects/closes
    closed = False
    dialog.reject = lambda: setattr(dialog, "_rejected_called", True)
    dialog._go_prev()
    assert getattr(dialog, "_rejected_called", False), "Clicking Back on step 0 must close dialog"


def test_setup_wizard_back_buttons(qapp, tmp_path):
    """Verify SetupWizardDialog top and bottom back buttons."""
    cfg_file = tmp_path / "settings.json"
    cfg_file.write_text("{}", encoding="utf-8")
    dialog = SetupWizardDialog(config_path=str(cfg_file))

    assert hasattr(dialog, "btn_header_back"), "Top header Back to Dashboard button must exist"
    assert hasattr(dialog, "btn_back"), "Bottom Back button must exist"
    assert dialog.btn_back.isEnabled(), "Bottom Back button must be enabled on step 0"

    # Step forward
    dialog._go_next()
    assert dialog.current_step == 1
    assert dialog.btn_back.text() == "← Back"

    # Step back
    dialog._go_back()
    assert dialog.current_step == 0
    assert "Back to Dashboard" in dialog.btn_back.text()

    # Back on step 0 rejects/closes
    dialog.reject = lambda: setattr(dialog, "_rejected_called", True)
    dialog._go_back()
    assert getattr(dialog, "_rejected_called", False), "Clicking Back on step 0 must close dialog"


def test_gemini_api_key_dynamic_integration():
    """Verify GeminiService dynamic API key configuration and test_connection."""
    gem = GeminiService(api_key="", enabled=True)
    assert not gem.is_configured()

    # Test with empty key
    res = gem.test_connection()
    assert not res["success"]
    assert "empty" in res["message"].lower()

    # Dynamically inject key at runtime
    gem.api_key = "test_key_ai_123"
    assert gem.is_configured()

    # Dynamic status
    st = gem.status()
    assert st["configured"] is True
    assert st["enabled"] is True


def test_socketio_alert_hub_and_service_streaming():
    """Verify AlertSocketHub and AlertService real-time broadcasting."""
    hub = AlertSocketHub(port=8789)
    started = hub.start()
    assert started, "AlertSocketHub must start successfully"
    assert hub.is_running()

    service = AlertService(socket_hub=hub)

    import socketio
    client = socketio.Client()
    received_alerts = []
    received_acks = []

    @client.on("alert_created")
    def on_alert(data):
        received_alerts.append(data)

    @client.on("alert_acknowledged")
    def on_ack(data):
        received_acks.append(data)

    try:
        client.connect(hub.get_url(), transports=["websocket", "polling"], wait_timeout=4)
        time.sleep(0.3)

        # Raise alert
        alert = service.raise_alert(
            category=AlertCategory.WARNING,
            title="Transformer Temperature Warning",
            message="Winding temperature reached 82°C.",
            source="sensor_t1",
        )
        time.sleep(0.5)

        assert len(received_alerts) == 1
        assert received_alerts[0]["title"] == "Transformer Temperature Warning"
        assert received_alerts[0]["category"] == "WARNING"

        # Acknowledge alert
        service.acknowledge(alert.alert_id)
        time.sleep(0.5)

        assert len(received_acks) == 1
        assert received_acks[0]["alert_id"] == alert.alert_id

    finally:
        client.disconnect()
        hub.stop()

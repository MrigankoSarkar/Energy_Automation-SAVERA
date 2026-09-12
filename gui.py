from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from config import PROJECT_ROOT, load_config, save_config
from scheduler import AutomationScheduler


APP_NAME = "EnergyAutomation"
APP_VERSION = "1.0.0"

UI_DIR = PROJECT_ROOT / "ui"
INDEX_FILE = UI_DIR / "index.html"

ASSETS_DIR = PROJECT_ROOT / "assets"

COMPANY_LOGO = ASSETS_DIR / "savera-logo.jpg"
APP_ICON = ASSETS_DIR / "app.ico"
FAVICON = ASSETS_DIR / "favicon.jpg"


class Bridge(QObject):

    def __init__(self, window):
        super().__init__()
        self.window = window

    # ========================================================
    # RUN NOW
    # ========================================================

    @Slot()
    def runNow(self):

        self.window._ui_notification(
            "Manual automation is starting...",
            "info"
        )

        self.window.scheduler.run_now(
            force=True
        )

    # ========================================================
    # START
    # ========================================================

    @Slot()
    def start(self):

        self.window._start_scheduler()

    @Slot()
    def startAutomation(self):

        self.window._start_scheduler()

    # ========================================================
    # STOP
    # ========================================================

    @Slot()
    def stop(self):

        self.window._stop_scheduler()

    @Slot()
    def stopAutomation(self):

        self.window._stop_scheduler()

    # ========================================================
    # REFRESH
    # ========================================================

    @Slot()
    def refresh(self):

        self.window._refresh_application()

    # ========================================================
    # SETTINGS
    # ========================================================

    @Slot()
    def getSettings(self):

        self.window._send_settings()

    @Slot(result=str)
    def getInitialState(self):

        return self.window._initial_state_json()

    @Slot(str)
    def saveSettings(self, settings_json):

        self.window._save_settings(
            settings_json
        )


class MainWindow(QMainWindow):

    # Background thread → Qt GUI thread
    schedulerEvent = Signal(
        str,
        object
    )

    def __init__(self):

        super().__init__()

        self.config = load_config()

        self.project_dir = PROJECT_ROOT

        self.db = self._create_database()

        # ====================================================
        # WINDOW
        # ====================================================

        self.setWindowTitle(
            f"{APP_NAME} — EMS Operations"
        )

        self.resize(
            1500,
            950
        )

        self.setMinimumSize(
            1100,
            700
        )

        self._set_icon()

        # ====================================================
        # WEB VIEW
        # ====================================================

        self.web = QWebEngineView(
            self
        )

        self.setCentralWidget(
            self.web
        )

        # ====================================================
        # WEB CHANNEL
        # ====================================================

        self.channel = QWebChannel(
            self.web.page()
        )

        self.bridge = Bridge(
            self
        )

        self.channel.registerObject(
            "bridge",
            self.bridge
        )

        self.web.page().setWebChannel(
            self.channel
        )

        # ====================================================
        # THREAD-SAFE SCHEDULER EVENTS
        # ====================================================

        self.schedulerEvent.connect(
            self._process_scheduler_event
        )

        # ====================================================
        # SCHEDULER
        # ====================================================

        self.scheduler = AutomationScheduler(
            self.config,
            self.project_dir,
            self.db
        )

        self.scheduler.set_event_callback(
            self._scheduler_callback
        )

        # ====================================================
        # PAGE LOADED
        # ====================================================

        self.web.loadFinished.connect(
            self._page_loaded
        )

        # ====================================================
        # LOAD HTML
        # ====================================================

        if INDEX_FILE.exists():

            self.web.setUrl(
                QUrl.fromLocalFile(
                    str(INDEX_FILE)
                )
            )

        else:

            raise FileNotFoundError(
                f"GUI-001: UI file not found: {INDEX_FILE}"
            )

    # ========================================================
    # DATABASE
    # ========================================================

    def _create_database(self):

        try:

            from database import Database

            try:
                return Database(
                    self.project_dir
                )

            except TypeError:
                return Database()

        except Exception as exc:

            print(
                "[DATABASE]",
                exc
            )

            return None

    # ========================================================
    # ICON
    # ========================================================

    def _set_icon(self):

        for icon_path in (
            APP_ICON,
            FAVICON,
            COMPANY_LOGO
        ):

            if icon_path.exists():

                self.setWindowIcon(
                    QIcon(
                        str(icon_path)
                    )
                )

                break

    # ========================================================
    # PAGE LOADED
    # ========================================================

    def _page_loaded(
        self,
        success
    ):

        if not success:

            self.send_event(
                "error",
                {
                    "message":
                        "EnergyAutomation UI failed to load."
                }
            )

            return

        # Send initial state only AFTER JS exists.
        self.send_event(
            "initialState",
            self._initial_state()
        )

        self._send_settings()

        self._send_scheduler_state()

        self._ui_notification(
            "EnergyAutomation is ready.",
            "success"
        )

        # Automatic start.
        if (
            self.config
            .get(
                "automation",
                {}
            )
            .get(
                "start_automatically",
                True
            )
        ):

            self._start_scheduler()

    # ========================================================
    # INITIAL STATE
    # ========================================================

    def _initial_state(self):

        next_run = (
            self.scheduler.get_next_run_at()
        )

        return {
            "settings": self.config,

            "report": None,

            "activity": [],

            "scheduler": {
                "running":
                    bool(
                        self.scheduler.running
                    ),

                "interval":
                    self.scheduler.interval_minutes,

                "next_run_at":
                    next_run.isoformat()
                    if next_run
                    else None
            }
        }

    def _initial_state_json(self):

        return json.dumps(
            self._initial_state(),
            ensure_ascii=False,
            default=str
        )

    # ========================================================
    # SEND EVENT TO JAVASCRIPT
    # ========================================================

    def send_event(
        self,
        event_name,
        payload
    ):

        event_json = json.dumps(
            event_name,
            ensure_ascii=False
        )

        payload_json = json.dumps(
            payload or {},
            ensure_ascii=False,
            default=str
        )

        javascript = (
            "window.backendEvent("
            f"{event_json},"
            f"{json.dumps(payload_json)}"
            ");"
        )

        try:

            self.web.page().runJavaScript(
                javascript
            )

        except Exception as exc:

            print(
                "[GUI JS ERROR]",
                exc
            )

    # ========================================================
    # THREAD-SAFE SCHEDULER CALLBACK
    # ========================================================

    def _scheduler_callback(
        self,
        event_name,
        payload
    ):

        self.schedulerEvent.emit(
            event_name,
            payload or {}
        )

    @Slot(str, object)
    def _process_scheduler_event(
        self,
        event_name,
        payload
    ):

        self.send_event(
            event_name,
            payload
        )

    # ========================================================
    # NOTIFICATION
    # ========================================================

    def _ui_notification(
        self,
        message,
        notification_type="info"
    ):

        self.send_event(
            "notification",
            {
                "type":
                    notification_type,

                "message":
                    message,

                "duration":
                    4500
            }
        )

    # ========================================================
    # START
    # ========================================================

    def _start_scheduler(self):

        try:

            if self.scheduler.running:

                self._ui_notification(
                    "Automatic monitoring is already running.",
                    "info"
                )

                return

            self.scheduler.start()

            self._send_scheduler_state()

        except Exception as exc:

            self.send_event(
                "error",
                {
                    "message":
                        f"Could not start automation: {exc}"
                }
            )

    # ========================================================
    # STOP
    # ========================================================

    def _stop_scheduler(self):

        try:

            self.scheduler.stop()

            self._send_scheduler_state()

            self._ui_notification(
                "Automatic monitoring stopped.",
                "warning"
            )

        except Exception as exc:

            self.send_event(
                "error",
                {
                    "message":
                        f"Could not stop automation: {exc}"
                }
            )

    # ========================================================
    # REFRESH
    # ========================================================

    def _refresh_application(self):

        try:

            self._ui_notification(
                "Refreshing application data...",
                "info"
            )

            # Reload settings only.
            self.config = load_config()

            # IMPORTANT:
            # Do NOT restart scheduler.
            # Do NOT change next_run_at.
            # Do NOT reset timer.

            self._send_settings()

            self._send_scheduler_state()

            self._ui_notification(
                "Application data refreshed.",
                "success"
            )

        except Exception as exc:

            self.send_event(
                "error",
                {
                    "message":
                        f"Refresh failed: {exc}"
                }
            )

    # ========================================================
    # SETTINGS
    # ========================================================

    def _send_settings(self):

        self.send_event(
            "settings",
            self.config
        )

    def _save_settings(
        self,
        settings_json
    ):

        try:

            settings = json.loads(
                settings_json
            )

            if not isinstance(
                settings,
                dict
            ):

                raise ValueError(
                    "Settings must be a JSON object."
                )

            save_config(
                settings
            )

            self.config = settings

            self._ui_notification(
                "Settings saved successfully.",
                "success"
            )

            self._send_settings()

            # If interval changed, restart scheduler
            # intentionally because the user explicitly
            # changed its configuration.
            if self.scheduler.running:

                self.scheduler.stop()

                self.scheduler.start()

            else:

                self._send_scheduler_state()

        except Exception as exc:

            self.send_event(
                "error",
                {
                    "message":
                        f"Settings could not be saved: {exc}"
                }
            )

    # ========================================================
    # SCHEDULER STATE
    # ========================================================

    def _send_scheduler_state(self):

        next_run = (
            self.scheduler.get_next_run_at()
        )

        self.send_event(
            "scheduler_state",
            {
                "running":
                    bool(
                        self.scheduler.running
                    ),

                "interval":
                    self.scheduler.interval_minutes,

                "next_run_at":
                    next_run.isoformat()
                    if next_run
                    else None
            }
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        try:

            self.scheduler.stop()

        except Exception:
            pass

        event.accept()


def main():

    app = QApplication(
        []
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    window = MainWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
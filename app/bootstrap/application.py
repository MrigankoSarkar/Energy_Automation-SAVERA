import json
from pathlib import Path
from typing import Optional

from app.bootstrap.dependencies import build_services
from ui.dashboard import Dashboard


class Application:
    def __init__(self, with_ui: bool = True):
        self.services = build_services()

        self.workflow = self.services["workflow"]
        self.scheduler = self.services["scheduler"]
        self.dashboard: Optional[Dashboard] = None

        if with_ui:
            try:
                self.dashboard = Dashboard(self)
            except Exception:
                # Allow headless operation if Qt display server cannot create widgets
                self.dashboard = None

    def start(self):
        settings_path = Path("config") / "settings.json"
        start_minimized = False
        start_automatically = True

        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    auto_cfg = cfg.get("automation", {})
                    start_minimized = auto_cfg.get("start_minimized", False)
                    start_automatically = auto_cfg.get("start_automatically", True)
            except Exception:
                pass

        if self.dashboard is not None:
            if start_minimized:
                self.dashboard.showMinimized()
            else:
                self.dashboard.show()

        if start_automatically and self.scheduler:
            self.scheduler.start()

    def show(self):
        if self.dashboard is not None:
            self.dashboard.show()

    def stop(self):
        if self.scheduler:
            self.scheduler.stop()

    def run_now(self):
        return self.workflow.run()
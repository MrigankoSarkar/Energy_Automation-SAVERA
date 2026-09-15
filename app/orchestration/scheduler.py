from __future__ import annotations

import threading
import time
from typing import Optional


class AutomationScheduler:

    def __init__(
        self,
        workflow,
        interval_minutes: int = 5,
    ):
        self.workflow = workflow
        self.interval_minutes = max(
            1,
            int(interval_minutes),
        )

        self._thread: Optional[
            threading.Thread
        ] = None

        self._stop_event = (
            threading.Event()
        )

        self.running = False

        self.last_result = None

    def is_running(self) -> bool:
        return self.running

    def start(self):

        if self.running:
            return

        self.running = True

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="EnergyAutomationScheduler",
        )

        self._thread.start()

    def stop(self):

        self.running = False

        self._stop_event.set()

        if (
            self._thread
            and self._thread.is_alive()
        ):
            self._thread.join(
                timeout=2
            )

    def run_now(self):

        try:
            self.last_result = (
                self.workflow.run()
            )

            return self.last_result

        except Exception as exc:
            self.last_result = {
                "success": False,
                "error": str(exc),
            }

            return self.last_result

    def execute(self):
        return self.run_now()

    def _worker(self):

        while not self._stop_event.is_set():

            try:
                self.last_result = (
                    self.workflow.run()
                )

            except Exception as exc:
                self.last_result = {
                    "success": False,
                    "error": str(exc),
                }

            self._stop_event.wait(
                self.interval_minutes * 60
            )
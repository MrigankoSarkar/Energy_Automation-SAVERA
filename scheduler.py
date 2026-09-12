from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional


class AutomationScheduler:
    """
    Background scheduler for EnergyAutomation.

    Supports both:

    New style:
        AutomationScheduler(
            engine,
            interval_minutes,
            event_callback
        )

    Existing GUI style:
        AutomationScheduler(
            config,
            project_dir,
            db
        )

    The scheduler never blocks the GUI thread.
    """

    def __init__(
        self,
        engine_or_config,
        interval_or_project_dir=None,
        event_callback_or_db=None,
    ):

        # ====================================================
        # INTERNAL STATE
        # ====================================================

        self.engine = None

        self.config = None

        self.project_dir = None

        self.db = None

        self.event_callback = None

        self.interval_minutes = 5

        self.running = False

        self.worker = None

        self.next_run_at: Optional[datetime] = None

        self._lock = threading.RLock()

        self._stop_event = threading.Event()


        # ====================================================
        # DETECT CONSTRUCTOR FORMAT
        # ====================================================

        # New style:
        #
        # AutomationScheduler(
        #     engine,
        #     5,
        #     callback
        # )
        #
        # Existing GUI style:
        #
        # AutomationScheduler(
        #     config,
        #     project_dir,
        #     db
        # )

        if isinstance(
            interval_or_project_dir,
            (int, float)
        ):

            # -----------------------------------------------
            # NEW STYLE
            # -----------------------------------------------

            self.engine = engine_or_config

            self.interval_minutes = max(
                1,
                int(interval_or_project_dir)
            )

            self.event_callback = (
                event_callback_or_db
            )

        else:

            # -----------------------------------------------
            # EXISTING GUI STYLE
            # -----------------------------------------------

            self.config = engine_or_config

            self.project_dir = (
                interval_or_project_dir
            )

            self.db = (
                event_callback_or_db
            )

            self.interval_minutes = max(
                1,
                int(
                    self.config
                    .get("automation", {})
                    .get(
                        "check_interval_minutes",
                        5
                    )
                )
            )

            # The actual AutomationEngine is created lazily.
            self.engine = None


        print(
            "[SCHEDULER] Initialized"
        )

        print(
            f"[SCHEDULER] Interval: "
            f"{self.interval_minutes} minutes"
        )


    # ========================================================
    # EVENT CALLBACK
    # ========================================================

    def set_event_callback(
        self,
        callback: Callable[
            [str, dict[str, Any]],
            None
        ]
    ):

        self.event_callback = callback


    def _emit(
        self,
        event_name: str,
        payload: Optional[
            dict[str, Any]
        ] = None,
    ):

        if payload is None:
            payload = {}

        callback = self.event_callback

        if callback is None:
            return

        try:

            callback(
                event_name,
                payload
            )

        except Exception as exc:

            print(
                "[SCHEDULER] Callback error:",
                exc
            )


    # ========================================================
    # ENGINE CREATION
    # ========================================================

    def _get_engine(self):

        if self.engine is not None:
            return self.engine

        # Existing GUI architecture.
        if self.config is not None:

            try:

                from automation_engine import (
                    AutomationEngine
                )

                self.engine = AutomationEngine(
                    self.config,
                    self.project_dir,
                    self.db,
                )

                return self.engine

            except TypeError:

                # Compatibility with another possible
                # AutomationEngine signature.

                try:

                    self.engine = AutomationEngine(
                        self.config
                    )

                    return self.engine

                except Exception:
                    raise

        raise RuntimeError(
            "SCHEDULER-001: Automation engine "
            "has not been configured."
        )


    # ========================================================
    # NEXT RUN
    # ========================================================

    def _set_next_run(
        self,
        when: datetime
    ):

        with self._lock:

            self.next_run_at = when

        self._emit(
            "next_run",
            {
                "next_run_at":
                    when.isoformat()
            }
        )

        self._emit(
            "scheduler_state",
            {
                "running":
                    self.running,

                "next_run_at":
                    when.isoformat()
            }
        )


    def get_next_run_at(self):

        with self._lock:
            return self.next_run_at


    # ========================================================
    # START
    # ========================================================

    def start(self):

        with self._lock:

            if self.running:
                return

            self.running = True

            self._stop_event.clear()


        next_run = (
            datetime.now()
            +
            timedelta(
                minutes=self.interval_minutes
            )
        )

        self._set_next_run(
            next_run
        )


        self.worker = threading.Thread(
            target=self._loop,
            daemon=True,
            name="EnergyAutomationScheduler"
        )

        self.worker.start()


        self._emit(
            "scheduler_state",
            {
                "running": True,

                "next_run_at":
                    next_run.isoformat(),

                "interval_minutes":
                    self.interval_minutes
            }
        )


        self._emit(
            "notification",
            {
                "type": "success",

                "message":
                    "Automatic EMS monitoring is running.",

                "duration": 4000
            }
        )


        print(
            "[SCHEDULER] Automatic monitoring started."
        )


    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        with self._lock:

            self.running = False

        self._stop_event.set()


        self._emit(
            "scheduler_state",
            {
                "running": False,

                "next_run_at": None
            }
        )


        self._emit(
            "notification",
            {
                "type": "warning",

                "message":
                    "Automatic EMS monitoring stopped.",

                "duration": 4000
            }
        )


        print(
            "[SCHEDULER] Automatic monitoring stopped."
        )


    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    def _loop(self):

        print(
            "[SCHEDULER] Background thread started."
        )

        while not self._stop_event.is_set():

            with self._lock:

                if not self.running:
                    break

                next_run = (
                    self.next_run_at
                )


            if next_run is None:

                next_run = (
                    datetime.now()
                    +
                    timedelta(
                        minutes=self.interval_minutes
                    )
                )

                self._set_next_run(
                    next_run
                )

                continue


            remaining = (
                next_run -
                datetime.now()
            ).total_seconds()


            # -----------------------------------------------
            # Wait without blocking GUI.
            # -----------------------------------------------

            if remaining > 0:

                self._stop_event.wait(
                    min(
                        1.0,
                        remaining
                    )
                )

                continue


            # =================================================
            # TIME TO RUN AUTOMATION
            # =================================================

            self._emit(
                "progress",
                {
                    "stage":
                        "automation",

                    "message":
                        "Automatic EMS report check started.",

                    "percent": 5
                }
            )


            self._emit(
                "notification",
                {
                    "type": "info",

                    "message":
                        "Automatic EMS report check started.",

                    "duration": 3500
                }
            )


            try:

                engine = (
                    self._get_engine()
                )

                result = engine.run(
                    force=False
                )


                self._emit(
                    "progress",
                    {
                        "stage":
                            "automation",

                        "message":
                            "Automatic EMS report check completed.",

                        "percent": 100
                    }
                )


                self._emit(
                    "automation_result",
                    result
                )


                self._emit(
                    "notification",
                    {
                        "type": "success",

                        "message":
                            "Automatic EMS report check completed successfully.",

                        "duration": 5000
                    }
                )


            except Exception as exc:

                print(
                    "[SCHEDULER ERROR]",
                    repr(exc)
                )


                self._emit(
                    "error",
                    {
                        "message":
                            str(exc)
                    }
                )


                self._emit(
                    "notification",
                    {
                        "type": "error",

                        "message":
                            str(exc),

                        "duration": 8000
                    }
                )


            # =================================================
            # SCHEDULE NEXT CHECK
            # =================================================

            if self.running:

                next_run = (
                    datetime.now()
                    +
                    timedelta(
                        minutes=self.interval_minutes
                    )
                )

                self._set_next_run(
                    next_run
                )


        print(
            "[SCHEDULER] Background thread stopped."
        )


    # ========================================================
    # MANUAL RUN
    # ========================================================

    def run_now(
        self,
        force: bool = True
    ):

        def worker():

            self._emit(
                "progress",
                {
                    "stage":
                        "manual",

                    "message":
                        "Manual EMS automation started.",

                    "percent": 5
                }
            )


            self._emit(
                "notification",
                {
                    "type": "info",

                    "message":
                        "Manual EMS automation started.",

                    "duration": 3500
                }
            )


            try:

                engine = (
                    self._get_engine()
                )

                result = engine.run(
                    force=force
                )


                self._emit(
                    "automation_result",
                    result
                )


                self._emit(
                    "progress",
                    {
                        "stage":
                            "manual",

                        "message":
                            "Manual automation completed.",

                        "percent": 100
                    }
                )


                self._emit(
                    "notification",
                    {
                        "type": "success",

                        "message":
                            "Manual automation completed successfully.",

                        "duration": 5000
                    }
                )


            except Exception as exc:

                print(
                    "[MANUAL RUN ERROR]",
                    repr(exc)
                )


                self._emit(
                    "error",
                    {
                        "message":
                            str(exc)
                    }
                )


                self._emit(
                    "notification",
                    {
                        "type": "error",

                        "message":
                            str(exc),

                        "duration": 8000
                    }
                )


        threading.Thread(
            target=worker,
            daemon=True,
            name="EnergyAutomationManualRun"
        ).start()


    # ========================================================
    # COMPATIBILITY METHOD
    # ========================================================

    def execute(
        self,
        force: bool = False
    ):

        self.run_now(
            force=force
        )
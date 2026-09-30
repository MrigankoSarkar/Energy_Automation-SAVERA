"""
Headless workflow pipeline provider for Core Automation Microservice.
Provides AutoCAD AcCoreConsole / MATLAB headless computational engine architecture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.bootstrap.dependencies import build_services

logger = logging.getLogger("services.core_automation")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class CoreAutomationEngine:
    _instance: Optional[CoreAutomationEngine] = None

    def __init__(self):
        self.services = build_services()
        self.workflow = self.services.get("workflow")
        self.scheduler = self.services.get("scheduler")
        self.history_repo = self.services.get("report_repository")
        self.excel_service = self.services.get("excel_service")
        self.last_run_result: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> CoreAutomationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run_cycle(self) -> Dict[str, Any]:
        if not self.workflow:
            return {"success": False, "message": "Workflow engine not initialized."}
        try:
            result = self.workflow.run()
            self.last_run_result = result
            return result
        except Exception as exc:
            logger.error("Core automation cycle failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def run_gap_healing(self, days: int = 30) -> Dict[str, Any]:
        if not self.workflow:
            return {"success": False, "message": "Workflow service not available."}
        try:
            recovered = []
            if hasattr(self.workflow, "_recover_missing_reports"):
                recovered = self.workflow._recover_missing_reports()
            return {
                "success": True,
                "lookback_days": days,
                "recovered_count": len(recovered),
                "recovered_dates": recovered,
                "message": f"Gap healing completed for last {days} days.",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        scheduler_active = False
        if self.scheduler:
            scheduler_active = getattr(self.scheduler, "is_running", lambda: False)
            if callable(scheduler_active):
                scheduler_active = scheduler_active()

        latest_report = None
        if self.history_repo:
            try:
                latest_report = self.history_repo.get_latest_report()
            except Exception:
                pass

        wb_path = getattr(self.excel_service, "workbook_path", "data/Test_BI_Analysis_Report_2026.xlsx")

        return {
            "engine": "CoreAutomationEngine",
            "scheduler_running": scheduler_active,
            "last_cycle_result": self.last_run_result,
            "latest_persisted_report": latest_report,
            "storage_path": str(wb_path),
        }

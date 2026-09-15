"""
Alert Service and Rules Engine for EnergyAutomation.
Manages enterprise alerts across Critical, Warning, Info, and AI categories.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertCategory(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    AI_INSIGHT = "AI_INSIGHT"


@dataclass
class Alert:
    alert_id: str
    category: str
    title: str
    message: str
    timestamp: str
    acknowledged: bool = False
    source: str = "system"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlertService:
    """
    Centralized Alert Service maintaining system notifications,
    deduplication, persistent state, and rule-based triggering.
    """

    def __init__(self, database: Any = None, event_bus: Any = None) -> None:
        self.database = database
        self.event_bus = event_bus
        self._alerts: List[Alert] = []
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Create alerts table in SQLite database if available."""
        if not self.database:
            return
        try:
            self.database.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL,
                    details TEXT
                )
                """
            )
            # Load existing unacknowledged alerts
            rows = self.database.fetch_all(
                "SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY timestamp DESC"
            )
            import json

            with self._lock:
                for r in rows:
                    details = {}
                    if r["details"]:
                        try:
                            details = json.loads(r["details"])
                        except Exception:
                            pass
                    self._alerts.append(
                        Alert(
                            alert_id=r["id"],
                            category=r["category"],
                            title=r["title"],
                            message=r["message"],
                            timestamp=r["timestamp"],
                            acknowledged=bool(r["acknowledged"]),
                            source=r["source"],
                            details=details,
                        )
                    )
        except Exception as exc:
            logger.warning(f"Failed to initialize alerts table in DB: {exc}")

    def raise_alert(
        self,
        category: AlertCategory | str,
        title: str,
        message: str,
        source: str = "system",
        details: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Raise a new alert. Skips raising if an identical unacknowledged alert already exists.
        """
        cat_str = category.value if isinstance(category, AlertCategory) else str(category)
        with self._lock:
            # Deduplication check
            for existing in self._alerts:
                if (
                    not existing.acknowledged
                    and existing.category == cat_str
                    and existing.title == title
                ):
                    return existing

            alert_id = f"alert_{uuid.uuid4().hex[:10]}"
            now_iso = datetime.now().isoformat()
            alert = Alert(
                alert_id=alert_id,
                category=cat_str,
                title=title,
                message=message,
                timestamp=now_iso,
                acknowledged=False,
                source=source,
                details=details or {},
            )
            self._alerts.insert(0, alert)

            # Persist to database
            if self.database:
                try:
                    import json

                    self.database.execute(
                        """
                        INSERT OR REPLACE INTO alerts (id, category, title, message, timestamp, acknowledged, source, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            alert.alert_id,
                            alert.category,
                            alert.title,
                            alert.message,
                            alert.timestamp,
                            1 if alert.acknowledged else 0,
                            alert.source,
                            json.dumps(alert.details),
                        ),
                    )
                except Exception as exc:
                    logger.warning(f"Could not persist alert to database: {exc}")

        # Publish event
        if self.event_bus:
            try:
                self.event_bus.publish(
                    "alert.raised",
                    data=alert.to_dict(),
                    source="alert_service",
                )
            except Exception:
                pass

        return alert

    def acknowledge(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    if self.database:
                        try:
                            self.database.execute(
                                "UPDATE alerts SET acknowledged = 1 WHERE id = ?",
                                (alert_id,),
                            )
                        except Exception as exc:
                            logger.warning(f"Could not update alert acknowledgment in DB: {exc}")
                    return True
        return False

    def acknowledge_all(self) -> int:
        """Mark all unacknowledged alerts as acknowledged."""
        count = 0
        with self._lock:
            for alert in self._alerts:
                if not alert.acknowledged:
                    alert.acknowledged = True
                    count += 1
            if self.database:
                try:
                    self.database.execute("UPDATE alerts SET acknowledged = 1")
                except Exception:
                    pass
        return count

    def get_alerts(
        self,
        category: Optional[AlertCategory | str] = None,
        unacknowledged_only: bool = False,
        limit: int = 100,
    ) -> List[Alert]:
        """Query alerts with optional filtering."""
        cat_filter = (
            category.value
            if isinstance(category, AlertCategory)
            else (str(category) if category else None)
        )
        with self._lock:
            filtered = self._alerts
            if cat_filter:
                filtered = [a for a in filtered if a.category == cat_filter]
            if unacknowledged_only:
                filtered = [a for a in filtered if not a.acknowledged]
            return list(filtered[:limit])

    def get_counts(self) -> Dict[str, int]:
        """Return counts of unacknowledged alerts grouped by category."""
        counts = {
            "total": 0,
            AlertCategory.CRITICAL.value: 0,
            AlertCategory.WARNING.value: 0,
            AlertCategory.INFO.value: 0,
            AlertCategory.AI_INSIGHT.value: 0,
        }
        with self._lock:
            for alert in self._alerts:
                if not alert.acknowledged:
                    counts["total"] += 1
                    if alert.category in counts:
                        counts[alert.category] += 1
        return counts

    def evaluate_workflow_result(
        self,
        result: Dict[str, Any],
        missing_dates: Optional[List[str]] = None,
    ) -> List[Alert]:
        """
        Evaluate workflow execution context against enterprise alert rules.
        """
        generated: List[Alert] = []

        # Rule 1: Missing reports detected
        if missing_dates:
            count = len(missing_dates)
            cat = AlertCategory.CRITICAL if count >= 3 else AlertCategory.WARNING
            dates_str = ", ".join(missing_dates[:4])
            if count > 4:
                dates_str += f" (+{count - 4} more)"
            alert = self.raise_alert(
                category=cat,
                title=f"{count} Missing EMS Report(s) Detected",
                message=f"Missing report dates identified in past window: {dates_str}. Automated recovery available.",
                source="reconciliation",
                details={"missing_dates": missing_dates},
            )
            generated.append(alert)

        # Rule 2: Workflow failure
        if not result.get("success", False):
            err = result.get("error") or "Unknown report processing failure."
            alert = self.raise_alert(
                category=AlertCategory.CRITICAL,
                title="EMS Automation Workflow Error",
                message=f"Processing stopped with error: {err}",
                source="workflow",
                details={"error": str(err)},
            )
            generated.append(alert)

        # Rule 3: Unmapped numeric meters
        processed_list = result.get("processed", [])
        for p in processed_list:
            excel_res = p.get("excel")
            unmapped = getattr(excel_res, "skipped_meters", []) if excel_res else []
            if unmapped:
                alert = self.raise_alert(
                    category=AlertCategory.WARNING,
                    title="Unmapped Meter Reading(s) Detected",
                    message=f"Report contained {len(unmapped)} meter(s) not mapped to Excel headers: {', '.join(unmapped[:3])}",
                    source="excel_service",
                    details={"unmapped": unmapped},
                )
                generated.append(alert)

            # Rule 4: Power BI sync pending or error
            pbi_res = p.get("powerbi")
            if pbi_res and not pbi_res.get("success", False):
                alert = self.raise_alert(
                    category=AlertCategory.INFO,
                    title="Power BI Sync Pending / Deferred",
                    message=pbi_res.get("message") or "Power BI synchronization is in local export mode.",
                    source="powerbi",
                )
                generated.append(alert)

            # Rule 5: AI anomaly detected
            ai_res = p.get("ai")
            if ai_res and ai_res.get("status") == "attention_required":
                alert = self.raise_alert(
                    category=AlertCategory.AI_INSIGHT,
                    title="Energy Consumption Anomaly Flagged",
                    message=ai_res.get("explanation") or "Gemini AI detected an abnormal energy distribution pattern.",
                    source="gemini",
                    details=ai_res,
                )
                generated.append(alert)

        return generated

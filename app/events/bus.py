"""
Thread-safe in-process Event Bus for EnergyAutomation.
Enforces service isolation and decoupled asynchronous-safe communication.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    REPORT_DISCOVERED = "report.discovered"
    REPORT_PARSED = "report.parsed"
    REPORT_VALIDATED = "report.validated"
    EXCEL_UPDATED = "excel.updated"
    DATABASE_RECORDED = "database.recorded"
    ANOMALY_DETECTED = "anomaly.detected"
    POWERBI_SYNC_REQUESTED = "powerbi.sync.requested"
    POWERBI_SYNC_COMPLETED = "powerbi.sync.completed"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"
    ALERT_RAISED = "alert.raised"
    SCHEDULER_STATE_CHANGED = "scheduler.state_changed"


@dataclass(frozen=True)
class Event:
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class EventBus:
    """
    Thread-safe event bus ensuring complete failure isolation.
    If an external listener (such as Power BI or Gemini) raises an error,
    it is logged safely and does not impact the core deterministic pipeline.
    """

    def __init__(self, max_history: int = 200) -> None:
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()
        self._max_history = max_history
        self._history: List[Event] = []

    def subscribe(
        self,
        event_type: str | EventType,
        handler: Callable[[Event], None],
    ) -> Callable[[], None]:
        """
        Register an event handler. Returns an unsubscribe function.
        Use '*' to subscribe to all events.
        """
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(handler)

        def unsubscribe():
            self.unsubscribe(key, handler)

        return unsubscribe

    def unsubscribe(
        self,
        event_type: str | EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """Remove an event handler."""
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        with self._lock:
            if key in self._subscribers and handler in self._subscribers[key]:
                self._subscribers[key].remove(handler)

    def publish(
        self,
        event_or_type: Event | EventType | str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "system",
    ) -> Event:
        """
        Publish an event to all registered subscribers.
        Subscribers are called safely with error isolation.
        """
        if isinstance(event_or_type, Event):
            event = event_or_type
        else:
            evt_type = (
                event_or_type.value
                if isinstance(event_or_type, EventType)
                else str(event_or_type)
            )
            event = Event(
                event_type=evt_type,
                data=data or {},
                source=source,
            )

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            # Get exact match handlers + wildcard handlers
            handlers = list(self._subscribers.get(event.event_type, []))
            wildcards = list(self._subscribers.get("*", []))

        # Invoke handlers outside lock to prevent deadlocks
        for handler in handlers + wildcards:
            try:
                handler(event)
            except Exception as exc:
                logger.warning(
                    f"EventBus handler {getattr(handler, '__name__', handler)} "
                    f"failed on event {event.event_type}: {exc}",
                    exc_info=True,
                )

        return event

    def get_history(self, limit: int = 50) -> List[Event]:
        """Return recent event history."""
        with self._lock:
            return list(self._history[-limit:])

    def clear(self) -> None:
        """Clear all subscribers and history."""
        with self._lock:
            self._subscribers.clear()
            self._history.clear()


# Global singleton instance
_GLOBAL_BUS: Optional[EventBus] = None
_BUS_LOCK = threading.Lock()


def get_event_bus() -> EventBus:
    """Retrieve the application-wide EventBus singleton."""
    global _GLOBAL_BUS
    if _GLOBAL_BUS is None:
        with _BUS_LOCK:
            if _GLOBAL_BUS is None:
                _GLOBAL_BUS = EventBus()
    return _GLOBAL_BUS

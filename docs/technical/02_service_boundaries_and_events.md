# Chapter 2: Service Boundaries & Event-Driven Architecture

This chapter details the decoupled modular architecture of EnergyAutomation, the thread-safe `EventBus` implementation, event taxonomy, and failure isolation guarantees.

---

## 1. Modular Decoupling & The EventBus Pattern

In traditional enterprise automation scripts, pipeline steps are often tightly coupled: if an optional cloud sync fails, the entire script crashes, leaving local files half-written.

EnergyAutomation eliminates tight coupling by employing an **In-Process Publish-Subscribe EventBus** (`app/events/bus.py`). Core pipeline services execute their primary duties and publish domain events. Secondary and tertiary subsystems (such as UI updates, alert notifications, and Power BI cloud sync) subscribe to these events independently.

```mermaid
sequenceDiagram
    autonumber
    participant WC as WorkflowCoordinator
    participant EB as EventBus
    participant PDF as PDFParser
    participant VAL as DataValidator
    participant XL as ExcelService
    participant DB as PersistenceRepo
    participant ALT as AlertService
    participant PBI as PowerBIService
    participant UI as Qt Dashboard

    WC->>EB: publish(WorkflowStartedEvent)
    EB-->>UI: on_workflow_started()
    
    WC->>PDF: parse_pdf(path)
    PDF-->>WC: parsed_report
    WC->>EB: publish(PDFParsedEvent)
    EB-->>UI: update_meter_table()
    
    WC->>VAL: validate(parsed_report)
    VAL-->>WC: validation_result
    WC->>EB: publish(ReportValidatedEvent)
    
    WC->>XL: update_workbook(report)
    XL-->>WC: success
    WC->>EB: publish(ExcelUpdatedEvent)
    EB-->>UI: refresh_status_badge()
    
    WC->>DB: save_audit_record(report)
    DB-->>WC: audit_id
    WC->>EB: publish(AuditSavedEvent)
    
    WC->>ALT: evaluate_workflow(report, result)
    ALT-->>WC: alerts_generated
    
    opt Power BI Enabled
        WC->>PBI: push_realtime(report)
        Note over PBI: If network drops, error isolated
    end
    
    WC->>EB: publish(WorkflowCompletedEvent)
    EB-->>UI: show_success_toast()
```

---

## 2. EventBus Implementation Details

The `EventBus` class provides:
1. **Thread-Safe Registration**: Subscriptions and subscriber lists are guarded by re-entrant mutexes (`threading.RLock`), supporting multi-threaded GUI and worker thread environments.
2. **Wildcard & Exact Matching**: Subscriptions can target specific event types (e.g. `subscribe("excel.updated", callback)`) or catch-all wildcard patterns (`subscribe("*", audit_callback)`).
3. **Robust Error Isolation**: If an individual subscriber callback raises an unhandled exception, the `EventBus` catches the error, logs a detailed traceback, and continues notifying remaining subscribers. The publisher is never interrupted.
4. **Bounded Event History**: Retains the last $N$ events (default: 100) in a ring buffer (`collections.deque`), enabling retrospective diagnostic inspection and UI history replay.

---

## 3. Domain Event Taxonomy

All events inherit from the immutable `Event` dataclass:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

@dataclass(frozen=True)
class Event:
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### Standard System Events
| Event Type | Typical Payload Keys | Published By | Typical Subscribers |
| :--- | :--- | :--- | :--- |
| `workflow.started` | `trigger`, `report_date`, `source` | `WorkflowCoordinator` | Dashboard, Status Bar |
| `pdf.parsed` | `date`, `meter_count`, `total_kwh`, `file_hash` | `PDFParser` | Raw Data View, Plant Map |
| `report.validated` | `is_valid`, `error_count`, `warnings` | `DataValidator` | Alert Center, Logs |
| `excel.updated` | `workbook_path`, `sheet`, `row`, `meters_written` | `ExcelService` | Excel Ops View, Status Badge |
| `audit.saved` | `audit_id`, `record_hash`, `timestamp` | `PersistenceRepo` | Audit Trail View |
| `alert.raised` | `alert_id`, `severity`, `title`, `message` | `AlertService` | Alert Center, System Tray Toast |
| `workflow.completed`| `duration_sec`, `status`, `summary` | `WorkflowCoordinator` | Dashboard, Notification Engine |
| `workflow.failed` | `error_type`, `error_message`, `stage` | `WorkflowCoordinator` | Alert Center, Dialog Modal |

---

## 4. Failure Isolation Test Verification

The failure isolation mechanism is verified by unit test `tests/unit/test_event_bus.py::test_event_bus_error_isolation`:
```python
def test_event_bus_error_isolation():
    bus = EventBus()
    flaky_called = []
    healthy_called = []

    def failing_subscriber(event):
        flaky_called.append(True)
        raise RuntimeError("External network connection timed out!")

    def healthy_subscriber(event):
        healthy_called.append(True)

    bus.subscribe("data.synced", failing_subscriber)
    bus.subscribe("data.synced", healthy_subscriber)

    # Publish event - must not raise exception
    bus.publish("data.synced", {"status": "ok"})

    assert len(flaky_called) == 1
    assert len(healthy_called) == 1  # Executed despite earlier subscriber failure
```
This guarantees that secondary logging, telemetry, or analytics failures will never corrupt primary Excel or SQLite operations.

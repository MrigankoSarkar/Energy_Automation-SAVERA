# Developer Guide: Environment Setup, Architecture & Contribution Standards

This guide is for software engineers, automation developers, and maintainers working on EnergyAutomation.

---

## 1. Development Environment Setup

### 1. Python Virtual Environment
EnergyAutomation requires Python 3.10+ (specifically validated through Python 3.14 on Windows):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 2. Code Quality & Formatting Standards
- **Imports**: Formatted cleanly with `from __future__ import annotations`, standard library imports, third-party imports, and application-level imports.
- **Type Annotations**: Strict type hints used across all function parameters and return values.
- **Error Handling**: Non-technical user-facing messages combined with structured logging via `app.monitoring.logger.get_logger`.

---

## 2. Core Architectural Patterns

### 1. In-Process EventBus Pattern (`app/events/bus.py`)
Decouple services by publishing domain events instead of directly calling downstream consumers:
```python
from app.events.bus import get_event_bus

bus = get_event_bus()
bus.publish("report.validated", {"report_date": "2026-02-15", "meter_count": 18})
```
- **Error Isolation**: Subscribers run in a try/except boundary so a failure in a secondary subscriber (e.g. cloud Power BI push) will never crash the core publisher.

### 2. Infallible Excel Path Resolution (`app/services/excel/service.py`)
Never use raw string concatenation or assume paths are clean. Always normalize paths via:
```python
from app.services.excel.service import ExcelService
clean_path = ExcelService.resolve_clean_path(raw_path)
```

### 3. Strict Deterministic Rule Validation (`app/services/validation/service.py`)
Validation rules must remain deterministic. Never inject heuristics or LLM queries into the mathematical validation pipeline.

---

## 3. Running Automated Tests

```powershell
# Run all tests
python -m pytest tests -v

# Run with coverage report
python -m pytest tests --cov=app --cov-report=term-missing

# Run a specific unit test suite
python -m pytest tests/unit/test_excel_service.py -v

# Run GUI wiring tests offscreen
python -m pytest tests/end_to_end/test_application_e2e.py -v
```

---

## 4. Packaging and Deployment

For desktop distribution, the application can be frozen into a standalone executable using PyInstaller:
```powershell
pyinstaller --noconsole --name "EnergyAutomation" `
    --icon "assets/app.ico" `
    --add-data "assets;assets" `
    --add-data "config;config" `
    main.py
```
*(Note: Always verify that `data/` and `credentials/` remain writable adjacent to the executable).*

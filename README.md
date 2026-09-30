# EnergyAutomation — Enterprise EMS Intelligence & Microservices Platform

> **Automated Energy Management System (EMS) for Savera MS**  
> Ingests daily NBSense PDF reports from Gmail, validates active energy across 18 plant meters, safely updates production Excel workbooks preserving dynamic formulas, maintains an immutable SQLite audit trail, provides conversational AI intelligence via Google Gemini, and delivers live management analytics via **Plotly Dash Management & Engineering BI**.  
> **Architecture**: Modular Microservices architecture inspired by AutoCAD and MATLAB engine patterns, with a Windows 11 Fluent Design desktop shell powered by **PySide6 + QFluentWidgets**.

---

## 1. Executive Summary

### What is EnergyAutomation?
EnergyAutomation is an enterprise manufacturing platform purpose-built for industrial energy monitoring. Built on Python, FastAPI, Plotly Dash, and PySide6, it bridges the physical factory floor and corporate management reporting by automating the flow of meter telemetry from email inboxes straight into verified Excel spreadsheets, REST APIs, and interactive engineering dashboards.

### What does it automate?
1. **Report Retrieval**: Connects to the plant's operational Gmail account every morning and discovers the latest NBSense EMS daily reports.
2. **Deterministic PDF Extraction**: Extracts active energy readings across all 18 facility meters in under 50 milliseconds using PyMuPDF.
3. **Data Quality Validation**: Rejects corrupted values, enforces non-negative energy bounds, rejects duplicate meter tags, and strictly preserves unpolled meters as `N/A` (never coercing to `0.0`).
4. **Excel Formula Preservation**: Opens `Test_BI_Analysis_Report_2026.xlsx`, creates an automated pre-write backup snapshot in `data/backups/`, updates only the specific date row, and verifies that live calculation formulas (`=SUM(C16:Q16)` and cumulative row 4 `=SUM(R5:R34)`) remain completely intact.
5. **Weekend Gap Healing**: Automatically inspects the past 30 days every run, identifies missing Sunday or holiday reports, and ingests them chronologically without data gaps.
6. **Plotly Dash Management & Engineering BI**: Delivers an interactive web-accessible business and engineering dashboard with Pareto analysis, granular feeder tables, load comparisons, and data quality audits on port `8050`.
7. **Advisory AI Assistance**: Connects to Google Gemini with resilient multi-model failover (`gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-3.8-flash`) and deterministic fallback reasoning, allowing managers to ask operational questions in plain English without modifying production data.

---

## 2. Microservices Architecture (AutoCAD / MATLAB Modular Pattern)

The system operates across decoupled, independent microservices:

| Microservice | Port | Description |
| :--- | :--- | :--- |
| **API Gateway** | `8000` | Unified reverse proxy and aggregated health probe |
| **Core Automation Service** | `8001` | Headless pipeline for Gmail polling, PDF parsing, validation, Excel writing, and APScheduler |
| **Data & Telemetry Service** | `8002` | Telemetry query engine, KPI calculations, data freshness, and gap diagnostics |
| **AI Advisory Service** | `8003` | Gemini conversational intelligence with multi-model failover |
| **Plotly Dash BI Service** | `8050` | Interactive web dashboard for business executives and engineering teams |
| **Desktop Client** | Standalone | Windows 11 Fluent desktop application (PySide6) |

---

## 3. Quick Start & Execution

### Option A: Desktop Application
Double click `run.bat` or run:
```powershell
python main.py
```

### Option B: Plotly Dash BI Dashboard
Double click `run_dash.bat` or run:
```powershell
python main.py --service=dash
```
Open your browser at `http://localhost:8050`.

### Option C: Launch All Microservices
Double click `run_services.bat` or run:
```powershell
python main.py --service=all
```

---

## 4. Documentation

Comprehensive documentation is organized in the `docs/` directory:
- [System Architecture](file:///e:/Savera_MS_2026/EnergyAutomation_new/docs/architecture/ARCHITECTURE.md)
- [Plotly Dash Deployment Guide](file:///e:/Savera_MS_2026/EnergyAutomation_new/docs/deployment/DASH_DEPLOYMENT.md)
- [Troubleshooting & Operational Runbook](file:///e:/Savera_MS_2026/EnergyAutomation_new/docs/admin-guide/TROUBLESHOOTING.md)
- [Guided Tour & User Manual](file:///e:/Savera_MS_2026/EnergyAutomation_new/docs/user-guide/TOUR_GUIDE.md)
- [Desktop UI/UX Design System Guide](file:///e:/Savera_MS_2026/EnergyAutomation_new/docs/technical/UI_UX_GUIDE.md)

# EnergyAutomation — Enterprise EMS Intelligence & Excel Automation Platform

> **Automated Energy Management System (EMS) for Savera MS**  
> Ingests daily NBSense PDF reports from Gmail, validates active energy across 18 plant meters, safely updates production Excel workbooks preserving dynamic formulas, maintains an immutable SQLite audit trail, provides conversational AI intelligence via Google Gemini, and delivers live management analytics via **Streamlit Management BI**.  
> **UI Layer**: Microsoft Fluent Design System powered by **PySide6 + QFluentWidgets** with instant Light/Dark theme switching, responsive navigation, elevated KPI cards, zero fake telemetry, and centralized toast notifications.

---

## 1. Executive Summary (In Plain Language)

### What is EnergyAutomation?
EnergyAutomation is a Windows desktop application purpose-built for manufacturing facilities to streamline daily electrical energy monitoring. Built on Python, PySide6, and QFluentWidgets, it bridges the physical factory floor and corporate management reporting by automating the flow of meter telemetry from email inboxes straight into verified Excel spreadsheets and cloud executive dashboards.

### What does it automate?
1. **Report Retrieval**: Connects to the plant's operational Gmail account every morning and discovers the latest 18-page NBSense EMS daily report.
2. **Deterministic PDF Extraction**: Extracts active energy readings across all 18 facility meters in under 50 milliseconds using high-performance C-bindings (PyMuPDF).
3. **Data Quality Validation**: Rejects corrupted values, enforces non-negative energy thresholds, rejects duplicate meter names, and strictly preserves unpolled meters as `N/A` (never coercing to `0.0`).
4. **Excel Formula Preservation**: Opens `Test_BI_Analysis_Report_2026.xlsx`, creates an automated pre-write backup snapshot in `backups/`, updates only the specific date row (e.g. Row 16 for `15-Feb-2026`), and verifies that live calculation formulas (`=SUM(C16:Q16)` and cumulative row 4 `=SUM(R5:R34)`) remain completely intact.
5. **Weekend Gap Healing**: Automatically inspects the past 30 days every run, identifies missing Sunday or holiday reports, and ingests them chronologically without data gaps.
6. **Streamlit Management BI**: Provides an interactive, web-accessible executive dashboard with live cloud storage synchronization (Google Drive, OneDrive, Dropbox), Pareto analysis, load curves, and plant zone breakdowns.
7. **Advisory AI Assistance**: Connects to Google Gemini 2.5 (with local deterministic rule fallback) allowing plant managers to ask operational questions in plain English without modifying production data.

### Who uses it?
- **Plant Managers & Directors**: Review real-time executive KPIs, Day-over-Day consumption variance, and the visual Plant Topology Map.
- **Electrical Maintenance Engineers**: Inspect feeder load distributions, check power factors, investigate communication glitches, and review audit trail timestamps.
- **Energy Auditors & Management**: Review monthly Excel workbooks and Streamlit BI dashboards to ensure reconciliation, avoid maximum demand utility penalties, and optimize plant efficiency.

### How do I start it?
- **Desktop Application**: Run `python main.py` or double-click `run.bat`.
- **Streamlit BI Dashboard**: Run `.\.venv\Scripts\python -m streamlit run streamlit_app/app.py` or launch directly from Page 7 in the desktop application.
- **Headless Mode**: Run `python run.py --headless` for background server scheduling.

---

## 2. Key Architecture & System Tiers

```text
┌─────────────────────────────────────────────────────────────┐
│               Tier 1: Core Automation Engine                │
│    Gmail OAuth 2.0 ──► PyMuPDF Parser ──► Bounds Validator  │
│                           │                                 │
│                           ▼                                 │
│          openpyxl Atomic Engine ──► SQLite Audit Ledger     │
│                   [SOLE SOURCE OF TRUTH]                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Tier 2: Desktop GUI (PySide6│    │   Tier 3: Management BI      │
│     + QFluentWidgets)        │    │        (Streamlit)           │
│  - 11 Unified Enterprise     │    │  - Browser & Mobile Access   │
│    Pages                     │    │  - Cloud Storage Sync        │
│  - Zero Fake Telemetry       │    │    (GDrive, OneDrive, etc.)  │
│  - Centralized Toasts &      │    │  - Strictly Read-Only        │
│    Friendly Error Dialogs    │    │    In-Memory BytesIO         │
│  - Permanent Light Onboarding│    │  - Pareto & Load Curves      │
└──────────────────────────────┘    └──────────────────────────────┘
```

### Architectural Invariants
1. **Deterministic Single Source of Truth**: The Core Engine is the sole authority that writes to Excel and SQLite. Streamlit and Gemini AI never mutate Excel files or database records.
2. **Zero Fake Telemetry**: Metric cards and tables display real data parsed from `Test_BI_Analysis_Report_2026.xlsx` or SQLite via `DashboardDataService`. If no data exists, the UI renders `NOT ACTIVE` or `NO DATA AVAILABLE`.
3. **`N/A` Integrity Policy**: Unpolled meters are preserved as `NaN` / empty cells and are **never coerced to 0.0**, preventing artificial skew in baseline calculations.
4. **Formula Safety Guarantee**: Daily total formulas `=SUM(C{row}:Q{row})` and cumulative row 4 formulas (`=SUM(R5:R34)`) are strictly preserved.
5. **Permanent Light Onboarding**: Guided Tour and Setup Wizard modals are styled with explicit high-contrast Light Theme tokens to ensure perfect legibility regardless of OS or dark theme settings.

---

## 3. System Requirements & Quickstart

### Prerequisites
- **Operating System**: Windows 10 (64-bit, 21H2+) or Windows 11 (Professional / Enterprise / Server 2022).
- **Python**: Python 3.10 to 3.14 (64-bit).

### Step-by-Step Installation
```powershell
# 1. Clone repository
git clone https://github.com/MrigankoSarkar/Energy_Automation-SAVERA.git
cd Energy_Automation-SAVERA

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install production dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Run automated test suite (61 tests)
python -m pytest tests -v

# 5. Launch Desktop Application
python main.py
```

---

## 4. Desktop Pages & Capabilities

EnergyAutomation provides 11 unified operational views accessible via the collapsible left navigation bar:

1. **Executive Dashboard**: System readiness banner, live KPI cards (Latest, Previous Shift, MTD, YTD), health matrix, top 5 consuming feeders, quick action buttons.
2. **Energy Analytics**: Statistical load distribution, daily/weekly trends, meter consumption breakdowns.
3. **Meter Analysis**: Comprehensive catalog of all 18 industrial meters across Savera MS.
4. **Plant Map & Hierarchy**: Interactive visual hierarchy map grouping meters into 7 manufacturing zones.
5. **Shift Reports & Audit**: Searchable ledger of every ingested PDF report with SHA-256 hashes and date filters.
6. **Historical Data Recovery**: Detection of missing calendar dates, weekend gap analysis, and one-click backfilling.
7. **Google Gemini AI Insights**: Advisory natural-language energy assistant with canned prompts and offline fallback.
8. **Streamlit Management BI**: Integrated web launcher and local background server controller for the Streamlit dashboard.
9. **Alert Rule Manager**: Customizable threshold alerts, incident logs, and email dispatch status.
10. **Processing History & Logs**: Live event stream and diagnostic logs.
11. **System Configuration & Settings**: File path pickers, OAuth diagnostics, scheduler interval setup, and Guided Tour / Setup Wizard launcher.
12. **Help Center & Support**: Built-in 13-topic technical guides, electrical glossary, and troubleshooting FAQ.

---

## 5. Testing & Verification

EnergyAutomation includes 61 automated test cases spanning unit, integration, and end-to-end suites:

```powershell
# Run full test suite
python -m pytest tests -v

# Run UI end-to-end tests (headless offscreen)
python -m pytest tests/end_to_end/test_application_e2e.py -v

# Run Streamlit BI tests
python -m pytest tests/unit/test_streamlit_data.py tests/unit/test_streamlit_analytics.py tests/unit/test_streamlit_cloud.py -v
```

All 61 tests pass 100% cleanly.

---

## 6. Project Documentation Suite

Detailed technical documentation is available in the repository:
- [**ARCHITECTURE.md**](file:///e:/Savera_MS_2026/EnergyAutomation_new/ARCHITECTURE.md): Full architectural blueprint, component boundaries, and data flow.
- [**UI_UX_GUIDE.md**](file:///e:/Savera_MS_2026/EnergyAutomation_new/UI_UX_GUIDE.md): Windows 11 Fluent Design tokens, typography hierarchy, and contrast rules.
- [**STREAMLIT_DEPLOYMENT.md**](file:///e:/Savera_MS_2026/EnergyAutomation_new/STREAMLIT_DEPLOYMENT.md): Streamlit Community Cloud deployment and cloud drive sync guide.
- [**TOUR_GUIDE.md**](file:///e:/Savera_MS_2026/EnergyAutomation_new/TOUR_GUIDE.md): 14-stop user walkthrough and onboarding manual.
- [**TROUBLESHOOTING.md**](file:///e:/Savera_MS_2026/EnergyAutomation_new/TROUBLESHOOTING.md): Operational runbook for Excel file locks, OAuth tokens, and unpolled meters.

---

## 7. Security & Invariants

- **Secret Protection**: `.gitignore` strictly excludes all `.json` credentials and `.pickle` token files in `credentials/`.
- **Log Masking**: API keys and client secrets are automatically redacted in UI logs and log files (`AIzaSy****`).
- **Atomic File Writing**: Spreadsheet updates write to a temporary buffer before atomic rename, guaranteeing zero workbook corruption during unexpected power outages.
- **Pre-Save Backups**: Timestamped snapshots are created in `backups/` before every file modification.

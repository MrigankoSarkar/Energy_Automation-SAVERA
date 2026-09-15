# EnergyAutomation — Enterprise EMS Intelligence & Excel Automation Platform

> **Automated Energy Management System (EMS) for Savera MS**  
> Ingests daily NBSense PDF reports from Gmail, validates active energy across 18 plant meters, safely updates production Excel workbooks preserving dynamic formulas, maintains an immutable SQLite audit trail, exports Power BI Star Schema datasets, and provides conversational AI intelligence via Google Gemini.  
> **UI Layer**: Microsoft Fluent Design System powered by **PySide6 + QFluentWidgets** with instant Light/Dark theme switching, responsive navigation, elevated KPI cards, and smooth toast notifications.

---

## 1. Executive Summary (In Plain Language)

### What is EnergyAutomation?
EnergyAutomation is a Windows desktop application purpose-built for manufacturing facilities to streamline daily electrical energy monitoring. Built on Python, PySide6, and QFluentWidgets, it bridges the physical factory floor and corporate management reporting by automating the flow of meter telemetry from email inboxes straight into verified Excel spreadsheets and cloud executive dashboards.

### What does it automate?
1. **Report Retrieval**: Connects to the plant's operational Gmail account every morning and discovers the latest 18-page NBSense EMS daily report.
2. **Deterministic PDF Extraction**: Extracts active energy readings across all 18 facility meters in under 50 milliseconds using high-performance C-bindings (PyMuPDF).
3. **Data Quality Validation**: Rejects corrupted values, enforces non-negative energy thresholds, rejects duplicate meter names, and strictly preserves unpolled meters as `N/A` (never coercing to `0.0`).
4. **Excel Formula Preservation**: Opens `Test_BI_Analysis_Report_2026.xlsx`, creates an automated pre-write backup snapshot in `data/backups/`, updates only the specific date row (e.g. Row 16 for `15-Feb-2026`), and verifies that live calculation formulas (`=SUM(C16:Q16)` and cumulative row 4 `=SUM(R5:R34)`) remain completely intact.
5. **Weekend Gap Healing**: Automatically inspects the past 30 days every run, identifies missing Sunday or holiday reports, and ingests them chronologically without data gaps.
6. **Power BI Star Schema**: Prepares dimensional business intelligence tables (`Fact_EnergyConsumption`, `Dim_Date`, `Dim_Meter`, `Dim_Area`, `Dim_Report`) and pre-built DAX measures for instant corporate reporting.
7. **Advisory AI Assistance**: Connects to Google Gemini 2.5 (with local deterministic rule fallback) allowing plant managers to ask operational questions in plain English without modifying production data.

### Who uses it?
- **Plant Managers & Directors**: Use **Simple Mode** on the Executive Dashboard to monitor facility totals, track Day-over-Day consumption variance, and view the visual Plant Topology Map.
- **Electrical Maintenance Engineers**: Use **Engineer Mode** to inspect Modbus meter registers, check power factors, investigate communication glitches, and review audit trail timestamps.
- **Energy Auditors & Accountants**: Review monthly Excel workbooks and Power BI reports to ensure reconciliation and avoid maximum demand utility penalties.

### How do I start it?
- **Desktop Shortcut**: Double-click the `EnergyAutomation` icon on your Windows Desktop.
- **Command Line**: Run `python main.py` or double-click `run.bat`.
- **Headless Mode**: Run `python run.py --headless` for unmanned server scheduling.

### What do I need to configure?
1. **Excel Workbook**: Point the application to your existing `Test_BI_Analysis_Report_2026.xlsx` in Settings.
2. **Gmail API**: Complete one-time Google OAuth authorization via the Setup Wizard.
3. **Gemini API (Optional)**: Add your Google Gemini API key to enable cloud AI assistance (or use local fallback).
4. **Power BI (Optional)**: Add Azure Service Principal credentials for real-time cloud streaming.

### What happens automatically?
The built-in scheduler awakens automatically at **06:00 AM** every morning, checks Gmail for the previous 24-hour shift report, updates Excel, logs the audit transaction, alerts operators of any anomalies, and prepares Power BI datasets—without human intervention.

### Where can I get help?
Click the **Help & Support** button in the sidebar (or press `Ctrl+11`), or click **Restart Guided Tour** at the top of the application for an interactive 1-minute walkthrough.

---

## 2. Key Architecture & Design Principles

```text
               +-------------------------------------------+
               |        NBSense Daily PDF Report           |
               |          (18 Meters / 18 Pages)           |
               +-------------------------------------------+
                                     │
                                     ▼
               +-------------------------------------------+
               |     Deterministic PDF Parsing Engine      |
               |   (PyMuPDF • Unit Normalizer • N/A Safe)  |
               +-------------------------------------------+
                                     │
                                     ▼
               +-------------------------------------------+
               |      Mathematical Validation Service      |
               | (Bounds • Uniqueness • Target: 9,206.83)  |
               +-------------------------------------------+
                                     │
                                     ▼
               +-------------------------------------------+
               |        In-Process Thread-Safe EventBus    |
               |       (Decoupled Failure Isolation)       |
               +-------------------------------------------+
                 │                 │                     │
                 ▼                 ▼                     ▼
      +------------------+  +---------------+  +------------------+
      |  Excel Service   |  | SQLite Audit  |  |  Alert Service   |
      | (Formula Safety) |  |   Database    |  | (Centralized Hub)|
      +------------------+  +---------------+  +------------------+
                 │                                       │
                 ▼                                       ▼
      +------------------+                     +------------------+
      |  Power BI Model  |                     |  Gemini AI Layer |
      |  (Star Schema)   |                     | (Advisory Only)  |
      +------------------+                     +------------------+
```

### Architectural Invariants
1. **Deterministic Single Source of Truth**: Data parsing, calculations, and persistence are strictly rule-based. AI never mutates Excel spreadsheets or database records.
2. **Baseline Reference Total**: For the standard reference report (`15-02-2026`), total active energy across all 18 mapped meters is exactly **9,206.83 kWh**.
3. **`N/A` Integrity Policy**: Physical communication dropouts report `N/A`. The pipeline enforces `N/A != 0.0`. Meters that report `N/A` are stored as `None`/`N/A` and never coerced to zero, avoiding artificial skew in machine efficiency baselines.
4. **Formula Safety Guarantee**: Row 16 formula `=SUM(C16:Q16)` and cumulative row 4 formulas (`=SUM(R5:R34)`, `=SUM(C5:C34)`) are strictly preserved.
5. **Path Normalization Safety**: Prevents the Windows nested quote bug (`<project>\"<absolute-path>"`) by resolving and sanitizing all paths through `resolve_clean_path()`.
6. **Failure Isolation**: External service failures (Power BI cloud network drop or Gemini API rate limit) never interrupt local Excel updates or SQLite audit logging.

---

## 3. System Requirements & Installation

### Prerequisites
- **Operating System**: Windows 10 (64-bit, 21H2+) or Windows 11 (Professional / Enterprise / Server 2022).
- **Python**: Python 3.10 to 3.14 (64-bit).
- **C++ Runtime**: Microsoft Visual C++ 2015–2022 Redistributable (x64).

### Step-by-Step Installation
```powershell
# 1. Clone repository
git clone https://github.com/MrigankoSarkar/Energy_Automation-SAVERA.git C:\Savera_EMS\EnergyAutomation
cd C:\Savera_EMS\EnergyAutomation

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install production dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Run automated test suite
python -m pytest tests -v
```

---

## 4. Configuration Guide

Settings are managed via `config/settings.json` or through the interactive **Setup Wizard** (`ui/dialogs/setup_wizard.py`):

```json
{
  "company": "Savera MS",
  "plant": "Chennai Manufacturing Plant",
  "excel": {
    "file": "Test_BI_Analysis_Report_2026.xlsx",
    "worksheet": "EMS Monitoring Report",
    "header_row": 3,
    "date_column": 2,
    "first_data_row": 5,
    "total_column": 18,
    "update_total": true,
    "fail_on_unmapped_numeric_meter": false
  },
  "automation": {
    "check_interval_minutes": 5,
    "start_automatically": true,
    "start_minimized": false
  },
  "gemini": {
    "enabled": true,
    "model": "gemini-2.5-flash",
    "api_key": ""
  },
  "powerbi": {
    "enabled": false,
    "workspace_id": "",
    "dataset_id": ""
  }
}
```

### Environment Variable Overrides
Create a `.env` file from `.env.example`:
```env
EXCEL_WORKBOOK_PATH=Test_BI_Analysis_Report_2026.xlsx
GEMINI_API_KEY=AIzaSyYourSecretKeyHere
POWERBI_CLIENT_ID=your-azure-app-id
POWERBI_CLIENT_SECRET=your-azure-secret
POWERBI_TENANT_ID=your-azure-tenant-id
POWERBI_WORKSPACE_ID=your-powerbi-workspace-id
```

---

## 5. User Interface & Operations Guide (PySide6 + QFluentWidgets)

EnergyAutomation features a modern **Microsoft Fluent Design** interface built with `PySide6` and `QFluentWidgets`:
- **FluentWindow Shell**: Frameless desktop window with integrated titlebar controls, branded Savera MS header, global search, mode toggle, and live system clock.
- **Light & Dark Theme Switching**: Instant toggling between Fluent Light and Fluent Dark modes via the titlebar switch (`SwitchButton`), dynamically updating all navigation, cards, tables, dialogs, and text fields.
- **Toast Notifications**: Non-blocking `InfoBar` notifications for real-time operation status (e.g. `InfoBar.success`, `InfoBar.error`).
- **Dual-Mode Experience**: Toggle between **Simple Mode** (executive summaries, KPI cards) and **Engineer Mode** (detailed Modbus telemetry, cell coordinates, and execution latencies).

### 1. Executive Dashboard (Page 0)
- **System Readiness Banner**: `ElevatedCardWidget` displaying `SYSTEM READY`, `SYSTEM PARTIALLY READY`, or `SYSTEM NOT READY` with status checklist and direct configure button.
- **System Health Matrix**: 6 live subsystem cards (Gmail, Reports, Excel, Automation, Gemini, Power BI).
- **Energy Overview Cards**: Today (9,206.83 kWh), Yesterday (9,180.40 kWh), MTD (kWh), YTD (kWh), and Day-over-Day variance badge.
- **Top Consuming Meters Preview**: Front-page ranking of highest consumers in a styled `TableWidget`.
- **Operations Panel**: One-click "Run Automation Now" (`PrimaryPushButton`), "Pause Scheduler", and "Refresh Status".

### 2. Plant Energy Topology Map (Page 3)
Interactive industrial map grouping all 18 facility meters into 7 production areas:
- `SUB-01`: Main Substation & Utility Incomer
- `PRS-01`: Heavy Press & Stamping Shop
- `MCH-01`: CNC & Precision Machining Center
- `WLD-01`: Welding & Robotic Assembly Cells
- `UTL-01`: Kaeser Air Compressors & Central Utilities
- `PNT-01`: Powder Coating & Heat Treatment
- `ADM-01`: Administrative Offices & Plant Lighting

### 3. Historical Data Recovery & Gap Healing (Page 5)
- Automated lookback across 30 calendar days.
- Detects weekend/Sunday omissions and downloads missing reports chronologically.

### 4. Power BI Star Schema & Fabric Export (Page 7)
- Generates `Fact_EnergyConsumption.csv`, `Dim_Date.csv`, `Dim_Meter.csv`, `Dim_Area.csv`, `Dim_Report.csv`.
- Exports pre-engineered DAX formulas in `measures.dax` (Total Active Energy, Incomer vs Sub-meters, Distribution Loss %, Power Factor).

### 5. Centralized Alert Center (Page 8)
- Automated incident management categorized into `CRITICAL`, `WARNING`, `INFO`, `AI_INSIGHT`.
- One-click acknowledgment, severity filtering, and audit logging.

### 6. Help Center & Support (Page 11)
- 13 comprehensive guides answering *What, Why, How, Next Steps, and Troubleshooting*.
- Interactive "Restart Guided Tour" button.

---

## 6. Testing & Quality Assurance

EnergyAutomation includes 49 automated test cases spanning unit, integration, and end-to-end suites:

```powershell
# Run full test suite
python -m pytest tests -v

# Run only UI end-to-end tests (headless offscreen)
python -m pytest tests/end_to_end/test_application_e2e.py -v

# Run Excel formula integrity tests
python -m pytest tests/unit/test_excel_service.py -v
```

### Test Coverage Summary
- `test_application_bootstrap_headless`: Service wiring and scheduler start/stop.
- `test_application_dashboard_wiring`: Offscreen Qt dashboard verification across all 12 operational views, search, mode toggle, tour, and setup wizard.
- `test_workflow_end_to_end_real_pdf_and_excel`: End-to-end real PDF ingestion verifying 9,206.83 kWh and Excel row 16 formula preservation.
- `test_idempotency`: Verifies ingesting the same report twice updates in-place without duplicating rows or distorting sums.
- `test_excel_path_normalization_and_safety`: Verifies absolute, relative, and quoted path resolution.
- `test_na_energy_normalization`: Verifies unpolled meters remain `None`/`N/A` and are never converted to 0.0.
- `test_event_bus_error_isolation`: Verifies subscriber exceptions never crash core publishers.

---

## 7. Project Directory Structure

```text
EnergyAutomation_new/
├── app/
│   ├── bootstrap/          # Startup container & dependency wiring
│   ├── contracts/          # Protocol interfaces and data transfer objects
│   ├── events/             # In-process EventBus with error isolation
│   ├── monitoring/         # Structured logger, health monitors, and metrics
│   ├── orchestration/      # WorkflowCoordinator, APScheduler, and retry logic
│   ├── persistence/        # SQLite database repository and audit log
│   └── services/           # Decoupled domain service implementations
│       ├── ai/             # Google Gemini integration & local rule fallback
│       ├── alert/          # Centralized AlertService and threshold rules
│       ├── analytics/      # Plant topology, zone aggregation, baseline analytics
│       ├── excel/          # Openpyxl workbook manager, path safety, formula verifier
│       ├── gmail/          # Gmail API OAuth client and PDF extractor
│       ├── pdf/            # PyMuPDF parser, table tokenizer, unit normalizer
│       ├── powerbi/        # Star schema generator, DAX builder, REST push
│       ├── reconciliation/ # 30-day missing date gap detector & weekend classifier
│       └── validation/     # Mathematical bounds and meter integrity validator
├── assets/                 # Savera MS logo, window icon, branding assets
├── config/                 # Canonical configuration files (settings.json, powerbi.json)
├── data/                   # Workbooks, backups, SQLite database, Power BI exports
├── docs/                   # Full documentation suite (User, Admin, Developer, Tech, QA)
├── tests/                  # Pytest test suite (Unit, Integration, End-to-End)
├── ui/                     # Presentation layer (PySide6 + QFluentWidgets)
│   ├── dialogs/            # Setup wizard and guided tour dialogs
│   ├── widgets/            # Plant topology map, KPI cards, metric tables
│   └── dashboard.py        # FluentWindow shell with collapsible navigation & theme switch
├── .env.example            # Environment variables template
├── .gitignore              # Strict secret and temporary file exclusion rules
├── main.py                 # Primary application entry point
├── requirements.txt        # Production Python dependencies
└── run.bat                 # Convenient Windows batch launcher
```

---

## 8. Security & Compliance

- **Secret Protection**: `.gitignore` strictly ignores all `.json` and `.pickle` token files in `credentials/`, preventing inadvertent commits.
- **Log Masking**: Google API keys and Azure secrets are automatically redacted in UI logs and log files (`AIzaSy****`).
- **Atomic File Writing**: Spreadsheet updates write to a temporary `.tmp` file before an atomic OS rename, guaranteeing zero workbook corruption during unexpected power outages.
- **Backup Retention**: Pre-write timestamped snapshots are created in `data/backups/` before every file modification, retaining the last 30 daily runs.

---

## 9. Known Limitations & Operational Notes

- **Excel Open Lock**: If Microsoft Excel has `Test_BI_Analysis_Report_2026.xlsx` open with an exclusive lock, Windows prevents file modification. EnergyAutomation notifies the operator in friendly plain language to close Excel and retry.
- **External API Connectivity**: When operating in air-gapped manufacturing environments without internet access, Gmail sync, cloud Power BI, and Gemini cloud Q&A operate in deterministic offline fallback mode. Local Excel automation and SQLite auditing operate with 100% functionality.

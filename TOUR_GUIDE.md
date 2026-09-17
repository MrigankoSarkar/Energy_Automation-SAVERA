# EnergyAutomation — Guided Tour & User Onboarding Manual

## 1. Introduction

Welcome to **EnergyAutomation**! This manual mirrors the interactive 14-stop onboarding tour built into the desktop application and provides step-by-step guidance for operators, plant engineers, and executives.

---

## 2. Walkthrough of Application Views

### Stop 0: Welcome to EnergyAutomation
- **Purpose**: Eliminates manual keying of daily NBSense energy monitoring reports from Gmail into Excel.
- **Core Automation**: Automatically retrieves PDFs, validates active energy totals, atomic-updates the production workbook preserving formulas, and publishes live management analytics via Streamlit BI.

### Stop 1: Executive Dashboard (Page 0)
- **What to look for**:
  - **System Readiness Banner**: Shows whether the system is green and operational.
  - **KPI Cards**: Latest Daily Reading (kWh), Previous Shift (kWh), Month-to-Date (kWh), Year-to-Date (kWh).
  - **Top 5 Consuming Feeders**: Real-time table ranking today's biggest energy consumers.
- **Actions**: Click **Run Automation Now** to trigger an on-demand ingestion cycle.

### Stop 2: System Health Matrix (Page 0)
- **Subsystems Monitored**: Gmail OAuth, EMS Report Ingestion, Excel Persistence, Automation Scheduler, Gemini AI Advisory, Streamlit Management BI.
- **Status Badges**:
  - Green (Normal): All credentials and services connected.
  - Yellow (Warning): Missing optional credentials (e.g. Gemini key) or pending scan.
  - Red (Action Required): Excel file locked or Gmail authorization expired.

### Stop 3: Energy Trends & Analytics (Page 1)
- **Analytics Available**:
  - Daily consumption bar charts and weekly moving averages.
  - Peak vs Off-Peak load analysis.
  - Energy variance against historical shift baselines.

### Stop 4: Meter Analysis (Page 2)
- **Catalog**: Complete profile of all 18 industrial meters across Savera MS.
- **Details**: Meter serial, rated power (kW), assigned production zone, and active communication status.

### Stop 5: Plant Map & Hierarchy (Page 3)
- **Topology**: Interactive visual map organizing meters into 7 manufacturing zones:
  1. Surface Treatment & Plating Plant
  2. Finishing & Powder Coating Plant
  3. Press & Fabrication Line
  4. Compressed Air Generation Substation
  5. RO & DM Water Treatment Facility
  6. Packaging & Stitching Line
  7. Main Incomer Power Distribution

### Stop 6: Shift Reports & Audit Trail (Page 4)
- **Features**:
  - Immutable SQLite ledger of every ingested PDF report.
  - Searchable by report date, sender, and attachment filename.
  - Audit details include SHA-256 attachment hashes, processing timestamps, and meter reading counts.

### Stop 7: Historical Data Recovery (Page 5)
- **Purpose**: Detects and resolves missing calendar dates (such as Sunday gaps or mail downtime).
- **Actions**:
  1. Click **Scan for Missing Dates** to analyze the last 30 days.
  2. Review detected gap dates in the recovery list.
  3. Click **Run Historical Gap Healing Now** to query Gmail for matching historical reports and update the workbook.

### Stop 8: Google Gemini AI Insights (Page 6)
- **Conversational Assistant**: Ask natural-language questions such as:
  - *"Which department consumed the most power this week?"*
  - *"What was our total energy consumption for September?"*
  - *"Are there any unusual spikes in compressor usage?"*
- **Safety Guarantee**: Gemini AI operates strictly in advisory mode with read-only access. It cannot edit Excel files or alter database entries.

### Stop 9: Streamlit Management BI (Page 7)
- **Features**:
  - Web-based executive management dashboard.
  - Interactive KPI gauges, load curves, and multi-facility comparisons.
- **Actions**: Click **Launch in Browser** to view `http://localhost:8501`, or **Start Background Server** to manage local execution.

### Stop 10: Alert Rule Manager & Incident Logs (Page 8)
- **Alert Rules**: Configure threshold limits (e.g. Incomer daily consumption > 5,000 kWh).
- **Notification Channels**: Windows notifications, desktop toasts, and automated email alerts.

### Stop 11: Processing History & Logs (Page 9)
- **Diagnostic Logging**: Live chronological event feed capturing scheduler runs, PDF parse events, validation checks, and file writes.

### Stop 12: System Configuration & Settings (Page 10)
- **Configurable Settings**:
  - Production Excel file path and worksheet name.
  - Gmail sender filter and historical lookback window.
  - Automation polling interval (default: 5 minutes).
  - Launch **Setup Wizard** or **Guided Tour** at any time.

### Stop 13: Help Center & Support (Page 11)
- **Resources**: 13 built-in engineering guides, an electrical terminology glossary (kWh, kVAh, PF, MD), and troubleshooting FAQ.

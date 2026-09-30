# EnergyAutomation — Guided Tour & User Onboarding Manual

## 1. Introduction

Welcome to **EnergyAutomation**! This manual mirrors the streamlined onboarding tour built into the desktop application and provides step-by-step guidance for operators, plant engineers, and executives.

---

## 2. Walkthrough of Application Views

### Stop 0: Welcome to EnergyAutomation
- **Purpose**: Eliminates manual keying of daily NBSense energy monitoring reports from Gmail into Excel.
- **Core Automation**: Automatically retrieves PDFs, validates active energy totals, atomic-updates the production workbook preserving formulas, and exposes live management analytics via Plotly Dash BI.

### Stop 1: Executive Dashboard (Page 0)
- **What to look for**:
  - **System Readiness Banner**: Shows whether the automation system is green and operational.
  - **KPI Cards**: Latest Daily Reading (kWh), Previous Shift (kWh), Month-to-Date (kWh), System Status.
  - **Top Consuming Feeders**: Real-time table ranking today's biggest energy consumers.
- **Actions**: Click **Run Automation Now** to trigger an on-demand ingestion cycle.

### Stop 2: System Health Matrix
- **Subsystems Monitored**: Gmail OAuth, EMS Ingestion, Excel Persistence, Automation Scheduler, Gemini AI Advisory, Plotly Dash BI.
- **Status Badges**:
  - Green (Normal): All credentials and microservices connected.
  - Yellow (Warning): Missing optional credentials or pending scan.
  - Red (Action Required): Excel file locked or Gmail authorization expired.

### Stop 3: Historical Data Recovery
- **Purpose**: Detects and resolves missing calendar dates (such as weekend gaps or mail downtime).
- **Actions**:
  1. Click **Scan for Missing Dates** to analyze the last 30 days.
  2. Review detected gap dates in the recovery list.
  3. Click **Run Historical Gap Healing Now** to query Gmail for matching historical reports and update the workbook.

### Stop 4: Google Gemini AI Insights
- **Conversational Energy Assistant**: Ask natural-language questions such as:
  - *"What was the total energy consumed on the latest report?"*
  - *"Which feeder had the highest consumption?"*
  - *"Were there any missing reports in the last 30 days?"*
- **Safety Guarantee**: Gemini AI operates strictly in advisory mode with read-only access. It cannot edit Excel files or alter database entries.
- **Resilient AI**: Built with multi-model failover (`gemini-flash-latest`, `gemini-flash-lite-latest`) and instant connection testing.

### Stop 5: Plotly Dash Management BI
- **Features**:
  - Web-based executive management and deep engineering analysis dashboard on port `8050`.
  - Detailed engineering feeder telemetry data grid, interactive load charts, and data quality metrics.
- **Actions**: Click **Launch in Browser** to view `http://localhost:8050`, or **Start Background Server** to manage local execution.

### Stop 6: Alert Rule Manager & Incident Logs
- **Alert Rules**: Configure threshold limits (e.g., Incomer daily consumption > 5,000 kWh).
- **Notification Channels**: Windows notifications, desktop toasts, and automated alert logs.

### Stop 7: Processing History & Logs
- **Diagnostic Logging**: Live chronological event feed capturing scheduler runs, PDF parse events, validation checks, and file writes.

### Stop 8: System Configuration & Settings
- **Configurable Settings**:
  - Production Excel file path and worksheet name.
  - Gmail sender filter and historical lookback window.
  - Automation polling interval (default: 5 minutes).
  - Google Gemini API Key configuration and real-time connectivity testing.

### Stop 9: Help Center & Support
- **Resources**: Built-in engineering guides, an electrical terminology glossary (kWh, kVAh, PF, MD), and troubleshooting FAQ.

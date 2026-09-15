# EnergyAutomation — User Guide: Dashboard & Monitoring

## 1. Executive Dashboard Overview
The **Executive Dashboard** is the primary monitoring screen for plant managers and operators. It provides a real-time summary of energy operations, ingestion health, and key performance indicators.

---

## 2. Key Elements on the Dashboard

### 1. System Status Ribbon
Located at the top of the dashboard:
- **Status Indicator**:
  - 🟢 **Green (Ready / Completed)**: Pipeline is operational, reports processed successfully.
  - 🔵 **Blue (Processing)**: Currently downloading, parsing, or reconciling EMS reports.
  - 🟡 **Amber (Warning)**: Scheduler paused or historical gap detected.
  - 🔴 **Red (Error)**: A processing error occurred (e.g. workbook locked by another user).

### 2. Operational KPI Cards
- **Reports Processed**: Total number of daily report cycles executed during this session.
- **Successful**: Ingestions completed with Excel updated and verified.
- **Failed**: Operations encountering an unhandled exception.
- **Last Run**: Timestamp of the most recent automated execution.

### 3. Operations & Scheduler Controls
- **Run Automation Now**: Triggers an immediate report ingestion and reconciliation cycle in a non-blocking background worker thread.
- **Pause / Start Scheduler**: Suspends or resumes the automated background timer.
- **Refresh Status**: Updates live UI indicators and reloads system diagnostics.

### 4. Live Activity Summary
Displays the latest operational narrative, including:
- Total active energy extracted from the latest report (e.g. `9,206.83 kWh`).
- Number of mapped meter cells updated in Excel (15 meter cells + 1 Total formula cell = 16 cells).
- Verification confirmation from `ExcelVerifier`.

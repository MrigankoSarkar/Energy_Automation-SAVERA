# Chapter 8: Troubleshooting & Frequently Asked Questions (FAQ)

This chapter provides systematic diagnostic steps and solutions for common operational issues encountered when running EnergyAutomation.

---

## 1. Quick Diagnostic Flowchart

```text
Issue Detected
  │
  ├──► Excel Error? ─────────► Check file lock (WinError 32) or path spaces.
  │                            Ensure "Test_BI_Analysis_Report_2026.xlsx" is closed in Excel.
  │
  ├──► Gmail Sync Failure? ──► Verify credentials.json, token.pickle, and app password.
  │                            Check internet connection and OAuth scopes.
  │
  ├──► PDF Parse Failure? ───► Verify file format (NBSense standard vs corrupted PDF).
  │                            Ensure date format matches DD-MM-YYYY.
  │
  ├──► Data Discrepancy? ────► Check Alert Center. Verify N/A vs 0.0 kWh policy.
  │                            Ensure no manual edits overwrote row 16 / row 4 formulas.
  │
  └──► Power BI Sync Error? ─► Verify Azure App Registration client secret & dataset ID.
                               Check if Power BI tenant allows Service Principal push.
```

---

## 2. Common Errors & Step-by-Step Solutions

### Problem 1: Excel File Is Locked (`PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`)

* **Root Cause**: Microsoft Excel or another user has `Test_BI_Analysis_Report_2026.xlsx` open with an exclusive write lock.
* **Impact**: The automation cannot write the parsed day's readings to the workbook.
* **Resolution**:
  1. Save your changes and close Microsoft Excel on the host computer.
  2. If the file appears closed but the lock persists, open **Windows Task Manager** (`Ctrl+Shift+Esc`), locate `EXCEL.EXE` under Background Processes, and click **End Task**.
  3. In EnergyAutomation, go to **Alert Center** or the **Activity Log** and click **Retry Workflow Run**.
  4. Notice that EnergyAutomation writes to an atomic temporary file before swapping to prevent partial workbook corruption if a lock occurs mid-write.

---

### Problem 2: Excel Path Doubling / Quote Nesting Issue

* **Root Cause**: Earlier legacy versions improperly quoted file paths when calling the Excel handler, producing invalid path strings such as `e:\Savera_MS_2026\EnergyAutomation_new\"e:\...\Test_BI_Analysis_Report_2026.xlsx"`.
* **Resolution**:
  - This issue has been permanently addressed in the `ExcelService` path normalization engine (`resolve_clean_path()`), which strips enclosing quotes, resolves absolute paths, and checks file existence before invoking `openpyxl`.
  - If you encounter a custom path error in **Settings**, click **Reset to Default Path** or use the file browser button to re-select the file cleanly.

---

### Problem 3: Meter Shows `N/A` Instead of a Number

* **Root Cause**: The physical NBSense energy meter had a communication timeout, RS-485 Modbus glitch, or power cut on the factory floor during that polling window. The NBSense PDF report explicitly printed `N/A` for active energy.
* **Resolution**:
  - **Do NOT manually enter `0.0` in the Excel spreadsheet!**
  - EnergyAutomation enforces the rule: `N/A != 0.0`. A reading of `0.0` implies the machine ran all day with zero energy, which skews baseline and machine efficiency models.
  - EnergyAutomation records `N/A` in the audit log and places an empty cell or `N/A` marker in Excel, preserving mathematical integrity and flagging a **Warning** in the Alert Center.

---

### Problem 4: Formula Verification Alert (`Excel Formula Check Failed`)

* **Root Cause**: A user accidentally edited Row 16 (`=SUM(C16:Q16)`) or Row 4 (`=SUM(R5:R34)` / `=SUM(C5:C34)`) in Excel, replacing the live formula with a static number.
* **Resolution**:
  1. Open the Excel workbook `Test_BI_Analysis_Report_2026.xlsx`.
  2. Navigate to the active month sheet (e.g., `FEB - 2026`).
  3. Inspect cell `R16` (or the respective row total). Ensure it contains `=SUM(C16:Q16)`.
  4. Inspect cell `R4` (Total Active Energy) and column cumulative headers in Row 4. Ensure formulas are intact.
  5. Save the workbook. EnergyAutomation will verify formulas on the next run.
  6. Alternatively, restore the automatic backup created under `data/backups/` prior to the modification.

---

### Problem 5: Missing Dates / Friday to Monday Jump

* **Root Cause**: Plant operations were shut down over the weekend, or the EMS server only generated a cumulative report on Monday.
* **Resolution**:
  - Navigate to **Data Reconciliation** (`Ctrl+5`).
  - The reconciliation engine automatically detects whether missing dates fall on **Sundays** or standard non-working shifts.
  - If a legitimate report was received via alternate email, use **Data Recovery & Manual Upload** (`Ctrl+6`) to drag-and-drop the missing PDF and ingest it immediately.

---

## 3. Frequently Asked Questions (FAQ)

#### Q1: Can I run EnergyAutomation on a computer without Microsoft Office installed?
**Yes.** EnergyAutomation uses `openpyxl` with strict open-standard XML manipulation. It does not require Microsoft Office, Excel COM automation, or Office 365 desktop client licenses.

#### Q2: What happens if the internet goes down at 06:00 AM during the scheduled run?
EnergyAutomation will fail gracefully without crashing. It records a `ConnectivityWarning` in the Alert Center and retries on the next scheduled polling cycle (or when you click **Run Now** after connectivity is restored).

#### Q3: How do I switch between Simple Mode and Engineer Mode?
Use the **Mode Toggle** located in the top navigation bar or at the bottom of the sidebar. You can also press `Ctrl+M` to toggle between the simplified executive view and the full diagnostic engineering view.

#### Q4: Does EnergyAutomation overwrite my existing Excel formatting, cell colors, or fonts?
**No.** EnergyAutomation opens the existing workbook, updates only the specific meter cells corresponding to the report date, verifies formula integrity, and saves the file preserving existing cell styles, borders, and number formats.

#### Q5: How many backups does EnergyAutomation retain?
By default, the system creates an automated timestamped backup in `data/backups/` before every write operation and retains the last 30 daily snapshots. Old backups are automatically rotated to conserve disk space.

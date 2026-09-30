# EnergyAutomation — Troubleshooting & Operational Runbook

This guide covers resolution steps for common operational issues encountered in enterprise production environments.

---

## 1. Excel Workbook Lock Conflict (`WinError 32` / `PermissionError`)

### Symptom
The desktop application or automation engine reports:
`[Errno 13] Permission denied: 'Test_BI_Analysis_Report_2026.xlsx'` or `[WinError 32] The process cannot access the file because it is being used by another process`.

### Root Cause
Windows places an exclusive write lock on Excel files whenever:
1. A user currently has the workbook open in Microsoft Excel desktop.
2. Cloud file synchronization agents (OneDrive, Google Drive for Desktop, Dropbox) are actively uploading changes.
3. Another automated process holds an open file handle.

### Resolution Steps
1. **Close Excel**: Ask users to save and close `Test_BI_Analysis_Report_2026.xlsx`.
2. **Exponential Backoff**: The Core Engine will automatically retry the atomic save 3 times with exponential backoff (`1s`, `2s`, `4s`).
3. **Recovery Buffer**: If the file remains locked, the engine saves changes into a safe staging buffer `data/staging/pending_update_<timestamp>.json` and raises a non-destructive desktop warning.
4. **OneDrive Autosave**: If the workbook is stored in a synced OneDrive folder, consider using an export copy or pausing sync during shift updates.

---

## 2. Gmail OAuth Token Expiry or Authentication Failure

### Symptom
Logs show `RefreshError: Token has been expired or revoked` or `FileNotFoundError: credentials/gmail/credentials.json`.

### Root Cause
Google OAuth refresh tokens expire if inactive for 6 months, or if the Google Cloud OAuth Consent Screen is set to "Testing" mode (tokens expire after 7 days).

### Resolution Steps
1. **Production OAuth Consent Screen**: In Google Cloud Console (`console.cloud.google.com`), set your OAuth application status from **Testing** to **In Production** to ensure refresh tokens never expire.
2. **Re-authorize**:
   - Delete `credentials/token.json`.
   - Ensure `credentials/gmail/credentials.json` is present.
   - Run the setup authentication:
     ```bash
     .\.venv\Scripts\python -c "from app.services.gmail.auth import GmailAuthenticator; GmailAuthenticator().authenticate()"
     ```
   - A browser window will open requesting one-time authorization.

---

## 3. Unpolled Meters & Missing Telemetry (`N/A` vs `0.0`)

### Symptom
A meter on the plant floor was offline or unpolled during the shift, resulting in `N/A` or blank entries in the PDF report.

### System Invariant
- **EnergyAutomation NEVER coerces `N/A` to `0.0`**. Coercing missing telemetry to 0 causes false downtime alerts, distorts load duration averages, and corrupts historical variance models.
- Unpolled meters are stored as `np.nan` (in Pandas) and empty cells (in Excel), and labeled as `N/A (Unpolled)` in the UI.

### Verification
Open the **Executive Dashboard**. Unpolled meters will display a warning status badge rather than an erroneous 0 kWh reading.

---

## 4. Historical Weekend Gaps (Sundays & Plant Holidays)

### Symptom
The **System Readiness** banner reports *"Detected missing calendar dates in 30-day lookback"*.

### Explanation
Manufacturing lines may not operate on Sundays or gazetted holidays, meaning NBSense EMS does not transmit an email report.

### Resolution Steps
1. Navigate to **Historical Data Recovery**.
2. Click **Scan for Missing Dates**.
3. Dates are automatically classified into **Sunday / Scheduled Downtime** vs **Unexplained Gap**.
4. If an email report exists in Gmail for that date, click **Run Historical Gap Healing Now** to backfill the missing readings.

---

## 5. Plotly Dash BI Connection Issues

### Symptom
Browser displays `ConnectionRefusedError` on `http://localhost:8050` or Plotly Dash shows server unreachable.

### Resolution Steps
1. **Local Server Not Running**:
   - Navigate to **Plotly Dash BI** in the desktop app.
   - Check the **Server Status** indicator. If stopped, click **Start Background Server**.
   - Or run `run_dash.bat` in the terminal.
2. **Port Conflict**:
   - Ensure port 8050 is not occupied by another process. Set `DASH_PORT=8055` in the environment if required.

---

## 6. Google Gemini AI Connection Issues

### Symptom
AI panel displays `Connection failed` or `404/503 error`.

### Resolution Steps
1. **Verify API Key**:
   - Ensure a valid Gemini API key is configured in **Settings** or environment variable `GEMINI_API_KEY`.
2. **Model Availability**:
   - The engine automatically fails over between `gemini-flash-latest`, `gemini-flash-lite-latest`, and `gemini-3.8-flash`.
   - Click **Test Connection** in the AI Insights panel to verify latency and model status.

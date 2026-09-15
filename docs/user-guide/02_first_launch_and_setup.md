# EnergyAutomation — User Guide: First Launch & Setup

## 1. Initial Launch
When starting EnergyAutomation for the first time:
1. Double-click the application shortcut or run `main.py`.
2. The application opens with the **Enterprise Setup Wizard**.
3. You can also launch the wizard at any time by clicking **⚙ Setup Wizard** in the top header bar or under **Settings**.

---

## 2. The 8-Step Setup Wizard

### Step 1: Company & Facility Profile
Enter your organization details:
- **Organization Name**: `Savera MS` (default)
- **Plant / Facility Name**: `Chennai Manufacturing Plant`

### Step 2: Excel Workbook Configuration
- **Excel Workbook Path**: Click **Browse...** to select your existing company workbook (e.g. `Test_BI_Analysis_Report_2026.xlsx`).
- **Target Worksheet**: Enter the exact sheet name (e.g. `EMS Monitoring Report`).
- *Formula Guarantee*: The system automatically verifies that row 16 formula `=SUM(C16:Q16)` and cumulative row 4 formulas (`=SUM(R5:R34)` and `=SUM(C5:C34)`) will remain intact.

### Step 3: Gmail Automation Configuration
- **Sender Filter**: `alerts@nbsense.com` (default)
- **Subject Filter**: `Ems Monitoring Report` (default)
- **Historical Gap Lookback**: Set between `1` and `90` days (recommended: `30` days). This ensures missed Sunday reports or holiday runs are automatically detected and backfilled chronologically.

### Step 4: Google Gemini AI Intelligence
- Check **Enable Google Gemini AI Intelligence** to activate conversational energy Q&A.
- Enter your Gemini API Key or leave blank to operate in verified deterministic offline fallback mode.
- *Strict Rule*: Gemini AI operates strictly in read-only advisory mode and will never edit Excel directly.

### Step 5: Power BI Analytics Configuration
- If your organization has an active Microsoft Power BI / Fabric tenant, check **Enable Power BI Cloud API Direct Publishing** and enter your Workspace and Dataset GUIDs.
- If not configured, the application automatically operates in **Local Export Mode**, creating clean CSV tables and DAX measures in `data/powerbi/`.

### Step 6: Automation Scheduler
- Set the background check interval in minutes (default: `5` minutes).
- Choose whether to launch minimized to the Windows System Tray on startup.

### Step 7: Live Diagnostics & Connection Testing
Click the **Test** buttons to check:
- Excel Workbook accessibility
- Gmail OAuth token or credential file availability
- Google Gemini AI connectivity

### Step 8: Confirmation & System Launch
Review your configuration summary and click **Save & Start** to begin monitoring.

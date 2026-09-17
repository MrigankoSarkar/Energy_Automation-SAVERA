# EnergyAutomation — Streamlit Management BI Deployment & Cloud Guide

## 1. Overview

**Streamlit Management BI** is the executive and plant engineering business intelligence dashboard for EnergyAutomation. It provides real-time interactive energy analytics, load duration curves, plant zone distributions, and data quality audits accessible from any web browser or mobile device.

The dashboard operates **strictly read-only** against the synchronized production Excel workbook (`Test_BI_Analysis_Report_2026.xlsx`) or SQLite database. It never modifies Excel formulas or writes raw meter telemetry.

---

## 2. Main Entry Point

The designated entry point for local execution and Streamlit Community Cloud deployment is:

```text
streamlit_app/app.py
```

> [!IMPORTANT]
> Do NOT create or rename a root `streamlit_app.py` script. Having a root file with that name collides with the `streamlit_app` package and breaks Python module resolution.

---

## 3. Local Execution

### Option A: Direct Launch from Desktop GUI
1. Open the **EnergyAutomation** desktop application.
2. In the navigation sidebar, click **Streamlit BI** (Page 7).
3. Click **Start Background Server** to launch the local Streamlit process.
4. Click **Launch in Browser** to automatically open `http://localhost:8501`.

### Option B: Terminal Launch
Run the following command from the repository root:

```bash
.\.venv\Scripts\python -m streamlit run streamlit_app/app.py
```

The application will bind to `http://localhost:8501`.

---

## 4. Deploying to Streamlit Community Cloud

### 4.1 Prerequisites
- A GitHub repository containing the EnergyAutomation project.
- A free account on [share.streamlit.io](https://share.streamlit.io).
- Cloud storage share link for the production Excel workbook (Google Drive, OneDrive, or Dropbox).

### 4.2 Deployment Steps
1. Navigate to **share.streamlit.io** and click **New app**.
2. Select your repository: `MrigankoSarkar/Energy_Automation-SAVERA` (or your fork).
3. Set the **Main file path** to:
   ```text
   streamlit_app/app.py
   ```
4. Expand **Advanced settings** and configure your cloud storage environment secrets in the **Secrets** section:

```toml
[general]
app_title = "Savera MS — Energy Intelligence Dashboard"

[cloud_storage]
provider = "google_drive"  # Options: google_drive, onedrive, dropbox, direct_url
shared_url = "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing"
cache_ttl_seconds = 300
```

5. Click **Deploy!**

---

## 5. Cloud Storage Synchronization Setup

The dashboard automatically translates share links into direct streaming downloads and caches them with `@st.cache_data(ttl=300)`:

### 5.1 Google Drive
1. In Google Drive, right-click `Test_BI_Analysis_Report_2026.xlsx` -> **Share**.
2. Under General Access, select **Anyone with the link can view**.
3. Copy the URL. It will look like:
   `https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OIvE2up0I/view?usp=sharing`
4. The cloud provider automatically converts this to:
   `https://drive.google.com/uc?export=download&id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OIvE2up0I`

### 5.2 Microsoft OneDrive / SharePoint
1. In OneDrive, right-click the workbook -> **Share** -> **Anyone with the link**.
2. Copy the share link (e.g. `https://1drv.ms/u/s!...`).
3. Paste the URL into the dashboard cloud settings. The provider converts it using base64 URL encoding to a direct OneDrive download stream.

### 5.3 Dropbox
1. Right-click the workbook in Dropbox -> **Copy link**.
2. The provider automatically appends or replaces `dl=1` for direct binary streaming.

---

## 6. Architecture & Data Integrity Invariants

1. **Strictly Read-Only**: The Streamlit app opens the workbook in memory via `io.BytesIO`. It never calls `wb.save()` and cannot corrupt Excel formulas.
2. **Formula Invariant**: Daily totals `=SUM(C16:Q16)` and row 4 cumulative totals `=SUM(R5:R34)` are evaluated in memory via `WorkbookDataValidator` if openpyxl's cached values are `None`.
3. **Unpolled Meter Invariant**: Meters with no reading or `N/A` are stored as `np.nan` and never coerced to `0.0`.
4. **Cache Invalidation**: Users can click the **Sync Now** button in the sidebar to invalidate the 300-second cache and pull the latest shift data immediately.

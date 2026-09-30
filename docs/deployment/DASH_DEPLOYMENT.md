# EnergyAutomation — Plotly Dash Management & Engineering BI Deployment Guide

## 1. Overview

**Plotly Dash BI** is the executive and plant engineering business intelligence microservice for EnergyAutomation. Designed with **Dash** and **Dash Bootstrap Components**, it delivers deep interactive analysis for business and engineering teams:
- **Executive BI Overview**: Real-time KPI summaries, Shift vs Baseline comparisons, MTD Cumulative totals, and Feeder Share Pareto/Donut graphs.
- **Engineering Analytics Grid**: Detailed feeder telemetry data table, high-resolution load comparison charts, operational threshold diagnostics, and outlier detection.
- **Data Quality & Telemetry Assurance**: Ingestion freshness timeline, missing shift detection, and mathematical reconciliation audits.

The dashboard operates **strictly read-only** against the Data Service API (`http://localhost:8002/api/v1/data`) or local production Excel workbook (`data/Test_BI_Analysis_Report_2026.xlsx`), preserving all formulas.

---

## 2. Microservice Entry Point

The designated entry point for the Plotly Dash microservice is:

```text
services/dash_service/app.py
```

Standard listening port: **`8050`** (configurable via environment variable `DASH_PORT`).

---

## 3. Local Execution

### Option A: From Desktop Client
1. Open the **EnergyAutomation** desktop application (`python main.py`).
2. In the navigation sidebar, click **Plotly Dash BI**.
3. Click **Start Background Server** to launch the Dash service on port 8050.
4. Click **Launch in Browser** to automatically open `http://localhost:8050`.

### Option B: Unified Services Launcher
Run the batch launcher:
```cmd
run_dash.bat
```
or via the multi-service CLI:
```bash
python main.py --service=dash
```

---

## 4. Production & Cloud Deployment

### 4.1 Production WSGI Server (Gunicorn / Waitress)
For multi-user corporate deployments, run Plotly Dash using a production WSGI server:

**Windows (Waitress)**:
```bash
waitress-serve --port=8050 services.dash_service.app:server
```

**Linux / Container (Gunicorn)**:
```bash
gunicorn -w 4 -b 0.0.0.0:8050 services.dash_service.app:server
```

### 4.2 Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8050
CMD ["waitress-serve", "--port=8050", "services.dash_service.app:server"]
```

---

## 5. Architectural Boundaries & Data Invariants

1. **Decoupled Architecture**: Plotly Dash functions as an independent microservice in the AutoCAD / MATLAB style service model. It consumes data from the Data Service API or local staging.
2. **Formula Safety**: Daily total formulas `=SUM(C{row}:Q{row})` and cumulative monthly row 4 formulas `=SUM(R5:R34)` are strictly preserved.
3. **Zero Fake Telemetry**: Unpolled meters are recorded as `None` / `NaN`—never coerced to `0.0`.

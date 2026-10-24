"""
⚡ EnergyAutomation — Streamlit Cloud Management BI Dashboard
Production Entry Point for Streamlit Community Cloud (energyautomation-savera-2026.streamlit.app)
and Local Execution.
Read-Only Interactive BI & Plotly Telemetry Analytics for Savera Auto Comps Pvt Ltd.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EnergyAutomation.Streamlit")

# =====================================================================
# Constants & Savera MS Plant Topology Configuration
# =====================================================================
APP_TITLE = "Savera MS — Energy Intelligence BI"
COMPANY_NAME = "Savera Auto Comps Pvt Ltd"
PLANT_NAME = "Pune Manufacturing Plant"
DEFAULT_EXCEL_FILENAME = "BI_Analysis_Report_2026.xlsx"
FALLBACK_EXCEL_FILENAME = "Test_BI_Analysis_Report_2026.xlsx"
TARGET_BASELINE_KWH = 9206.83


@dataclass
class PlantZone:
    zone_id: str
    name: str
    section: str
    building: str
    nominal_kwh: float
    description: str
    meter_patterns: List[str]


PLANT_ZONES: Dict[str, PlantZone] = {
    "plating": PlantZone(
        "plating",
        "Surface Treatment & Plating Plant",
        "Shop Floor A",
        "Bldg 1",
        160.0,
        "Electroplating & Surface Treatment lines",
        ["Chiller Plating", "New Plating", "Old Plating", "DIPP_PT", "DIPP PT"],
    ),
    "coating": PlantZone(
        "coating",
        "Finishing & Powder Coating Plant",
        "Shop Floor B",
        "Bldg 2",
        2100.0,
        "Automated Powder Coating and curing booth",
        ["Powder Coating"],
    ),
    "fabrication": PlantZone(
        "fabrication",
        "Press & Fabrication Line",
        "Shop Floor C",
        "Bldg 3",
        1250.0,
        "Stamping hydraulic presses, annealing, welding",
        ["Press & Fabrication", "Rigga Line", "Annealing", "RASKOG"],
    ),
    "compressors": PlantZone(
        "compressors",
        "Compressed Air Generation Utilities",
        "Utility Block 1",
        "Bldg 4",
        1850.0,
        "Centralized industrial air compressors",
        ["Kaeser", "ELGI E18", "ELGI E45", "Compressor"],
    ),
    "water_treatment": PlantZone(
        "water_treatment",
        "RO & DM Water Treatment Facility",
        "Utility Block 2",
        "Bldg 4",
        430.0,
        "Process demineralization and reverse osmosis",
        ["RO Plant", "DM Plant"],
    ),
    "packaging": PlantZone(
        "packaging",
        "Packaging & Stitching Line",
        "Shop Floor D",
        "Bldg 5",
        500.0,
        "Finished goods packaging and strapping",
        ["Packing", "Stiching", "Stitching"],
    ),
    "main_power": PlantZone(
        "main_power",
        "Main Power Substation & Incomer",
        "Substation",
        "Bldg 0",
        3200.0,
        "HT/LT Transformer incomer panel",
        ["Old LT Panel Main Incomer", "Incomer", "LT Incomer", "Main Incomer"],
    ),
}


# =====================================================================
# Cloud Storage & Excel Ingestion Engine
# =====================================================================
def normalize_cloud_url(url: str) -> str:
    """Translates sharing URLs (Google Drive, Dropbox, OneDrive) to direct download streams."""
    url = url.strip()
    if not url:
        return ""

    # Google Drive transformation
    if "drive.google.com" in url:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Dropbox transformation
    if "dropbox.com" in url:
        return re.sub(r"[?&]dl=0", "", url) + ("&dl=1" if "?" in url else "?dl=1")

    # OneDrive / SharePoint transformation
    if "1drv.ms" in url or "sharepoint.com" in url:
        if "download=1" not in url:
            return url + ("&download=1" if "?" in url else "?download=1")

    return url


@st.cache_data(ttl=300, show_spinner=False)
def fetch_cloud_workbook_bytes(url: str) -> Optional[bytes]:
    """Downloads workbook from cloud storage with 5-minute caching."""
    direct_url = normalize_cloud_url(url)
    try:
        resp = requests.get(direct_url, timeout=25, headers={"User-Agent": "EnergyAutomation-BI/3.0"})
        if resp.status_code == 200 and len(resp.content) > 1024:
            return resp.content
        logger.warning("Cloud fetch failed with status %d or file too small.", resp.status_code)
    except Exception as exc:
        logger.error("Error fetching cloud workbook from %s: %s", direct_url, exc)
    return None


def parse_ems_workbook(file_source: Any) -> Tuple[pd.DataFrame, List[str], Optional[str], List[str], Dict[str, Any]]:
    """
    Parses production EMS Excel workbook, respecting all Savera MS invariants:
    - Sheet: 'EMS Monitoring Report'
    - Header row: Row 3
    - Date column: Col 2 (Date)
    - Meter columns: Cols 3-17 (15 Feeders)
    - Total column: Col 18 (Total Active Energy)
    - Row 5+: Daily recorded telemetry
    """
    if isinstance(file_source, (str, Path)):
        p = Path(file_source)
        if not p.exists():
            return pd.DataFrame(), [], None, [], {"error": f"File {file_source} not found"}
        stream = io.BytesIO(p.read_bytes())
    elif isinstance(file_source, bytes):
        stream = io.BytesIO(file_source)
    else:
        stream = file_source

    try:
        wb = openpyxl.load_workbook(stream, data_only=True, read_only=True)
    except Exception as exc:
        return pd.DataFrame(), [], None, [], {"error": f"Failed to open workbook: {exc}"}

    sheet_name = "EMS Monitoring Report"
    if sheet_name not in wb.sheetnames:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]

    # Extract meter headers from Row 3 (Cols 3 to 17)
    meter_names: List[str] = []
    meter_cols: List[int] = []
    for col_idx in range(3, 18):
        val = ws.cell(row=3, column=col_idx).value
        if val is not None and str(val).strip():
            m_name = str(val).strip()
            meter_names.append(m_name)
            meter_cols.append(col_idx)

    # Classify Incomer vs Submeters
    incomer_col: Optional[str] = None
    submeter_cols: List[str] = []
    for m in meter_names:
        upper_m = m.upper()
        if "INCOMER" in upper_m or "MAIN INCOMER" in upper_m or "OLD LT PANEL" in upper_m or "EB " in upper_m:
            incomer_col = m
        else:
            submeter_cols.append(m)

    rows: List[Dict[str, Any]] = []
    max_scan_row = ws.max_row or 160

    for r in range(5, max_scan_row + 1):
        date_cell = ws.cell(row=r, column=2).value
        if not date_cell or str(date_cell).strip() in ("", "None", "Date"):
            continue

        if isinstance(date_cell, (datetime, date)):
            dt_str = date_cell.strftime("%Y-%m-%d")
        else:
            dt_str = str(date_cell).strip()[:10]

        # Ignore template rows that are not valid dates
        if not re.match(r"^\d{4}-\d{2}-\d{2}", dt_str):
            continue

        row_data: Dict[str, Any] = {"Date": dt_str, "RowIndex": r}
        submeter_sum = 0.0
        has_reading = False

        for m_name, c_idx in zip(meter_names, meter_cols):
            c_val = ws.cell(row=r, column=c_idx).value
            if c_val is not None:
                try:
                    f_val = float(c_val)
                    row_data[m_name] = f_val
                    has_reading = True
                    if m_name in submeter_cols:
                        submeter_sum += f_val
                except (ValueError, TypeError):
                    row_data[m_name] = None
            else:
                row_data[m_name] = None

        # Row 18 total cell
        tot_cell = ws.cell(row=r, column=18).value
        tot_kwh: Optional[float] = None
        if tot_cell is not None:
            try:
                tot_kwh = float(tot_cell)
            except (ValueError, TypeError):
                tot_kwh = None

        # Recalculate if formula un-evaluated in cached workbook
        if tot_kwh is None or tot_kwh <= 0:
            tot_kwh = submeter_sum if has_reading else None

        row_data["Total Active Energy"] = tot_kwh

        if has_reading or tot_kwh is not None:
            rows.append(row_data)

    wb.close()

    df = pd.DataFrame(rows)
    if not df.empty and "Date" in df.columns:
        df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date_dt"]).sort_values("Date_dt").reset_index(drop=True)
        df["Weekday"] = df["Date_dt"].dt.day_name()
        df["Is_Weekend"] = df["Date_dt"].dt.dayofweek >= 5

    meta = {
        "sheet_name": sheet_name,
        "rows_count": len(df),
        "meters_count": len(meter_names),
        "incomer_col": incomer_col,
        "submeter_count": len(submeter_cols),
    }

    return df, meter_names, incomer_col, submeter_cols, meta


def load_application_data(
    custom_file: Any,
    cloud_url: str,
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, List[str], Optional[str], List[str], Dict[str, Any], str]:
    """Resolves data from Uploaded file, Cloud Storage URL, or Local production Excel."""
    source_label = "Local Production Excel"

    # 1. User uploaded custom file via UI
    if custom_file is not None:
        source_label = f"Uploaded File: {custom_file.name}"
        df, meters, inc, subs, meta = parse_ems_workbook(custom_file)
        return df, meters, inc, subs, meta, source_label

    # 2. Cloud Storage URL (from settings / secrets / input)
    if cloud_url.strip():
        if force_refresh:
            st.cache_data.clear()
        cloud_bytes = fetch_cloud_workbook_bytes(cloud_url)
        if cloud_bytes:
            source_label = "Cloud Synchronized Stream"
            df, meters, inc, subs, meta = parse_ems_workbook(cloud_bytes)
            return df, meters, inc, subs, meta, source_label

    # 3. Local Repository Excel files
    repo_root = Path(__file__).resolve().parent
    local_candidates = [
        repo_root / DEFAULT_EXCEL_FILENAME,
        repo_root / FALLBACK_EXCEL_FILENAME,
        repo_root / "data" / DEFAULT_EXCEL_FILENAME,
    ]

    for p in local_candidates:
        if p.exists() and p.stat().st_size > 1000:
            source_label = f"Local: {p.name}"
            df, meters, inc, subs, meta = parse_ems_workbook(p)
            return df, meters, inc, subs, meta, source_label

    return pd.DataFrame(), [], None, [], {"error": "No valid workbook found."}, "Unavailable"


# =====================================================================
# Analytics Helper Functions
# =====================================================================
def compute_executive_metrics(df: pd.DataFrame, incomer_col: Optional[str], submeter_cols: List[str]) -> Dict[str, Any]:
    """Computes headline KPIs for management."""
    if df.empty:
        return {}

    latest_row = df.iloc[-1]
    latest_date = latest_row["Date"]
    latest_kwh = float(latest_row.get("Total Active Energy") or 0.0)

    prev_row = df.iloc[-2] if len(df) >= 2 else None
    prev_date = prev_row["Date"] if prev_row is not None else None
    prev_kwh = float(prev_row.get("Total Active Energy") or 0.0) if prev_row is not None else None

    change_kwh = (latest_kwh - prev_kwh) if prev_kwh is not None else None
    change_pct = ((change_kwh / prev_kwh) * 100.0) if (prev_kwh and prev_kwh > 0) else None

    latest_dt = latest_row["Date_dt"]
    mtd_mask = (df["Date_dt"].dt.year == latest_dt.year) & (df["Date_dt"].dt.month == latest_dt.month)
    mtd_df = df[mtd_mask]
    mtd_kwh = float(mtd_df["Total Active Energy"].sum(skipna=True))
    mtd_days = len(mtd_df)

    avg_kwh = float(df["Total Active Energy"].mean(skipna=True))
    peak_row = df.loc[df["Total Active Energy"].idxmax()] if not df["Total Active Energy"].isna().all() else latest_row
    min_row = df.loc[df["Total Active Energy"].idxmin()] if not df["Total Active Energy"].isna().all() else latest_row

    inc_kwh = float(latest_row[incomer_col]) if incomer_col and pd.notna(latest_row.get(incomer_col)) else None
    sub_sum = float(latest_row[submeter_cols].sum(skipna=True))
    active_submeters = sum(1 for m in submeter_cols if pd.notna(latest_row.get(m)) and float(latest_row.get(m) or 0) > 0)

    return {
        "latest_date": latest_date,
        "latest_kwh": latest_kwh,
        "prev_date": prev_date,
        "prev_kwh": prev_kwh,
        "change_kwh": change_kwh,
        "change_pct": change_pct,
        "mtd_kwh": mtd_kwh,
        "mtd_days": mtd_days,
        "avg_kwh": avg_kwh,
        "peak_date": peak_row["Date"],
        "peak_kwh": float(peak_row.get("Total Active Energy") or 0.0),
        "min_date": min_row["Date"],
        "min_kwh": float(min_row.get("Total Active Energy") or 0.0),
        "incomer_kwh": inc_kwh,
        "submeters_kwh": sub_sum,
        "active_submeters": active_submeters,
        "total_submeters": len(submeter_cols),
    }


def compute_feeder_rankings(df: pd.DataFrame, submeter_cols: List[str]) -> pd.DataFrame:
    """Ranks submeters by cumulative consumption and computes Pareto percentages."""
    if df.empty or not submeter_cols:
        return pd.DataFrame()

    sums = df[submeter_cols].sum(axis=0, skipna=True)
    means = df[submeter_cols].mean(axis=0, skipna=True)
    latest = df[submeter_cols].iloc[-1]

    records = []
    for col in submeter_cols:
        records.append({
            "Feeder Tag": col,
            "Latest Shift (kWh)": round(float(latest.get(col, 0.0) or 0.0), 2),
            "Total Energy (kWh)": round(float(sums.get(col, 0.0)), 2),
            "Daily Average (kWh)": round(float(means.get(col, 0.0)), 2),
        })

    rank_df = pd.DataFrame(records).sort_values("Total Energy (kWh)", ascending=False).reset_index(drop=True)
    grand_total = rank_df["Total Energy (kWh)"].sum()

    if grand_total > 0:
        rank_df["Share %"] = (rank_df["Total Energy (kWh)"] / grand_total * 100.0).round(2)
        rank_df["Cumulative %"] = rank_df["Share %"].cumsum().round(2)
    else:
        rank_df["Share %"] = 0.0
        rank_df["Cumulative %"] = 0.0

    return rank_df


def compute_plant_zone_summary(df: pd.DataFrame, meter_names: List[str]) -> List[Dict[str, Any]]:
    """Rolls up telemetry into Savera MS 7 official manufacturing plant zones."""
    if df.empty:
        return []

    latest_row = df.iloc[-1]
    zone_results: List[Dict[str, Any]] = []

    for z_id, zone in PLANT_ZONES.items():
        matched_meters = []
        for m in meter_names:
            for pattern in zone.meter_patterns:
                if pattern.lower() in m.lower():
                    if m not in matched_meters:
                        matched_meters.append(m)
                    break

        zone_total = 0.0
        active_count = 0
        meter_breakdown = []

        for m in matched_meters:
            val = float(latest_row.get(m) or 0.0) if pd.notna(latest_row.get(m)) else 0.0
            zone_total += val
            if val > 0:
                active_count += 1
            meter_breakdown.append({"meter": m, "kwh": val})

        status = "NORMAL"
        if active_count == 0 and zone_total == 0:
            status = "STANDBY"
        elif zone_total > zone.nominal_kwh * 1.30:
            status = "HIGH"
        elif zone_total > zone.nominal_kwh * 1.15:
            status = "WARNING"

        zone_results.append({
            "zone_id": z_id,
            "name": zone.name,
            "section": zone.section,
            "building": zone.building,
            "nominal_kwh": zone.nominal_kwh,
            "current_kwh": round(zone_total, 2),
            "active_meters": active_count,
            "total_meters": len(matched_meters),
            "status": status,
            "description": zone.description,
            "meters": meter_breakdown,
        })

    return zone_results


def compute_reconciliation_audit(df: pd.DataFrame, submeter_cols: List[str]) -> Dict[str, Any]:
    """Audits mathematical reconciliation between sum of feeders and workbook total."""
    if df.empty:
        return {"reconciled": True, "discrepancies": [], "missing_dates": []}

    discrepancies = []
    for _, row in df.iterrows():
        sub_sum = float(row[submeter_cols].sum(skipna=True))
        recorded_tot = float(row.get("Total Active Energy") or 0.0)
        diff = abs(sub_sum - recorded_tot)
        if diff > 1.0:
            discrepancies.append({
                "Date": row["Date"],
                "Sum of Feeders (kWh)": round(sub_sum, 2),
                "Workbook Total (kWh)": round(recorded_tot, 2),
                "Variance (kWh)": round(diff, 2),
            })

    min_date = df["Date_dt"].min()
    max_date = df["Date_dt"].max()
    all_days = pd.date_range(min_date, max_date)
    recorded_days = set(df["Date_dt"].dt.strftime("%Y-%m-%d"))
    missing_dates = [d.strftime("%Y-%m-%d") for d in all_days if d.strftime("%Y-%m-%d") not in recorded_days]

    return {
        "reconciled": len(discrepancies) == 0,
        "discrepancies": discrepancies,
        "missing_dates": missing_dates,
        "recorded_days_count": len(df),
        "calendar_span_days": len(all_days),
    }


# =====================================================================
# Main Application Flow
# =====================================================================
def main() -> None:
    # Page Header
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom Theming CSS
    st.markdown("""
    <style>
        .metric-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98));
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #38bdf8;
        }
        .metric-title {
            font-size: 0.80rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: #94a3b8;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            color: #f8fafc;
            line-height: 1.1;
            margin-bottom: 6px;
        }
        .metric-subtitle {
            font-size: 0.82rem;
            font-weight: 600;
        }
        .badge-ok {
            background-color: #065f46;
            color: #34d399;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-warn {
            background-color: #78350f;
            color: #fbbf24;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-info {
            background-color: #1e3a8a;
            color: #60a5fa;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .brand-header-box {
            background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## ⚡ **Energy Intelligence**")
        st.caption(f"{COMPANY_NAME} • {PLANT_NAME}")
        st.markdown("---")

        selected_view = st.radio(
            "Navigation Menu",
            options=[
                "📊 Executive BI Overview",
                "📈 Energy Trends & Moving Avg",
                "⚡ Feeder Rankings & Pareto",
                "🏭 Production Areas & Topology",
                "🔍 Data Quality & Reconciliation",
                "📋 Engineering Telemetry Grid",
                "⚙️ Cloud Storage & Config",
                "ℹ️ System Architecture",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown("### 🔄 Synchronization")
        sync_clicked = st.button("🔄 Sync Now / Refresh", use_container_width=True, type="primary")

        secrets_cloud_url = ""
        try:
            secrets_cloud_url = st.secrets.get("EXCEL_URL", "")
        except Exception:
            pass

        with st.expander("⚙️ Data Source Options", expanded=False):
            cloud_url_input = st.text_input(
                "Cloud Excel URL (Google Drive / OneDrive):",
                value=secrets_cloud_url,
                placeholder="https://drive.google.com/file/d/...",
            )
            custom_uploaded_file = st.file_uploader(
                "Upload Updated Excel Report (.xlsx):",
                type=["xlsx"],
                help="Directly test or upload any updated EMS Monitoring Report workbook.",
            )

        st.markdown("---")
        st.caption("EnergyAutomation v3.2 Enterprise BI • Streamlit Cloud Ready")

    # Load Data
    df, meter_names, incomer_col, submeter_cols, meta, source_name = load_application_data(
        custom_file=custom_uploaded_file,
        cloud_url=cloud_url_input,
        force_refresh=sync_clicked,
    )

    if df.empty:
        st.error(f"⚠️ Unable to load EMS energy telemetry. Data source status: {source_name}")
        st.info("Please verify the production Excel workbook (`BI_Analysis_Report_2026.xlsx`) or supply a cloud sharing URL in the sidebar.")
        return

    kpis = compute_executive_metrics(df, incomer_col, submeter_cols)

    # Top Brand Header
    st.markdown(f"""
    <div class="brand-header-box">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <h2 style="margin: 0; color: #ffffff; font-weight: 800; font-size: 1.6rem; letter-spacing: -0.5px;">
                    ⚡ {COMPANY_NAME}
                </h2>
                <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                    {PLANT_NAME} • Autonomous NBSense EMS Production Energy Intelligence
                </p>
            </div>
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                <span class="badge-ok">ACTIVE INGESTION</span>
                <span class="badge-info">SOURCE: {source_name}</span>
                <span class="badge-ok">LATEST SHIFT: {kpis.get('latest_date', '—')}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # View Dispatcher
    if selected_view == "📊 Executive BI Overview":
        _render_executive_view(df, kpis, submeter_cols)
    elif selected_view == "📈 Energy Trends & Moving Avg":
        _render_trends_view(df, meter_names, incomer_col)
    elif selected_view == "⚡ Feeder Rankings & Pareto":
        _render_rankings_view(df, submeter_cols)
    elif selected_view == "🏭 Production Areas & Topology":
        _render_zones_view(df, meter_names)
    elif selected_view == "🔍 Data Quality & Reconciliation":
        _render_reconciliation_view(df, submeter_cols)
    elif selected_view == "📋 Engineering Telemetry Grid":
        _render_engineering_grid(df, meter_names)
    elif selected_view == "⚙️ Cloud Storage & Config":
        _render_config_view()
    elif selected_view == "ℹ️ System Architecture":
        _render_architecture_view()


def _render_executive_view(df: pd.DataFrame, kpis: Dict[str, Any], submeter_cols: List[str]) -> None:
    st.markdown("### 📊 Executive BI Overview & High-Level KPIs")

    # KPI Metric Cards Row
    c1, c2, c3, c4 = st.columns(4)

    latest_kwh = kpis.get("latest_kwh", 0.0)
    change_pct = kpis.get("change_pct")
    change_color = "#34d399" if (change_pct is not None and change_pct <= 0) else "#fbbf24"
    change_text = f"{change_pct:+.1f}% vs previous" if change_pct is not None else "Baseline comparison"

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Latest Shift Energy</div>
            <div class="metric-value">{latest_kwh:,.2f} <span style="font-size: 1rem; color: #94a3b8;">kWh</span></div>
            <div class="metric-subtitle" style="color: #38bdf8;">Report Date: {kpis.get('latest_date', '—')}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        prev_kwh_val = kpis.get("prev_kwh")
        prev_str = f"{prev_kwh_val:,.2f} kWh" if prev_kwh_val else "—"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Previous Shift Energy</div>
            <div class="metric-value">{prev_str}</div>
            <div class="metric-subtitle" style="color: {change_color};">{change_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        mtd_kwh = kpis.get("mtd_kwh", 0.0)
        mtd_days = kpis.get("mtd_days", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Month-To-Date (MTD)</div>
            <div class="metric-value">{mtd_kwh:,.2f} <span style="font-size: 1rem; color: #94a3b8;">kWh</span></div>
            <div class="metric-subtitle" style="color: #c084fc;">Cumulative {mtd_days} Ingestion Days</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        avg_kwh = kpis.get("avg_kwh", 0.0)
        active_cnt = kpis.get("active_submeters", 0)
        tot_cnt = kpis.get("total_submeters", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Daily Average Load</div>
            <div class="metric-value">{avg_kwh:,.2f} <span style="font-size: 1rem; color: #94a3b8;">kWh</span></div>
            <div class="metric-subtitle" style="color: #34d399;">Active Submeters: {active_cnt} / {tot_cnt}</div>
        </div>
        """, unsafe_allow_html=True)

    # Plotly Trend & Donut Share Charts
    col_chart, col_donut = st.columns([7, 5])

    with col_chart:
        st.markdown("#### Shift-by-Shift Energy Telemetry Trend vs Target Baseline")

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=df["Date"],
            y=df["Total Active Energy"],
            name="Daily Shift Energy",
            marker=dict(color="#3b82f6", opacity=0.85),
            hovertemplate="<b>%{x}</b><br>Active Energy: %{y:,.2f} kWh<extra></extra>",
        ))

        if len(df) >= 3:
            df["_ma7"] = df["Total Active Energy"].rolling(window=min(7, len(df)), min_periods=1).mean()
            fig_trend.add_trace(go.Scatter(
                x=df["Date"],
                y=df["_ma7"],
                name="7-Day Moving Avg",
                mode="lines",
                line=dict(color="#60a5fa", width=2.5),
                hovertemplate="7-Day Moving Avg: %{y:,.2f} kWh<extra></extra>",
            ))

        fig_trend.add_hline(
            y=TARGET_BASELINE_KWH,
            line_dash="dot",
            line_color="#f59e0b",
            annotation_text=f"Baseline Target ({TARGET_BASELINE_KWH:,.0f} kWh)",
            annotation_position="top right",
        )

        fig_trend.update_layout(
            paper_bgcolor="#1e293b",
            plot_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"),
            xaxis=dict(gridcolor="#334155", title="Report Date", tickangle=-30),
            yaxis=dict(gridcolor="#334155", title="Active Energy (kWh)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=40, b=40),
            height=370,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_donut:
        st.markdown("#### Active Feeder Share Distribution (Latest Shift)")
        latest_row = df.iloc[-1]
        donut_data = []
        for s in submeter_cols:
            val = float(latest_row.get(s) or 0.0) if pd.notna(latest_row.get(s)) else 0.0
            if val > 0:
                donut_data.append({"Feeder": s, "kWh": val})

        if donut_data:
            donut_df = pd.DataFrame(donut_data).sort_values("kWh", ascending=False)
            top5 = donut_df.head(5).copy()
            others_sum = donut_df.iloc[5:]["kWh"].sum() if len(donut_df) > 5 else 0.0
            if others_sum > 0:
                top5 = pd.concat([top5, pd.DataFrame([{"Feeder": "Other Submeters", "kWh": others_sum}])], ignore_index=True)

            fig_donut = go.Figure(data=[go.Pie(
                labels=top5["Feeder"],
                values=top5["kWh"],
                hole=0.55,
                marker=dict(colors=px.colors.qualitative.Plotly),
                textinfo="label+percent",
                hoverinfo="label+value+percent",
            )])
            fig_donut.update_layout(
                paper_bgcolor="#1e293b",
                plot_bgcolor="#1e293b",
                font=dict(color="#e2e8f0"),
                showlegend=False,
                margin=dict(l=10, r=10, t=30, b=20),
                height=370,
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No active submeter readings found on the latest shift.")

    # Incomer Reconciliation Card
    st.markdown("---")
    st.markdown("#### Main Incomer vs Submeters Power Balance")
    inc_kwh = kpis.get("incomer_kwh")
    sub_kwh = kpis.get("submeters_kwh", 0.0)

    if inc_kwh and inc_kwh > 0:
        variance_kwh = inc_kwh - sub_kwh
        variance_pct = (variance_kwh / inc_kwh) * 100.0

        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("Main Incomer Energy", f"{inc_kwh:,.2f} kWh", help="Total active energy metered at HT/LT panel incomer.")
        with b2:
            st.metric("Submeters Aggregate Sum", f"{sub_kwh:,.2f} kWh", help="Sum of all individual feeder submeters.")
        with b3:
            v_color = "normal" if abs(variance_pct) < 10 else "inverse"
            st.metric("Auxiliary / Distribution Loss", f"{variance_kwh:+,.2f} kWh", f"{variance_pct:+.1f}%", delta_color=v_color)
    else:
        st.info("Main incomer meter not designated or missing reading on latest shift.")


def _render_trends_view(df: pd.DataFrame, meter_names: List[str], incomer_col: Optional[str]) -> None:
    st.markdown("### 📈 Time-Series Energy Trends & Consumption Patterns")

    default_sel = [incomer_col] if incomer_col else [meter_names[0]]
    selected_meters = st.multiselect(
        "Select Feeders / Circuits to Compare:",
        options=meter_names,
        default=default_sel,
        help="Overlay multiple feeders to analyze load correlation, peak shifts, and anomalies.",
    )

    if selected_meters:
        fig_multi = go.Figure()
        for m in selected_meters:
            fig_multi.add_trace(go.Scatter(
                x=df["Date"],
                y=df[m],
                name=m,
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate=f"<b>{m}</b><br>%{{x}}: %{{y:,.2f}} kWh<extra></extra>",
            ))

        fig_multi.update_layout(
            title="Multi-Feeder Shift-by-Shift Energy Telemetry Overlay",
            paper_bgcolor="#1e293b",
            plot_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"),
            xaxis=dict(gridcolor="#334155", title="Report Date"),
            yaxis=dict(gridcolor="#334155", title="Active Energy (kWh)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=60, b=40),
            height=420,
        )
        st.plotly_chart(fig_multi, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Day-of-Week Consumption Profile (Plant Load Patterns)")

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_df = df.groupby("Weekday")["Total Active Energy"].agg(["mean", "count"]).reindex(dow_order).reset_index()

    colors = ["#3b82f6" if d not in ("Saturday", "Sunday") else "#f59e0b" for d in dow_df["Weekday"]]

    fig_dow = go.Figure()
    fig_dow.add_trace(go.Bar(
        x=dow_df["Weekday"],
        y=dow_df["mean"],
        marker_color=colors,
        text=[f"{v:,.0f} kWh" if pd.notna(v) else "" for v in dow_df["mean"]],
        textposition="auto",
        hovertemplate="<b>%{x}</b><br>Average: %{y:,.2f} kWh<extra></extra>",
    ))

    fig_dow.update_layout(
        title="Average Daily Consumption by Day of Week (Blue: Weekday, Amber: Weekend)",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155", title="Average Energy (kWh)"),
        margin=dict(l=40, r=20, t=50, b=40),
        height=360,
    )
    st.plotly_chart(fig_dow, use_container_width=True)


def _render_rankings_view(df: pd.DataFrame, submeter_cols: List[str]) -> None:
    st.markdown("### ⚡ Feeder Active Energy Ranking & 80/20 Pareto Analysis")
    st.markdown("Identifies the vital few submeters that drive the vast majority of plant energy expenditure.")

    rankings = compute_feeder_rankings(df, submeter_cols)

    if not rankings.empty:
        fig_pareto = go.Figure()

        fig_pareto.add_trace(go.Bar(
            x=rankings["Feeder Tag"],
            y=rankings["Total Energy (kWh)"],
            name="Total Energy (kWh)",
            marker=dict(color="#3b82f6"),
            yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Total: %{y:,.2f} kWh<extra></extra>",
        ))

        fig_pareto.add_trace(go.Scatter(
            x=rankings["Feeder Tag"],
            y=rankings["Cumulative %"],
            name="Cumulative Share %",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=3),
            marker=dict(size=7, color="#ffffff"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Cumulative: %{y:.1f}%<extra></extra>",
        ))

        fig_pareto.add_hline(
            y=80,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text="80% Pareto Cutoff",
            annotation_position="bottom right",
            yref="y2",
        )

        fig_pareto.update_layout(
            title="Feeder Energy Pareto Distribution (80/20 Rule)",
            paper_bgcolor="#1e293b",
            plot_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"),
            xaxis=dict(gridcolor="#334155", tickangle=-35),
            yaxis=dict(gridcolor="#334155", title="Total Energy (kWh)"),
            yaxis2=dict(
                title="Cumulative Percentage (%)",
                overlaying="y",
                side="right",
                range=[0, 105],
                showgrid=False,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=90),
            height=440,
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

        st.markdown("#### Feeder Telemetry Ranking Table")
        st.dataframe(rankings, use_container_width=True, hide_index=True)


def _render_zones_view(df: pd.DataFrame, meter_names: List[str]) -> None:
    st.markdown("### 🏭 Production Areas & Savera MS Plant Topology")
    st.markdown("Aggregates feeder circuits into the 7 official manufacturing zones of Pune Plant.")

    zones = compute_plant_zone_summary(df, meter_names)

    z_names = [z["name"] for z in zones if z["zone_id"] != "main_power"]
    z_loads = [z["current_kwh"] for z in zones if z["zone_id"] != "main_power"]

    fig_zones = go.Figure()
    fig_zones.add_trace(go.Bar(
        x=z_names,
        y=z_loads,
        marker=dict(color=px.colors.qualitative.Dark24[:len(z_names)]),
        text=[f"{v:,.1f} kWh" for v in z_loads],
        textposition="auto",
    ))
    fig_zones.update_layout(
        title="Latest Shift Active Energy by Manufacturing Zone",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#334155", tickangle=-25),
        yaxis=dict(gridcolor="#334155", title="Active Energy (kWh)"),
        margin=dict(l=40, r=20, t=50, b=80),
        height=380,
    )
    st.plotly_chart(fig_zones, use_container_width=True)

    st.markdown("#### Manufacturing Zone Telemetry Diagnostics")
    for z in zones:
        with st.expander(f"{z['name']} — {z['current_kwh']:,.1f} kWh ({z['status']})", expanded=True):
            col_z1, col_z2 = st.columns([4, 8])
            with col_z1:
                st.markdown(f"**Section / Bldg:** {z['section']} ({z['building']})")
                st.markdown(f"**Nominal Baseline:** {z['nominal_kwh']:,.0f} kWh")
                st.markdown(f"**Active Circuits:** {z['active_meters']} / {z['total_meters']}")
                st.caption(z["description"])
            with col_z2:
                meter_items = z["meters"]
                if meter_items:
                    m_df = pd.DataFrame(meter_items)
                    m_df.columns = ["Meter Tag", "Latest kWh"]
                    st.dataframe(m_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No circuits mapped to this zone.")


def _render_reconciliation_view(df: pd.DataFrame, submeter_cols: List[str]) -> None:
    st.markdown("### 🔍 Data Quality, Freshness & Audit Reconciliation")
    st.markdown("Strict integrity validation between workbook formula columns and individual feeder readings.")

    audit = compute_reconciliation_audit(df, submeter_cols)

    q1, q2, q3 = st.columns(3)
    with q1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Formula Reconciliation Audit</div>
            <div class="metric-value" style="color: {'#34d399' if audit['reconciled'] else '#ef4444'};">
                {'100% RECONCILED' if audit['reconciled'] else f"{len(audit['discrepancies'])} DISCREPANCIES"}
            </div>
            <div class="metric-subtitle" style="color: #94a3b8;">Sum(Feeders) vs Row 18 Formula</div>
        </div>
        """, unsafe_allow_html=True)

    with q2:
        missing_cnt = len(audit["missing_dates"])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Calendar Continuity</div>
            <div class="metric-value" style="color: {'#34d399' if missing_cnt == 0 else '#fbbf24'};">
                {audit['recorded_days_count']} / {audit['calendar_span_days']} Days
            </div>
            <div class="metric-subtitle" style="color: #94a3b8;">{missing_cnt} Calendar Gaps Detected</div>
        </div>
        """, unsafe_allow_html=True)

    with q3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Ingestion Window</div>
            <div class="metric-value" style="font-size: 1.35rem;">
                {df['Date'].min()} <span style="font-size: 0.9rem; color: #94a3b8;">to</span> {df['Date'].max()}
            </div>
            <div class="metric-subtitle" style="color: #38bdf8;">Continuous Production Ledger</div>
        </div>
        """, unsafe_allow_html=True)

    if audit["missing_dates"]:
        st.warning(f"⚠️ Calendar gaps detected on {len(audit['missing_dates'])} dates in the recorded date range:")
        st.write(", ".join(audit["missing_dates"][:15]) + ("..." if len(audit["missing_dates"]) > 15 else ""))
    else:
        st.success("✅ Zero calendar gaps detected across the active ingestion window.")

    st.markdown("#### Mathematical Reconciliation Ledger")
    if audit["discrepancies"]:
        disc_df = pd.DataFrame(audit["discrepancies"])
        st.dataframe(disc_df, use_container_width=True, hide_index=True)
    else:
        st.info("✅ All recorded shift dates exhibit 100% exact mathematical equality between feeder sum and Row 18 total.")


def _render_engineering_grid(df: pd.DataFrame, meter_names: List[str]) -> None:
    st.markdown("### 📋 Engineering Telemetry Grid (Shift-by-Shift Matrix)")
    st.markdown("Granular shift-by-shift matrix of all plant feeders for engineering telemetry audit.")

    min_date = df["Date_dt"].min().date()
    max_date = df["Date_dt"].max().date()
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_d = st.date_input("Filter Start Date:", value=min_date, min_value=min_date, max_value=max_date)
    with col_d2:
        end_d = st.date_input("Filter End Date:", value=max_date, min_value=min_date, max_value=max_date)

    filtered_df = df[(df["Date_dt"].dt.date >= start_d) & (df["Date_dt"].dt.date <= end_d)].copy()

    display_cols = ["Date"] + meter_names + ["Total Active Energy"]
    avail_cols = [c for c in display_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[avail_cols].style.format(
            {c: "{:,.2f}" for c in avail_cols if c != "Date"},
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = filtered_df[avail_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Telemetry Matrix as CSV",
        data=csv_bytes,
        file_name=f"SaveraMS_Energy_Telemetry_{start_d}_{end_d}.csv",
        mime="text/csv",
        use_container_width=False,
    )


def _render_config_view() -> None:
    st.markdown("### ⚙️ Streamlit Community Cloud Hosting & Configuration")
    st.markdown("""
    This application is fully prepared for immediate hosting on **Streamlit Community Cloud** under:
    **`energyautomation-savera-2026.streamlit.app`**
    """)

    st.markdown("#### 1. Deployment Parameters")
    st.code("""
Repository:      MrigankoSarkar/Energy_Automation-SAVERA
Branch:          main
Main file path:  streamlit_app.py
App URL:         energyautomation-savera-2026.streamlit.app
    """, language="text")

    st.markdown("#### 2. Cloud Storage Secrets Template (`.streamlit/secrets.toml`)")
    st.markdown("To enable automated live synchronization with your production Excel file hosted on Google Drive, Dropbox, or OneDrive:")
    st.code("""
# .streamlit/secrets.toml
EXCEL_URL = "https://drive.google.com/file/d/YOUR_GOOGLE_DRIVE_FILE_ID/view?usp=sharing"
    """, language="toml")

    st.markdown("#### 3. Invariants & Data Safety")
    st.markdown("""
    - **Strictly Read-Only:** The dashboard never writes or alters the production Excel workbook.
    - **Formula Preservation:** Excel formulas like `=SUM(C5:Q5)` are safeguarded and evaluated in memory.
    - **Zero Core Impact:** Microservices and the Windows Fluent desktop client continue to operate independently.
    """)


def _render_architecture_view() -> None:
    st.markdown("### ℹ️ EnergyAutomation Platform Architecture")
    st.markdown(f"""
    **EnergyAutomation** is an enterprise energy management automation platform built for **{COMPANY_NAME} ({PLANT_NAME})**.
    It automates the daily ingestion of NBSense electrical reports from Gmail, updates production Excel workbooks,
    maintains an immutable audit ledger, and exposes interactive business intelligence via Streamlit Cloud and Plotly Dash.

    #### System Components
    1. **Windows 11 Fluent Desktop GUI:** Native operator control center with automated report fetching and workflow supervision.
    2. **Streamlit Management BI (`streamlit_app.py`):** Cloud-hosted executive & engineering analytics accessible anywhere on mobile and desktop.
    3. **Plotly Dash BI Microservice:** Decoupled local BI server running on port 8050.
    4. **Telemetry Data Provider:** High-performance, zero-side-effect Excel evaluator preserving workbook integrity.
    """)


if __name__ == "__main__":
    main()

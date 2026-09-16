"""
About & System Architecture View for EnergyAutomation Streamlit BI.
Explains the end-to-end data pipeline, architectural separation of concerns,
and system configuration parameters.
"""

from __future__ import annotations

import streamlit as st

from streamlit_app.config import DashboardConfig
from streamlit_app.data_loader import LoadedData


def render_about_view(config: DashboardConfig, loaded_data: LoadedData) -> None:
    """Renders the architectural overview and documentation tab."""
    st.subheader("System Architecture & Data Pipeline")

    st.markdown(
        """
        ### End-to-End Enterprise Automation Pipeline

        ```
        ┌─────────────────────────┐
        │       Gmail Inbox       │  Automated daily monitoring for "EMS Monitoring Report"
        └────────────┬────────────┘
                     │  1. PDF Report Download
                     ▼
        ┌─────────────────────────┐
        │  EnergyAutomation Core  │  Desktop engine (APScheduler, PyMuPDF, Pydantic)
        │  • PDF Parsing          │  Extracts meter energy readings in kWh
        │  • Data Validation      │  Validates ranges & dates (SQLite audit log)
        │  • Header Mapping       │  Maps NBSense meter names to Excel headers
        │  • Excel Service        │  Updates Test_BI_Analysis_Report_2026.xlsx
        │                         │  Preserves formulas: =SUM(C{row}:Q{row}) & row 4 YTD
        └────────────┬────────────┘
                     │  2. Synchronized File Save
                     ▼
        ┌─────────────────────────┐
        │  Cloud Storage / Drive  │  Google Drive / OneDrive / Dropbox / Local FS
        └────────────┬────────────┘
                     │  3. Read-Only Direct Download (Streamlit Caching)
                     ▼
        ┌─────────────────────────┐
        │   Streamlit BI Layer    │  Management Analytics, Interactive Plotly Trends,
        │                         │  7-Zone Topology, Executive KPIs, CSV Export
        └─────────────────────────┘
        ```
        """
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Architectural Principles & Invariants")
        st.markdown(
            """
            1. **Strict Separation of Concerns**:
               - **EnergyAutomation Core** is the **sole source of truth** for data ingestion, Gmail processing, PDF parsing, validation, and Excel updating.
               - **Streamlit BI** is strictly a **read-only visualization & management layer**. It never modifies the workbook, writes to cells, or alters backend state.
            2. **Preservation of Excel Formulas**:
               - Cumulative row 4 (`Cum.  (YTD)`) formulas `=SUM(C5:C34)` and daily row sum formulas `=SUM(C{row}:Q{row})` are 100% preserved.
            3. **N/A Invariant**:
               - Disconnected or unpolled meters (`N/A`) are preserved as `NaN` and are never coerced to `0.0`.
            4. **Dual Mode Support**:
               - **Local Storage**: Zero-network offline execution for workstations and unit tests.
               - **Cloud Synchronization**: Direct URL translation for Google Drive, OneDrive, and Dropbox.
            """
        )

    with col2:
        st.markdown("### Active Runtime Configuration")
        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-size: 0.88rem; line-height: 1.8;">
                <div><strong>Data Source Mode:</strong> <code>{config.data_source.upper()}</code></div>
                <div><strong>Cloud Provider:</strong> <code>{config.cloud_provider}</code></div>
                <div><strong>Target Excel Sheet:</strong> <code>{config.worksheet_name}</code></div>
                <div><strong>Cache TTL:</strong> <code>{config.cache_ttl_seconds} seconds</code></div>
                <div><strong>Auto-Refresh Interval:</strong> <code>{config.refresh_interval_seconds} seconds</code></div>
                <div><strong>Company Name:</strong> {config.company_name}</div>
                <div><strong>Facility:</strong> {config.plant_name}</div>
                <div><strong>Current Freshness:</strong> {loaded_data.freshness_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

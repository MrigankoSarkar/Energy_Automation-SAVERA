"""
Main Application Entry Point for EnergyAutomation Streamlit BI Dashboard.
Autonomous EMS Intelligence, Cloud Excel Synchronization & Executive Analytics.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from streamlit_app.config import DashboardConfig, load_config
from streamlit_app.data_loader import DataLoader, LoadedData
from streamlit_app.analytics import EnergyAnalytics
from streamlit_app.components.branding import render_branding_header
from streamlit_app.components.freshness_banner import render_freshness_banner
from streamlit_app.pages_views import (
    render_executive_view,
    render_energy_trends_view,
    render_meter_analysis_view,
    render_plant_areas_view,
    render_data_quality_view,
    render_engineering_view,
    render_about_view,
)


def main() -> None:
    # Page configuration
    st.set_page_config(
        page_title="Savera MS — Energy Intelligence & Executive BI",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load initial configuration
    config = load_config()

    # Sidebar: Navigation & Controls
    with st.sidebar:
        st.markdown("### ⚡ **Energy Intelligence**")
        st.caption(f"{config.company_name} &bull; {config.plant_name}")
        st.markdown("---")

        nav_view = st.radio(
            "Navigation Menu",
            options=[
                "📊 Executive Overview",
                "📈 Energy Trends & Patterns",
                "⚡ Meter Rankings & Pareto",
                "🏭 Production Areas & Topology",
                "🔍 Data Quality & Reconciliation",
                "📋 Engineering Data Grid",
                "ℹ️ System Architecture",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown("### 🔄 Synchronization")

        # Sync Now button
        force_sync = st.button("🔄 Sync Now / Refresh", use_container_width=True, type="primary")

        # Runtime Data Source Override (Local vs Cloud toggle)
        with st.expander("⚙️ Source Settings", expanded=False):
            mode_choice = st.selectbox(
                "Data Source:",
                options=["Local Storage", "Cloud Synchronization"],
                index=0 if config.data_source == "local" else 1,
            )

            effective_source = "local" if mode_choice == "Local Storage" else "cloud"
            cloud_url_input = config.excel_url
            if effective_source == "cloud":
                cloud_url_input = st.text_input(
                    "Cloud Excel URL:",
                    value=config.excel_url,
                    placeholder="https://drive.google.com/file/d/...",
                )

            # Re-wrap config if user tweaked runtime inputs in sidebar
            if effective_source != config.data_source or (effective_source == "cloud" and cloud_url_input != config.excel_url):
                config = DashboardConfig(
                    data_source=effective_source,
                    cloud_provider=config.cloud_provider,
                    excel_url=cloud_url_input,
                    local_excel_path=config.local_excel_path,
                    worksheet_name=config.worksheet_name,
                    header_row=config.header_row,
                    date_column=config.date_column,
                    first_data_row=config.first_data_row,
                    total_column=config.total_column,
                    cache_ttl_seconds=config.cache_ttl_seconds,
                    refresh_interval_seconds=config.refresh_interval_seconds,
                    company_name=config.company_name,
                    plant_name=config.plant_name,
                    app_title=config.app_title,
                    timezone=config.timezone,
                    logo_path=config.logo_path,
                )

    # Top Application Header
    render_branding_header(config)

    # Load Data
    data_loader = DataLoader(config)
    loaded_data: LoadedData = data_loader.load_data(force_refresh=force_sync)

    # Freshness & Connection Status Banner
    render_freshness_banner(loaded_data)

    # Initialize Analytics Engine
    analytics = EnergyAnalytics(loaded_data.parsed)

    # Dispatch to Selected View
    if "Executive Overview" in nav_view:
        render_executive_view(analytics)
    elif "Energy Trends" in nav_view:
        render_energy_trends_view(analytics)
    elif "Meter Rankings" in nav_view:
        render_meter_analysis_view(analytics)
    elif "Production Areas" in nav_view:
        render_plant_areas_view(analytics)
    elif "Data Quality" in nav_view:
        render_data_quality_view(analytics)
    elif "Engineering Data Grid" in nav_view:
        render_engineering_view(analytics)
    elif "System Architecture" in nav_view:
        render_about_view(config, loaded_data)


if __name__ == "__main__":
    main()

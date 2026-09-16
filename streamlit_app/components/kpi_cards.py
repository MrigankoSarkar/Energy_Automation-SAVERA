"""
Executive KPI Card Component for EnergyAutomation Streamlit BI.
Renders clean industrial metric cards for executive decision-makers.
"""

from __future__ import annotations

import streamlit as st

from streamlit_app.analytics import ExecutiveKPIs


def render_kpi_cards(kpis: ExecutiveKPIs) -> None:
    """Renders the standard 5-column executive metric cards row."""
    col1, col2, col3, col4, col5 = st.columns(5)

    # Format DoD Delta
    if kpis.dod_change_kwh > 0:
        delta_class = "delta-pos"
        delta_arrow = "▲"
        delta_str = f"{delta_arrow} +{kpis.dod_change_kwh:,.1f} kWh (+{kpis.dod_change_pct:.1f}%)"
    elif kpis.dod_change_kwh < 0:
        delta_class = "delta-neg"
        delta_arrow = "▼"
        delta_str = f"{delta_arrow} {kpis.dod_change_kwh:,.1f} kWh ({kpis.dod_change_pct:.1f}%)"
    else:
        delta_class = "delta-neutral"
        delta_str = "0.0 kWh (0.0%)"

    with col1:
        date_label = kpis.latest_date.strftime("%d %b %Y") if kpis.latest_date else "N/A"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Latest Day ({date_label})</div>
                <div class="value">{kpis.latest_total_kwh:,.1f} <span style="font-size: 1rem; color: #64748b;">kWh</span></div>
                <div class="{delta_class}">{delta_str} vs prior day</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Month-to-Date (MTD)</div>
                <div class="value">{kpis.mtd_total_kwh:,.0f} <span style="font-size: 1rem; color: #64748b;">kWh</span></div>
                <div class="delta-neutral">Across {kpis.mtd_days_count} recorded days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Daily Average</div>
                <div class="value">{kpis.avg_daily_kwh:,.1f} <span style="font-size: 1rem; color: #64748b;">kWh/day</span></div>
                <div class="delta-neutral">All recorded days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        peak_label = kpis.peak_date.strftime("%d %b") if kpis.peak_date else "N/A"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Peak Day ({peak_label})</div>
                <div class="value" style="color: #b91c1c;">{kpis.peak_kwh:,.1f} <span style="font-size: 1rem; color: #64748b;">kWh</span></div>
                <div class="delta-neutral">Min: {kpis.min_kwh:,.1f} kWh ({kpis.min_date.strftime('%d %b') if kpis.min_date else 'N/A'})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        pct_active = (kpis.active_meters_count / kpis.total_meters_count * 100) if kpis.total_meters_count > 0 else 0
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Meters Active</div>
                <div class="value" style="color: #047857;">{kpis.active_meters_count} <span style="font-size: 1.1rem; color: #64748b;">/ {kpis.total_meters_count}</span></div>
                <div class="delta-neutral">{pct_active:.0f}% operational rate</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

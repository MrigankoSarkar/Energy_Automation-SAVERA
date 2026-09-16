"""
Plant Production Areas & Topology View for EnergyAutomation Streamlit BI.
Visualizes energy distribution across the 7 official Savera MS facility zones,
evaluating nominal baselines and identifying equipment anomalies.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics


def render_plant_areas_view(analytics: EnergyAnalytics) -> None:
    """Renders the 7-zone production area analysis tab."""
    st.subheader("Facility Production Areas & Energy Topology")

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    # Option to view for Latest Date or Average across period
    view_mode = st.radio(
        "Evaluation Basis:",
        options=["Latest Recorded Date", "Period Daily Average"],
        horizontal=True,
        key="zone_eval_basis",
    )

    eval_date = analytics.df.iloc[-1][analytics.date_col] if "Latest" in view_mode else None
    zones = analytics.get_zone_breakdown(target_date=eval_date)

    if not zones:
        st.warning("No zone topology mappings found.")
        return

    # Filter out main_power incomer for submeter zone charts
    submeter_zones = [z for z in zones if z["zone_id"] != "main_power"]

    # Visual Breakdown: Bar Chart comparing Actual vs Nominal Baseline
    st.markdown("### Production Zones: Actual vs Nominal Baseline (kWh)")

    zone_names = [z["name"] for z in submeter_zones]
    actual_kwh = [z["total_kwh"] for z in submeter_zones]
    nominal_kwh = [z["nominal_kwh"] for z in submeter_zones]

    fig_zones = go.Figure()
    fig_zones.add_trace(
        go.Bar(
            name="Actual Energy (kWh)",
            x=zone_names,
            y=actual_kwh,
            marker_color="#2563eb",
            hovertemplate="<b>%{x}</b><br>Actual: %{y:,.1f} kWh<extra></extra>",
        )
    )
    fig_zones.add_trace(
        go.Bar(
            name="Nominal Baseline (kWh)",
            x=zone_names,
            y=nominal_kwh,
            marker_color="#cbd5e1",
            hovertemplate="<b>%{x}</b><br>Nominal: %{y:,.1f} kWh<extra></extra>",
        )
    )

    fig_zones.update_layout(
        barmode="group",
        margin=dict(l=20, r=20, t=30, b=80),
        height=350,
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    st.plotly_chart(fig_zones, use_container_width=True)

    st.markdown("---")
    st.markdown("### Production Zone Detail Cards")

    # Grid of Zone Cards
    cols = st.columns(2)
    for idx, z in enumerate(zones):
        target_col = cols[idx % 2]
        with target_col:
            status = z["status"]
            status_color = {
                "NORMAL": "#047857",
                "WARNING": "#b45309",
                "HIGH": "#b91c1c",
                "INACTIVE": "#64748b",
            }.get(status, "#64748b")

            status_bg = {
                "NORMAL": "#ecfdf5",
                "WARNING": "#fefce8",
                "HIGH": "#fef2f2",
                "INACTIVE": "#f1f5f9",
            }.get(status, "#f1f5f9")

            meters_html = "".join(
                f"<li style='margin-bottom: 2px;'>{m['meter_name']}: <strong>{m['kwh']:,.1f} kWh</strong> ({m['status']})</li>"
                for m in z["meters"]
            ) if z["meters"] else "<li style='color: #94a3b8;'>No meters linked</li>"

            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #1e293b;">{z['name']}</div>
                            <div style="font-size: 0.82rem; color: #64748b;">{z['section']} &bull; {z['building']}</div>
                        </div>
                        <span style="background: {status_bg}; color: {status_color}; border: 1px solid {status_color}40; padding: 2px 8px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700;">
                            {status}
                        </span>
                    </div>
                    <div style="display: flex; gap: 24px; margin: 12px 0; background: #f8fafc; padding: 10px 14px; border-radius: 6px;">
                        <div>
                            <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Consumption</div>
                            <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a;">{z['total_kwh']:,.1f} kWh</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Baseline</div>
                            <div style="font-size: 1.25rem; font-weight: 600; color: #64748b;">{z['nominal_kwh']:,.1f} kWh</div>
                        </div>
                        {f'''<div>
                            <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Submeter Share</div>
                            <div style="font-size: 1.25rem; font-weight: 700; color: #2563eb;">{z['percentage']:.1f}%</div>
                        </div>''' if z['zone_id'] != 'main_power' else ''}
                    </div>
                    <div style="font-size: 0.85rem; color: #334155; margin-top: 8px;">
                        <strong>Connected Meters ({len(z['meters'])}):</strong>
                        <ul style="margin: 4px 0 0 0; padding-left: 20px; font-size: 0.82rem; color: #475569;">
                            {meters_html}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

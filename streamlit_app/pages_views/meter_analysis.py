"""
Meter Analysis and Ranking Deep-Dive View for EnergyAutomation Streamlit BI.
Provides Pareto analysis, consumption ranking filters, and individual equipment drilldowns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics


def render_meter_analysis_view(analytics: EnergyAnalytics) -> None:
    """Renders the meter ranking and drill-down tab."""
    st.subheader("Submeter Energy Rankings & Pareto Analysis")

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    rankings = analytics.get_meter_rankings(include_incomer=False)
    if rankings.empty:
        st.warning("No submeter records found.")
        return

    # Filter by Top 5 / Top 10 / All
    view_filter = st.radio(
        "Display Filter:",
        options=["Top 5 Consumers", "Top 10 Consumers", "All Submeters"],
        horizontal=True,
        key="meter_rank_filter",
    )

    limit = 5 if "5" in view_filter else (10 if "10" in view_filter else len(rankings))
    disp_rankings = rankings.head(limit)

    col_pareto, col_table = st.columns([7, 5])

    with col_pareto:
        st.markdown("### Pareto Consumption Curve")
        # Dual-axis chart: Bars for consumption, line for cumulative %
        fig_pareto = go.Figure()

        fig_pareto.add_trace(
            go.Bar(
                x=rankings["Meter"],
                y=rankings["Total kWh"],
                name="Total kWh",
                marker_color="#3b82f6",
                yaxis="y",
                hovertemplate="<b>%{x}</b><br>Total: %{y:,.1f} kWh<extra></extra>",
            )
        )

        fig_pareto.add_trace(
            go.Scatter(
                x=rankings["Meter"],
                y=rankings["Cumulative %"],
                name="Cumulative %",
                mode="lines+markers",
                line=dict(color="#ef4444", width=2.5),
                yaxis="y2",
                hovertemplate="Cumulative: %{y:.1f}%<extra></extra>",
            )
        )

        # Reference 80% line
        fig_pareto.add_hline(
            y=80,
            yref="y2",
            line_dash="dot",
            line_color="#64748b",
            annotation_text="80% Threshold",
            annotation_position="bottom right",
        )

        fig_pareto.update_layout(
            margin=dict(l=20, r=20, t=30, b=80),
            height=380,
            xaxis=dict(tickangle=-40),
            yaxis=dict(title="Total Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

    with col_table:
        st.markdown(f"### {view_filter}")
        st.dataframe(
            disp_rankings[["Meter", "Total kWh", "Daily Avg kWh", "Share %", "Cumulative %"]],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # Section 2: Individual Meter Drill-Down
    st.markdown("### Single Equipment Drill-Down")

    selected_meter = st.selectbox(
        "Select Machine / Meter for Deep-Dive Analysis:",
        options=analytics.meter_cols,
        key="meter_drilldown_selector",
    )

    if selected_meter and selected_meter in analytics.df.columns:
        m_series = analytics.df[selected_meter].dropna()
        date_series = analytics.df.loc[m_series.index, analytics.date_col]

        tot = float(m_series.sum()) if not m_series.empty else 0.0
        avg = float(m_series.mean()) if not m_series.empty else 0.0
        p_max = float(m_series.max()) if not m_series.empty else 0.0
        p_min = float(m_series.min()) if not m_series.empty else 0.0
        std = float(m_series.std()) if len(m_series) > 1 else 0.0

        m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
        m_c1.metric("Total Consumption", f"{tot:,.1f} kWh")
        m_c2.metric("Daily Average", f"{avg:,.1f} kWh")
        m_c3.metric("Peak Day", f"{p_max:,.1f} kWh")
        m_c4.metric("Minimum Day", f"{p_min:,.1f} kWh")
        m_c5.metric("Std Deviation", f"{std:,.1f} kWh")

        # Daily profile bar chart
        fig_m = go.Figure(
            data=[
                go.Bar(
                    x=date_series,
                    y=m_series,
                    marker_color="#0ea5e9",
                    hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{selected_meter}: %{{y:,.1f}} kWh<extra></extra>",
                )
            ]
        )
        fig_m.add_hline(
            y=avg,
            line_dash="dash",
            line_color="#f59e0b",
            annotation_text=f"Average ({avg:.1f} kWh)",
            annotation_position="top left",
        )
        fig_m.update_layout(
            title=f"Daily Consumption Profile: {selected_meter}",
            margin=dict(l=20, r=20, t=40, b=20),
            height=300,
            xaxis=dict(title="Date"),
            yaxis=dict(title="Active Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
        )
        st.plotly_chart(fig_m, use_container_width=True)

"""
Energy Trends and Time-Series Analytics View for EnergyAutomation Streamlit BI.
Provides date range filtering, multi-meter overlay comparisons, cumulative energy tracking,
and weekday vs weekend operational analysis.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics


def render_energy_trends_view(analytics: EnergyAnalytics) -> None:
    """Renders the interactive energy trends tab."""
    st.subheader("Energy Trends & Operational Patterns")

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    df = analytics.df.copy()
    date_col = analytics.date_col
    total_col = analytics.total_col

    # Filter controls
    f_col1, f_col2 = st.columns([4, 8])

    min_date = df[date_col].min()
    max_date = df[date_col].max()

    with f_col1:
        date_range = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="trends_date_range",
        )

    # Filter dataframe by dates
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
        filtered_df = df[(df[date_col] >= start_d) & (df[date_col] <= end_d)].copy()
    else:
        filtered_df = df.copy()

    with f_col2:
        default_meters = [analytics.submeter_cols[0]] if analytics.submeter_cols else []
        if len(analytics.submeter_cols) > 1:
            default_meters.append(analytics.submeter_cols[1])

        selected_meters = st.multiselect(
            "Select Meters to Compare",
            options=analytics.meter_cols,
            default=default_meters,
            key="trends_meter_selector",
        )

    if filtered_df.empty:
        st.warning("No data found for the selected date range.")
        return

    # Section 1: Multi-Meter Trend Comparison
    st.markdown("### Daily Consumption Overlay")
    fig_trends = go.Figure()

    # Always plot total or incomer if desired
    fig_trends.add_trace(
        go.Scatter(
            x=filtered_df[date_col],
            y=filtered_df[total_col],
            mode="lines+markers",
            name="Plant Total",
            line=dict(color="#2563eb", width=3),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Total: %{y:,.1f} kWh<extra></extra>",
        )
    )

    palette = px.colors.qualitative.Dark24
    for idx, meter in enumerate(selected_meters):
        if meter in filtered_df.columns:
            color = palette[idx % len(palette)]
            fig_trends.add_trace(
                go.Scatter(
                    x=filtered_df[date_col],
                    y=filtered_df[meter],
                    mode="lines+markers",
                    name=meter,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{meter}: %{{y:,.1f}} kWh<extra></extra>",
                )
            )

    fig_trends.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=380,
        xaxis=dict(title="Date", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="Active Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    st.plotly_chart(fig_trends, use_container_width=True)

    # Section 2: Cumulative Energy Progression & Weekday Analysis
    sec_left, sec_right = st.columns(2)

    with sec_left:
        st.markdown("### Cumulative Energy Growth")
        cum_df = filtered_df.copy()
        cum_df["_cum_total"] = cum_df[total_col].cumsum()

        fig_cum = go.Figure()
        fig_cum.add_trace(
            go.Scatter(
                x=cum_df[date_col],
                y=cum_df["_cum_total"],
                mode="lines",
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.1)",
                line=dict(color="#2563eb", width=2.5),
                name="Cumulative Total",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Cumulative: %{y:,.1f} kWh<extra></extra>",
            )
        )
        fig_cum.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=320,
            xaxis=dict(title="Date", showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="Cumulative kWh", showgrid=True, gridcolor="#f1f5f9"),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    with sec_right:
        st.markdown("### Day-of-Week Operational Profile")
        ww_stats = analytics.get_weekday_vs_weekend()
        by_day = ww_stats.get("by_day", {})

        if by_day:
            days_labels = list(by_day.keys())
            days_values = [v["avg_kwh"] for v in by_day.values()]

            colors = ["#3b82f6" if d not in ("Saturday", "Sunday") else "#f59e0b" for d in days_labels]

            fig_dow = go.Figure(
                data=[
                    go.Bar(
                        x=days_labels,
                        y=days_values,
                        marker_color=colors,
                        hovertemplate="<b>%{x}</b><br>Avg: %{y:,.1f} kWh<extra></extra>",
                    )
                ]
            )
            fig_dow.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=320,
                xaxis=dict(title="Day of Week"),
                yaxis=dict(title="Average Daily kWh", showgrid=True, gridcolor="#f1f5f9"),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
            )
            st.plotly_chart(fig_dow, use_container_width=True)

            st.markdown(
                f"""
                <div style="font-size: 0.85rem; color: #475569; text-align: center;">
                    Weekday Avg: <strong>{ww_stats['weekday_avg']:,.1f} kWh</strong> &bull;
                    Weekend Avg: <strong>{ww_stats['weekend_avg']:,.1f} kWh</strong> &bull;
                    Variance: <strong>{ww_stats['difference_pct']:+.1f}%</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

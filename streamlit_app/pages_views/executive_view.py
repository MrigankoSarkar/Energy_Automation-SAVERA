"""
Executive Summary View for EnergyAutomation Streamlit BI.
Presents high-level KPIs, top energy consumers, and plant-wide consumption balance.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics
from streamlit_app.components.kpi_cards import render_kpi_cards


def render_executive_view(analytics: EnergyAnalytics) -> None:
    """Renders the executive summary tab."""
    kpis = analytics.get_executive_kpis()
    render_kpi_cards(kpis)

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    st.markdown("---")

    col_chart, col_donut = st.columns([7, 5])

    with col_chart:
        st.subheader("Daily Plant Energy Consumption (kWh)")
        df = analytics.df.copy()
        date_col = analytics.date_col
        total_col = analytics.total_col

        fig_daily = go.Figure()

        # Bar series for daily consumption
        fig_daily.add_trace(
            go.Bar(
                x=df[date_col],
                y=df[total_col],
                name="Daily Total",
                marker_color="#3b82f6",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Total: %{y:,.1f} kWh<extra></extra>",
            )
        )

        # 7-day Moving Average if enough rows
        if len(df) >= 4:
            df["_ma7"] = df[total_col].rolling(window=min(7, len(df)), min_periods=1).mean()
            fig_daily.add_trace(
                go.Scatter(
                    x=df[date_col],
                    y=df["_ma7"],
                    name="Moving Avg",
                    line=dict(color="#f59e0b", width=3, dash="dash"),
                    hovertemplate="Moving Avg: %{y:,.1f} kWh<extra></extra>",
                )
            )

        fig_daily.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=340,
            xaxis=dict(title="Date", showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
        )
        st.plotly_chart(fig_daily, use_container_width=True)

    with col_donut:
        st.subheader("Top Consumers Share")
        rankings = analytics.get_meter_rankings()

        if not rankings.empty:
            # Group top 5 and aggregate others
            top5 = rankings.head(5).copy()
            others_val = rankings.iloc[5:]["Total kWh"].sum() if len(rankings) > 5 else 0.0

            donut_labels = list(top5["Meter"])
            donut_values = list(top5["Total kWh"])

            if others_val > 0:
                donut_labels.append("Other Submeters")
                donut_values.append(others_val)

            fig_donut = go.Figure(
                data=[
                    go.Pie(
                        labels=donut_labels,
                        values=donut_values,
                        hole=0.55,
                        textinfo="percent",
                        hoverinfo="label+value+percent",
                        marker=dict(colors=px.colors.qualitative.Prism),
                    )
                ]
            )
            fig_donut.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                height=340,
                showlegend=True,
                legend=dict(orientation="v", x=1.05, y=0.5),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # Secondary row: Incomer balance & Quick top table
    sec_left, sec_right = st.columns([6, 6])

    with sec_left:
        st.subheader("Submeter Energy Ranking")
        if not rankings.empty:
            st.dataframe(
                rankings[["Meter", "Total kWh", "Daily Avg kWh", "Share %"]].head(8),
                use_container_width=True,
                hide_index=True,
            )

    with sec_right:
        st.subheader("Incomer vs Submeter Reconciliation")
        incomer_col = analytics.incomer_col
        if incomer_col and incomer_col in analytics.df.columns:
            latest_row = analytics.df.iloc[-1]
            inc_val = latest_row[incomer_col]
            sub_sum = latest_row[analytics.submeter_cols].sum(skipna=True)
            diff = (inc_val - sub_sum) if pd.notna(inc_val) else 0.0
            diff_pct = (diff / inc_val * 100.0) if pd.notna(inc_val) and inc_val > 0 else 0.0

            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #1e293b; margin-bottom: 12px;">
                        Latest Day ({kpis.latest_date}):
                    </div>
                    <table style="width: 100%; font-size: 0.9rem; line-height: 2;">
                        <tr>
                            <td style="color: #64748b;">Main Incomer ({incomer_col}):</td>
                            <td style="text-align: right; font-weight: 700; color: #0f172a;">{inc_val:,.2f} kWh</td>
                        </tr>
                        <tr>
                            <td style="color: #64748b;">Submeters Aggregate Sum:</td>
                            <td style="text-align: right; font-weight: 700; color: #0f172a;">{sub_sum:,.2f} kWh</td>
                        </tr>
                        <tr style="border-top: 1px solid #e2e8f0;">
                            <td style="color: #64748b;">Distribution Balance Difference:</td>
                            <td style="text-align: right; font-weight: 700; color: {'#10b981' if abs(diff_pct) < 10 else '#f59e0b'};">
                                {diff:+,.2f} kWh ({diff_pct:+.1f}%)
                            </td>
                        </tr>
                    </table>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 12px;">
                        <em>Difference reflects auxiliary loads, transformer line losses, or unmonitored branch panels.</em>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Incomer meter not designated in current workbook configuration.")

"""
Executive & Business Intelligence View for Plotly Dash.
Designed for directors, plant managers, and business teams.
"""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc


def build_kpi_card(title: str, value: str, subtitle: str, color_accent: str = "#38bdf8") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="card-subtitle text-muted mb-1", style={"fontSize": "0.85rem", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
            html.H3(value, className="card-title fw-bold mb-1", style={"color": "#ffffff"}),
            html.Small(subtitle, style={"color": color_accent, "fontWeight": "600"}),
        ]),
        style={
            "backgroundColor": "#1e293b",
            "border": "1px solid #334155",
            "borderRadius": "8px",
            "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        },
        className="mb-3",
    )


def create_executive_view(summary: Dict[str, Any], df: pd.DataFrame, feeders: list) -> html.Div:
    if not summary or not summary.get("is_active") or df.empty:
        return html.Div([
            dbc.Alert("No active telemetry available in production workbook. Please run automation or verify data file.", color="warning")
        ])

    latest_kwh = summary.get("latest_kwh", 0.0) or 0.0
    latest_date = summary.get("latest_date", "—")
    prev_kwh = summary.get("previous_kwh")
    prev_date = summary.get("previous_date", "—")
    change_pct = summary.get("change_pct")
    mtd_kwh = summary.get("mtd_kwh", 0.0) or 0.0
    avg_kwh = summary.get("avg_daily_kwh", 0.0) or 0.0

    pct_str = f"{change_pct:+.1f}% vs previous" if change_pct is not None else "Baseline comparison"
    pct_color = "#4ade80" if (change_pct is not None and change_pct <= 0) else "#fbbf24"

    cards_row = dbc.Row([
        dbc.Col(build_kpi_card("Latest Shift Energy", f"{latest_kwh:,.2f} kWh", f"Report Date: {latest_date}", "#38bdf8"), md=3, sm=6),
        dbc.Col(build_kpi_card("Previous Shift", f"{prev_kwh:,.2f} kWh" if prev_kwh else "—", pct_str, pct_color), md=3, sm=6),
        dbc.Col(build_kpi_card("Month-To-Date (MTD)", f"{mtd_kwh:,.2f} kWh", "Cumulative Shift Energy", "#a855f7"), md=3, sm=6),
        dbc.Col(build_kpi_card("Average Daily Load", f"{avg_kwh:,.2f} kWh", f"Active Feeders: {summary.get('active_meters_count', 0)} / {summary.get('total_meters_count', 0)}", "#4ade80"), md=3, sm=6),
    ], className="mb-4")

    # Shift-by-Shift Trend Chart
    df_sorted = df.sort_values("Date").copy()
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=df_sorted["Date"].dt.strftime("%d-%b"),
        y=df_sorted["Total Active Energy"],
        name="Daily Shift Energy (kWh)",
        marker=dict(color="#3b82f6", opacity=0.85),
    ))
    fig_trend.add_trace(go.Scatter(
        x=df_sorted["Date"].dt.strftime("%d-%b"),
        y=df_sorted["Total Active Energy"],
        name="Consumption Trend",
        mode="lines+markers",
        line=dict(color="#60a5fa", width=2.5),
        marker=dict(size=6, color="#ffffff"),
    ))

    # Reference target line
    target_kwh = 9206.83
    fig_trend.add_hline(
        y=target_kwh,
        line_dash="dot",
        line_color="#f59e0b",
        annotation_text=f"Target Baseline ({target_kwh:,.0f} kWh)",
        annotation_position="top right",
    )

    fig_trend.update_layout(
        title="Shift-by-Shift Energy Telemetry Trend vs Baseline",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#334155", title="Report Date"),
        yaxis=dict(gridcolor="#334155", title="Total Active Energy (kWh)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )

    # Feeder Share Donut Chart
    feeder_items = [f for f in feeders if f.get("latest_kwh") and f["latest_kwh"] > 0]
    fig_donut = go.Figure()
    if feeder_items:
        names = [f["feeder_name"] for f in feeder_items]
        values = [f["latest_kwh"] for f in feeder_items]
        fig_donut.add_trace(go.Pie(
            labels=names,
            values=values,
            hole=0.45,
            marker=dict(colors=px.colors.qualitative.Plotly),
            textinfo="label+percent",
            hoverinfo="label+value+percent",
        ))
    fig_donut.update_layout(
        title="Active Feeder Share Distribution",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0"),
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
        height=380,
    )

    charts_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_trend, config={"displayModeBar": False})), style={"backgroundColor": "#1e293b", "border": "1px solid #334155"}), md=8),
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_donut, config={"displayModeBar": False})), style={"backgroundColor": "#1e293b", "border": "1px solid #334155"}), md=4),
    ], className="mb-4")

    return html.Div([
        html.H4("Executive Overview & Macro Indicators", className="fw-bold mb-3", style={"color": "#f8fafc"}),
        cards_row,
        charts_row,
    ])

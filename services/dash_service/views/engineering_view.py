"""
Engineering Operational Analysis View for Plotly Dash.
Granular telemetry grids, load balancing, and threshold diagnostics for plant engineers.
"""

from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc


def create_engineering_view(df: pd.DataFrame, feeders: List[Dict[str, Any]]) -> html.Div:
    if df.empty:
        return html.Div([
            dbc.Alert("No telemetry data loaded for engineering analysis.", color="warning")
        ])

    # Feeder Load Comparison Chart (Ranked)
    valid_feeders = [f for f in feeders if f.get("latest_kwh") is not None]
    sorted_feeders = sorted(valid_feeders, key=lambda x: x.get("latest_kwh", 0), reverse=True)

    fig_bars = go.Figure()
    if sorted_feeders:
        names = [f["feeder_name"] for f in sorted_feeders]
        loads = [f["latest_kwh"] for f in sorted_feeders]
        colors = ["#3b82f6" if "EB" not in n and "INCOMER" not in n.upper() else "#f59e0b" for n in names]

        fig_bars.add_trace(go.Bar(
            x=names,
            y=loads,
            marker_color=colors,
            text=[f"{v:,.1f}" for v in loads],
            textposition="auto",
        ))

    fig_bars.update_layout(
        title="Feeder Active Energy Ranking (Latest Shift)",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#334155", title="Feeder Tag", tickangle=-35),
        yaxis=dict(gridcolor="#334155", title="Active Energy (kWh)"),
        margin=dict(l=40, r=20, t=60, b=80),
        height=380,
    )

    # Prepare DataFrame for DataTable
    df_table = df.copy()
    if "Date" in df_table.columns:
        df_table["Date"] = df_table["Date"].dt.strftime("%Y-%m-%d")
    if "RowIndex" in df_table.columns:
        df_table = df_table.drop(columns=["RowIndex"])

    # Round all float columns
    float_cols = df_table.select_dtypes(include=["float64", "float32"]).columns
    for c in float_cols:
        df_table[c] = df_table[c].apply(lambda v: f"{v:,.2f}" if pd.notna(v) else "—")

    # Construct columns config for dash_table
    columns = [{"name": i, "id": i} for i in df_table.columns]

    table_card = dbc.Card(
        dbc.CardBody([
            html.H5("Detailed Feeder Telemetry Matrix (Shift-by-Shift)", className="card-title fw-bold mb-3", style={"color": "#f8fafc"}),
            dash_table.DataTable(
                id="engineering-datatable",
                columns=columns,
                data=df_table.to_dict("records"),
                page_size=15,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#0f172a",
                    "color": "#93c5fd",
                    "fontWeight": "bold",
                    "border": "1px solid #334155",
                    "textAlign": "center",
                },
                style_data={
                    "backgroundColor": "#1e293b",
                    "color": "#f8fafc",
                    "border": "1px solid #334155",
                    "fontSize": "0.85rem",
                    "textAlign": "center",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#243147",
                    },
                    {
                        "if": {"column_id": "Total Active Energy"},
                        "fontWeight": "bold",
                        "color": "#38bdf8",
                    },
                ],
            ),
        ]),
        style={"backgroundColor": "#1e293b", "border": "1px solid #334155"},
        className="mb-4",
    )

    return html.Div([
        html.H4("Engineering Telemetry & Feeder Analysis", className="fw-bold mb-3", style={"color": "#f8fafc"}),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_bars, config={"displayModeBar": False})), style={"backgroundColor": "#1e293b", "border": "1px solid #334155"}, className="mb-4"),
        table_card,
    ])

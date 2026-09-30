"""
Plotly Dash Business & Engineering Management BI Microservice (Port 8050).
Replaces legacy Streamlit dashboard with high-performance Plotly Dash application.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dash
from dash import Input, Output, State, dcc, html
import dash_bootstrap_components as dbc

from services.dash_service.config import load_dash_config
from services.dash_service.data_loader import DashDataLoader
from services.dash_service.views.data_quality_view import create_data_quality_view
from services.dash_service.views.engineering_view import create_engineering_view
from services.dash_service.views.executive_view import create_executive_view

config = load_dash_config()
loader = DashDataLoader()

# Initialize Dash application
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title=config.app_title,
    suppress_callback_exceptions=True,
)
server = app.server

# Top Navigation Bar
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Span("⚡", className="fs-3 me-2"),
                html.Span(f"{config.company_name} — Energy Intelligence BI", className="navbar-brand fw-bold fs-5 text-white"),
                html.Span(f"• {config.plant_name}", className="text-muted ms-2 fs-6 d-none d-md-inline"),
            ], className="d-flex align-items-center"),
        ], align="center", className="g-0"),
        dbc.Row([
            dbc.Col([
                dbc.Button("🔄 Sync / Refresh", id="btn-sync-refresh", color="primary", size="sm", className="me-2"),
                html.Span(id="sync-timestamp", className="text-muted small align-middle"),
            ], className="d-flex align-items-center"),
        ], align="center", className="g-0"),
    ], fluid=True),
    color="#0f172a",
    dark=True,
    className="border-bottom border-secondary mb-3 py-2",
)

# Main Application Layout
app.layout = html.Div([
    navbar,
    dcc.Interval(id="auto-refresh-interval", interval=60 * 1000, n_intervals=0),
    dbc.Container([
        dbc.Tabs(
            id="dash-tabs",
            active_tab="tab-executive",
            children=[
                dbc.Tab(label="📊 Executive BI Overview", tab_id="tab-executive", label_style={"cursor": "pointer"}),
                dbc.Tab(label="⚙️ Engineering Telemetry Grid", tab_id="tab-engineering", label_style={"cursor": "pointer"}),
                dbc.Tab(label="🔍 Data Quality & Reconciliation", tab_id="tab-quality", label_style={"cursor": "pointer"}),
            ],
            className="mb-4",
        ),
        html.Div(id="tab-content-container"),
    ], fluid=True, style={"maxWidth": "1600px", "paddingBottom": "40px"}),
], style={"backgroundColor": "#0b0f19", "minHeight": "100vh", "color": "#f8fafc"})


@app.callback(
    Output("tab-content-container", "children"),
    Output("sync-timestamp", "children"),
    Input("dash-tabs", "active_tab"),
    Input("btn-sync-refresh", "n_clicks"),
    Input("auto-refresh-interval", "n_intervals"),
)
def render_tab_content(active_tab: str, n_clicks: int, n_intervals: int):
    from datetime import datetime
    force_refresh = bool(n_clicks)
    summary = loader.get_summary(force_refresh=force_refresh)
    df = loader.get_dataframe(force_refresh=force_refresh)
    feeders = loader.get_feeders()
    quality = loader.get_data_quality()

    time_str = f"Updated: {datetime.now().strftime('%H:%M:%S')}"

    if active_tab == "tab-executive":
        return create_executive_view(summary, df, feeders), time_str
    elif active_tab == "tab-engineering":
        return create_engineering_view(df, feeders), time_str
    elif active_tab == "tab-quality":
        return create_data_quality_view(quality), time_str

    return html.Div([dbc.Alert("Tab not found.", color="danger")]), time_str


def main():
    port = int(os.getenv("DASH_PORT", str(config.port)))
    print(f"Starting Plotly Dash Management BI Microservice on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()

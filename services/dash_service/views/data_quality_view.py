"""
Data Quality, Telemetry Freshness & Audit Reconciliation View for Plotly Dash.
"""

from __future__ import annotations

from typing import Any, Dict
from dash import html
import dash_bootstrap_components as dbc


def create_data_quality_view(quality: Dict[str, Any]) -> html.Div:
    if not quality:
        return html.Div([dbc.Alert("No data quality metrics available.", color="warning")])

    freshness = quality.get("freshness_status", "UNKNOWN")
    latest_date = quality.get("latest_report_date", "—")
    missing_dates = quality.get("missing_dates", [])
    discrepancies = quality.get("discrepancies", [])
    reconciled = quality.get("formula_reconciliation_ok", True)

    fresh_color = "success" if freshness == "UP_TO_DATE" else "warning"

    overview_card = dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("TELEMETRY INGESTION STATUS", className="text-muted mb-1"),
                    dbc.Badge(freshness, color=fresh_color, className="fs-6 px-3 py-2"),
                ], md=4),
                dbc.Col([
                    html.H6("LATEST VERIFIED SHIFT", className="text-muted mb-1"),
                    html.H4(latest_date, className="fw-bold text-white"),
                ], md=4),
                dbc.Col([
                    html.H6("FORMULA INTEGRITY AUDIT", className="text-muted mb-1"),
                    dbc.Badge("100% RECONCILED" if reconciled else f"{len(discrepancies)} DISCREPANCIES", color="success" if reconciled else "danger", className="fs-6 px-3 py-2"),
                ], md=4),
            ])
        ]),
        style={"backgroundColor": "#1e293b", "border": "1px solid #334155"},
        className="mb-4",
    )

    # Missing Dates List
    missing_items = []
    if missing_dates:
        for md in missing_dates:
            missing_items.append(html.Li(f"Calendar Gap: {md}", className="text-warning mb-1"))
    else:
        missing_items.append(html.Li("Zero calendar gaps detected across the active ingestion window.", className="text-success"))

    gaps_card = dbc.Card(
        dbc.CardBody([
            html.H5("Calendar Gap & Weekend Detection", className="card-title fw-bold text-white mb-3"),
            html.P("Identifies missing daily NBSense reports across the 30-day window:", className="text-muted"),
            html.Ul(missing_items, style={"fontSize": "0.9rem"}),
        ]),
        style={"backgroundColor": "#1e293b", "border": "1px solid #334155"},
        className="mb-4",
    )

    # Reconciliation Audit Table
    discrepancy_rows = []
    if discrepancies:
        for disc in discrepancies:
            discrepancy_rows.append(html.Tr([
                html.Td(disc.get("date")),
                html.Td(f"{disc.get('feeder_sum', 0):,.2f}"),
                html.Td(f"{disc.get('recorded_total', 0):,.2f}"),
                html.Td(f"{disc.get('diff', 0):,.2f}", style={"color": "#f87171"}),
            ]))
    else:
        discrepancy_rows.append(html.Tr([
            html.Td("All dates", colSpan=4, className="text-center text-success py-3", style={"fontStyle": "italic"}),
        ]))

    reconciliation_table = dbc.Card(
        dbc.CardBody([
            html.H5("Mathematical Reconciliation Ledger (Sum of Feeders vs Row 18 Total)", className="card-title fw-bold text-white mb-3"),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Date"),
                    html.Th("Sum of Feeder Columns (kWh)"),
                    html.Th("Workbook Total Active Energy (kWh)"),
                    html.Th("Absolute Variance (kWh)"),
                ], style={"backgroundColor": "#0f172a", "color": "#93c5fd"})),
                html.Tbody(discrepancy_rows, style={"backgroundColor": "#1e293b", "color": "#f8fafc"}),
            ], bordered=True, responsive=True, hover=True),
        ]),
        style={"backgroundColor": "#1e293b", "border": "1px solid #334155"},
        className="mb-4",
    )

    return html.Div([
        html.H4("Data Quality, Freshness & Audit Reconciliation", className="fw-bold mb-3", style={"color": "#f8fafc"}),
        overview_card,
        dbc.Row([
            dbc.Col(gaps_card, md=6),
            dbc.Col(reconciliation_table, md=6),
        ]),
    ])

"""
Unit tests for Plotly Dash BI Microservice (services.dash_service).
Tests data loading, local fallback, view construction, and UI component generation.
"""

from __future__ import annotations

import pandas as pd
import pytest
from dash import html
import dash_bootstrap_components as dbc

from services.dash_service.data_loader import DashDataLoader
from services.dash_service.views.executive_view import build_kpi_card, create_executive_view
from services.dash_service.views.engineering_view import create_engineering_view
from services.dash_service.views.data_quality_view import create_data_quality_view


@pytest.fixture
def data_loader() -> DashDataLoader:
    return DashDataLoader(api_base_url="http://127.0.0.1:9999")  # Unused port forces local fallback


def test_data_loader_local_fallback_summary(data_loader: DashDataLoader):
    summary = data_loader.get_summary()
    assert isinstance(summary, dict)
    assert "is_active" in summary
    assert "latest_kwh" in summary
    assert "active_meters_count" in summary
    assert "workbook_path" in summary
    if summary["is_active"]:
        assert summary["latest_kwh"] > 0
        assert summary["latest_date"] is not None


def test_data_loader_local_fallback_dataframe(data_loader: DashDataLoader):
    df = data_loader.get_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Date" in df.columns
    # Invariant: Date must be datetime type
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    # Invariant: Total Active Energy or Incomer must be present
    assert any("Total" in col or "Incomer" in col for col in df.columns)


def test_data_loader_local_fallback_feeders(data_loader: DashDataLoader):
    feeders = data_loader.get_feeders()
    assert isinstance(feeders, list)
    assert len(feeders) > 0
    first = feeders[0]
    assert "feeder_name" in first
    assert "status" in first


def test_data_loader_local_fallback_quality(data_loader: DashDataLoader):
    quality = data_loader.get_data_quality()
    assert isinstance(quality, dict)
    assert "freshness_status" in quality
    assert "formula_reconciliation_ok" in quality


def test_build_kpi_card():
    card = build_kpi_card(
        title="Active Energy",
        value="12,450.00 kWh",
        subtitle="+2.4% vs previous",
        color_accent="#38bdf8",
    )
    assert isinstance(card, dbc.Card)


def test_create_executive_view(data_loader: DashDataLoader):
    summary = data_loader.get_summary()
    df = data_loader.get_dataframe()
    feeders = data_loader.get_feeders()

    view = create_executive_view(summary, df, feeders)
    assert isinstance(view, html.Div)

    # Test empty / inactive fallback
    empty_view = create_executive_view({}, pd.DataFrame(), [])
    assert isinstance(empty_view, html.Div)


def test_create_engineering_view(data_loader: DashDataLoader):
    df = data_loader.get_dataframe()
    feeders = data_loader.get_feeders()

    view = create_engineering_view(df, feeders)
    assert isinstance(view, html.Div)

    # Empty data fallback
    empty_view = create_engineering_view(pd.DataFrame(), [])
    assert isinstance(empty_view, html.Div)


def test_create_data_quality_view(data_loader: DashDataLoader):
    quality = data_loader.get_data_quality()

    view = create_data_quality_view(quality)
    assert isinstance(view, html.Div)

    # Empty data fallback
    empty_view = create_data_quality_view({})
    assert isinstance(empty_view, html.Div)

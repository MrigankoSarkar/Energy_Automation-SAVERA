"""
Configuration loader for EnergyAutomation Streamlit BI Dashboard.
Supports Streamlit secrets, environment variables, settings.json, and safe production defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Root path of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_JSON_PATH = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_EXCEL_FILENAME = "Test_BI_Analysis_Report_2026.xlsx"
DEFAULT_WORKSHEET = "EMS Monitoring Report"
LOGO_PATH = PROJECT_ROOT / "assets" / "savera-logo.jpg"


@dataclass(frozen=True)
class DashboardConfig:
    """Dashboard runtime configuration."""
    data_source: str  # 'cloud' or 'local'
    cloud_provider: str  # 'google_drive', 'onedrive', 'dropbox', 'direct_url', 'auto', 'local'
    excel_url: str
    local_excel_path: str
    worksheet_name: str
    header_row: int
    date_column: int
    first_data_row: int
    total_column: int
    cache_ttl_seconds: int
    refresh_interval_seconds: int
    company_name: str
    plant_name: str
    app_title: str
    timezone: str
    logo_path: Optional[str] = None


def _load_settings_json() -> Dict[str, Any]:
    """Reads settings.json if it exists."""
    if SETTINGS_JSON_PATH.exists():
        try:
            with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def load_config() -> DashboardConfig:
    """
    Loads DashboardConfig prioritizing:
    1. Streamlit st.secrets (if available)
    2. Environment variables
    3. config/settings.json
    4. Production defaults
    """
    secrets: Dict[str, Any] = {}
    try:
        import streamlit as st
        # st.secrets behaves like a dictionary
        secrets = dict(st.secrets)
    except Exception:
        pass

    settings = _load_settings_json()
    excel_settings = settings.get("excel", {})

    # Excel Path resolution
    default_local_path = str(PROJECT_ROOT / excel_settings.get("file", DEFAULT_EXCEL_FILENAME))
    local_path = (
        secrets.get("LOCAL_EXCEL_PATH")
        or os.environ.get("ENERGY_LOCAL_EXCEL_PATH")
        or default_local_path
    )
    # Ensure local path is absolute
    local_path_obj = Path(local_path)
    if not local_path_obj.is_absolute():
        local_path = str((PROJECT_ROOT / local_path_obj).resolve())

    # Cloud URL
    excel_url = (
        secrets.get("EXCEL_URL")
        or os.environ.get("ENERGY_EXCEL_URL")
        or ""
    ).strip()

    # Data Source: Default to cloud if EXCEL_URL is provided, else local
    default_source = "cloud" if excel_url else "local"
    data_source = (
        secrets.get("DATA_SOURCE")
        or os.environ.get("ENERGY_DATA_SOURCE")
        or default_source
    ).strip().lower()

    # Cloud Provider
    cloud_provider = (
        secrets.get("CLOUD_PROVIDER")
        or os.environ.get("ENERGY_CLOUD_PROVIDER")
        or "auto"
    ).strip().lower()

    # Intervals
    cache_ttl = int(
        secrets.get("CACHE_TTL")
        or os.environ.get("ENERGY_CACHE_TTL")
        or 300
    )
    refresh_interval = int(
        secrets.get("REFRESH_INTERVAL")
        or os.environ.get("ENERGY_REFRESH_INTERVAL")
        or 300
    )

    # Branding & App titles
    company_name = settings.get("company", "Savera MS")
    plant_name = settings.get("plant", "Manufacturing Plant")
    app_title = f"{company_name} — Energy Intelligence & Executive BI"
    timezone = "Asia/Kolkata"

    logo = str(LOGO_PATH) if LOGO_PATH.exists() else None

    return DashboardConfig(
        data_source=data_source,
        cloud_provider=cloud_provider,
        excel_url=excel_url,
        local_excel_path=local_path,
        worksheet_name=excel_settings.get("worksheet", DEFAULT_WORKSHEET),
        header_row=excel_settings.get("header_row", 3),
        date_column=excel_settings.get("date_column", 2),
        first_data_row=excel_settings.get("first_data_row", 5),
        total_column=excel_settings.get("total_column", 18),
        cache_ttl_seconds=cache_ttl,
        refresh_interval_seconds=refresh_interval,
        company_name=company_name,
        plant_name=plant_name,
        app_title=app_title,
        timezone=timezone,
        logo_path=logo,
    )

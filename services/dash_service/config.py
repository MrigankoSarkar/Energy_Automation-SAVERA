"""
Configuration loader for Plotly Dash BI Microservice.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class DashConfig:
    port: int = 8050
    host: str = "0.0.0.0"
    app_title: str = "Savera MS — Energy Intelligence & Executive BI"
    company_name: str = "Savera MS"
    plant_name: str = "Chennai Manufacturing Plant"
    data_service_url: str = "http://127.0.0.1:8002"
    theme: str = "DARK"


def load_dash_config() -> DashConfig:
    settings_file = REPO_ROOT / "config" / "settings.json"
    cfg = DashConfig()

    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cfg.company_name = raw.get("company", cfg.company_name)
            cfg.plant_name = raw.get("plant", cfg.plant_name)
            dash_section = raw.get("dash", {})
            cfg.port = int(dash_section.get("port", os.getenv("DASH_PORT", "8050")))
        except Exception:
            pass

    return cfg

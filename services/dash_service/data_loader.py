"""
Data loader for Plotly Dash BI Microservice.
Connects via REST API to Data Service with fallback to local provider.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

from services.data_service.provider import TelemetryDataProvider, TelemetrySummary

logger = logging.getLogger("services.dash_service.data_loader")


class DashDataLoader:
    def __init__(self, api_base_url: str = "http://127.0.0.1:8002"):
        self.api_base_url = api_base_url
        self._local_provider = TelemetryDataProvider()

    def get_summary(self, force_refresh: bool = False) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.api_base_url}/api/v1/data/summary", params={"force_refresh": force_refresh}, timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

        # Local fallback
        s = self._local_provider.get_summary(force_refresh=force_refresh)
        from dataclasses import asdict
        return asdict(s)

    def get_dataframe(self, force_refresh: bool = False) -> pd.DataFrame:
        try:
            r = requests.get(f"{self.api_base_url}/api/v1/data/readings", params={"limit": 500}, timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                records = data.get("records", [])
                if records:
                    df = pd.DataFrame(records)
                    if "Date" in df.columns:
                        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                        df = df.sort_values("Date").reset_index(drop=True)
                    return df
        except Exception:
            pass

        # Local fallback
        return self._local_provider.get_daily_dataframe(force_refresh=force_refresh)

    def get_feeders(self) -> List[Dict[str, Any]]:
        try:
            r = requests.get(f"{self.api_base_url}/api/v1/data/feeders", timeout=1.5)
            if r.status_code == 200:
                return r.json().get("feeders", [])
        except Exception:
            pass

        return self._local_provider.get_feeders_catalog()

    def get_data_quality(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.api_base_url}/api/v1/data/quality", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

        return self._local_provider.get_data_quality()

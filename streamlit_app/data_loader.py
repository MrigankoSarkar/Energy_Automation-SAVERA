"""
Data loading and caching orchestration for EnergyAutomation Streamlit BI.
Fetches workbooks via Cloud Storage or Local Storage, caches data with configurable TTL,
tracks data freshness, and provides fallback handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import streamlit as st

from streamlit_app.config import DashboardConfig, load_config
from streamlit_app.cloud_storage.factory import get_cloud_provider
from streamlit_app.data_validator import ParsedWorkbook, WorkbookDataValidator


@dataclass
class LoadedData:
    """Encapsulates parsed workbook, synchronization metadata, and freshness status."""
    parsed: ParsedWorkbook
    metadata: Dict[str, Any]
    freshness_status: str  # "LIVE", "RECENT", "STALE", "UNAVAILABLE"
    freshness_label: str   # Formatted text with colored bullet
    fetched_at: datetime
    error_message: Optional[str] = None


def compute_freshness(fetched_at: datetime, last_modified_str: Optional[str] = None) -> tuple[str, str]:
    """
    Computes data freshness category and human-readable label based on time delta.
    - LIVE: < 15 minutes
    - RECENT: 15 minutes - 2 hours
    - STALE: > 2 hours
    """
    now = datetime.now(timezone.utc)
    target_dt = fetched_at

    # If Last-Modified is available as ISO string, compare against it
    if last_modified_str:
        try:
            # Strip Z or offset for simple parse if needed
            dt_clean = last_modified_str.replace("Z", "+00:00")
            parsed_mod = datetime.fromisoformat(dt_clean)
            if parsed_mod.tzinfo is None:
                parsed_mod = parsed_mod.replace(tzinfo=timezone.utc)
            target_dt = parsed_mod
        except Exception:
            pass

    delta_seconds = (now - target_dt).total_seconds()
    if delta_seconds < 0:
        delta_seconds = 0

    if delta_seconds <= 15 * 60:
        return "LIVE", f"● LIVE ({int(delta_seconds // 60)}m ago)"
    elif delta_seconds <= 2 * 3600:
        return "RECENT", f"● RECENT ({int(delta_seconds // 60)}m ago)"
    else:
        hours = int(delta_seconds // 3600)
        return "STALE", f"● STALE ({hours}h ago)"


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_cached_workbook_bytes(
    data_source: str,
    cloud_provider: str,
    url_or_path: str,
    timeout: int = 25,
) -> tuple[bytes, Dict[str, Any]]:
    """Cached low-level fetcher function with TTL."""
    provider = get_cloud_provider(
        provider_name=cloud_provider if data_source == "cloud" else "local",
        url_or_path=url_or_path,
    )
    return provider.fetch_workbook_bytes(url_or_path, timeout=timeout)


class DataLoader:
    """High-level data loader coordinating fetch, validation, caching, and fallback."""

    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or load_config()
        self.validator = WorkbookDataValidator(
            sheet_name=self.config.worksheet_name,
            header_row=self.config.header_row,
            date_column=self.config.date_column,
            first_data_row=self.config.first_data_row,
            total_column=self.config.total_column,
        )

    def load_data(self, force_refresh: bool = False) -> LoadedData:
        """
        Loads and parses the EMS Excel report.
        If force_refresh is True, the cache is invalidated.
        Falls back to local file if cloud download fails.
        """
        if force_refresh:
            try:
                st.cache_data.clear()
            except Exception:
                pass

        target_url_or_path = (
            self.config.excel_url
            if self.config.data_source == "cloud" and self.config.excel_url
            else self.config.local_excel_path
        )

        effective_source = self.config.data_source
        file_bytes: Optional[bytes] = None
        metadata: Dict[str, Any] = {}
        error_msg: Optional[str] = None
        fetch_time = datetime.now(timezone.utc)

        # 1. Primary Attempt
        try:
            file_bytes, metadata = _fetch_cached_workbook_bytes(
                data_source=effective_source,
                cloud_provider=self.config.cloud_provider,
                url_or_path=target_url_or_path,
            )
        except Exception as primary_err:
            # 2. Fallback to Local Storage if Cloud Failed
            if effective_source == "cloud" and self.config.local_excel_path:
                try:
                    file_bytes, metadata = _fetch_cached_workbook_bytes(
                        data_source="local",
                        cloud_provider="local",
                        url_or_path=self.config.local_excel_path,
                    )
                    metadata["fallback_activated"] = True
                    metadata["fallback_reason"] = str(primary_err)
                except Exception as fallback_err:
                    error_msg = f"Cloud synchronization failed ({primary_err}) and local fallback failed ({fallback_err})."
            else:
                error_msg = f"Failed to load workbook: {primary_err}"

        # If data could not be obtained
        if file_bytes is None:
            empty_parsed = self.validator.parse_workbook(b"")
            return LoadedData(
                parsed=empty_parsed,
                metadata=metadata,
                freshness_status="UNAVAILABLE",
                freshness_label="● UNAVAILABLE",
                fetched_at=fetch_time,
                error_message=error_msg,
            )

        # 3. Parse and Validate
        parsed = self.validator.parse_workbook(file_bytes)

        # 4. Determine Freshness
        if metadata.get("fallback_activated"):
            freshness_status = "STALE"
            freshness_label = "● STALE (Local Fallback)"
        else:
            freshness_status, freshness_label = compute_freshness(
                fetch_time,
                metadata.get("last_modified"),
            )

        return LoadedData(
            parsed=parsed,
            metadata=metadata,
            freshness_status=freshness_status,
            freshness_label=freshness_label,
            fetched_at=fetch_time,
            error_message=None if parsed.is_valid else parsed.error_message,
        )

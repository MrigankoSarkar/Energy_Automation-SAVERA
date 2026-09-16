"""
Data Freshness and Synchronization Status Banner for EnergyAutomation.
Displays live synchronization state, cache indicators, provider info, and manual refresh controls.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional
import streamlit as st

from streamlit_app.data_loader import LoadedData


def render_freshness_banner(
    loaded_data: LoadedData,
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    """Renders the top status bar indicating source, provider, freshness, and refresh button."""
    status = loaded_data.freshness_status
    badge_class = {
        "LIVE": "badge-live",
        "RECENT": "badge-recent",
        "STALE": "badge-stale",
        "UNAVAILABLE": "badge-unavailable",
    }.get(status, "badge-unavailable")

    provider = loaded_data.metadata.get("provider", "Unknown Provider")
    source_url = loaded_data.metadata.get("source_url", "")

    # Shorten source path/URL for display
    display_source = source_url
    if len(display_source) > 60:
        display_source = display_source[:28] + "..." + display_source[-28:]

    sync_time_str = loaded_data.fetched_at.strftime("%H:%M:%S UTC")

    st.markdown(
        f"""
        <div style="background: #f1f5f9; border-radius: 8px; padding: 10px 16px; margin: 12px 0 20px 0; border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
                <span class="{badge_class}">{loaded_data.freshness_label}</span>
                <span style="font-size: 0.88rem; color: #334155; font-weight: 500;">
                    <strong>Source:</strong> {provider} &bull; <code style="font-size: 0.8rem; background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{display_source}</code>
                </span>
                <span style="font-size: 0.82rem; color: #64748b;">
                    Synced: {sync_time_str}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if loaded_data.metadata.get("fallback_activated"):
        st.warning(
            f"⚠️ **Cloud synchronization failed:** Using local fallback workbook. Reason: {loaded_data.metadata.get('fallback_reason')}",
            icon="⚠️",
        )

    if loaded_data.error_message:
        st.error(f"❌ **Workbook Parsing Notice:** {loaded_data.error_message}", icon="❌")

"""
Branding and enterprise layout styling for EnergyAutomation Streamlit BI.
Renders corporate logo, headers, badges, and injects clean industrial styling.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
import streamlit as st

from streamlit_app.config import DashboardConfig


def _get_base64_image(image_path: str) -> Optional[str]:
    """Reads image file and returns base64 data URI."""
    try:
        p = Path(image_path)
        if p.exists() and p.is_file():
            data = p.read_bytes()
            encoded = base64.b64encode(data).decode("utf-8")
            suffix = p.suffix.lower().replace(".", "")
            mime = "image/jpeg" if suffix in ("jpg", "jpeg") else "image/png"
            return f"data:{mime};base64,{encoded}"
    except Exception:
        pass
    return None


def render_branding_header(config: DashboardConfig) -> None:
    """Renders the top application header with logo and enterprise title."""
    logo_data_uri = _get_base64_image(config.logo_path) if config.logo_path else None

    # Custom CSS for executive card styling, badges, and metrics
    custom_css = """
    <style>
    /* Executive Card Styling */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
        border-color: #cbd5e1;
    }
    .metric-card .label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .metric-card .value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .metric-card .delta-pos {
        font-size: 0.85rem;
        font-weight: 600;
        color: #ef4444;
        margin-top: 4px;
    }
    .metric-card .delta-neg {
        font-size: 0.85rem;
        font-weight: 600;
        color: #10b981;
        margin-top: 4px;
    }
    .metric-card .delta-neutral {
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748b;
        margin-top: 4px;
    }

    /* Freshness Badges */
    .badge-live {
        background-color: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-recent {
        background-color: #fefce8;
        color: #854d0e;
        border: 1px solid #fef08a;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-stale {
        background-color: #fff7ed;
        color: #9a3412;
        border: 1px solid #fed7aa;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-unavailable {
        background-color: #fef2f2;
        color: #991b1b;
        border: 1px solid #fecaca;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Clean table headers */
    thead tr th {
        background-color: #f8fafc !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_data_uri:
            st.markdown(
                f'<img src="{logo_data_uri}" style="max-height: 65px; border-radius: 6px; margin-top: 4px;" alt="Logo" />',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("🏢 **SAVERA MS**")

    with col2:
        st.markdown(
            f"""
            <div style="padding-left: 8px;">
                <div style="font-size: 1.55rem; font-weight: 800; color: #1e293b; line-height: 1.2;">
                    {config.company_name} — Energy Intelligence & Executive BI
                </div>
                <div style="font-size: 0.9rem; color: #64748b; font-weight: 500; margin-top: 2px;">
                    {config.plant_name} &bull; Live NBSense EMS Synchronization & Analytics
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

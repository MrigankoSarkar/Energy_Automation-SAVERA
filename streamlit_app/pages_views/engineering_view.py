"""
Engineering Data Grid & Export View for EnergyAutomation Streamlit BI.
Provides raw data inspection, searchable meter grid, format preservation,
and direct CSV export capabilities for operational engineers.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics


def render_engineering_view(analytics: EnergyAnalytics) -> None:
    """Renders the raw engineering tabular view with export options."""
    st.subheader("Engineering Data Grid & Export")

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    # Filter controls
    c1, c2, c3 = st.columns([4, 4, 4])

    with c1:
        show_all = st.checkbox("Include template/future unpopulated rows", value=False)

    df_source = analytics.parsed.df_all if show_all else analytics.parsed.df_daily

    # Clean display dataframe
    display_df = df_source.copy()
    # Drop internal helper columns if present
    drop_cols = [c for c in display_df.columns if c.startswith("_")]
    display_df = display_df.drop(columns=drop_cols)

    with c2:
        search_meter = st.text_input("Filter Columns by Name:", placeholder="e.g. Compressor or Plating")

    if search_meter:
        matched_cols = [analytics.date_col] + [
            c for c in display_df.columns
            if search_meter.lower() in c.lower() and c != analytics.date_col
        ]
        if analytics.total_col in display_df.columns and analytics.total_col not in matched_cols:
            matched_cols.append(analytics.total_col)
        display_df = display_df[[c for c in matched_cols if c in display_df.columns]]

    # Format numeric columns for clean view
    formatted_df = display_df.copy()
    for col in formatted_df.columns:
        if col != analytics.date_col:
            formatted_df[col] = formatted_df[col].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else ("N/A" if pd.isna(x) else str(x))
            )

    with c3:
        # CSV Export
        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_bytes,
            file_name=f"Savera_Energy_Report_{analytics.df.iloc[-1][analytics.date_col]}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown(f"**Showing {len(display_df)} rows & {len(display_df.columns)} columns:**")
    st.dataframe(
        formatted_df,
        use_container_width=True,
        hide_index=True,
        height=450,
    )

    st.markdown("---")
    st.markdown("### Workbook Metadata & Configuration Schema")

    rep = analytics.parsed.validation_report
    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.info(f"**Worksheet:** `{rep.get('sheet_name', 'N/A')}`\n\n**Total Rows:** {rep.get('total_excel_rows', 0)}")
    m_c2.info(f"**Meters Detected:** {rep.get('meters_detected', 0)}\n\n**Submeters Count:** {rep.get('submeters_count', 0)}")
    m_c3.info(f"**Date Range:** `{rep.get('start_date', 'N/A')}` to `{rep.get('end_date', 'N/A')}`")

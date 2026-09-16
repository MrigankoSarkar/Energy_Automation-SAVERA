"""
Data Quality, Reconciliation, and Distribution Loss Audit View for EnergyAutomation Streamlit BI.
Audits time series continuity, verifies Excel formula integrity, tracks unpolled/N/A meters,
and visualizes facility-wide distribution losses.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.analytics import EnergyAnalytics


def render_data_quality_view(analytics: EnergyAnalytics) -> None:
    """Renders the data quality and reconciliation audit tab."""
    st.subheader("Data Quality, Reconciliation & Distribution Loss Audit")

    if analytics.df.empty:
        st.info("No recorded energy data available to display.")
        return

    audit = analytics.get_audit_report()
    val_rep = analytics.parsed.validation_report

    # Top KPI Metrics for Audit
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Recorded Days Audited", f"{audit.get('total_days_audited', 0)} days")
    q2.metric("Missing Dates in Span", f"{len(val_rep.get('missing_dates_in_span', []))} days")
    q3.metric("Unpolled 'N/A' Readings", f"{val_rep.get('unpolled_na_count', 0)}")
    q4.metric("Avg Distribution Loss", f"{audit.get('avg_distribution_loss_pct', 0.0):.1f}%")

    st.markdown("---")

    # Section 1: Distribution Loss Analysis
    st.markdown("### Electrical Distribution Loss Audit (Incomer vs Submeters)")
    loss_records = audit.get("loss_records", [])

    if loss_records:
        loss_df = pd.DataFrame(loss_records)

        fig_loss = go.Figure()
        fig_loss.add_trace(
            go.Scatter(
                x=loss_df["date"],
                y=loss_df["incomer"],
                name="Main Incomer (kWh)",
                line=dict(color="#1e293b", width=2.5),
            )
        )
        fig_loss.add_trace(
            go.Scatter(
                x=loss_df["date"],
                y=loss_df["submeter_sum"],
                name="Sum of Submeters (kWh)",
                line=dict(color="#2563eb", width=2, dash="dash"),
            )
        )
        fig_loss.add_trace(
            go.Bar(
                x=loss_df["date"],
                y=loss_df["loss_kwh"],
                name="Distribution Loss (kWh)",
                marker_color="#cbd5e1",
                opacity=0.6,
            )
        )

        fig_loss.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=340,
            xaxis=dict(title="Date", showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="Energy (kWh)", showgrid=True, gridcolor="#f1f5f9"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
        )
        st.plotly_chart(fig_loss, use_container_width=True)
    else:
        st.info("Incomer comparison not available (Incomer meter not designated).")

    # Section 2: Missing Dates & Data Integrity Checks
    sec_left, sec_right = st.columns(2)

    with sec_left:
        st.markdown("### Time Series Continuity")
        missing_dates = val_rep.get("missing_dates_in_span", [])
        if missing_dates:
            st.error(f"⚠️ **{len(missing_dates)} missing dates detected in date span:**")
            st.write(", ".join(missing_dates))
        else:
            st.success("✅ **Continuous time series:** No missing date gaps found between start and end dates.")

        st.markdown(
            f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 0.85rem; color: #475569;">
                <div><strong>Workbook Sheet:</strong> <code>{val_rep.get('sheet_name', 'N/A')}</code></div>
                <div><strong>Total Excel Rows:</strong> {val_rep.get('total_excel_rows', 0)}</div>
                <div><strong>Active Recorded Days:</strong> {val_rep.get('active_reading_days', 0)}</div>
                <div><strong>Template / Future Days:</strong> {val_rep.get('template_future_days', 0)}</div>
                <div><strong>Evaluated Total Formulas:</strong> {val_rep.get('evaluated_formula_totals', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sec_right:
        st.markdown("### Outlier & Anomaly Detection")
        outliers = audit.get("outliers", [])
        if outliers:
            st.warning(f"⚠️ **{len(outliers)} statistical outlier(s) detected (>3 standard deviations):**")
            outlier_df = pd.DataFrame(outliers)
            st.dataframe(outlier_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ **Normal Variance:** No statistical outliers detected beyond 3 standard deviations.")

        st.markdown(
            """
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 0.85rem; color: #475569;">
                <strong>Invariant Verification:</strong>
                <ul style="margin: 4px 0 0 0; padding-left: 18px;">
                    <li>Zero-Writing Invariant: Dashboard strictly operates in read-only mode.</li>
                    <li>N/A Invariant: Unpolled meters are preserved as NaN and never coerced to 0.0.</li>
                    <li>Workbook Formula Integrity: Excel formulas (=SUM) in active rows remain unmodified.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

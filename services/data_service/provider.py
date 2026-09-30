"""
Data provider for the Data & Telemetry microservice.
Evaluates production Excel workbook and SQLite audit ledger without fake telemetry.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
import pandas as pd

logger = logging.getLogger("services.data_service")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class TelemetrySummary:
    is_active: bool
    latest_date: Optional[str]
    latest_kwh: Optional[float]
    previous_date: Optional[str]
    previous_kwh: Optional[float]
    change_pct: Optional[float]
    mtd_kwh: Optional[float]
    avg_daily_kwh: Optional[float]
    active_meters_count: int
    total_meters_count: int
    incomer_kwh: Optional[float]
    submeters_kwh: Optional[float]
    workbook_path: str
    last_synced: str


class TelemetryDataProvider:
    def __init__(self, excel_path: Optional[str | Path] = None):
        if excel_path:
            self.excel_path = Path(excel_path)
        else:
            cfg_file = REPO_ROOT / "config" / "settings.json"
            chosen_file = None
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        cfg_data = json.load(f).get("excel", {})
                        chosen_file = cfg_data.get("workbook_path") or cfg_data.get("file")
                except Exception:
                    pass
            if chosen_file:
                p = Path(chosen_file)
                self.excel_path = p if p.is_absolute() else (REPO_ROOT / p)
                if not self.excel_path.exists():
                    alt = REPO_ROOT / "Test_BI_Analysis_Report_2026.xlsx"
                    if alt.exists():
                        self.excel_path = alt
            else:
                default_path = REPO_ROOT / "Test_BI_Analysis_Report_2026.xlsx"
                self.excel_path = default_path

        self._cached_summary: Optional[TelemetrySummary] = None
        self._cached_df: Optional[pd.DataFrame] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 30.0  # 30 seconds cache

    def get_summary(self, force_refresh: bool = False) -> TelemetrySummary:
        import time
        now = time.time()
        if not force_refresh and self._cached_summary and (now - self._cache_time < self._cache_ttl):
            return self._cached_summary

        df = self.get_daily_dataframe(force_refresh=force_refresh)
        if df.empty:
            summary = TelemetrySummary(
                is_active=False,
                latest_date=None,
                latest_kwh=None,
                previous_date=None,
                previous_kwh=None,
                change_pct=None,
                mtd_kwh=None,
                avg_daily_kwh=None,
                active_meters_count=0,
                total_meters_count=0,
                incomer_kwh=None,
                submeters_kwh=None,
                workbook_path=str(self.excel_path),
                last_synced=datetime.now().isoformat(),
            )
            self._cached_summary = summary
            self._cache_time = now
            return summary

        df_valid = df.dropna(subset=["Total Active Energy"])
        if df_valid.empty:
            df_valid = df

        latest_row = df_valid.iloc[-1]
        latest_date_str = str(latest_row.get("Date", "—"))[:10]
        latest_kwh = float(latest_row.get("Total Active Energy", 0.0))

        prev_date_str = None
        prev_kwh = None
        change_pct = None
        if len(df_valid) >= 2:
            prev_row = df_valid.iloc[-2]
            prev_date_str = str(prev_row.get("Date", "—"))[:10]
            prev_kwh = float(prev_row.get("Total Active Energy", 0.0))
            if prev_kwh > 0:
                change_pct = ((latest_kwh - prev_kwh) / prev_kwh) * 100.0

        mtd_kwh = float(df_valid["Total Active Energy"].sum())
        avg_kwh = float(df_valid["Total Active Energy"].mean())

        meter_cols = [c for c in df.columns if c not in {"Date", "Total Active Energy", "RowIndex"}]
        active_meters = sum(1 for m in meter_cols if pd.notna(latest_row.get(m)) and float(latest_row.get(m) or 0) > 0)

        incomer_col = next((c for c in meter_cols if "EB" in c or "INCOMER" in c.upper()), None)
        incomer_kwh = float(latest_row[incomer_col]) if incomer_col and pd.notna(latest_row.get(incomer_col)) else None
        submeters_kwh = (latest_kwh - incomer_kwh) if (incomer_kwh is not None and latest_kwh >= incomer_kwh) else latest_kwh

        summary = TelemetrySummary(
            is_active=True,
            latest_date=latest_date_str,
            latest_kwh=latest_kwh,
            previous_date=prev_date_str,
            previous_kwh=prev_kwh,
            change_pct=round(change_pct, 1) if change_pct is not None else None,
            mtd_kwh=round(mtd_kwh, 2),
            avg_daily_kwh=round(avg_kwh, 2),
            active_meters_count=active_meters,
            total_meters_count=len(meter_cols),
            incomer_kwh=round(incomer_kwh, 2) if incomer_kwh is not None else None,
            submeters_kwh=round(submeters_kwh, 2) if submeters_kwh is not None else None,
            workbook_path=str(self.excel_path),
            last_synced=datetime.now().isoformat(),
        )
        self._cached_summary = summary
        self._cache_time = now
        return summary

    def get_daily_dataframe(self, force_refresh: bool = False) -> pd.DataFrame:
        if not force_refresh and self._cached_df is not None:
            return self._cached_df

        if not self.excel_path.exists():
            logger.warning("Configured Excel workbook does not exist: %s. Awaiting user file selection.", self.excel_path)
            return pd.DataFrame()

        try:
            wb = openpyxl.load_workbook(str(self.excel_path), data_only=True, read_only=False)
            sheet_name = "EMS Monitoring Report"
            if sheet_name not in wb.sheetnames:
                sheet_name = wb.sheetnames[0]
            ws = wb[sheet_name]

            # Parse headers from row 3
            header_row = 3
            meter_names = []
            meter_col_indices = []

            for col in range(3, 18):
                val = ws.cell(row=header_row, column=col).value
                if val:
                    val_str = str(val).strip()
                    meter_names.append(val_str)
                    meter_col_indices.append(col)

            rows = []
            for r in range(5, 36):
                date_val = ws.cell(row=r, column=2).value
                if not date_val:
                    continue

                if isinstance(date_val, datetime):
                    dt_str = date_val.strftime("%Y-%m-%d")
                elif isinstance(date_val, date):
                    dt_str = date_val.isoformat()
                else:
                    dt_str = str(date_val).strip()

                row_data: Dict[str, Any] = {"Date": dt_str, "RowIndex": r}
                row_sum = 0.0
                has_readings = False

                for m_name, c_idx in zip(meter_names, meter_col_indices):
                    c_val = ws.cell(row=r, column=c_idx).value
                    if c_val is not None:
                        try:
                            f_val = float(c_val)
                            row_data[m_name] = f_val
                            row_sum += f_val
                            has_readings = True
                        except (ValueError, TypeError):
                            row_data[m_name] = None
                    else:
                        row_data[m_name] = None

                tot_val = ws.cell(row=r, column=18).value
                if tot_val is not None:
                    try:
                        row_data["Total Active Energy"] = float(tot_val)
                    except (ValueError, TypeError):
                        row_data["Total Active Energy"] = row_sum if has_readings else None
                else:
                    row_data["Total Active Energy"] = row_sum if has_readings else None

                if has_readings or row_data["Total Active Energy"] is not None:
                    rows.append(row_data)

            wb.close()
            df = pd.DataFrame(rows)
            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.sort_values("Date").reset_index(drop=True)

            self._cached_df = df
            return df
        except Exception as exc:
            logger.error("Failed to parse workbook %s: %s", self.excel_path, exc)
            return pd.DataFrame()

    def get_feeders_catalog(self) -> List[Dict[str, Any]]:
        df = self.get_daily_dataframe()
        if df.empty:
            return []

        meter_cols = [c for c in df.columns if c not in {"Date", "Total Active Energy", "RowIndex"}]
        latest_row = df.iloc[-1] if not df.empty else None
        tot_kwh = float(latest_row.get("Total Active Energy", 0.0)) if latest_row is not None else 0.0

        catalog = []
        for m in meter_cols:
            val = float(latest_row.get(m)) if latest_row is not None and pd.notna(latest_row.get(m)) else None
            share = (val / tot_kwh * 100.0) if (val and tot_kwh > 0) else 0.0
            catalog.append({
                "feeder_name": m,
                "latest_kwh": val,
                "share_pct": round(share, 2),
                "status": "OK" if val is not None else "UNPOLLED",
            })
        return catalog

    def get_data_quality(self) -> Dict[str, Any]:
        df = self.get_daily_dataframe()
        summary = self.get_summary()

        if df.empty:
            return {
                "freshness_status": "NO_DATA",
                "missing_dates_count": 0,
                "missing_dates": [],
                "formula_reconciliation_ok": False,
                "discrepancies": [],
            }

        dates = df["Date"].dropna().dt.date.tolist()
        missing = []
        if len(dates) >= 2:
            all_days = pd.date_range(start=dates[0], end=dates[-1], freq="D").date
            for day in all_days:
                if day not in dates:
                    missing.append(day.isoformat())

        discrepancies = []
        meter_cols = [c for c in df.columns if c not in {"Date", "Total Active Energy", "RowIndex"}]
        for idx, row in df.iterrows():
            d_str = str(row["Date"])[:10]
            sum_feeders = sum(float(row[m]) for m in meter_cols if pd.notna(row.get(m)))
            tot = float(row.get("Total Active Energy", 0.0) or 0.0)
            if abs(sum_feeders - tot) > 1.0 and tot > 0:
                discrepancies.append({
                    "date": d_str,
                    "feeder_sum": round(sum_feeders, 2),
                    "recorded_total": round(tot, 2),
                    "diff": round(abs(sum_feeders - tot), 2),
                })

        return {
            "freshness_status": "UP_TO_DATE" if summary.is_active else "STALE",
            "latest_report_date": summary.latest_date,
            "missing_dates_count": len(missing),
            "missing_dates": missing,
            "formula_reconciliation_ok": len(discrepancies) == 0,
            "discrepancies": discrepancies,
            "active_meters": summary.active_meters_count,
            "total_meters": summary.total_meters_count,
        }

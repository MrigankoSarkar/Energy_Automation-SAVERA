"""
Analytics and KPI Engine for EnergyAutomation Streamlit BI.
Calculates executive metrics, meter rankings, plant topology rollups,
time-series statistics, weekday vs weekend patterns, and data quality audits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from streamlit_app.data_validator import ParsedWorkbook

# Import official plant topology zones
try:
    from app.services.analytics.plant_topology import PLANT_ZONES, PlantTopologyService, PlantZone
except ImportError:
    # Standalone fallback if package root is not on sys.path
    from dataclasses import field

    @dataclass
    class PlantZone:
        zone_id: str
        name: str
        section: str
        building: str
        nominal_kwh: float
        description: str
        meters: List[str] = field(default_factory=list)

    PLANT_ZONES = {
        "plating": PlantZone("plating", "Surface Treatment & Plating Plant", "Shop Floor A", "Bldg 1", 160.0, "Electroplating lines", ["Chiller Plating Plant", "New Plating Plant", "Old Plating Plant", "DIPP_PT_PANEĹ", "DIPP_PT_PANEL"]),
        "coating": PlantZone("coating", "Finishing & Powder Coating Plant", "Shop Floor B", "Bldg 2", 2100.0, "Powder coating booth", ["Powder Coating"]),
        "fabrication": PlantZone("fabrication", "Press & Fabrication Line", "Shop Floor C", "Bldg 3", 1250.0, "Stamping presses & welding", ["Press & Fabrication", "Rigga Line Fabrication", "Annealing Furnance", "Annealing Furnace", "RASKOG"]),
        "compressors": PlantZone("compressors", "Compressed Air Generation Substation", "Utility Block 1", "Bldg 4", 1850.0, "Air compressors", ["Kaeser ASD 60 40HP Air Compressor", "ELGI E18 25HP Air Compressor", "ELGI E45 60HP Air Compressor"]),
        "water_treatment": PlantZone("water_treatment", "RO & DM Water Treatment Facility", "Utility Block 2", "Bldg 4", 430.0, "Process water plant", ["RO Plant", "DM Plant"]),
        "packaging": PlantZone("packaging", "Packaging & Stitching Line", "Shop Floor D", "Bldg 5", 500.0, "Packaging lines", ["Packing & Stiching Line", "Packing & Stitching Line"]),
        "main_power": PlantZone("main_power", "Main Power Substation & Incomer", "Substation", "Bldg 0", 3200.0, "Main incomer", ["Old LT Panel Main Incomer", "LT Incomer", "Main Incomer"]),
    }


@dataclass
class ExecutiveKPIs:
    """Executive KPI card metrics."""
    latest_date: Optional[date]
    latest_total_kwh: float
    previous_date: Optional[date]
    previous_total_kwh: float
    dod_change_kwh: float
    dod_change_pct: float
    mtd_total_kwh: float
    mtd_days_count: int
    ytd_total_kwh: float
    avg_daily_kwh: float
    peak_date: Optional[date]
    peak_kwh: float
    min_date: Optional[date]
    min_kwh: float
    active_meters_count: int
    total_meters_count: int
    incomer_kwh: Optional[float]
    submeters_kwh: float


class EnergyAnalytics:
    """Calculates all BI metrics and aggregations from a ParsedWorkbook."""

    def __init__(self, parsed: ParsedWorkbook):
        self.parsed = parsed
        self.df = parsed.df_daily.copy()
        self.incomer_col = parsed.incomer_col
        self.submeter_cols = parsed.submeter_cols
        self.meter_cols = parsed.meter_cols
        self.total_col = parsed.total_col
        self.date_col = parsed.date_col

        if not self.df.empty and self.date_col in self.df.columns:
            # Ensure Date column is proper date object and sorted
            self.df["_dt"] = pd.to_datetime(self.df[self.date_col])
            self.df = self.df.sort_values(by="_dt").reset_index(drop=True)
            self.df["_weekday"] = self.df["_dt"].dt.day_name()
            self.df["_is_weekend"] = self.df["_dt"].dt.dayofweek >= 5

    def get_executive_kpis(self) -> ExecutiveKPIs:
        """Computes top-level executive KPIs."""
        if self.df.empty:
            return ExecutiveKPIs(
                latest_date=None, latest_total_kwh=0.0, previous_date=None,
                previous_total_kwh=0.0, dod_change_kwh=0.0, dod_change_pct=0.0,
                mtd_total_kwh=0.0, mtd_days_count=0, ytd_total_kwh=0.0,
                avg_daily_kwh=0.0, peak_date=None, peak_kwh=0.0, min_date=None,
                min_kwh=0.0, active_meters_count=0, total_meters_count=len(self.meter_cols),
                incomer_kwh=None, submeters_kwh=0.0,
            )

        # Totals series (fallback to submeters sum if total_col is missing)
        if self.total_col in self.df.columns:
            total_series = self.df[self.total_col].fillna(0.0)
        else:
            total_series = self.df[self.submeter_cols].sum(axis=1)

        latest_idx = len(self.df) - 1
        latest_row = self.df.iloc[latest_idx]
        latest_date = latest_row[self.date_col]
        latest_total = float(total_series.iloc[latest_idx])

        # Previous day
        prev_date = None
        prev_total = 0.0
        dod_change_kwh = 0.0
        dod_change_pct = 0.0
        if len(self.df) >= 2:
            prev_row = self.df.iloc[latest_idx - 1]
            prev_date = prev_row[self.date_col]
            prev_total = float(total_series.iloc[latest_idx - 1])
            dod_change_kwh = latest_total - prev_total
            if prev_total > 0:
                dod_change_pct = (dod_change_kwh / prev_total) * 100.0

        # MTD: sum of all days in the latest month
        latest_dt = latest_row["_dt"]
        mtd_mask = (self.df["_dt"].dt.year == latest_dt.year) & (self.df["_dt"].dt.month == latest_dt.month)
        mtd_df = self.df[mtd_mask]
        mtd_total = float(total_series[mtd_mask].sum())
        mtd_days = len(mtd_df)

        # YTD: sum of all recorded days
        ytd_total = float(total_series.sum())

        # Average, Peak, Min
        avg_daily = float(total_series.mean())
        peak_idx = int(total_series.idxmax())
        peak_date = self.df.iloc[peak_idx][self.date_col]
        peak_kwh = float(total_series.iloc[peak_idx])

        min_idx = int(total_series.idxmin())
        min_date = self.df.iloc[min_idx][self.date_col]
        min_kwh = float(total_series.iloc[min_idx])

        # Active meters on latest date
        active_meters = 0
        for m in self.meter_cols:
            if m in latest_row:
                val = latest_row[m]
                if pd.notna(val) and float(val) > 0.0:
                    active_meters += 1

        incomer_kwh = None
        if self.incomer_col and self.incomer_col in latest_row:
            inc_val = latest_row[self.incomer_col]
            if pd.notna(inc_val):
                incomer_kwh = float(inc_val)

        submeters_kwh = float(latest_row[self.submeter_cols].sum(skipna=True))

        return ExecutiveKPIs(
            latest_date=latest_date,
            latest_total_kwh=round(latest_total, 2),
            previous_date=prev_date,
            previous_total_kwh=round(prev_total, 2),
            dod_change_kwh=round(dod_change_kwh, 2),
            dod_change_pct=round(dod_change_pct, 1),
            mtd_total_kwh=round(mtd_total, 2),
            mtd_days_count=mtd_days,
            ytd_total_kwh=round(ytd_total, 2),
            avg_daily_kwh=round(avg_daily, 2),
            peak_date=peak_date,
            peak_kwh=round(peak_kwh, 2),
            min_date=min_date,
            min_kwh=round(min_kwh, 2),
            active_meters_count=active_meters,
            total_meters_count=len(self.meter_cols),
            incomer_kwh=round(incomer_kwh, 2) if incomer_kwh is not None else None,
            submeters_kwh=round(submeters_kwh, 2),
        )

    def get_meter_rankings(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_incomer: bool = False,
    ) -> pd.DataFrame:
        """
        Calculates total consumption and share for each meter over the selected date range.
        Returns DataFrame with: Meter, Total kWh, Daily Avg kWh, Share %, Cumulative %
        """
        if self.df.empty:
            return pd.DataFrame()

        filtered = self.df.copy()
        if start_date:
            filtered = filtered[filtered["_dt"].dt.date >= start_date]
        if end_date:
            filtered = filtered[filtered["_dt"].dt.date <= end_date]

        if filtered.empty:
            return pd.DataFrame()

        target_cols = self.meter_cols if include_incomer else self.submeter_cols
        available_cols = [c for c in target_cols if c in filtered.columns]

        totals = filtered[available_cols].sum(axis=0)
        means = filtered[available_cols].mean(axis=0)

        records = []
        for m in available_cols:
            records.append({
                "Meter": m,
                "Total kWh": round(float(totals[m]), 2),
                "Daily Avg kWh": round(float(means[m]), 2),
            })

        res_df = pd.DataFrame(records).sort_values(by="Total kWh", ascending=False).reset_index(drop=True)
        grand_total = res_df["Total kWh"].sum()

        if grand_total > 0:
            res_df["Share %"] = (res_df["Total kWh"] / grand_total * 100.0).round(1)
            res_df["Cumulative %"] = res_df["Share %"].cumsum().round(1)
        else:
            res_df["Share %"] = 0.0
            res_df["Cumulative %"] = 0.0

        return res_df

    def get_zone_breakdown(
        self,
        target_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates consumption by the 7 official Savera MS plant zones.
        If target_date is provided, uses that specific day; otherwise uses average across all recorded days.
        """
        if self.df.empty:
            return []

        if target_date:
            row_match = self.df[self.df["_dt"].dt.date == target_date]
            if not row_match.empty:
                ref_series = row_match.iloc[0]
                period_label = f"Date: {target_date}"
            else:
                ref_series = self.df.iloc[-1]
                period_label = f"Latest Date: {self.df.iloc[-1][self.date_col]}"
        else:
            ref_series = self.df[self.meter_cols].mean(axis=0)
            period_label = f"Daily Average ({len(self.df)} days)"

        zones_result: List[Dict[str, Any]] = []
        plant_submeter_total = 0.0

        for zone_id, zone in PLANT_ZONES.items():
            zone_meters = []
            zone_total = 0.0
            active_count = 0

            for m_pattern in zone.meters:
                # Find matching columns in DataFrame
                matched_cols = [c for c in self.meter_cols if m_pattern.lower() in c.lower() or c.lower() in m_pattern.lower()]
                for col in matched_cols:
                    if col in ref_series:
                        val = ref_series[col]
                        val_float = float(val) if pd.notna(val) else 0.0
                        zone_total += val_float
                        if val_float > 0:
                            active_count += 1
                        zone_meters.append({
                            "meter_name": col,
                            "kwh": round(val_float, 2),
                            "status": "OK" if pd.notna(val) else "N/A",
                        })

            if zone_id != "main_power":
                plant_submeter_total += zone_total

            status = "NORMAL"
            if active_count == 0 and zone_total == 0:
                status = "INACTIVE"
            elif zone_total > zone.nominal_kwh * 1.30:
                status = "HIGH"
            elif zone_total > zone.nominal_kwh * 1.15:
                status = "WARNING"

            zones_result.append({
                "zone_id": zone_id,
                "name": zone.name,
                "section": zone.section,
                "building": zone.building,
                "nominal_kwh": zone.nominal_kwh,
                "total_kwh": round(zone_total, 2),
                "active_meters": active_count,
                "status": status,
                "meters": zone_meters,
                "description": zone.description,
            })

        # Compute percentage of submeters total
        for z in zones_result:
            if z["zone_id"] != "main_power" and plant_submeter_total > 0:
                z["percentage"] = round((z["total_kwh"] / plant_submeter_total) * 100.0, 1)
            else:
                z["percentage"] = 0.0

        return zones_result

    def get_weekday_vs_weekend(self) -> Dict[str, Any]:
        """Calculates weekday vs weekend consumption patterns."""
        if self.df.empty:
            return {"weekday_avg": 0.0, "weekend_avg": 0.0, "by_day": {}}

        total_col_to_use = self.total_col if self.total_col in self.df.columns else None
        if total_col_to_use:
            work_series = self.df[total_col_to_use].fillna(0.0)
        else:
            work_series = self.df[self.submeter_cols].sum(axis=1)

        temp_df = pd.DataFrame({
            "kwh": work_series,
            "is_weekend": self.df["_is_weekend"],
            "weekday": self.df["_weekday"],
            "day_num": self.df["_dt"].dt.dayofweek,
        })

        weekday_data = temp_df[~temp_df["is_weekend"]]
        weekend_data = temp_df[temp_df["is_weekend"]]

        weekday_avg = float(weekday_data["kwh"].mean()) if not weekday_data.empty else 0.0
        weekend_avg = float(weekend_data["kwh"].mean()) if not weekend_data.empty else 0.0

        by_day_df = temp_df.groupby(["day_num", "weekday"])["kwh"].agg(["mean", "count"]).reset_index()
        by_day_df = by_day_df.sort_values(by="day_num")

        day_dict = {
            row["weekday"]: {"avg_kwh": round(row["mean"], 2), "days_count": int(row["count"])}
            for _, row in by_day_df.iterrows()
        }

        diff_pct = 0.0
        if weekday_avg > 0:
            diff_pct = round(((weekend_avg - weekday_avg) / weekday_avg) * 100.0, 1)

        return {
            "weekday_avg": round(weekday_avg, 2),
            "weekend_avg": round(weekend_avg, 2),
            "difference_pct": diff_pct,
            "by_day": day_dict,
        }

    def get_audit_report(self) -> Dict[str, Any]:
        """Performs data quality and distribution loss audit."""
        if self.df.empty:
            return {"status": "EMPTY"}

        total_days = len(self.df)
        incomer_present = bool(self.incomer_col and self.incomer_col in self.df.columns)

        loss_records = []
        if incomer_present:
            for _, row in self.df.iterrows():
                inc = row[self.incomer_col]
                sub_sum = row[self.submeter_cols].sum(skipna=True)
                if pd.notna(inc) and inc > 0:
                    diff = inc - sub_sum
                    loss_pct = (diff / inc) * 100.0
                    loss_records.append({
                        "date": row[self.date_col],
                        "incomer": round(inc, 2),
                        "submeter_sum": round(sub_sum, 2),
                        "loss_kwh": round(diff, 2),
                        "loss_pct": round(loss_pct, 1),
                    })

        avg_loss_pct = float(np.mean([r["loss_pct"] for r in loss_records])) if loss_records else 0.0

        # Outlier detection (days > 3 standard deviations from mean)
        tot_series = self.df[self.total_col].fillna(0.0) if self.total_col in self.df.columns else self.df[self.submeter_cols].sum(axis=1)
        mean_tot = tot_series.mean()
        std_tot = tot_series.std()
        outliers = []
        if std_tot > 0:
            for idx, val in tot_series.items():
                if abs(val - mean_tot) > 3 * std_tot:
                    outliers.append({
                        "date": self.df.iloc[idx][self.date_col],
                        "kwh": round(val, 2),
                        "z_score": round((val - mean_tot) / std_tot, 2),
                    })

        return {
            "total_days_audited": total_days,
            "incomer_monitored": incomer_present,
            "avg_distribution_loss_pct": round(avg_loss_pct, 1),
            "loss_records": loss_records,
            "outliers_count": len(outliers),
            "outliers": outliers,
        }

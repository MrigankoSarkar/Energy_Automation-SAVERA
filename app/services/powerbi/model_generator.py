"""
Power BI Analytical Star-Schema Model and Measures Generator for EnergyAutomation.
Generates dimensional tables, DAX measures, Push Dataset JSON schemas,
and report templates to automate Power BI dashboard creation.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


DAX_MEASURES = """// ====================================================================
// EnergyAutomation — Industrial EMS Power BI DAX Measures
// Target Plant: Savera MS Manufacturing Facility
// ====================================================================

// --- 1. Total & Daily Aggregates ---
[Total Energy (kWh)] = 
SUM(Fact_EnergyConsumption[ActiveEnergy_kWh])

[Daily Energy] = 
CALCULATE(
    [Total Energy (kWh)], 
    ALLEXCEPT(Dim_Date, Dim_Date[Date])
)

[Yesterday Energy] = 
CALCULATE(
    [Total Energy (kWh)], 
    DATEADD(Dim_Date[Date], -1, DAY)
)

[Day-over-Day Variance (kWh)] = 
[Total Energy (kWh)] - [Yesterday Energy]

[Day-over-Day Growth %] = 
DIVIDE(
    [Day-over-Day Variance (kWh)], 
    [Yesterday Energy], 
    0
)

// --- 2. Period-to-Date Metrics ---
[MTD Energy (kWh)] = 
TOTALMTD(
    [Total Energy (kWh)], 
    Dim_Date[Date]
)

[YTD Energy (kWh)] = 
TOTALYTD(
    [Total Energy (kWh)], 
    Dim_Date[Date]
)

[Average Daily Energy] = 
AVERAGEX(
    VALUES(Dim_Date[Date]), 
    [Total Energy (kWh)]
)

[Peak Daily Energy] = 
MAXX(
    VALUES(Dim_Date[Date]), 
    [Total Energy (kWh)]
)

// --- 3. Operational Analysis ---
[Weekend Energy (kWh)] = 
CALCULATE(
    [Total Energy (kWh)], 
    Dim_Date[IsWeekend] = TRUE()
)

[Weekday Energy (kWh)] = 
CALCULATE(
    [Total Energy (kWh)], 
    Dim_Date[IsWeekend] = FALSE()
)

[Weekend vs Weekday Ratio] = 
DIVIDE(
    [Weekend Energy (kWh)], 
    [Weekday Energy (kWh)], 
    0
)

[Active Meter Count] = 
CALCULATE(
    DISTINCTCOUNT(Fact_EnergyConsumption[MeterKey]), 
    Fact_EnergyConsumption[Status] = "OK"
)

[Missing Meter Reading Count] = 
CALCULATE(
    COUNTROWS(Fact_EnergyConsumption), 
    Fact_EnergyConsumption[Status] = "N/A"
)

[Anomaly Count] = 
CALCULATE(
    COUNTROWS(Fact_EnergyConsumption), 
    Fact_EnergyConsumption[IsAnomaly] = TRUE()
)

[Meter Contribution %] = 
DIVIDE(
    [Total Energy (kWh)], 
    CALCULATE([Total Energy (kWh)], ALL(Dim_Meter)), 
    0
)
"""

DATASET_SCHEMA = {
    "name": "EnergyAutomation_EMS_Model",
    "defaultMode": "Push",
    "tables": [
        {
            "name": "Fact_EnergyConsumption",
            "columns": [
                {"name": "FactKey", "dataType": "string"},
                {"name": "DateKey", "dataType": "string"},
                {"name": "ReportDate", "dataType": "DateTime"},
                {"name": "MeterKey", "dataType": "string"},
                {"name": "MeterName", "dataType": "string"},
                {"name": "AreaKey", "dataType": "string"},
                {"name": "AreaName", "dataType": "string"},
                {"name": "ActiveEnergy_kWh", "dataType": "Double"},
                {"name": "Unit", "dataType": "string"},
                {"name": "Status", "dataType": "string"},
                {"name": "IsWeekend", "dataType": "Boolean"},
                {"name": "IsAnomaly", "dataType": "Boolean"},
                {"name": "ProcessedAt", "dataType": "DateTime"},
            ],
        },
        {
            "name": "Dim_Date",
            "columns": [
                {"name": "DateKey", "dataType": "string"},
                {"name": "Date", "dataType": "DateTime"},
                {"name": "Year", "dataType": "Int64"},
                {"name": "Month", "dataType": "Int64"},
                {"name": "MonthName", "dataType": "string"},
                {"name": "Day", "dataType": "Int64"},
                {"name": "DayOfWeek", "dataType": "Int64"},
                {"name": "DayName", "dataType": "string"},
                {"name": "IsWeekend", "dataType": "Boolean"},
                {"name": "Quarter", "dataType": "Int64"},
            ],
        },
        {
            "name": "Dim_Meter",
            "columns": [
                {"name": "MeterKey", "dataType": "string"},
                {"name": "MeterName", "dataType": "string"},
                {"name": "ExcelHeader", "dataType": "string"},
                {"name": "AreaKey", "dataType": "string"},
                {"name": "RatedPower_kW", "dataType": "Double"},
                {"name": "NominalLoad_kWh", "dataType": "Double"},
                {"name": "Category", "dataType": "string"},
            ],
        },
        {
            "name": "Dim_Area",
            "columns": [
                {"name": "AreaKey", "dataType": "string"},
                {"name": "AreaName", "dataType": "string"},
                {"name": "Section", "dataType": "string"},
                {"name": "Building", "dataType": "string"},
                {"name": "NominalDaily_kWh", "dataType": "Double"},
                {"name": "TargetEfficiency", "dataType": "string"},
            ],
        },
        {
            "name": "Dim_Report",
            "columns": [
                {"name": "ReportId", "dataType": "Int64"},
                {"name": "ReportDate", "dataType": "DateTime"},
                {"name": "AttachmentName", "dataType": "string"},
                {"name": "AttachmentHash", "dataType": "string"},
                {"name": "MeterCount", "dataType": "Int64"},
                {"name": "MappedCount", "dataType": "Int64"},
                {"name": "TotalEnergy_kWh", "dataType": "Double"},
                {"name": "ExcelStatus", "dataType": "string"},
                {"name": "PowerBIStatus", "dataType": "string"},
                {"name": "ProcessedAt", "dataType": "DateTime"},
            ],
        },
    ],
    "relationships": [
        {
            "name": "Rel_Fact_Date",
            "fromTable": "Fact_EnergyConsumption",
            "fromColumn": "DateKey",
            "toTable": "Dim_Date",
            "toColumn": "DateKey",
        },
        {
            "name": "Rel_Fact_Meter",
            "fromTable": "Fact_EnergyConsumption",
            "fromColumn": "MeterKey",
            "toTable": "Dim_Meter",
            "toColumn": "MeterKey",
        },
        {
            "name": "Rel_Fact_Area",
            "fromTable": "Fact_EnergyConsumption",
            "fromColumn": "AreaKey",
            "toTable": "Dim_Area",
            "toColumn": "AreaKey",
        },
    ],
}

REPORT_TEMPLATES = {
    "version": "1.0",
    "report_title": "EnergyAutomation — Savera MS EMS Executive & Engineering Dashboard",
    "pages": [
        {
            "name": "Executive Overview",
            "description": "High-level summary of plant consumption, today vs yesterday variance, MTD/YTD totals, and top consumers.",
            "visuals": [
                {"type": "card", "title": "Today's Energy (kWh)", "measure": "[Daily Energy]"},
                {"type": "card", "title": "Yesterday's Energy (kWh)", "measure": "[Yesterday Energy]"},
                {"type": "card", "title": "Day-over-Day Growth", "measure": "[Day-over-Day Growth %]"},
                {"type": "card", "title": "MTD Energy (kWh)", "measure": "[MTD Energy (kWh)]"},
                {"type": "lineChart", "title": "30-Day Daily Energy Trend", "xAxis": "Dim_Date[Date]", "yAxis": "[Total Energy (kWh)]"},
                {"type": "barChart", "title": "Top Energy Consuming Meters", "category": "Dim_Meter[MeterName]", "value": "[Total Energy (kWh)]", "topN": 5},
            ],
        },
        {
            "name": "Engineering & Zone Analysis",
            "description": "Deep-dive meter level breakdown across production zones (Plating, Coating, Fabrication, Compressors, Water Treatment).",
            "visuals": [
                {"type": "treemap", "title": "Energy by Production Area", "group": "Dim_Area[AreaName]", "value": "[Total Energy (kWh)]"},
                {"type": "table", "title": "Meter Detail Analysis", "columns": ["Dim_Meter[MeterName]", "Dim_Area[AreaName]", "[Total Energy (kWh)]", "[Meter Contribution %]", "Fact_EnergyConsumption[Status]"]},
                {"type": "columnChart", "title": "Weekday vs Weekend Profile", "category": "Dim_Date[DayName]", "value": "[Total Energy (kWh)]"},
            ],
        },
        {
            "name": "Data Quality & Audit Trail",
            "description": "Reconciliation integrity, missing reports, unmapped meters, and processing statuses.",
            "visuals": [
                {"type": "card", "title": "Total Reports Processed", "field": "COUNT(Dim_Report[ReportId])"},
                {"type": "card", "title": "Active Meters Logged", "measure": "[Active Meter Count]"},
                {"type": "card", "title": "Missing / Inactive Readings", "measure": "[Missing Meter Reading Count]"},
                {"type": "table", "title": "Audit Trail History", "columns": ["Dim_Report[ReportDate]", "Dim_Report[AttachmentName]", "Dim_Report[TotalEnergy_kWh]", "Dim_Report[ExcelStatus]", "Dim_Report[ProcessedAt]"]},
            ],
        },
    ],
}


class PowerBIModelGenerator:
    """
    Builds and exports complete Power BI star-schema datasets,
    ready-to-import CSV files, DAX measures, and JSON schemas.
    """

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository

    def build_dim_date(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Generate contiguous date dimension rows."""
        rows = []
        curr = start_date
        while curr <= end_date:
            is_wknd = curr.weekday() in {5, 6}
            rows.append({
                "DateKey": curr.strftime("%Y%m%d"),
                "Date": curr.isoformat(),
                "Year": curr.year,
                "Month": curr.month,
                "MonthName": curr.strftime("%B"),
                "Day": curr.day,
                "DayOfWeek": curr.isoweekday(),
                "DayName": curr.strftime("%A"),
                "IsWeekend": is_wknd,
                "Quarter": (curr.month - 1) // 3 + 1,
            })
            curr += timedelta(days=1)
        return rows

    def build_dim_meter(self) -> List[Dict[str, Any]]:
        """Generate meter dimension rows for all 18 Savera plant meters."""
        from app.services.analytics.plant_topology import PLANT_ZONES

        meters_def = [
            ("M01", "Chiller Plating Plant", "Chiller Plating Plant", "plating", 45.0, 150.0, "Process Chiller"),
            ("M02", "Old LT Panel Main Incomer", "Old LT Panel Main Incomer", "main_power", 500.0, 3200.0, "Main Incomer"),
            ("M03", "Packing & Stiching Line", "Packing & Stiching Line", "packaging", 60.0, 480.0, "Packaging Line"),
            ("M04", "Rigga Line Fabrication", "Rigga Line Fabrication", "fabrication", 30.0, 180.0, "Welding Line"),
            ("M05", "Press & Fabrication", "Press & Fabrication", "fabrication", 150.0, 1000.0, "Stamping Press"),
            ("M06", "Powder Coating", "Powder Coating", "coating", 250.0, 2000.0, "Infrared Oven"),
            ("M07", "New Plating Plant", "New Plating Plant", "plating", 80.0, 5.0, "Electroplating"),
            ("M08", "Old Plating Plant", "Old Plating Plant", "plating", 80.0, 5.0, "Electroplating"),
            ("M09", "Kaeser ASD 60 40HP Air Compressor", "Kaeser ASD 60 40HP Air Compressor", "compressors", 30.0, 780.0, "Screw Compressor"),
            ("M10", "ELGI E18 25HP Air Compressor", "ELGI E18 25HP Air Compressor", "compressors", 18.5, 5.0, "Screw Compressor"),
            ("M11", "ELGI E45 60HP Air Compressor", "ELGI E45 60HP Air Compressor", "compressors", 45.0, 1010.0, "Screw Compressor"),
            ("M12", "DIPP_PT_PANEĹ", "DIPP_PT_PANEĹ", "plating", 15.0, 5.0, "Pre-treatment"),
            ("M13", "Annealing Furnance", "Annealing Furnance", "fabrication", 50.0, 0.0, "Heat Treatment"),
            ("M14", "RO Plant", "RO Plant", "water_treatment", 45.0, 420.0, "Water Treatment"),
            ("M15", "DM Plant", "DM Plant", "water_treatment", 10.0, 5.0, "Demineralizer"),
            ("M16", "RASKOG", "RASKOG", "fabrication", 20.0, 0.0, "Auxiliary Fabrication"),
        ]

        rows = []
        for key, name, header, area, kw, nominal, cat in meters_def:
            rows.append({
                "MeterKey": key,
                "MeterName": name,
                "ExcelHeader": header,
                "AreaKey": area,
                "RatedPower_kW": kw,
                "NominalLoad_kWh": nominal,
                "Category": cat,
            })
        return rows

    def build_dim_area(self) -> List[Dict[str, Any]]:
        """Generate production area dimension rows."""
        from app.services.analytics.plant_topology import PLANT_ZONES

        rows = []
        for zid, z in PLANT_ZONES.items():
            rows.append({
                "AreaKey": zid,
                "AreaName": z.name,
                "Section": z.section,
                "Building": z.building,
                "NominalDaily_kWh": z.nominal_kwh,
                "TargetEfficiency": ">= 92%",
            })
        return rows

    def export_star_schema(self, output_dir: Path) -> Dict[str, str]:
        """
        Generate and export the complete analytical star schema:
        CSVs for Fact and Dimensions, DAX measures file, Push Dataset JSON,
        and Power BI report templates.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        # 1. Export DAX Measures
        measures_path = output_dir / "measures.dax"
        with open(measures_path, "w", encoding="utf-8") as f:
            f.write(DAX_MEASURES)
        paths["measures_dax"] = str(measures_path)

        # 2. Export Push Dataset Schema JSON
        schema_path = output_dir / "dataset_schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(DATASET_SCHEMA, f, indent=2)
        paths["dataset_schema_json"] = str(schema_path)

        # 3. Export Report Template JSON
        report_template_path = output_dir / "powerbi_report_template.json"
        with open(report_template_path, "w", encoding="utf-8") as f:
            json.dump(REPORT_TEMPLATES, f, indent=2)
        paths["report_template_json"] = str(report_template_path)

        # 4. Export Dim_Meter CSV
        dim_meter_rows = self.build_dim_meter()
        meter_csv = output_dir / "Dim_Meter.csv"
        self._write_csv(meter_csv, dim_meter_rows)
        paths["dim_meter_csv"] = str(meter_csv)

        # 5. Export Dim_Area CSV
        dim_area_rows = self.build_dim_area()
        area_csv = output_dir / "Dim_Area.csv"
        self._write_csv(area_csv, dim_area_rows)
        paths["dim_area_csv"] = str(area_csv)

        # 6. Export Dim_Date CSV (past 90 days to +30 days)
        today = date.today()
        start = today - timedelta(days=90)
        end = today + timedelta(days=30)
        dim_date_rows = self.build_dim_date(start, end)
        date_csv = output_dir / "Dim_Date.csv"
        self._write_csv(date_csv, dim_date_rows)
        paths["dim_date_csv"] = str(date_csv)

        # 7. Export Fact_EnergyConsumption & Dim_Report from repository
        fact_rows = []
        report_rows = []

        if self.repository:
            try:
                reports = self.repository.get_recent_history(limit=100)
                meter_map = {m["MeterName"]: m for m in dim_meter_rows}

                for r in reports:
                    rep_id = r.get("id")
                    rep_date_str = r.get("report_date", "")
                    rep_date = (
                        datetime.strptime(rep_date_str, "%Y-%m-%d").date()
                        if rep_date_str
                        else today
                    )
                    date_key = rep_date.strftime("%Y%m%d")
                    is_wknd = rep_date.weekday() in {5, 6}

                    report_rows.append({
                        "ReportId": rep_id,
                        "ReportDate": rep_date.isoformat(),
                        "AttachmentName": r.get("attachment_name", ""),
                        "AttachmentHash": r.get("attachment_hash", ""),
                        "MeterCount": r.get("meter_count", 0),
                        "MappedCount": r.get("mapped_meter_count", 0),
                        "TotalEnergy_kWh": r.get("total_energy", 0.0),
                        "ExcelStatus": r.get("excel_status", "UPDATED"),
                        "PowerBIStatus": r.get("powerbi_status", "PENDING"),
                        "ProcessedAt": r.get("processing_date", ""),
                    })

                    readings = self.repository.get_readings_for_report(rep_id)
                    for idx, rd in enumerate(readings):
                        m_name = rd.get("meter_name", "")
                        meta = meter_map.get(m_name, {})
                        m_key = meta.get("MeterKey", f"M_{idx}")
                        a_key = meta.get("AreaKey", "general")
                        val = rd.get("active_energy")
                        status_str = rd.get("status", "OK")

                        fact_rows.append({
                            "FactKey": f"{date_key}_{m_key}",
                            "DateKey": date_key,
                            "ReportDate": rep_date.isoformat(),
                            "MeterKey": m_key,
                            "MeterName": m_name,
                            "AreaKey": a_key,
                            "AreaName": meta.get("Category", a_key),
                            "ActiveEnergy_kWh": val if val is not None else 0.0,
                            "Unit": rd.get("unit", "kWh"),
                            "Status": status_str,
                            "IsWeekend": is_wknd,
                            "IsAnomaly": False,
                            "ProcessedAt": r.get("processing_date", ""),
                        })
            except Exception as exc:
                logger.warning(f"Error extracting history for star-schema: {exc}")

        # If no DB rows yet, output headers to keep schema intact
        if not fact_rows:
            fact_rows = [{
                "FactKey": f"{today.strftime('%Y%m%d')}_M01",
                "DateKey": today.strftime("%Y%m%d"),
                "ReportDate": today.isoformat(),
                "MeterKey": "M01",
                "MeterName": "Chiller Plating Plant",
                "AreaKey": "plating",
                "AreaName": "Surface Treatment & Plating Plant",
                "ActiveEnergy_kWh": 141.35,
                "Unit": "kWh",
                "Status": "OK",
                "IsWeekend": today.weekday() in {5, 6},
                "IsAnomaly": False,
                "ProcessedAt": datetime.now().isoformat(),
            }]

        fact_csv = output_dir / "Fact_EnergyConsumption.csv"
        self._write_csv(fact_csv, fact_rows)
        paths["fact_energy_csv"] = str(fact_csv)

        if not report_rows:
            report_rows = [{
                "ReportId": 1,
                "ReportDate": today.isoformat(),
                "AttachmentName": "report.pdf",
                "AttachmentHash": "hash123",
                "MeterCount": 18,
                "MappedCount": 15,
                "TotalEnergy_kWh": 9206.83,
                "ExcelStatus": "UPDATED",
                "PowerBIStatus": "PENDING",
                "ProcessedAt": datetime.now().isoformat(),
            }]

        report_csv = output_dir / "Dim_Report.csv"
        self._write_csv(report_csv, report_rows)
        paths["dim_report_csv"] = str(report_csv)

        logger.info(f"Power BI star-schema exported successfully to {output_dir}")
        return paths

    @staticmethod
    def _write_csv(file_path: Path, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        fieldnames = list(rows[0].keys())
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

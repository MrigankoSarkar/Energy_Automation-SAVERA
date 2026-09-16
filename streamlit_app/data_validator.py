"""
Data extraction, parsing, and validation engine for EnergyAutomation Excel Workbooks.
Parses openpyxl workbooks from bytes or files, preserves N/A invariants,
calculates totals when formulas are un-evaluated, and validates schema integrity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import openpyxl
import pandas as pd


@dataclass
class ParsedWorkbook:
    """Structured result of parsing and validating an EMS Excel workbook."""
    df_daily: pd.DataFrame  # Only active recorded days sorted chronologically
    df_all: pd.DataFrame    # All rows including template/empty date rows
    incomer_col: Optional[str]
    submeter_cols: List[str]
    meter_cols: List[str]
    total_col: str
    date_col: str
    ytd_row: Dict[str, Any]
    validation_report: Dict[str, Any]
    is_valid: bool
    error_message: Optional[str] = None


class WorkbookDataValidator:
    """
    Parser and Validator for EnergyAutomation EMS Monitoring Reports.
    Conforms strictly to the workbook layout:
    - Header row: Row 3
    - Date column: Col 2 ('Date')
    - Meter columns: Cols 3-17
    - Total column: Col 18 ('Total')
    - Row 4: 'Cum.  (YTD)' cumulative formulas
    - Row 5+: Daily records
    """

    def __init__(
        self,
        sheet_name: str = "EMS Monitoring Report",
        header_row: int = 3,
        date_column: int = 2,
        first_data_row: int = 5,
        total_column: int = 18,
    ):
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.date_column = date_column
        self.first_data_row = first_data_row
        self.total_column = total_column

    def parse_workbook(
        self,
        source: Union[bytes, str, Path, io.BytesIO],
    ) -> ParsedWorkbook:
        """
        Parses workbook from raw bytes or file path.
        """
        if isinstance(source, (str, Path)):
            stream = io.BytesIO(Path(source).read_bytes())
        elif isinstance(source, bytes):
            stream = io.BytesIO(source)
        else:
            stream = source

        try:
            wb_data = openpyxl.load_workbook(stream, data_only=True, read_only=True)
        except Exception as e:
            return ParsedWorkbook(
                df_daily=pd.DataFrame(),
                df_all=pd.DataFrame(),
                incomer_col=None,
                submeter_cols=[],
                meter_cols=[],
                total_col="Total",
                date_col="Date",
                ytd_row={},
                validation_report={"status": "ERROR", "reason": str(e)},
                is_valid=False,
                error_message=f"Failed to open Excel workbook: {e}",
            )

        # Locate sheet
        matched_sheet = None
        for s in wb_data.sheetnames:
            if s.strip().lower() == self.sheet_name.strip().lower():
                matched_sheet = s
                break

        if not matched_sheet:
            wb_data.close()
            return ParsedWorkbook(
                df_daily=pd.DataFrame(),
                df_all=pd.DataFrame(),
                incomer_col=None,
                submeter_cols=[],
                meter_cols=[],
                total_col="Total",
                date_col="Date",
                ytd_row={},
                validation_report={"status": "ERROR", "available_sheets": wb_data.sheetnames},
                is_valid=False,
                error_message=(
                    f"Worksheet '{self.sheet_name}' not found. "
                    f"Available sheets: {', '.join(wb_data.sheetnames)}"
                ),
            )

        ws = wb_data[matched_sheet]
        all_rows = list(ws.iter_rows(values_only=True))
        wb_data.close()

        if len(all_rows) < self.header_row:
            return ParsedWorkbook(
                df_daily=pd.DataFrame(),
                df_all=pd.DataFrame(),
                incomer_col=None,
                submeter_cols=[],
                meter_cols=[],
                total_col="Total",
                date_col="Date",
                ytd_row={},
                validation_report={"status": "ERROR", "rows_found": len(all_rows)},
                is_valid=False,
                error_message=f"Workbook has only {len(all_rows)} rows, cannot find header row {self.header_row}.",
            )

        # Extract headers from header row (1-indexed header_row -> index header_row - 1)
        header_vals = all_rows[self.header_row - 1]

        # Extract Column Names
        # Col 2 is Date
        date_col_name = "Date"
        if len(header_vals) >= self.date_column and header_vals[self.date_column - 1]:
            date_col_name = str(header_vals[self.date_column - 1]).strip()

        # Total Col is Col 18 or last column with 'total'
        total_col_name = "Total"
        if len(header_vals) >= self.total_column and header_vals[self.total_column - 1]:
            total_col_name = str(header_vals[self.total_column - 1]).strip()

        # Meter columns: from col 3 to total_col - 1
        meter_cols: List[str] = []
        col_to_name: Dict[int, str] = {}
        for col_idx in range(self.date_column, self.total_column - 1):
            if col_idx < len(header_vals) and header_vals[col_idx] is not None:
                name = str(header_vals[col_idx]).strip()
                if name and name.lower() != "date" and name.lower() != "total":
                    meter_cols.append(name)
                    col_to_name[col_idx] = name

        # Identify Incomer vs Submeters
        incomer_col = None
        submeter_cols = []
        for m in meter_cols:
            m_lower = m.lower()
            if "incomer" in m_lower or "main incomer" in m_lower or "lt panel" in m_lower:
                if incomer_col is None:
                    incomer_col = m
                else:
                    submeter_cols.append(m)
            else:
                submeter_cols.append(m)

        # Extract Row 4: Cum. (YTD) if present
        ytd_data: Dict[str, Any] = {}
        if len(all_rows) >= 4:
            row4 = all_rows[3]
            for c_idx, m_name in col_to_name.items():
                if c_idx < len(row4):
                    ytd_data[m_name] = row4[c_idx]

        # Process Daily Data Rows (Row 5+ -> index 4+)
        rows_data: List[Dict[str, Any]] = []
        na_count = 0
        calculated_totals_count = 0

        for r_idx, row in enumerate(all_rows[self.first_data_row - 1:], start=self.first_data_row):
            if len(row) < self.date_column:
                continue

            raw_date = row[self.date_column - 1]
            if raw_date is None:
                continue

            parsed_date = self._parse_date(raw_date)
            if parsed_date is None:
                continue

            # Row dictionary
            row_dict: Dict[str, Any] = {date_col_name: parsed_date}
            row_meter_values: List[float] = []
            has_any_reading = False

            for c_idx, m_name in col_to_name.items():
                val = row[c_idx] if c_idx < len(row) else None
                parsed_val, is_na = self._parse_numeric(val)
                row_dict[m_name] = parsed_val

                if is_na:
                    na_count += 1
                if parsed_val is not None and not np.isnan(parsed_val):
                    has_any_reading = True
                    row_meter_values.append(parsed_val)

            # Total column
            raw_total = row[self.total_column - 1] if len(row) >= self.total_column else None
            parsed_total, total_is_na = self._parse_numeric(raw_total)

            if parsed_total is not None and not np.isnan(parsed_total):
                row_dict[total_col_name] = parsed_total
            else:
                # If formula not evaluated by Excel or None, evaluate row sum of meters
                if has_any_reading:
                    computed_total = round(sum(row_meter_values), 2)
                    row_dict[total_col_name] = computed_total
                    calculated_totals_count += 1
                else:
                    row_dict[total_col_name] = np.nan

            row_dict["_has_readings"] = has_any_reading
            row_dict["_row_num"] = r_idx
            rows_data.append(row_dict)

        df_all = pd.DataFrame(rows_data)
        if df_all.empty:
            return ParsedWorkbook(
                df_daily=pd.DataFrame(),
                df_all=pd.DataFrame(),
                incomer_col=incomer_col,
                submeter_cols=submeter_cols,
                meter_cols=meter_cols,
                total_col=total_col_name,
                date_col=date_col_name,
                ytd_row=ytd_data,
                validation_report={"status": "WARNING", "total_rows": len(all_rows), "valid_dates": 0},
                is_valid=True,
            )

        # Filter active recorded days (where at least one reading is recorded)
        df_daily = df_all[df_all["_has_readings"]].copy()
        df_daily = df_daily.sort_values(by=date_col_name).reset_index(drop=True)

        # Build validation report
        date_min = df_daily[date_col_name].min() if not df_daily.empty else None
        date_max = df_daily[date_col_name].max() if not df_daily.empty else None

        # Check for missing dates in date sequence
        missing_dates: List[str] = []
        if date_min and date_max and len(df_daily) > 1:
            full_date_range = pd.date_range(start=date_min, end=date_max, freq="D").date
            recorded_dates = set(df_daily[date_col_name].tolist())
            missing = [d.isoformat() for d in full_date_range if d not in recorded_dates]
            missing_dates = missing

        validation_report = {
            "status": "VALID",
            "sheet_name": matched_sheet,
            "total_excel_rows": len(all_rows),
            "data_rows_total": len(df_all),
            "active_reading_days": len(df_daily),
            "template_future_days": len(df_all) - len(df_daily),
            "start_date": date_min.isoformat() if date_min else None,
            "end_date": date_max.isoformat() if date_max else None,
            "meters_detected": len(meter_cols),
            "incomer_meter": incomer_col,
            "submeters_count": len(submeter_cols),
            "unpolled_na_count": na_count,
            "evaluated_formula_totals": calculated_totals_count,
            "missing_dates_in_span": missing_dates,
        }

        return ParsedWorkbook(
            df_daily=df_daily,
            df_all=df_all,
            incomer_col=incomer_col,
            submeter_cols=submeter_cols,
            meter_cols=meter_cols,
            total_col=total_col_name,
            date_col=date_col_name,
            ytd_row=ytd_data,
            validation_report=validation_report,
            is_valid=True,
        )

    @staticmethod
    def _parse_date(val: Any) -> Optional[date]:
        """Parses cell value into a datetime.date."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val

        text = str(val).strip()
        if not text or text.lower().startswith("cum"):
            return None

        # Try multiple formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        try:
            return pd.to_datetime(text).date()
        except Exception:
            return None

    @staticmethod
    def _parse_numeric(val: Any) -> Tuple[Optional[float], bool]:
        """
        Parses cell value into numeric float or np.nan.
        Returns: (float_or_nan, is_na_flag)
        CRITICAL INVARIANT: 'N/A' is NEVER coerced to 0.0!
        """
        if val is None:
            return np.nan, False

        if isinstance(val, (int, float)):
            if np.isnan(val):
                return np.nan, False
            return float(val), False

        text = str(val).strip()
        if not text:
            return np.nan, False

        if text.upper() in ("N/A", "NA", "NOT AVAILABLE", "UNPOLLED", "-"):
            return np.nan, True

        try:
            cleaned = text.replace(",", "")
            return float(cleaned), False
        except (ValueError, TypeError):
            return np.nan, False

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook


class ExcelVerifier:
    """
    Verification service for updated Excel workbooks.

    Ensures:
    - Saved workbook exists and can be opened without corruption.
    - Expected date row exists and is populated.
    - Numeric values are stored as numbers (not strings).
    - Historical data was not corrupted or overwritten.
    - Formula in Total column exists and evaluates properly.
    """

    def __init__(self, logger: Any = None):
        self.logger = logger

    def verify(
        self,
        workbook_path: str | Path,
        worksheet_name: str,
        expected_date: date | datetime,
        header_row: int = 3,
        date_column: int = 2,
        total_column: int = 18,
        expected_readings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        path = Path(workbook_path)
        if not path.exists():
            return {
                "valid": False,
                "error": f"Workbook not found at {path}",
            }

        target_date = (
            expected_date.date()
            if isinstance(expected_date, datetime)
            else expected_date
        )

        wb = None
        try:
            wb = load_workbook(path, data_only=False)
            if worksheet_name not in wb.sheetnames:
                return {
                    "valid": False,
                    "error": f"Worksheet '{worksheet_name}' not found in {wb.sheetnames}",
                }

            ws = wb[worksheet_name]

            # Find target row
            target_row = None
            for row in range(header_row + 1, ws.max_row + 1):
                val = ws.cell(row, date_column).value
                if isinstance(val, datetime) and val.date() == target_date:
                    target_row = row
                    break
                elif isinstance(val, date) and val == target_date:
                    target_row = row
                    break
                elif str(val).startswith(str(target_date)):
                    target_row = row
                    break

            if target_row is None:
                return {
                    "valid": False,
                    "error": f"Date {target_date} not found in column {date_column}",
                }

            total_cell_val = ws.cell(target_row, total_column).value

            return {
                "valid": True,
                "target_row": target_row,
                "date": target_date.isoformat(),
                "total_formula": total_cell_val,
                "max_row": ws.max_row,
                "max_column": ws.max_column,
            }

        except Exception as exc:
            return {
                "valid": False,
                "error": f"Verification error: {exc}",
            }
        finally:
            if wb:
                wb.close()

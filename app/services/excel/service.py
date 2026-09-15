import os
import shutil
from copy import copy
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.contracts.excel import ExcelUpdateResult
from app.services.excel.mapper import ExcelMapper
from app.services.excel.verifier import ExcelVerifier


class ExcelService:
    """
    Excel service for EnergyAutomation.

    Compatible with:
        1. Dependency-container keyword construction.
        2. ExcelService(settings, logger).
        3. Workflow calls using validated_report.
        4. Workflow calls using report_date/readings keyword arguments.
    """

    def __init__(
        self,
        settings: Optional[dict[str, Any]] = None,
        logger: Any = None,
        workbook_path: Optional[str | Path] = None,
        excel_file: Optional[str | Path] = None,
        file_path: Optional[str | Path] = None,
        path: Optional[str | Path] = None,
        worksheet: Optional[str] = None,
        worksheet_name: Optional[str] = None,
        sheet_name: Optional[str] = None,
        header_row: Optional[int] = None,
        date_column: Optional[int] = None,
        first_data_row: Optional[int] = None,
        total_column: Optional[int] = None,
        update_total: Optional[bool] = None,
        fail_on_unmapped_numeric_meter: Optional[bool] = None,
        **kwargs: Any,
    ):
        self.settings = settings or {}
        self.logger = logger

        excel_settings = self._get_excel_settings(self.settings)

        configured_path = (
            workbook_path
            or excel_file
            or file_path
            or path
            or excel_settings.get("file")
            or excel_settings.get("workbook_path")
            or excel_settings.get("path")
        )

        self.workbook_path = (
            self._normalize_path(configured_path)
            if configured_path
            else None
        )

        self.worksheet_name = (
            worksheet
            or worksheet_name
            or sheet_name
            or excel_settings.get("worksheet")
            or excel_settings.get("worksheet_name")
            or excel_settings.get("sheet_name")
            or "EMS Monitoring Report"
        )

        self.header_row = int(
            header_row
            if header_row is not None
            else excel_settings.get("header_row", 3)
        )

        self.date_column = int(
            date_column
            if date_column is not None
            else excel_settings.get("date_column", 2)
        )

        self.first_data_row = int(
            first_data_row
            if first_data_row is not None
            else excel_settings.get("first_data_row", 5)
        )

        self.total_column = int(
            total_column
            if total_column is not None
            else excel_settings.get("total_column", 18)
        )

        self.update_total = bool(
            update_total
            if update_total is not None
            else excel_settings.get("update_total", True)
        )

        self.fail_on_unmapped_numeric_meter = bool(
            fail_on_unmapped_numeric_meter
            if fail_on_unmapped_numeric_meter is not None
            else excel_settings.get(
                "fail_on_unmapped_numeric_meter",
                False,
            )
        )

        self.mapper = ExcelMapper()
        self.verifier = ExcelVerifier(logger=self.logger)

    def get_existing_dates(self) -> list[date]:
        """
        Read all existing dates in the date column of the active worksheet.
        """
        workbook_path = self._require_workbook()
        wb = load_workbook(
            workbook_path,
            read_only=True,
            data_only=True,
        )
        try:
            if self.worksheet_name not in wb.sheetnames:
                return []
            ws = wb[self.worksheet_name]
            dates: list[date] = []
            for row in range(self.first_data_row, ws.max_row + 1):
                val = ws.cell(row, self.date_column).value
                coerced = self._coerce_date(val)
                if coerced:
                    dates.append(coerced)
            return dates
        finally:
            wb.close()

    def get_report_dates(self) -> list[date]:
        """Compatibility alias."""
        return self.get_existing_dates()


    # ================================================================
    # Configuration
    # ================================================================

    @staticmethod
    def _get_excel_settings(
        settings: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        if not settings:
            return {}

        excel = settings.get("excel", settings)

        return excel if isinstance(excel, dict) else {}

    @staticmethod
    def _normalize_path(value: Any, base_dir: Optional[Path] = None) -> Optional[Path]:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        # Robustly strip any repeated or mixed surrounding quotes and whitespace
        while len(text) >= 2 and (
            (text[0] == '"' and text[-1] == '"')
            or (text[0] == "'" and text[-1] == "'")
        ):
            text = text[1:-1].strip()

        if not text:
            return None

        raw_path = Path(text).expanduser()
        if raw_path.is_absolute():
            return raw_path.resolve()

        root = base_dir or Path.cwd()
        return (root / raw_path).resolve()

    def _apply_settings(
        self,
        settings: Optional[dict[str, Any]],
    ) -> None:
        if not settings:
            return

        excel = self._get_excel_settings(settings)

        if not excel:
            return

        workbook_file = (
            excel.get("file")
            or excel.get("workbook_path")
            or excel.get("path")
        )

        if workbook_file:
            self.workbook_path = self._normalize_path(
                workbook_file
            )

        if excel.get("worksheet") is not None:
            self.worksheet_name = str(
                excel["worksheet"]
            )
        elif excel.get("worksheet_name") is not None:
            self.worksheet_name = str(
                excel["worksheet_name"]
            )
        elif excel.get("sheet_name") is not None:
            self.worksheet_name = str(
                excel["sheet_name"]
            )

        if excel.get("header_row") is not None:
            self.header_row = int(
                excel["header_row"]
            )

        if excel.get("date_column") is not None:
            self.date_column = int(
                excel["date_column"]
            )

        if excel.get("first_data_row") is not None:
            self.first_data_row = int(
                excel["first_data_row"]
            )

        if excel.get("total_column") is not None:
            self.total_column = int(
                excel["total_column"]
            )

        if excel.get("update_total") is not None:
            self.update_total = bool(
                excel["update_total"]
            )

        if (
            excel.get(
                "fail_on_unmapped_numeric_meter"
            )
            is not None
        ):
            self.fail_on_unmapped_numeric_meter = bool(
                excel[
                    "fail_on_unmapped_numeric_meter"
                ]
            )

    # ================================================================
    # Logging
    # ================================================================

    def _log(
        self,
        level: str,
        message: str,
    ) -> None:
        if self.logger is None:
            return

        method = getattr(
            self.logger,
            level,
            None,
        )

        if callable(method):
            try:
                method(message)
                return
            except Exception:
                pass

        generic = getattr(
            self.logger,
            "log",
            None,
        )

        if callable(generic):
            try:
                generic(
                    level.upper(),
                    message,
                )
            except Exception:
                pass

    # ================================================================
    # Workbook
    # ================================================================

    def _require_workbook(self) -> Path:
        if self.workbook_path is None:
            raise ValueError(
                "Excel workbook path is not configured."
            )

        path = self._normalize_path(self.workbook_path)
        if path is None:
            raise ValueError("Excel workbook path is invalid or empty.")

        if not path.exists():
            raise FileNotFoundError(
                f"Excel workbook does not exist: {path}"
            )

        if not path.is_file():
            raise FileNotFoundError(
                f"Excel workbook is not a file: {path}"
            )

        return path

    def get_headers(self) -> list[str]:
        workbook_path = self._require_workbook()

        wb = load_workbook(
            workbook_path,
            read_only=True,
            data_only=False,
        )

        try:
            if self.worksheet_name not in wb.sheetnames:
                raise ValueError(
                    f"Worksheet '{self.worksheet_name}' "
                    f"does not exist. Available worksheets: "
                    f"{', '.join(wb.sheetnames)}"
                )

            ws = wb[self.worksheet_name]

            headers = []

            for column in range(
                1,
                ws.max_column + 1,
            ):
                value = ws.cell(
                    self.header_row,
                    column,
                ).value

                headers.append(
                    ""
                    if value is None
                    else str(value).strip()
                )

            return headers

        finally:
            wb.close()

    @staticmethod
    def _normalize_header(value: Any) -> str:
        if value is None:
            return ""

        text = str(value)

        text = text.replace(
            "\u00a0",
            " ",
        )

        text = text.replace(
            "\r",
            " ",
        )

        text = text.replace(
            "\n",
            " ",
        )

        return " ".join(
            text.split()
        ).strip().casefold()

    def _build_header_map(
        self,
        ws,
    ) -> dict[str, Any]:
        raw_headers = [
            ws.cell(
                self.header_row,
                column,
            ).value
            for column in range(1, ws.max_column + 1)
        ]
        return self.mapper.build_header_map(
            raw_headers,
            start_column=1,
        )

    # ================================================================
    # Date helpers
    # ================================================================

    @staticmethod
    def _coerce_date(
        value: Any,
    ) -> Optional[date]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        text = str(value).strip()

        if not text:
            return None

        formats = (
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
        )

        for fmt in formats:
            try:
                return datetime.strptime(
                    text,
                    fmt,
                ).date()
            except ValueError:
                continue

        return None

    def _find_existing_date_row(
        self,
        ws,
        report_date: date,
    ) -> Optional[int]:
        for row in range(
            self.first_data_row,
            ws.max_row + 1,
        ):
            value = ws.cell(
                row,
                self.date_column,
            ).value

            existing_date = self._coerce_date(
                value
            )

            if existing_date == report_date:
                return row

        return None

    # ================================================================
    # Generic object helpers
    # ================================================================

    @staticmethod
    def _get_attr(
        obj: Any,
        *names: str,
        default: Any = None,
    ) -> Any:
        if obj is None:
            return default

        if isinstance(obj, dict):
            for name in names:
                if name in obj:
                    return obj[name]

            return default

        for name in names:
            if hasattr(obj, name):
                return getattr(
                    obj,
                    name,
                )

        return default

    # ================================================================
    # Report extraction
    # ================================================================

    def _extract_report_date(
        self,
        report: Any,
        explicit_date: Any = None,
    ) -> date:
        value = (
            explicit_date
            if explicit_date is not None
            else self._get_attr(
                report,
                "report_date",
                "date",
                "reading_date",
            )
        )

        result = self._coerce_date(
            value
        )

        if result is None:
            raise ValueError(
                "The report does not contain "
                "a valid report date."
            )

        return result

    def _extract_readings(
        self,
        report: Any,
        explicit_readings: Any = None,
    ) -> list[Any]:
        if explicit_readings is not None:
            return list(explicit_readings)

        readings = self._get_attr(
            report,
            "readings",
            "meter_readings",
            "items",
            default=[],
        )

        if readings is None:
            return []

        return list(readings)

    def _extract_meter_name(
        self,
        reading: Any,
    ) -> str:
        value = self._get_attr(
            reading,
            "meter_name",
            "name",
            "meter",
            "device_name",
        )

        if value is None:
            return ""

        return " ".join(
            str(value)
            .replace("\u00a0", " ")
            .split()
        ).strip()

    def _extract_status(
        self,
        reading: Any,
    ) -> str:
        value = self._get_attr(
            reading,
            "status",
            default="",
        )

        if value is None:
            return ""

        return str(value).strip().upper()

    def _extract_energy(
        self,
        reading: Any,
    ) -> Optional[float]:
        value = self._get_attr(
            reading,
            "active_energy",
            "energy",
            "value",
            "reading",
            "consumption",
            "kwh",
        )

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # ================================================================
    # Excel formatting
    # ================================================================

    @staticmethod
    def _copy_cell_style(
        source,
        target,
    ) -> None:
        if source.has_style:
            target._style = copy(
                source._style
            )

        if source.number_format:
            target.number_format = (
                source.number_format
            )

        if source.alignment:
            target.alignment = copy(
                source.alignment
            )

        if source.protection:
            target.protection = copy(
                source.protection
            )

    def _copy_row_style(
        self,
        ws,
        source_row: int,
        target_row: int,
    ) -> None:
        if source_row <= 0:
            return

        for column in range(
            1,
            max(
                ws.max_column,
                self.total_column,
            ) + 1,
        ):
            self._copy_cell_style(
                ws.cell(
                    source_row,
                    column,
                ),
                ws.cell(
                    target_row,
                    column,
                ),
            )

        height = ws.row_dimensions[
            source_row
        ].height

        if height is not None:
            ws.row_dimensions[
                target_row
            ].height = height

    # ================================================================
    # Main Excel update
    # ================================================================

    def update_existing_workbook(
        self,
        validated_report: Any = None,
        readings: Any = None,
        report_date: Any = None,
        settings: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ExcelUpdateResult:
        """
        Update the existing workbook.

        Supported calling styles:

        update_existing_workbook(
            validated_report
        )

        or:

        update_existing_workbook(
            report_date=report_date,
            readings=readings
        )

        Additional keyword arguments are intentionally accepted so
        small differences between workflow versions do not crash
        the application.
        """

        if settings:
            self._apply_settings(
                settings
            )

        # ------------------------------------------------------------
        # Determine report object
        # ------------------------------------------------------------

        report = validated_report

        if report is not None:
            wrapped_report = self._get_attr(
                report,
                "report",
                default=None,
            )

            if wrapped_report is not None:
                report = wrapped_report

        # ------------------------------------------------------------
        # Some workflow versions may use "date"
        # instead of "report_date".
        # ------------------------------------------------------------

        if report_date is None:
            report_date = kwargs.get(
                "date"
            )

        if readings is None:
            readings = kwargs.get(
                "meter_readings"
            )

        # ------------------------------------------------------------
        # Extract values
        # ------------------------------------------------------------

        final_report_date = (
            self._extract_report_date(
                report,
                report_date,
            )
        )

        final_readings = (
            self._extract_readings(
                report,
                readings,
            )
        )

        if not final_readings:
            raise ValueError(
                "No meter readings were supplied "
                "to ExcelService."
            )

        workbook_path = (
            self._require_workbook()
        )

        self._log(
            "info",
            (
                "Starting Excel update: "
                f"{workbook_path}"
            ),
        )

        self._log(
            "info",
            (
                f"Worksheet='{self.worksheet_name}', "
                f"ReportDate={final_report_date}"
            ),
        )

        # ------------------------------------------------------------
        # Load workbook
        # ------------------------------------------------------------

        wb = load_workbook(
            workbook_path,
            data_only=False,
        )

        try:
            if (
                self.worksheet_name
                not in wb.sheetnames
            ):
                raise ValueError(
                    f"Worksheet '{self.worksheet_name}' "
                    f"does not exist. Available worksheets: "
                    f"{', '.join(wb.sheetnames)}"
                )

            ws = wb[
                self.worksheet_name
            ]

            header_map = (
                self._build_header_map(ws)
            )

            if not header_map:
                raise ValueError(
                    "No Excel headers were found "
                    f"on row {self.header_row}."
                )

            # --------------------------------------------------------
            # Find existing date or create new row
            # --------------------------------------------------------

            target_row = (
                self._find_existing_date_row(
                    ws,
                    final_report_date,
                )
            )

            is_new_row = (
                target_row is None
            )

            if target_row is None:
                target_row = max(
                    self.first_data_row,
                    ws.max_row + 1,
                )

                if target_row > self.first_data_row:
                    self._copy_row_style(
                        ws,
                        target_row - 1,
                        target_row,
                    )

                self._log(
                    "info",
                    (
                        f"Creating Excel row "
                        f"{target_row} for "
                        f"{final_report_date}."
                    ),
                )

            else:
                self._log(
                    "info",
                    (
                        f"Updating existing Excel row "
                        f"{target_row} for "
                        f"{final_report_date}."
                    ),
                )

            # --------------------------------------------------------
            # Write date
            # --------------------------------------------------------

            date_cell = ws.cell(
                target_row,
                self.date_column,
            )

            date_cell.value = (
                final_report_date
            )

            if (
                not date_cell.number_format
                or date_cell.number_format
                == "General"
            ):
                date_cell.number_format = (
                    "dd-mm-yyyy"
                )

            # --------------------------------------------------------
            # Meter updates
            # --------------------------------------------------------

            updated_cells = []
            skipped_meters = []
            numeric_columns = []

            for reading in final_readings:

                meter_name = (
                    self._extract_meter_name(
                        reading
                    )
                )

                if not meter_name:
                    skipped_meters.append(
                        "<unknown meter>"
                    )
                    continue

                column, matched_header = (
                    self.mapper.find(
                        meter_name,
                        header_map,
                    )
                )

                if column is None:
                    normalized = (
                        self._normalize_header(
                            meter_name
                        )
                    )
                    column = header_map.get(
                        normalized
                    )

                status = (
                    self._extract_status(
                        reading
                    )
                )

                energy = (
                    self._extract_energy(
                        reading
                    )
                )

                # ----------------------------------------------------
                # N/A
                # ----------------------------------------------------

                if status in {
                    "N/A",
                    "NA",
                    "NOT_AVAILABLE",
                    "NOT AVAILABLE",
                }:
                    self._log(
                        "info",
                        (
                            f"N/A reading skipped: "
                            f"{meter_name}"
                        ),
                    )

                    skipped_meters.append(
                        f"{meter_name} (N/A)"
                    )

                    continue

                # ----------------------------------------------------
                # No numeric reading
                # ----------------------------------------------------

                if energy is None:
                    self._log(
                        "warning",
                        (
                            f"Non-numeric reading skipped: "
                            f"{meter_name}"
                        ),
                    )

                    skipped_meters.append(
                        (
                            f"{meter_name} "
                            "(no numeric value)"
                        )
                    )

                    continue

                # ----------------------------------------------------
                # Meter isn't in Excel
                # ----------------------------------------------------

                if column is None:
                    message = (
                        f"Numeric meter '{meter_name}' "
                        "is not mapped to an Excel column."
                    )

                    self._log(
                        "warning",
                        message,
                    )

                    skipped_meters.append(
                        f"{meter_name} (unmapped)"
                    )

                    if (
                        self.fail_on_unmapped_numeric_meter
                    ):
                        raise ValueError(
                            message
                        )

                    continue

                # ----------------------------------------------------
                # Prevent writing into Total column
                # ----------------------------------------------------

                if (
                    column
                    == self.total_column
                ):
                    message = (
                        f"Meter '{meter_name}' "
                        "maps to the Total column. "
                        "The meter value was skipped."
                    )

                    self._log(
                        "warning",
                        message,
                    )

                    skipped_meters.append(
                        f"{meter_name} (total column)"
                    )

                    continue

                # ----------------------------------------------------
                # Write value
                # ----------------------------------------------------

                cell = ws.cell(
                    target_row,
                    column,
                )

                cell.value = energy

                if (
                    not cell.number_format
                    or cell.number_format
                    == "General"
                ):
                    cell.number_format = (
                        "0.00"
                    )

                coordinate = (
                    f"{get_column_letter(column)}"
                    f"{target_row}"
                )

                updated_cells.append(
                    coordinate
                )

                numeric_columns.append(
                    column
                )

                self._log(
                    "info",
                    (
                        f"Excel update: "
                        f"{meter_name} = "
                        f"{energy:.2f} kWh "
                        f"-> {coordinate}"
                    ),
                )

            # --------------------------------------------------------
            # Total
            # --------------------------------------------------------

            total_value = None

            if self.update_total:

                meter_columns = sorted(
                    set(numeric_columns)
                )

                meter_columns = [
                    column
                    for column in meter_columns
                    if (
                        column
                        != self.date_column
                        and column
                        != self.total_column
                    )
                ]

                if meter_columns:

                    # If columns form a contiguous range, use SUM(start:end) to preserve workbook convention
                    if meter_columns == list(
                        range(
                            meter_columns[0],
                            meter_columns[-1] + 1,
                        )
                    ):
                        first_col = get_column_letter(
                            meter_columns[0]
                        )
                        last_col = get_column_letter(
                            meter_columns[-1]
                        )
                        formula = (
                            f"=SUM({first_col}{target_row}:{last_col}{target_row})"
                        )
                    else:
                        references = [
                            (
                                f"{get_column_letter(column)}"
                                f"{target_row}"
                            )
                            for column in meter_columns
                        ]
                        formula = (
                            "="
                            + "+".join(
                                references
                            )
                        )

                    total_cell = ws.cell(
                        target_row,
                        self.total_column,
                    )

                    total_cell.value = formula
                    total_cell.number_format = (
                        "0.00"
                    )

                    total_coordinate = (
                        f"{get_column_letter(self.total_column)}"
                        f"{target_row}"
                    )

                    updated_cells.append(
                        total_coordinate
                    )

                    self._log(
                        "info",
                        (
                            f"Total formula written: "
                            f"{total_coordinate} = "
                            f"{formula}"
                        ),
                    )

                    # Calculate a numeric value ourselves.
                    total_value = 0.0

                    for column in meter_columns:
                        value = ws.cell(
                            target_row,
                            column,
                        ).value

                        if isinstance(
                            value,
                            (int, float),
                        ) and not isinstance(
                            value,
                            bool,
                        ):
                            total_value += float(
                                value
                            )

                    total_value = round(
                        total_value,
                        2,
                    )

            # --------------------------------------------------------
            # Pre-save backup & Atomic Save
            # --------------------------------------------------------

            backup_dir = Path("data") / "backups"
            backup_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            backup_file = (
                backup_dir
                / f"{workbook_path.stem}_{timestamp}.xlsx"
            )
            try:
                shutil.copy2(
                    workbook_path,
                    backup_file,
                )
                self._log(
                    "info",
                    f"Workbook backup created: {backup_file}",
                )
            except Exception as exc:
                self._log(
                    "warning",
                    f"Could not create pre-save backup: {exc}",
                )

            temp_path = workbook_path.with_suffix(
                ".tmp.xlsx"
            )

            wb.save(temp_path)
            wb.close()
            wb = None

            os.replace(
                temp_path,
                workbook_path,
            )

            self._log(
                "info",
                (
                    f"Excel workbook saved successfully: "
                    f"{workbook_path}"
                ),
            )

            # Verification of saved workbook
            verification = self.verifier.verify(
                workbook_path=workbook_path,
                worksheet_name=self.worksheet_name,
                expected_date=final_report_date,
                header_row=self.header_row,
                date_column=self.date_column,
                total_column=self.total_column,
            )

            if not verification.get("valid"):
                self._log(
                    "warning",
                    f"Post-save verification warning: {verification.get('error')}",
                )

        finally:
            if wb is not None:
                wb.close()

        # ------------------------------------------------------------
        # Result
        # ------------------------------------------------------------

        message = (
            "Excel workbook updated successfully "
            f"for {final_report_date}. "
            f"Updated cells: {len(updated_cells)}."
        )

        if is_new_row:
            message += (
                f" New row: {target_row}."
            )
        else:
            message += (
                f" Existing row: {target_row}."
            )

        if skipped_meters:
            message += (
                f" Skipped: "
                f"{len(skipped_meters)}."
            )

        return ExcelUpdateResult(
            success=True,
            workbook=str(workbook_path),
            worksheet=self.worksheet_name,
            report_date=str(final_report_date),
            updated_cells=updated_cells,
            skipped_meters=skipped_meters,
            total_value=total_value,
            message=message,
        )

    # ================================================================
    # Verification
    # ================================================================

    def verify_date_row(
        self,
        report_date: date,
    ) -> dict[str, Any]:

        workbook_path = (
            self._require_workbook()
        )

        wb = load_workbook(
            workbook_path,
            data_only=False,
        )

        try:
            if (
                self.worksheet_name
                not in wb.sheetnames
            ):
                return {
                    "success": False,
                    "error": (
                        f"Worksheet "
                        f"'{self.worksheet_name}' "
                        "does not exist."
                    ),
                }

            ws = wb[
                self.worksheet_name
            ]

            row = (
                self._find_existing_date_row(
                    ws,
                    report_date,
                )
            )

            if row is None:
                return {
                    "success": False,
                    "error": (
                        f"No row found for "
                        f"{report_date}."
                    ),
                }

            values = {}

            for column in range(
                1,
                ws.max_column + 1,
            ):
                header = ws.cell(
                    self.header_row,
                    column,
                ).value

                if header is None:
                    continue

                values[
                    str(header)
                ] = ws.cell(
                    row,
                    column,
                ).value

            return {
                "success": True,
                "row": row,
                "date": report_date,
                "values": values,
            }

        finally:
            wb.close()
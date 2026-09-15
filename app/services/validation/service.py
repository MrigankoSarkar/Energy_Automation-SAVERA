from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Iterable


class ValidationService:
    """
    Deterministic validation service for NBSense EMS reports.

    Responsibilities
    ----------------
    1. Validate the parsed report structure.
    2. Validate the report date.
    3. Validate meter readings.
    4. Accept numeric Active Energy readings.
    5. Accept explicit N/A readings without converting them to zero.
    6. Validate energy units.
    7. Detect duplicate meters.
    8. Optionally validate mappings against Excel headers.
    9. Return structured validation information for the workflow/UI.

    This class does NOT:
    - modify Excel files
    - download Gmail messages
    - modify PDFs
    - publish Power BI data
    - make AI decisions
    """

    def __init__(
        self,
        minimum_active_energy: float = 0.0,
        maximum_active_energy: float = 100_000_000.0,
        expected_unit: str = "kWh",
        fail_on_unmapped_numeric_meter: bool = False,
    ) -> None:

        self.minimum_active_energy = float(
            minimum_active_energy
        )

        self.maximum_active_energy = float(
            maximum_active_energy
        )

        self.expected_unit = (
            str(expected_unit or "kWh").strip()
        )

        self.fail_on_unmapped_numeric_meter = bool(
            fail_on_unmapped_numeric_meter
        )

    # ================================================================
    # PUBLIC API
    # ================================================================

    def validate_report(
        self,
        report: dict[str, Any],
        expected_date: datetime | None = None,
        expected_meters: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """
        Validate a complete parsed NBSense report.

        Returns a structured result:

        {
            "valid": bool,
            "success": bool,
            "status": str,
            "errors": list[str],
            "warnings": list[str],
            "validated_readings": list[dict],
            "report_date": datetime | None,
            "report_date_iso": str | None,
            "reading_count": int,
            "valid_reading_count": int,
            "na_reading_count": int
        }
        """

        errors: list[str] = []
        warnings: list[str] = []
        validated_readings: list[dict[str, Any]] = []

        # ------------------------------------------------------------
        # Validate top-level object
        # ------------------------------------------------------------

        if not isinstance(report, dict):
            return {
                "valid": False,
                "success": False,
                "status": "invalid_report",
                "errors": [
                    "Parsed report is not a dictionary."
                ],
                "warnings": [],
                "validated_readings": [],
                "report_date": None,
                "report_date_iso": None,
                "reading_count": 0,
                "valid_reading_count": 0,
                "na_reading_count": 0,
            }

        # ------------------------------------------------------------
        # Report date
        # ------------------------------------------------------------

        report_date = self._extract_report_date(
            report
        )

        if report_date is None:
            errors.append(
                "Report date is missing or invalid."
            )

        elif expected_date is not None:

            if (
                report_date.date()
                != expected_date.date()
            ):
                errors.append(
                    "Report date does not match the "
                    f"expected date: expected "
                    f"{expected_date.date()}, received "
                    f"{report_date.date()}."
                )

        # ------------------------------------------------------------
        # Extract readings
        # ------------------------------------------------------------

        readings = self._extract_readings(
            report
        )

        if not readings:
            errors.append(
                "No meter readings were found in the report."
            )

        # ------------------------------------------------------------
        # Expected Excel meters
        # ------------------------------------------------------------

        expected_meter_set = {
            self.normalize_meter_name(name)
            for name in (
                expected_meters or []
            )
            if name
        }

        # ------------------------------------------------------------
        # Validate readings
        # ------------------------------------------------------------

        valid_reading_count = 0
        na_reading_count = 0

        for index, raw_reading in enumerate(
            readings,
            start=1,
        ):

            if not isinstance(
                raw_reading,
                dict,
            ):
                errors.append(
                    f"Reading #{index} is not a dictionary."
                )
                continue

            reading = (
                self._normalize_reading_structure(
                    raw_reading
                )
            )

            result = self.validate_reading(
                reading
            )

            meter_name = reading.get(
                "meter_name"
            )

            # --------------------------------------------------------
            # Valid reading
            # --------------------------------------------------------

            if result["valid"]:

                if result["status"] == "N/A":

                    na_reading_count += 1

                    validated_readings.append(
                        {
                            **reading,
                            "validation_status": "N/A",
                        }
                    )

                else:

                    valid_reading_count += 1

                    validated_readings.append(
                        {
                            **reading,
                            "validation_status": "VALID",
                        }
                    )

            # --------------------------------------------------------
            # Invalid reading
            # --------------------------------------------------------

            else:

                reading_errors = result.get(
                    "errors",
                    [],
                )

                if not reading_errors:
                    reading_errors = [
                        "Unknown validation error."
                    ]

                for error in reading_errors:

                    if meter_name:
                        errors.append(
                            f"{meter_name}: {error}"
                        )
                    else:
                        errors.append(
                            f"Reading #{index}: {error}"
                        )

            # --------------------------------------------------------
            # Excel mapping validation
            # --------------------------------------------------------

            if (
                expected_meter_set
                and meter_name
            ):

                normalized_meter = (
                    self.normalize_meter_name(
                        meter_name
                    )
                )

                if (
                    normalized_meter
                    not in expected_meter_set
                ):

                    if (
                        result.get("status")
                        == "VALID"
                        and result.get("value")
                        is not None
                    ):

                        message = (
                            "Numeric meter is not mapped "
                            "to an expected Excel header: "
                            f"{meter_name}"
                        )

                        if (
                            self.fail_on_unmapped_numeric_meter
                        ):
                            errors.append(
                                message
                            )
                        else:
                            warnings.append(
                                message
                            )

        # ------------------------------------------------------------
        # Duplicate detection
        # ------------------------------------------------------------

        duplicates = (
            self._find_duplicate_meters(
                readings
            )
        )

        for meter_name in duplicates:

            errors.append(
                "Duplicate meter reading detected: "
                f"{meter_name}"
            )

        # ------------------------------------------------------------
        # Final state
        # ------------------------------------------------------------

        valid = len(errors) == 0

        if valid:
            status = "valid"
        elif readings:
            status = "validation_failed"
        else:
            status = "invalid_report"

        return {
            "valid": valid,
            "success": valid,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "validated_readings": validated_readings,
            "report_date": report_date,
            "report_date_iso": (
                report_date.strftime(
                    "%Y-%m-%d"
                )
                if report_date
                else None
            ),
            "reading_count": len(readings),
            "valid_reading_count": (
                valid_reading_count
            ),
            "na_reading_count": (
                na_reading_count
            ),
        }

    def validate(
        self,
        report: dict[str, Any],
        expected_date: datetime | None = None,
        expected_meters: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias."""

        return self.validate_report(
            report,
            expected_date=expected_date,
            expected_meters=expected_meters,
        )

    # ================================================================
    # READING VALIDATION
    # ================================================================

    def validate_reading(
        self,
        reading: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate one EMS meter reading.

        N/A is explicitly valid.

        N/A is NEVER converted to zero.
        """

        errors: list[str] = []

        meter_name = reading.get(
            "meter_name"
        )

        value = reading.get(
            "active_energy"
        )

        unit = reading.get(
            "unit"
        )

        status = reading.get(
            "status"
        )

        # ------------------------------------------------------------
        # Meter name
        # ------------------------------------------------------------

        if not meter_name:
            errors.append(
                "Meter name is missing."
            )

        # ------------------------------------------------------------
        # Normalize status
        # ------------------------------------------------------------

        if status is not None:

            status = str(
                status
            ).strip().upper()

        # ------------------------------------------------------------
        # Explicit N/A
        # ------------------------------------------------------------

        if status == "N/A":

            return {
                "valid": (
                    len(errors) == 0
                ),
                "status": "N/A",
                "value": None,
                "errors": errors,
            }

        # ------------------------------------------------------------
        # Invalid status
        # ------------------------------------------------------------

        if status in {
            "MISSING",
            "INVALID",
            "ERROR",
        }:

            errors.append(
                "Active Energy status is "
                f"{status}."
            )

        # ------------------------------------------------------------
        # Missing value
        # ------------------------------------------------------------

        if value is None:

            errors.append(
                "Active Energy value is missing."
            )

        # ------------------------------------------------------------
        # Numeric value
        # ------------------------------------------------------------

        else:

            if isinstance(
                value,
                bool,
            ):

                errors.append(
                    "Active Energy value is not numeric."
                )

            elif not isinstance(
                value,
                (int, float),
            ):

                errors.append(
                    "Active Energy value is not numeric."
                )

            else:

                numeric_value = float(
                    value
                )

                if not math.isfinite(
                    numeric_value
                ):

                    errors.append(
                        "Active Energy value "
                        "must be finite."
                    )

                else:

                    if (
                        numeric_value
                        < self.minimum_active_energy
                    ):

                        errors.append(
                            f"Active Energy "
                            f"{numeric_value} is below "
                            "the minimum allowed value "
                            f"{self.minimum_active_energy}."
                        )

                    if (
                        numeric_value
                        > self.maximum_active_energy
                    ):

                        errors.append(
                            f"Active Energy "
                            f"{numeric_value} exceeds "
                            "the maximum allowed value "
                            f"{self.maximum_active_energy}."
                        )

        # ------------------------------------------------------------
        # Unit
        # ------------------------------------------------------------

        if unit:

            normalized_unit = (
                str(unit).strip()
            )

            if (
                normalized_unit.casefold()
                != self.expected_unit.casefold()
            ):

                errors.append(
                    "Unexpected energy unit: "
                    f"{normalized_unit}. "
                    f"Expected "
                    f"{self.expected_unit}."
                )

        elif value is not None:

            # Parser should normally provide kWh.
            # The normalizer also supplies kWh when a numeric
            # NBSense reading contains no explicit unit.
            errors.append(
                "Energy unit is missing."
            )

        # ------------------------------------------------------------
        # Return result
        # ------------------------------------------------------------

        return {
            "valid": len(errors) == 0,
            "status": (
                "VALID"
                if len(errors) == 0
                else "INVALID"
            ),
            "value": value,
            "errors": errors,
        }

    def validate_meter(
        self,
        meter_name: str,
        value: float | None,
        unit: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Convenience API for a single meter."""

        return self.validate_reading(
            {
                "meter_name": meter_name,
                "active_energy": value,
                "unit": unit,
                "status": (
                    status
                    if status is not None
                    else (
                        "N/A"
                        if value is None
                        else "VALID"
                    )
                ),
            }
        )

    # ================================================================
    # NORMALIZATION
    # ================================================================

    @staticmethod
    def normalize_meter_name(
        value: str | None,
    ) -> str:
        """
        Normalize meter names for comparison.

        Original parser values are not modified.
        """

        if value is None:
            return ""

        text = str(
            value
        )

        text = (
            text
            .replace("\u00a0", " ")
            .replace("\u200b", "")
            .replace("\ufeff", "")
        )

        text = " ".join(
            text.split()
        )

        return text.casefold().strip()

    @classmethod
    def _normalize_reading_structure(
        cls,
        reading: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize supported reading structures.

        Supported examples:

        {
            "meter_name": "...",
            "active_energy": 123.45,
            "unit": "kWh",
            "status": "VALID"
        }

        {
            "meter_name": "...",
            "value": 123.45,
            "unit": "kWh"
        }

        {
            "meter": "...",
            "energy": 123.45
        }
        """

        result = dict(
            reading
        )

        # ------------------------------------------------------------
        # Meter name aliases
        # ------------------------------------------------------------

        meter_name = (
            reading.get("meter_name")
            or reading.get("meter")
            or reading.get("name")
            or reading.get("Meter Name")
            or reading.get("meterName")
        )

        if meter_name is not None:

            result["meter_name"] = (
                str(meter_name).strip()
            )

        # ------------------------------------------------------------
        # Value aliases
        # ------------------------------------------------------------

        if (
            "active_energy"
            not in result
        ):

            for key in (
                "value",
                "energy",
                "activeEnergy",
                "active_energy_value",
                "Active Energy",
            ):

                if key in reading:

                    result[
                        "active_energy"
                    ] = reading.get(
                        key
                    )

                    break

        # ------------------------------------------------------------
        # Unit aliases
        # ------------------------------------------------------------

        if not result.get(
            "unit"
        ):

            for key in (
                "energy_unit",
                "unit_name",
                "Unit",
                "Energy Unit",
            ):

                if key in reading:

                    result["unit"] = (
                        reading.get(key)
                    )

                    break

        # ------------------------------------------------------------
        # Normalize status
        # ------------------------------------------------------------

        status = result.get(
            "status"
        )

        if status is not None:

            status_text = str(
                status
            ).strip().upper()

            if status_text in {
                "NA",
                "N.A.",
                "N/A",
                "NOT AVAILABLE",
                "NOT_AVAILABLE",
                "NOTAVAILABLE",
            }:

                result["status"] = "N/A"

            else:

                result["status"] = (
                    status_text
                )

        # ------------------------------------------------------------
        # Normalize value
        # ------------------------------------------------------------

        value = result.get(
            "active_energy"
        )

        if isinstance(
            value,
            str,
        ):

            value_text = (
                value.strip()
            )

            upper_value = (
                value_text.upper()
            )

            # Explicit N/A
            if upper_value in {
                "N/A",
                "NA",
                "N.A.",
                "NOT AVAILABLE",
                "NOT_AVAILABLE",
                "NOTAVAILABLE",
                "-",
                "--",
            }:

                result[
                    "active_energy"
                ] = None

                result["status"] = "N/A"

            else:

                cleaned = (
                    value_text
                    .replace(",", "")
                    .strip()
                )

                # Values such as:
                # 141.35 kWh
                # 0.04 kWh

                if cleaned.lower().endswith(
                    "kwh"
                ):

                    cleaned = (
                        cleaned[:-3]
                        .strip()
                    )

                    if not result.get(
                        "unit"
                    ):
                        result["unit"] = (
                            "kWh"
                        )

                try:

                    result[
                        "active_energy"
                    ] = float(
                        cleaned
                    )

                except ValueError:

                    # Leave it unchanged.
                    # validate_reading() will report
                    # the proper validation error.
                    pass

        # ------------------------------------------------------------
        # Infer status
        # ------------------------------------------------------------

        if not result.get(
            "status"
        ):

            if (
                result.get(
                    "active_energy"
                )
                is None
            ):

                result["status"] = "N/A"

            else:

                result["status"] = "VALID"

        # ------------------------------------------------------------
        # NBSense expected unit
        # ------------------------------------------------------------

        if (
            result.get(
                "active_energy"
            )
            is not None
            and not result.get(
                "unit"
            )
        ):

            result["unit"] = "kWh"

        return result

    # ================================================================
    # REPORT DATE
    # ================================================================

    @staticmethod
    def _extract_report_date(
        report: dict[str, Any],
    ) -> datetime | None:
        """
        Extract the report date.

        For NBSense reports this should represent the
        'To' date of the reporting period.
        """

        candidates = (
            report.get(
                "report_date"
            ),
            report.get(
                "report_date_iso"
            ),
            report.get(
                "to_date"
            ),
            report.get(
                "end_date"
            ),
        )

        formats = (
            "%Y-%m-%d",
            "%d %b %Y",
            "%d %B %Y",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        )

        for value in candidates:

            if isinstance(
                value,
                datetime,
            ):
                return value

            if not isinstance(
                value,
                str,
            ):
                continue

            text = value.strip()

            if not text:
                continue

            for fmt in formats:

                try:

                    return datetime.strptime(
                        text,
                        fmt,
                    )

                except ValueError:
                    continue

        return None

    # ================================================================
    # READING EXTRACTION
    # ================================================================

    @classmethod
    def _extract_readings(
        cls,
        report: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract meter readings.

        IMPORTANT:
        The previous implementation failed when:

            report["readings"]

        was a list.

        This implementation explicitly supports that structure.
        """

        # ------------------------------------------------------------
        # Format 1:
        # report["meters"] = [...]
        # ------------------------------------------------------------

        meters = report.get(
            "meters"
        )

        if isinstance(
            meters,
            list,
        ):

            return [
                cls._normalize_reading_structure(
                    item
                )
                for item in meters
                if isinstance(
                    item,
                    dict,
                )
            ]

        # ------------------------------------------------------------
        # Format 2:
        # report["readings"] = [...]
        #
        # THIS IS THE IMPORTANT FIX.
        # ------------------------------------------------------------

        readings = report.get(
            "readings"
        )

        if isinstance(
            readings,
            list,
        ):

            return [
                cls._normalize_reading_structure(
                    item
                )
                for item in readings
                if isinstance(
                    item,
                    dict,
                )
            ]

        # ------------------------------------------------------------
        # Format 3:
        # report["readings"] = {
        #     "Meter": {...}
        # }
        # ------------------------------------------------------------

        if isinstance(
            readings,
            dict,
        ):

            result: list[
                dict[str, Any]
            ] = []

            for meter_name, data in (
                readings.items()
            ):

                # Nested dictionary.
                if isinstance(
                    data,
                    dict,
                ):

                    item = {
                        "meter_name": meter_name,
                        "active_energy": (
                            data.get(
                                "active_energy"
                            )
                            if (
                                "active_energy"
                                in data
                            )
                            else data.get(
                                "value"
                            )
                        ),
                        "unit": data.get(
                            "unit"
                        ),
                        "status": data.get(
                            "status"
                        ),
                        "page": data.get(
                            "page"
                        ),
                    }

                    result.append(
                        cls._normalize_reading_structure(
                            item
                        )
                    )

                    continue

                # Direct numeric value.
                if isinstance(
                    data,
                    (int, float),
                ) and not isinstance(
                    data,
                    bool,
                ):

                    result.append(
                        cls._normalize_reading_structure(
                            {
                                "meter_name": (
                                    meter_name
                                ),
                                "active_energy": (
                                    data
                                ),
                                "unit": "kWh",
                                "status": "VALID",
                            }
                        )
                    )

                    continue

                # Direct N/A.
                if isinstance(
                    data,
                    str,
                ):

                    if (
                        data.strip().upper()
                        in {
                            "N/A",
                            "NA",
                            "N.A.",
                        }
                    ):

                        result.append(
                            cls._normalize_reading_structure(
                                {
                                    "meter_name": (
                                        meter_name
                                    ),
                                    "active_energy": None,
                                    "unit": "kWh",
                                    "status": "N/A",
                                }
                            )
                        )

            return result

        return []

    # ================================================================
    # DUPLICATE DETECTION
    # ================================================================

    @classmethod
    def _find_duplicate_meters(
        cls,
        readings: list[dict[str, Any]],
    ) -> list[str]:
        """
        Detect duplicate meter names after normalization.
        """

        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for reading in readings:

            meter_name = reading.get(
                "meter_name"
            )

            if not meter_name:
                continue

            normalized = (
                cls.normalize_meter_name(
                    meter_name
                )
            )

            if not normalized:
                continue

            if normalized in seen:

                if (
                    meter_name
                    not in duplicates
                ):

                    duplicates.append(
                        meter_name
                    )

            else:

                seen[
                    normalized
                ] = meter_name

        return duplicates
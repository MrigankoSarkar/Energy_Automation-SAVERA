from __future__ import annotations

from typing import Any, Dict, Optional


class EnergyAnalyzer:
    """
    Energy analysis orchestration layer.

    Responsibilities:
    - Run deterministic local anomaly checks.
    - Optionally use GeminiService for higher-level interpretation.
    - Produce business-friendly monitoring information.
    - Never directly modify Excel.
    - Never override deterministic validation.
    """

    def __init__(
        self,
        gemini_service=None,
        validation_service=None,
    ):
        self.gemini_service = gemini_service
        self.validation_service = validation_service

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def analyze(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze EMS data.

        Deterministic checks run first.
        Gemini is optional and only adds interpretation.
        """

        local_result = self._local_analysis(data)

        gemini_result = {
            "success": False,
            "status": "not_available",
            "analysis": None,
        }

        if self.gemini_service is not None:

            method = getattr(
                self.gemini_service,
                "analyze",
                None,
            )

            if callable(method):
                try:
                    gemini_result = method(
                        data=data,
                        context=context,
                    )
                except Exception as exc:
                    gemini_result = {
                        "success": False,
                        "status": "error",
                        "analysis": None,
                        "error": str(exc),
                    }

        return {
            "success": True,
            "local": local_result,
            "gemini": gemini_result,
            "anomalies": local_result.get(
                "anomalies",
                [],
            ),
            "anomaly_count": local_result.get(
                "anomaly_count",
                0,
            ),
            "status": self._overall_status(
                local_result
            ),
        }

    def analyze_report(
        self,
        report: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a complete EMS report."""
        return self.analyze(
            data=report,
            context=context,
        )

    def analyze_energy(
        self,
        readings: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze energy meter readings."""
        return self.analyze(
            data=readings,
            context=context,
        )

    def monitor(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Monitoring compatibility API."""
        return self.analyze(
            data=data,
            context=context,
        )

    def run(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrator compatibility API."""
        return self.analyze(
            data=data,
            context=context,
        )

    def execute(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scheduler/orchestrator compatibility API."""
        return self.analyze(
            data=data,
            context=context,
        )

    # ------------------------------------------------------------------
    # Deterministic local analysis
    # ------------------------------------------------------------------

    def _local_analysis(
        self,
        data: Any,
    ) -> Dict[str, Any]:

        # Prefer the dedicated GeminiService local checker
        # if it is available.
        if self.gemini_service is not None:

            method = getattr(
                self.gemini_service,
                "local_anomaly_check",
                None,
            )

            if callable(method):
                try:
                    return method(data)
                except Exception:
                    pass

        readings = self._normalize_readings(
            data
        )

        anomalies = []
        valid_count = 0
        na_count = 0

        for item in readings:

            meter = item["meter_name"]
            value = item["value"]
            status = item["status"].upper()

            if (
                value is None
                or status in {
                    "N/A",
                    "NA",
                    "MISSING",
                    "NOT_AVAILABLE",
                }
            ):
                na_count += 1
                continue

            numeric = self._to_float(
                value
            )

            if numeric is None:
                anomalies.append({
                    "meter": meter,
                    "type": "invalid_numeric_value",
                    "value": value,
                })
                continue

            valid_count += 1

            if numeric < 0:
                anomalies.append({
                    "meter": meter,
                    "type": "negative_energy",
                    "value": numeric,
                })

            if numeric > 100_000_000:
                anomalies.append({
                    "meter": meter,
                    "type": "extreme_energy_value",
                    "value": numeric,
                })

        return {
            "success": True,
            "anomaly_count": len(
                anomalies
            ),
            "anomalies": anomalies,
            "valid_count": valid_count,
            "na_count": na_count,
        }

    # ------------------------------------------------------------------
    # Validation integration
    # ------------------------------------------------------------------

    def validate_and_analyze(
        self,
        report: Any,
    ) -> Dict[str, Any]:
        """
        Run deterministic validation before analysis.

        Validation remains authoritative.
        """

        validation_result = None

        if self.validation_service is not None:

            method = getattr(
                self.validation_service,
                "validate_report",
                None,
            )

            if callable(method):
                try:
                    validation_result = method(
                        report
                    )
                except TypeError:
                    validation_result = method(
                        report=report
                    )

        analysis_result = self.analyze(
            report
        )

        return {
            "success": True,
            "validation": validation_result,
            "analysis": analysis_result,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @staticmethod
    def _overall_status(
        local_result: Dict[str, Any],
    ) -> str:

        anomaly_count = int(
            local_result.get(
                "anomaly_count",
                0,
            )
        )

        if anomaly_count > 0:
            return "attention_required"

        return "normal"

    # ------------------------------------------------------------------
    # Data normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_readings(
        readings: Any,
    ):

        if readings is None:
            return []

        if isinstance(readings, dict):

            if isinstance(
                readings.get("readings"),
                (list, tuple),
            ):
                readings = readings[
                    "readings"
                ]

            elif "meter_name" in readings:
                readings = [readings]

            else:
                converted = []

                for meter, value in readings.items():

                    if isinstance(
                        value,
                        dict,
                    ):
                        item = dict(value)
                        item.setdefault(
                            "meter_name",
                            meter,
                        )
                    else:
                        item = {
                            "meter_name": meter,
                            "value": value,
                        }

                    converted.append(item)

                readings = converted

        normalized = []

        for item in readings:

            if not isinstance(
                item,
                dict,
            ):
                continue

            meter = (
                item.get("meter_name")
                or item.get("meter")
                or item.get("name")
                or ""
            )

            value = (
                item.get("active_energy")
                if "active_energy" in item
                else item.get("value")
            )

            status = str(
                item.get("status")
                or ""
            )

            normalized.append({
                "meter_name": str(
                    meter
                ).strip(),
                "value": value,
                "unit": item.get(
                    "unit",
                    "kWh",
                ),
                "status": status,
            })

        return normalized

    # ------------------------------------------------------------------
    # Numeric conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        text = str(
            value
        ).strip()

        if not text:
            return None

        if text.upper() in {
            "N/A",
            "NA",
            "NONE",
            "NULL",
            "-",
        }:
            return None

        text = (
            text.replace(
                "kWh",
                "",
            )
            .replace(
                "KWH",
                "",
            )
            .replace(
                "kwh",
                "",
            )
            .replace(
                ",",
                "",
            )
            .strip()
        )

        try:
            return float(text)

        except (
            TypeError,
            ValueError,
        ):
            return None
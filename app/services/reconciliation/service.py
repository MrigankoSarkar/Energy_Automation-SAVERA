from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional


class ReconciliationService:
    """
    Determines which report dates require processing.

    Responsibilities:
    - Identify missing dates.
    - Identify yesterday's report.
    - Identify weekend/Sunday dates.
    - Identify historical/missed dates.
    - Avoid treating N/A as zero.
    - Remain independent from Excel-writing logic.
    """

    def __init__(
        self,
        gmail_service=None,
        excel_service=None,
        repository=None,
        expected_days_back: int = 7,
    ):
        self.gmail_service = gmail_service
        self.excel_service = excel_service
        self.repository = repository
        self.expected_days_back = max(
            1,
            int(expected_days_back),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reconcile(
        self,
        report_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compare available report dates with the expected date range.

        This method does not modify Excel.

        Returns:
            {
                "success": True,
                "reference_date": "...",
                "expected_dates": [...],
                "available_dates": [...],
                "missing_dates": [...],
                "yesterday_missing": True/False,
                "weekend_missing": [...],
                "historical_missing": [...],
            }
        """

        # If report_dates is a dict representing a parsed report, extract its date
        input_dates: List[Any] = []
        if isinstance(report_dates, dict):
            extracted_date = (
                report_dates.get("report_date")
                or report_dates.get("report_date_iso")
                or report_dates.get("date")
            )
            if extracted_date:
                input_dates.append(extracted_date)
            if reference_date is None and extracted_date:
                reference_date = extracted_date
        elif report_dates is not None:
            input_dates = list(report_dates)

        # Include dates from Excel if available
        excel_dates = self.get_excel_dates()
        all_dates = list(input_dates) + list(excel_dates)

        ref = self._normalize_date(
            reference_date
        ) or date.today()

        lookback = (
            self.expected_days_back
            if days_back is None
            else max(1, int(days_back))
        )

        available = {
            normalized
            for normalized in (
                self._normalize_date(value)
                for value in all_dates
            )
            if normalized is not None
        }

        expected = [
            ref - timedelta(days=offset)
            for offset in range(1, lookback + 1)
        ]

        missing = [
            item
            for item in expected
            if item not in available
        ]

        yesterday = ref - timedelta(days=1)

        weekend_missing = [
            item
            for item in missing
            if item.weekday() >= 5
        ]

        historical_missing = [
            item
            for item in missing
            if item != yesterday
        ]

        return {
            "success": True,
            "reference_date": ref.isoformat(),
            "expected_dates": [
                item.isoformat()
                for item in expected
            ],
            "available_dates": [
                item.isoformat()
                for item in sorted(available)
            ],
            "missing_dates": [
                item.isoformat()
                for item in missing
            ],
            "yesterday_missing": (
                yesterday in missing
            ),
            "weekend_missing": [
                item.isoformat()
                for item in weekend_missing
            ],
            "historical_missing": [
                item.isoformat()
                for item in historical_missing
            ],
        }

    def find_missing_dates(
        self,
        available_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> List[date]:
        """
        Return dates missing from the expected historical window.
        """

        ref = (
            self._normalize_date(reference_date)
            or date.today()
        )

        lookback = (
            self.expected_days_back
            if days_back is None
            else max(1, int(days_back))
        )

        available = {
            normalized
            for normalized in (
                self._normalize_date(value)
                for value in (available_dates or [])
            )
            if normalized is not None
        }

        return [
            ref - timedelta(days=offset)
            for offset in range(1, lookback + 1)
            if (
                ref - timedelta(days=offset)
            ) not in available
        ]

    def find_missing_report_dates(
        self,
        available_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> List[date]:
        """
        Compatibility alias.
        """
        return self.find_missing_dates(
            available_dates=available_dates,
            reference_date=reference_date,
            days_back=days_back,
        )

    def get_missing_dates(
        self,
        available_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> List[date]:
        """
        Compatibility alias.
        """
        return self.find_missing_dates(
            available_dates=available_dates,
            reference_date=reference_date,
            days_back=days_back,
        )

    def is_weekend(
        self,
        value: Any,
    ) -> bool:
        normalized = self._normalize_date(value)

        if normalized is None:
            return False

        return normalized.weekday() >= 5

    def is_sunday(
        self,
        value: Any,
    ) -> bool:
        normalized = self._normalize_date(value)

        if normalized is None:
            return False

        return normalized.weekday() == 6

    def is_yesterday(
        self,
        value: Any,
        reference_date: Optional[Any] = None,
    ) -> bool:
        normalized = self._normalize_date(value)

        if normalized is None:
            return False

        reference = (
            self._normalize_date(reference_date)
            or date.today()
        )

        return normalized == (
            reference - timedelta(days=1)
        )

    def classify_date(
        self,
        value: Any,
        reference_date: Optional[Any] = None,
    ) -> str:
        """
        Classify a report date for workflow decisions.

        Possible values:
        - yesterday
        - sunday
        - weekend
        - historical
        - today
        - invalid
        """

        normalized = self._normalize_date(value)

        if normalized is None:
            return "invalid"

        reference = (
            self._normalize_date(reference_date)
            or date.today()
        )

        if normalized == reference:
            return "today"

        if normalized == (
            reference - timedelta(days=1)
        ):
            return "yesterday"

        if normalized.weekday() == 6:
            return "sunday"

        if normalized.weekday() >= 5:
            return "weekend"

        return "historical"

    # ------------------------------------------------------------------
    # Gmail reconciliation
    # ------------------------------------------------------------------

    def search_for_missing_reports(
        self,
        missing_dates: Iterable[Any],
    ) -> Dict[str, Any]:
        """
        Ask the configured Gmail service to locate reports for
        missing dates when the service provides a compatible method.

        The method is intentionally defensive because Gmail service
        implementations can differ between development and production.
        """

        dates = [
            normalized
            for normalized in (
                self._normalize_date(value)
                for value in missing_dates
            )
            if normalized is not None
        ]

        if not dates:
            return {
                "success": True,
                "found": [],
                "not_found": [],
            }

        if self.gmail_service is None:
            return {
                "success": False,
                "found": [],
                "not_found": [
                    item.isoformat()
                    for item in dates
                ],
                "reason": "Gmail service is not configured.",
            }

        found = []
        not_found = []

        for target_date in dates:
            result = self._search_gmail_for_date(
                target_date
            )

            if result:
                found.append({
                    "date": target_date.isoformat(),
                    "result": result,
                })
            else:
                not_found.append(
                    target_date.isoformat()
                )

        return {
            "success": True,
            "found": found,
            "not_found": not_found,
        }

    def find_missed_reports(
        self,
        missing_dates: Iterable[Any],
    ) -> Dict[str, Any]:
        """
        Compatibility alias for historical/missed report recovery.
        """
        return self.search_for_missing_reports(
            missing_dates
        )

    # ------------------------------------------------------------------
    # Excel date discovery
    # ------------------------------------------------------------------

    def get_excel_dates(self) -> List[date]:
        """
        Read existing Excel dates when the configured Excel service
        exposes a compatible workbook-reading method.

        Failure to inspect Excel returns an empty list rather than
        inventing dates.
        """

        if self.excel_service is None:
            return []

        candidates = (
            "get_existing_dates",
            "get_report_dates",
            "read_existing_dates",
        )

        for method_name in candidates:
            method = getattr(
                self.excel_service,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:
                result = method()

                return [
                    normalized
                    for normalized in (
                        self._normalize_date(item)
                        for item in (result or [])
                    )
                    if normalized is not None
                ]

            except Exception:
                continue

        return []

    def reconcile_excel(
        self,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Reconcile the dates currently present in Excel.
        """

        available = self.get_excel_dates()

        return self.reconcile(
            report_dates=available,
            reference_date=reference_date,
            days_back=days_back,
        )

    # ------------------------------------------------------------------
    # Combined reconciliation
    # ------------------------------------------------------------------

    def run(
        self,
        report_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility entry point used by orchestrators.
        """

        result = self.reconcile(
            report_dates=report_dates,
            reference_date=reference_date,
            days_back=days_back,
        )

        if result["missing_dates"]:
            gmail_result = (
                self.search_for_missing_reports(
                    result["missing_dates"]
                )
            )

            result["gmail_recovery"] = (
                gmail_result
            )

        return result

    def execute(
        self,
        report_dates: Optional[Iterable[Any]] = None,
        reference_date: Optional[Any] = None,
        days_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility alias for scheduler/orchestrator code.
        """
        return self.run(
            report_dates=report_dates,
            reference_date=reference_date,
            days_back=days_back,
        )

    # ------------------------------------------------------------------
    # Internal Gmail adapter
    # ------------------------------------------------------------------

    def _search_gmail_for_date(
        self,
        target_date: date,
    ):
        """
        Try common Gmail service method names without assuming
        a specific implementation.
        """

        method_names = (
            "find_report_for_date",
            "find_reports_for_date",
            "search_report_for_date",
            "search_reports_for_date",
            "find_report",
        )

        for method_name in method_names:
            method = getattr(
                self.gmail_service,
                method_name,
                None,
            )

            if not callable(method):
                continue

            attempts = (
                lambda: method(target_date),
                lambda: method(target_date.isoformat()),
            )

            for attempt in attempts:
                try:
                    result = attempt()

                    if result:
                        return result

                except (
                    TypeError,
                    ValueError,
                    AttributeError,
                ):
                    continue

        return None

    # ------------------------------------------------------------------
    # Date normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_date(
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

        # Handle ISO timestamps.
        if "T" in text:
            try:
                return datetime.fromisoformat(
                    text.replace("Z", "+00:00")
                ).date()
            except ValueError:
                pass

        formats = (
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y.%m.%d",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d %Y",
            "%b %d %Y",
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
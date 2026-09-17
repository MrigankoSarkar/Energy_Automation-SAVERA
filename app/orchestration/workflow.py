"""
EnergyAutomation
Automation Workflow

Responsible for orchestrating:

Gmail
    ↓
PDF
    ↓
Validation
    ↓
AI Analysis
    ↓
AI Decision
    ↓
Excel
    ↓
Power BI
    ↓
Database
    ↓
Notification

Design rule
-----------
The workflow works with GmailRepository for report discovery/download
operations. GmailService remains the low-level Gmail API client.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class AutomationWorkflow:

    def __init__(
        self,
        gmail_service,
        pdf_service,
        validation_service,
        reconciliation_service,
        excel_service,
        energy_analyzer,
        ai_decision_engine=None,
        powerbi_service=None,
        powerbi_publisher=None,
        powerbi_refresh=None,
        notification_service=None,
        repository=None,
        gmail_repository=None,
        event_bus=None,
        alert_service=None,
    ):
        """
        Initialize the automation workflow.

        Parameters
        ----------
        gmail_service:
            Low-level Gmail service.

        gmail_repository:
            Report-oriented Gmail repository.

        The repository is preferred for workflow report operations.
        """

        # ------------------------------------------------------------------
        # Gmail
        # ------------------------------------------------------------------

        self.gmail_service = gmail_service

        # If an explicit repository was supplied, use it.
        #
        # Otherwise retain backwards compatibility by allowing the
        # gmail_service argument itself to implement find_reports().
        self.gmail_repository = (
            gmail_repository
            if gmail_repository is not None
            else (
                gmail_service
                if hasattr(
                    gmail_service,
                    "find_reports",
                )
                else None
            )
        )

        # IMPORTANT:
        #
        # Existing workflow code expects self.gmail.find_reports().
        #
        # Therefore self.gmail must point to the repository whenever
        # available.
        self.gmail = (
            self.gmail_repository
            if self.gmail_repository is not None
            else gmail_service
        )

        # ------------------------------------------------------------------
        # Other services
        # ------------------------------------------------------------------

        self.pdf = pdf_service

        self.validation = (
            validation_service
        )

        self.reconciliation = (
            reconciliation_service
        )

        self.excel = (
            excel_service
        )

        self.analyzer = (
            energy_analyzer
        )

        self.ai_decision = (
            ai_decision_engine
        )

        self.powerbi = (
            powerbi_service
        )

        self.powerbi_publisher = (
            powerbi_publisher
        )

        self.powerbi_refresh = (
            powerbi_refresh
        )

        self.notifications = (
            notification_service
        )

        self.repository = (
            repository
        )

        self.event_bus = event_bus
        self.alert_service = alert_service
        self._last_missing_dates = []

        self._lock = threading.Lock()

    # ======================================================================
    # MAIN WORKFLOW
    # ======================================================================

    def run(
        self,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute the complete automation workflow.

        The method intentionally accepts optional positional/keyword
        arguments so the scheduler can invoke it without causing a
        signature mismatch.
        """

        blocking = kwargs.get("blocking", False)
        acquired = self._lock.acquire(blocking=blocking)
        if not acquired:
            return {
                "success": False,
                "status": "already_running",
                "message": "A report-processing operation is already running.",
                "steps": [],
                "processed": [],
            }

        result: Dict[str, Any] = {
            "success": False,
            "status": "started",
            "steps": [],
            "processed": [],
        }

        try:

            # --------------------------------------------------------------
            # Validate Gmail report source
            # --------------------------------------------------------------

            if self.gmail is None:

                raise RuntimeError(
                    "Gmail report repository is not configured."
                )

            if not hasattr(
                self.gmail,
                "find_reports",
            ):

                raise RuntimeError(
                    "Configured Gmail report source does not implement "
                    "find_reports()."
                )

            # --------------------------------------------------------------
            # 1. Find reports
            # --------------------------------------------------------------

            email_result = (
                self._find_reports()
            )

            result["steps"].append(
                {
                    "step": "gmail",
                    "result": email_result,
                }
            )

            # --------------------------------------------------------------
            # Normalize Gmail result
            # --------------------------------------------------------------

            reports = (
                self._extract_reports(
                    email_result
                )
            )

            # --------------------------------------------------------------
            # Historical gap detection & recovery
            # --------------------------------------------------------------

            recovered_reports = self._recover_missing_reports()
            if recovered_reports:
                result["steps"].append(
                    {
                        "step": "gap_recovery",
                        "recovered_count": len(recovered_reports),
                    }
                )
                seen_keys = set()
                deduped = []
                for rep in (reports + recovered_reports):
                    key = (
                        rep.get("message_id")
                        or rep.get("id")
                        or rep.get("file_path")
                        or rep.get("pdf_path")
                    )
                    if key and key in seen_keys:
                        continue
                    if key:
                        seen_keys.add(key)
                    deduped.append(rep)
                reports = deduped

            # --------------------------------------------------------------
            # No reports
            # --------------------------------------------------------------

            if not reports:

                result["success"] = True

                result["status"] = (
                    "no_new_reports"
                )

                return result

            # --------------------------------------------------------------
            # 2. Process every report
            # --------------------------------------------------------------

            processed = []

            for report in reports:

                processed_result = (
                    self._process_report(
                        report
                    )
                )

                processed.append(
                    processed_result
                )

            result["processed"] = (
                processed
            )

            # --------------------------------------------------------------
            # Overall status
            # --------------------------------------------------------------

            result["success"] = bool(
                processed
            ) and all(
                item.get(
                    "success",
                    False,
                )
                for item in processed
            )

            result["status"] = (
                "completed"
                if result["success"]
                else "completed_with_errors"
            )

            return result

        except Exception as exc:

            result["status"] = (
                "error"
            )

            result["error"] = str(
                exc
            )

            self._notify_error(
                "Automation Error",
                str(exc),
            )

            return result

        finally:
            if hasattr(self, "alert_service") and self.alert_service is not None:
                try:
                    missing = getattr(self, "_last_missing_dates", None)
                    self.alert_service.evaluate_workflow_result(result, missing_dates=missing)
                except Exception:
                    pass

            if hasattr(self, "event_bus") and self.event_bus is not None:
                try:
                    from app.events.bus import EventType
                    evt_type = (
                        EventType.PROCESSING_COMPLETED.value
                        if result.get("success")
                        else EventType.PROCESSING_FAILED.value
                    )
                    self.event_bus.publish(
                        evt_type,
                        data=result,
                        source="workflow",
                    )
                except Exception:
                    pass

            self._lock.release()

    # ======================================================================
    # GMAIL
    # ======================================================================

    def _find_reports(self) -> Any:
        """
        Retrieve NBSense reports from GmailRepository.

        Supports repository implementations that return either:

            list

        or:

            {"reports": [...]}
        """

        return self.gmail.find_reports()

    @staticmethod
    def _extract_reports(
        email_result: Any,
    ) -> list:

        if email_result is None:
            return []

        if isinstance(
            email_result,
            dict,
        ):

            reports = email_result.get(
                "reports",
                [],
            )

            if reports is None:
                return []

            if isinstance(
                reports,
                list,
            ):
                return reports

            return list(
                reports
            )

        if isinstance(
            email_result,
            (list, tuple),
        ):

            return list(
                email_result
            )

        return []

    def _recover_missing_reports(self) -> list:
        """
        Identify missing calendar dates from Excel/reconciliation
        and attempt automated historical backfill via Gmail.
        """
        if self.reconciliation is None or self.gmail is None:
            return []

        try:
            missing_fn = getattr(
                self.reconciliation, "find_missing_dates", None
            )
            if not callable(missing_fn):
                return []

            missing = missing_fn()
            self._last_missing_dates = missing or []
            if not missing:
                return []

            search_dates = getattr(
                self.gmail, "find_reports_for_dates", None
            )
            if callable(search_dates):
                return search_dates(missing)

            search_single = getattr(
                self.gmail, "find_reports_for_date", None
            )
            if callable(search_single):
                recovered = []
                for d in missing:
                    found = search_single(d)
                    if found:
                        if isinstance(found, list):
                            recovered.extend(found)
                        else:
                            recovered.append(found)
                return recovered

            return []
        except Exception:
            return []

    # ======================================================================
    # INDIVIDUAL REPORT
    # ======================================================================

    def _process_report(
        self,
        report: Dict[str, Any],
    ) -> Dict[str, Any]:

        output: Dict[str, Any] = {
            "success": False,
            "report": report,
            "status": "started",
        }

        try:

            # --------------------------------------------------------------
            # 1. Resolve PDF
            # --------------------------------------------------------------

            pdf_path = (
                self._resolve_pdf(
                    report
                )
            )

            if not pdf_path:

                raise RuntimeError(
                    "Unable to locate or download the PDF attachment "
                    "for the NBSense report."
                )

            output["pdf_path"] = str(
                pdf_path
            )

            # --------------------------------------------------------------
            # 2. Parse PDF
            # --------------------------------------------------------------

            parsed = self.pdf.parse(
                pdf_path
            )

            if parsed is None:

                raise RuntimeError(
                    "PDF parser returned no data."
                )

            output["parsed"] = (
                parsed
            )

            # --------------------------------------------------------------
            # 3. Validation
            # --------------------------------------------------------------

            validation = (
                self.validation.validate_report(
                    parsed
                )
            )

            output["validation"] = (
                validation
            )

            if not self._validation_ok(
                validation
            ):

                output["status"] = (
                    "validation_failed"
                )

                self._notify_error(
                    "Validation Failed",
                    (
                        "The NBSense report failed "
                        "validation."
                    ),
                )

                return output

            # --------------------------------------------------------------
            # 4. AI analysis
            # --------------------------------------------------------------

            analysis = (
                self._run_analysis(
                    parsed
                )
            )

            output["analysis"] = (
                analysis
            )

            # --------------------------------------------------------------
            # 5. AI decision
            # --------------------------------------------------------------

            decision = (
                self._run_decision(
                    parsed,
                    validation,
                    analysis,
                )
            )

            output["decision"] = (
                decision
            )

            if self._decision_rejected(
                decision
            ):

                output["status"] = (
                    "rejected"
                )

                return output

            # --------------------------------------------------------------
            # 6. Reconciliation
            # --------------------------------------------------------------

            reconciliation_result = (
                self._run_reconciliation(
                    parsed
                )
            )

            if reconciliation_result is not None:

                output[
                    "reconciliation"
                ] = reconciliation_result

            # --------------------------------------------------------------
            # 7. Excel
            # --------------------------------------------------------------

            report_date = (
                parsed.get(
                    "report_date"
                )
            )

            readings = (
                parsed.get(
                    "readings",
                    [],
                )
            )

            if not report_date:

                raise RuntimeError(
                    "PDF report date is missing."
                )

            if not isinstance(
                readings,
                list,
            ):

                raise RuntimeError(
                    "PDF readings must be a list."
                )

            excel_result = (
                self.excel.update_existing_workbook(
                    readings=readings,
                    report_date=report_date,
                )
            )

            output["excel"] = (
                excel_result
            )

            # --------------------------------------------------------------
            # 8. Power BI
            # --------------------------------------------------------------

            powerbi_result = (
                self._publish_powerbi(
                    readings,
                    parsed,
                )
            )

            output["powerbi"] = (
                powerbi_result
            )

            # --------------------------------------------------------------
            # 9. Database
            # --------------------------------------------------------------

            self._record_report(
                report=report,
                parsed=parsed,
                excel_result=excel_result,
                validation_result=validation,
                powerbi_result=powerbi_result,
                ai_result=analysis,
            )

            # --------------------------------------------------------------
            # 10. Success notification
            # --------------------------------------------------------------

            self._notify_success(
                "Report Processed",
                (
                    "EMS report for "
                    f"{report_date} "
                    "was processed successfully."
                ),
            )

            output["success"] = (
                True
            )

            output["status"] = (
                "completed"
            )

            return output

        except Exception as exc:

            output["error"] = str(
                exc
            )

            output["status"] = (
                "error"
            )

            self._record_report(
                report=report,
                parsed=output.get("parsed") or {},
                excel_result=None,
                validation_result=output.get("validation"),
                powerbi_result=output.get("powerbi"),
                ai_result=output.get("analysis"),
                error=exc,
            )

            self._notify_error(
                "Report Processing Error",
                str(exc),
            )

            return output

    # ======================================================================
    # PDF RESOLUTION
    # ======================================================================

    def _resolve_pdf(
        self,
        report: Dict[str, Any],
    ) -> Optional[str]:

        # --------------------------------------------------------------
        # Existing PDF path
        # --------------------------------------------------------------

        if isinstance(
            report,
            dict,
        ):

            for key in (
                "pdf_path",
                "file_path",
                "attachment_path",
                "path",
            ):

                value = report.get(
                    key
                )

                if value:

                    path = Path(
                        str(value)
                    )

                    if path.exists():

                        return str(
                            path
                        )

        # --------------------------------------------------------------
        # Repository download
        # --------------------------------------------------------------

        repository = (
            self.gmail_repository
        )

        if repository is not None:

            # Preferred repository method.
            download_reports = getattr(
                repository,
                "download_reports",
                None,
            )

            if callable(
                download_reports
            ):

                downloaded = (
                    download_reports(
                        report
                    )
                )

                resolved = (
                    self._extract_downloaded_pdf(
                        downloaded
                    )
                )

                if resolved:

                    return resolved

        # --------------------------------------------------------------
        # Low-level Gmail compatibility
        # --------------------------------------------------------------

        gmail_service = (
            self.gmail_service
        )

        if gmail_service is not None:

            # Existing projects may expose one of these methods.
            for method_name in (
                "download_report",
                "download_pdf_attachment",
                "download_pdf_attachments",
            ):

                method = getattr(
                    gmail_service,
                    method_name,
                    None,
                )

                if not callable(
                    method
                ):
                    continue

                downloaded = (
                    method(
                        report
                    )
                )

                resolved = (
                    self._extract_downloaded_pdf(
                        downloaded
                    )
                )

                if resolved:

                    return resolved

        return None

    @staticmethod
    def _extract_downloaded_pdf(
        downloaded: Any,
    ) -> Optional[str]:

        if downloaded is None:
            return None

        # --------------------------------------------------------------
        # Direct path
        # --------------------------------------------------------------

        if isinstance(
            downloaded,
            (str, Path),
        ):

            path = Path(
                str(downloaded)
            )

            if path.exists():

                return str(
                    path
                )

            return None

        # --------------------------------------------------------------
        # Dictionary
        # --------------------------------------------------------------

        if isinstance(
            downloaded,
            dict,
        ):

            for key in (
                "pdf_path",
                "file_path",
                "attachment_path",
                "path",
            ):

                value = downloaded.get(
                    key
                )

                if value:

                    path = Path(
                        str(value)
                    )

                    if path.exists():

                        return str(
                            path
                        )

            # Some implementations return:
            #
            # {"files": [...]}
            #
            nested = downloaded.get(
                "files"
            )

            resolved = (
                AutomationWorkflow
                ._extract_downloaded_pdf(
                    nested
                )
            )

            if resolved:
                return resolved

            return None

        # --------------------------------------------------------------
        # List / tuple
        # --------------------------------------------------------------

        if isinstance(
            downloaded,
            (list, tuple),
        ):

            for item in downloaded:

                resolved = (
                    AutomationWorkflow
                    ._extract_downloaded_pdf(
                        item
                    )
                )

                if resolved:
                    return resolved

            return None

        return None

    # ======================================================================
    # AI ANALYSIS
    # ======================================================================

    def _run_analysis(
        self,
        parsed: Dict[str, Any],
    ) -> Any:

        analyzer = (
            self.analyzer
        )

        method = getattr(
            analyzer,
            "analyze",
            None,
        )

        if not callable(
            method
        ):

            return {}

        return method(
            parsed
        )

    # ======================================================================
    # AI DECISION
    # ======================================================================

    def _run_decision(
        self,
        parsed: Dict[str, Any],
        validation: Dict[str, Any],
        analysis: Any,
    ) -> Dict[str, Any]:

        decision_engine = (
            self.ai_decision
        )

        method = getattr(
            decision_engine,
            "decide",
            None,
        )

        if not callable(
            method
        ):

            return {
                "decision": "approve",
                "reason": (
                    "No AI decision method "
                    "is configured."
                ),
            }

        decision = method(
            report=parsed,
            validation_result=validation,
            analysis_result=analysis,
        )

        if decision is None:

            return {
                "decision": "approve"
            }

        if isinstance(
            decision,
            dict,
        ):

            return decision

        return {
            "decision": "approve",
            "result": decision,
        }

    @staticmethod
    def _decision_rejected(
        decision: Any,
    ) -> bool:

        if not isinstance(
            decision,
            dict,
        ):
            return False

        value = decision.get(
            "decision"
        )

        if value is None:
            return False

        return str(
            value
        ).strip().lower() == "reject"

    # ======================================================================
    # RECONCILIATION
    # ======================================================================

    def _run_reconciliation(
        self,
        parsed: Dict[str, Any],
    ) -> Any:

        service = (
            self.reconciliation
        )

        if service is None:
            return None

        # Reconciliation implementations can differ between project
        # versions. Use only an actually available method.

        for method_name in (
            "reconcile",
            "validate",
            "compare",
        ):

            method = getattr(
                service,
                method_name,
                None,
            )

            if not callable(
                method
            ):
                continue

            try:
                return method(
                    parsed
                )

            except TypeError:

                try:
                    return method(
                        report=parsed
                    )

                except TypeError:
                    continue

        return None

    # ======================================================================
    # POWER BI
    # ======================================================================

    def _publish_powerbi(
        self,
        readings: list,
        parsed: Dict[str, Any],
    ) -> Any:

        publisher = (
            self.powerbi_publisher
        )

        if publisher is None:
            return {
                "success": True,
                "status": "disabled",
            }

        publish = getattr(
            publisher,
            "publish",
            None,
        )

        if not callable(
            publish
        ):

            return {
                "success": False,
                "status": "publisher_method_missing",
            }

        # Current project publisher API.
        try:

            return publish(
                readings
            )

        except TypeError:

            # Compatibility with richer publisher implementations.
            try:

                return publish(
                    readings=readings,
                    report=parsed,
                )

            except TypeError:

                return publish(
                    report=parsed
                )

    # ======================================================================
    # DATABASE
    # ======================================================================

    def _record_report(
        self,
        report: Dict[str, Any],
        parsed: Dict[str, Any],
        excel_result: Any = None,
        validation_result: Any = None,
        powerbi_result: Any = None,
        ai_result: Any = None,
        error: Any = None,
    ) -> None:

        repository = (
            self.repository
        )

        if repository is None:
            return

        method = getattr(
            repository,
            "record_processed_report",
            None,
        )

        if not callable(
            method
        ):
            return

        try:
            try:
                method(
                    report=report,
                    parsed=parsed,
                    excel_result=excel_result,
                    validation_result=validation_result,
                    powerbi_result=powerbi_result,
                    ai_result=ai_result,
                    error=error,
                )
            except TypeError:
                method(
                    report,
                    parsed,
                    excel_result,
                )

        except Exception:
            # Database history must never corrupt an otherwise successful
            # Excel/report-processing operation.
            pass

    # ======================================================================
    # NOTIFICATIONS
    # ======================================================================

    def _notify_success(
        self,
        title: str,
        message: str,
    ) -> None:

        service = (
            self.notifications
        )

        if service is None:
            return

        method = getattr(
            service,
            "success",
            None,
        )

        if callable(
            method
        ):

            try:
                method(
                    title,
                    message,
                )

            except Exception:
                pass

    def _notify_error(
        self,
        title: str,
        message: str,
    ) -> None:

        service = (
            self.notifications
        )

        if service is None:
            return

        method = getattr(
            service,
            "error",
            None,
        )

        if callable(
            method
        ):

            try:
                method(
                    title,
                    message,
                )

            except Exception:
                pass

    # ======================================================================
    # VALIDATION
    # ======================================================================

    @staticmethod
    def _validation_ok(
        result: Optional[Dict[str, Any]],
    ) -> bool:

        if result is None:
            return False

        if not isinstance(
            result,
            dict,
        ):

            return bool(
                result
            )

        # Explicit negative states always fail.

        if result.get(
            "success"
        ) is False:

            return False

        if result.get(
            "valid"
        ) is False:

            return False

        if result.get(
            "is_valid"
        ) is False:

            return False

        return True


__all__ = [
    "AutomationWorkflow",
]
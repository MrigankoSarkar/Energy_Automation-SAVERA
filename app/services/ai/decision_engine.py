from __future__ import annotations

from typing import Any, Dict, Optional


class AIDecisionEngine:
    """
    Deterministic decision layer for AI-assisted monitoring.

    Gemini may provide explanations and observations, but this
    class remains responsible for deciding whether an automation
    result is safe to accept, review, retry, or reject.

    IMPORTANT:
    - Never allow Gemini to directly modify Excel.
    - Never treat an AI recommendation as numerical truth.
    - Validation remains authoritative.
    - Normal validated reports should proceed automatically.
    - Exceptions should be surfaced for human review.
    """

    DECISION_ACCEPT = "accept"
    DECISION_REVIEW = "review"
    DECISION_REJECT = "reject"
    DECISION_RETRY = "retry"

    def __init__(
        self,
        validation_service=None,
        energy_analyzer=None,
        gemini_service=None,
    ):
        self.validation_service = validation_service
        self.energy_analyzer = energy_analyzer
        self.gemini_service = gemini_service

    # ------------------------------------------------------------------
    # Main decision API
    # ------------------------------------------------------------------

    def decide(
        self,
        report: Any = None,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Determine the appropriate workflow action.

        Decision priority:

            validation failure -> reject/review
            processing error   -> retry/review
            anomaly            -> review
            valid normal data  -> accept

        Gemini never gets authority to bypass validation.
        """

        # --------------------------------------------------------------
        # 1. Processing error
        # --------------------------------------------------------------

        if error is not None:
            return self._decision(
                decision=self.DECISION_RETRY,
                reason="Processing error detected.",
                confidence="high",
                requires_human_review=True,
                details={
                    "error": str(error),
                },
            )

        # --------------------------------------------------------------
        # 2. Validation result
        # --------------------------------------------------------------

        validation = validation_result

        if validation is None and report is not None:
            validation = self._run_validation(
                report
            )

        if validation is not None:

            validation_ok = self._validation_is_successful(
                validation
            )

            if not validation_ok:
                return self._decision(
                    decision=self.DECISION_REJECT,
                    reason=(
                        "Deterministic validation failed."
                    ),
                    confidence="high",
                    requires_human_review=True,
                    details={
                        "validation": validation,
                    },
                )

        # --------------------------------------------------------------
        # 3. Analysis
        # --------------------------------------------------------------

        analysis = analysis_result

        if analysis is None and report is not None:
            analysis = self._run_analysis(
                report
            )

        # --------------------------------------------------------------
        # 4. Analyze anomalies
        # --------------------------------------------------------------

        anomaly_count = self._get_anomaly_count(
            analysis
        )

        if anomaly_count > 0:
            return self._decision(
                decision=self.DECISION_REVIEW,
                reason=(
                    "Potential energy anomaly detected."
                ),
                confidence="medium",
                requires_human_review=True,
                details={
                    "anomaly_count": anomaly_count,
                    "analysis": analysis,
                },
            )

        # --------------------------------------------------------------
        # 5. Normal validated report
        # --------------------------------------------------------------

        return self._decision(
            decision=self.DECISION_ACCEPT,
            reason=(
                "Report passed deterministic validation "
                "and no blocking anomaly was detected."
            ),
            confidence="high",
            requires_human_review=False,
            details={
                "validation": validation,
                "analysis": analysis,
            },
        )

    # ------------------------------------------------------------------
    # Compatibility APIs
    # ------------------------------------------------------------------

    def evaluate(
        self,
        report: Any = None,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            report=report,
            validation_result=validation_result,
            analysis_result=analysis_result,
            error=error,
        )

    def evaluate_report(
        self,
        report: Any,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            report=report,
            validation_result=validation_result,
            analysis_result=analysis_result,
        )

    def make_decision(
        self,
        report: Any = None,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            report=report,
            validation_result=validation_result,
            analysis_result=analysis_result,
            error=error,
        )

    def run(
        self,
        report: Any = None,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            report=report,
            validation_result=validation_result,
            analysis_result=analysis_result,
            error=error,
        )

    def execute(
        self,
        report: Any = None,
        validation_result: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            report=report,
            validation_result=validation_result,
            analysis_result=analysis_result,
            error=error,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _run_validation(
        self,
        report: Any,
    ) -> Optional[Dict[str, Any]]:

        if self.validation_service is None:
            return None

        method = getattr(
            self.validation_service,
            "validate_report",
            None,
        )

        if not callable(method):
            method = getattr(
                self.validation_service,
                "validate",
                None,
            )

        if not callable(method):
            return None

        try:
            result = method(report)

            if isinstance(result, dict):
                return result

            return {
                "success": bool(result),
                "valid": bool(result),
            }

        except Exception as exc:
            return {
                "success": False,
                "valid": False,
                "error": str(exc),
            }

    @staticmethod
    def _validation_is_successful(
        validation: Dict[str, Any],
    ) -> bool:

        # Explicit failure always wins.
        if validation.get("success") is False:
            return False

        if validation.get("valid") is False:
            return False

        if validation.get("is_valid") is False:
            return False

        if validation.get("passed") is False:
            return False

        # Explicit success/valid values.
        if (
            validation.get("success") is True
            or validation.get("valid") is True
            or validation.get("is_valid") is True
            or validation.get("passed") is True
        ):
            return True

        # If no explicit validation status exists,
        # do not invent a failure.
        return True

    # ------------------------------------------------------------------
    # Energy analysis
    # ------------------------------------------------------------------

    def _run_analysis(
        self,
        report: Any,
    ) -> Optional[Dict[str, Any]]:

        if self.energy_analyzer is None:
            return None

        method = getattr(
            self.energy_analyzer,
            "analyze",
            None,
        )

        if not callable(method):
            return None

        try:
            result = method(report)

            if isinstance(result, dict):
                return result

            return {
                "success": True,
                "analysis": result,
            }

        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "error": str(exc),
                "anomaly_count": 0,
            }

    @staticmethod
    def _get_anomaly_count(
        analysis: Optional[Dict[str, Any]],
    ) -> int:

        if not isinstance(
            analysis,
            dict,
        ):
            return 0

        try:
            return int(
                analysis.get(
                    "anomaly_count",
                    0,
                )
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0

    # ------------------------------------------------------------------
    # Decision object
    # ------------------------------------------------------------------

    @staticmethod
    def _decision(
        decision: str,
        reason: str,
        confidence: str,
        requires_human_review: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        return {
            "success": True,
            "decision": decision,
            "action": decision,
            "reason": reason,
            "confidence": confidence,
            "requires_human_review": (
                requires_human_review
            ),
            "details": details or {},
        }
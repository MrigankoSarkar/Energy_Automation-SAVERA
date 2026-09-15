"""
Power BI service facade.

This module provides the application-level PowerBIService used by
the orchestration layer.

The implementation is intentionally safe by default:
- Power BI integration is disabled unless explicitly configured.
- No public "Publish to web" behavior is performed automatically.
- Publishing and refresh operations delegate to the lower-level
  publisher/refresh services when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class PowerBIService:
    """
    Application-facing Power BI service.

    This class acts as the boundary between the automation workflow
    and Power BI integration.

    Power BI is considered configured only when explicitly enabled
    and the required identifiers are available.
    """

    def __init__(
        self,
        enabled: bool = False,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        workspace_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        publisher: Any = None,
        refresh_service: Any = None,
        **kwargs: Any,
    ) -> None:
        self.enabled = bool(enabled)

        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.workspace_id = workspace_id
        self.dataset_id = dataset_id

        self.publisher = publisher
        self.refresh_service = refresh_service

        # Preserve compatibility with future configuration values.
        self.extra_config: Dict[str, Any] = dict(kwargs)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """
        Return True when Power BI has been explicitly enabled and
        the minimum required configuration exists.
        """

        if not self.enabled:
            return False

        required = (
            self.tenant_id,
            self.client_id,
            self.client_secret,
            self.workspace_id,
            self.dataset_id,
        )

        return all(bool(value) for value in required)

    def status(self) -> Dict[str, Any]:
        """
        Return a safe status dictionary suitable for the UI.
        """

        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "workspace_id_present": bool(self.workspace_id),
            "dataset_id_present": bool(self.dataset_id),
        }

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish(
        self,
        rows: Optional[Iterable[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Publish data to Power BI.

        If Power BI is not configured, this returns a controlled
        skipped result instead of crashing the automation.
        """

        if not self.enabled:
            return {
                "success": False,
                "status": "disabled",
                "message": "Power BI integration is disabled.",
            }

        if not self.is_configured():
            return {
                "success": False,
                "status": "not_configured",
                "message": (
                    "Power BI integration is enabled but required "
                    "configuration is incomplete."
                ),
            }

        if self.publisher is None:
            return {
                "success": False,
                "status": "publisher_unavailable",
                "message": "Power BI publisher is not initialized.",
            }

        try:
            if hasattr(self.publisher, "publish"):
                result = self.publisher.publish(
                    rows=rows,
                    workspace_id=self.workspace_id,
                    dataset_id=self.dataset_id,
                    **kwargs,
                )

                return self._normalize_result(result)

            if hasattr(self.publisher, "push_rows"):
                result = self.publisher.push_rows(
                    rows or [],
                    workspace_id=self.workspace_id,
                    dataset_id=self.dataset_id,
                    **kwargs,
                )

                return self._normalize_result(result)

            return {
                "success": False,
                "status": "unsupported",
                "message": (
                    "Configured Power BI publisher does not expose "
                    "a supported publishing method."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    # Row push
    # ------------------------------------------------------------------

    def push_rows(
        self,
        rows: Iterable[Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Push rows to the configured Power BI dataset.
        """

        return self.publish(rows=rows, **kwargs)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Request a Power BI dataset refresh.
        """

        if not self.enabled:
            return {
                "success": False,
                "status": "disabled",
                "message": "Power BI integration is disabled.",
            }

        if not self.is_configured():
            return {
                "success": False,
                "status": "not_configured",
                "message": (
                    "Power BI integration is enabled but required "
                    "configuration is incomplete."
                ),
            }

        if self.refresh_service is None:
            return {
                "success": False,
                "status": "refresh_service_unavailable",
                "message": "Power BI refresh service is not initialized.",
            }

        try:
            if hasattr(self.refresh_service, "refresh"):
                result = self.refresh_service.refresh(
                    workspace_id=self.workspace_id,
                    dataset_id=self.dataset_id,
                    **kwargs,
                )

                return self._normalize_result(result)

            if hasattr(self.refresh_service, "execute"):
                result = self.refresh_service.execute(
                    workspace_id=self.workspace_id,
                    dataset_id=self.dataset_id,
                    **kwargs,
                )

                return self._normalize_result(result)

            return {
                "success": False,
                "status": "unsupported",
                "message": (
                    "Configured Power BI refresh service does not expose "
                    "a supported refresh method."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "message": str(exc),
            }

    def prepare_executive_dataset(
        self,
        readings: list[dict],
        report_date: str,
        historical_reports: Optional[list[dict]] = None,
    ) -> Dict[str, Any]:
        """
        Prepare executive-level KPIs and analytics dataset for Power BI publishing.
        """
        valid_readings = [
            r for r in readings
            if str(r.get("status", "")).upper() not in {"N/A", "NA"}
            and (r.get("value") is not None or r.get("active_energy") is not None)
        ]

        today_energy = round(
            sum(float(r.get("value") if r.get("value") is not None else r.get("active_energy", 0.0)) for r in valid_readings),
            2,
        )

        history = historical_reports or []
        yesterday_energy = 0.0
        mtd_energy = today_energy
        ytd_energy = today_energy

        if history:
            sorted_hist = sorted(history, key=lambda x: x.get("report_date", ""), reverse=True)
            if sorted_hist:
                yesterday_energy = float(sorted_hist[0].get("total_energy", 0.0) or 0.0)
            mtd_energy += sum(float(h.get("total_energy", 0.0) or 0.0) for h in history if str(h.get("report_date", "")).startswith(report_date[:7]))
            ytd_energy += sum(float(h.get("total_energy", 0.0) or 0.0) for h in history if str(h.get("report_date", "")).startswith(report_date[:4]))

        top_meters = sorted(
            [
                {
                    "meter_name": r.get("meter_name", ""),
                    "value": float(r.get("value") if r.get("value") is not None else r.get("active_energy", 0.0)),
                    "unit": r.get("unit", "kWh"),
                }
                for r in valid_readings
            ],
            key=lambda x: x["value"],
            reverse=True,
        )

        return {
            "report_date": report_date,
            "today_energy": today_energy,
            "yesterday_energy": round(yesterday_energy, 2),
            "mtd_energy": round(mtd_energy, 2),
            "ytd_energy": round(ytd_energy, 2),
            "active_meters_count": len(valid_readings),
            "total_meters_count": len(readings),
            "top_5_meters": top_meters[:5],
            "meter_breakdown": top_meters,
            "data_quality_status": "EXCELLENT" if len(valid_readings) >= 14 else "ATTENTION_REQUIRED",
        }

    def generate_star_schema(
        self,
        output_dir: Optional[str | Path] = None,
    ) -> Dict[str, str]:
        """
        Generate and export Power BI star-schema tables (CSVs), DAX measures,
        Push Dataset JSON schema, and report templates.
        """
        from app.services.powerbi.model_generator import PowerBIModelGenerator

        target_dir = Path(output_dir) if output_dir else Path("data/powerbi")
        generator = PowerBIModelGenerator(
            repository=self.extra_config.get("repository")
        )
        return generator.export_star_schema(target_dir)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_result(result: Any) -> Dict[str, Any]:
        """
        Normalize lower-level service results into a predictable
        dictionary.
        """

        if isinstance(result, dict):
            return result

        if result is True:
            return {
                "success": True,
                "status": "success",
                "message": "Power BI operation completed successfully.",
            }

        if result is False:
            return {
                "success": False,
                "status": "failed",
                "message": "Power BI operation failed.",
            }

        return {
            "success": True,
            "status": "success",
            "result": result,
        }


__all__ = ["PowerBIService"]
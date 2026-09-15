"""
Health monitoring for EnergyAutomation.
"""

from __future__ import annotations

from typing import Any, Dict


class HealthService:
    """
    Checks the availability/status of application services.
    """

    def check(
        self,
        services: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check all supplied services.

        A service exposing a callable ``status()`` method will have
        that method called. Otherwise the service is considered
        available if it exists.
        """

        result: Dict[str, Any] = {}

        for name, service in services.items():

            try:
                if service is None:
                    result[name] = {
                        "available": False,
                        "error": "Service is None.",
                    }
                    continue

                status_method = getattr(
                    service,
                    "status",
                    None,
                )

                if callable(status_method):
                    status = status_method()

                    if isinstance(status, dict):
                        result[name] = status
                    else:
                        result[name] = {
                            "available": True,
                            "status": status,
                        }

                else:
                    result[name] = {
                        "available": True
                    }

            except Exception as exc:

                result[name] = {
                    "available": False,
                    "error": str(exc),
                }

        return result

    def status(self) -> Dict[str, Any]:
        """
        Return the health service's own status.
        """

        return {
            "available": True,
            "service": "HealthService",
        }


# Backward-compatible alias.
HealthMonitor = HealthService


__all__ = [
    "HealthService",
    "HealthMonitor",
]
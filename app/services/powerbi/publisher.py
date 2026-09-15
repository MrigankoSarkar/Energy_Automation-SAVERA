from __future__ import annotations

from typing import Any, Dict


class PowerBIPublisher:

    def __init__(self, service):
        self.service = service

    def publish(
        self,
        rows: Any,
    ) -> Dict[str, Any]:

        return self.service.publish(
            rows
        )

    def publish_report(
        self,
        report: Any,
    ) -> Dict[str, Any]:

        return self.service.publish(
            report
        )
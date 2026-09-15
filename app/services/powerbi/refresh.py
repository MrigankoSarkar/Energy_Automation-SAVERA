from __future__ import annotations

from typing import Any, Dict


class PowerBIRefreshService:

    def __init__(self, service):
        self.service = service

    def refresh(self) -> Dict[str, Any]:
        return self.service.refresh()

    def run(self) -> Dict[str, Any]:
        return self.refresh()

    def execute(self) -> Dict[str, Any]:
        return self.refresh()
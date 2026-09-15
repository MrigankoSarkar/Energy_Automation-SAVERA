from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


class NotificationService:

    def __init__(self):
        self.history = []

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
    ) -> Dict[str, Any]:

        item = {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "title": title,
            "message": message,
            "level": level,
        }

        self.history.append(item)

        print(
            f"[{level.upper()}] "
            f"{title}: {message}"
        )

        return {
            "success": True,
            "notification": item,
        }

    def info(
        self,
        title: str,
        message: str,
    ):
        return self.notify(
            title,
            message,
            "info",
        )

    def success(
        self,
        title: str,
        message: str,
    ):
        return self.notify(
            title,
            message,
            "success",
        )

    def warning(
        self,
        title: str,
        message: str,
    ):
        return self.notify(
            title,
            message,
            "warning",
        )

    def error(
        self,
        title: str,
        message: str,
    ):
        return self.notify(
            title,
            message,
            "error",
        )
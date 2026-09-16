"""
Local Storage Provider for EnergyAutomation.
Allows the Streamlit BI dashboard to read local Excel files seamlessly using the
same provider protocol as cloud providers, ideal for offline/desktop development.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, Tuple

from streamlit_app.cloud_storage.base import CloudStorageProvider


class LocalStorageProvider(CloudStorageProvider):
    """Provider for loading local Excel workbooks from the filesystem."""

    def get_provider_name(self) -> str:
        return "Local Storage"

    def convert_sharing_url(self, sharing_url: str) -> str:
        return sharing_url.strip()

    def fetch_workbook_bytes(
        self,
        url_or_path: str,
        timeout: int = 20,
    ) -> Tuple[bytes, Dict[str, Any]]:
        path = Path(url_or_path.strip())
        if not path.is_absolute():
            path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(f"Local workbook not found at path: {path}")

        if not path.is_file():
            raise IsADirectoryError(f"Local workbook path is a directory, not a file: {path}")

        stat = path.stat()
        content = path.read_bytes()

        if not content:
            raise ValueError(f"Local workbook file is empty (0 bytes): {path}")

        last_modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        metadata: Dict[str, Any] = {
            "provider": self.get_provider_name(),
            "source_url": str(path),
            "original_url": url_or_path,
            "content_length": stat.st_size,
            "last_modified": last_modified_dt.isoformat(),
            "etag": f'"{int(stat.st_mtime)}-{stat.st_size}"',
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return content, metadata

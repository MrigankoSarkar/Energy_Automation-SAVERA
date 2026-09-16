"""
Google Drive Cloud Storage Provider for EnergyAutomation.
Translates Google Drive sharing links to direct download endpoints and fetches Excel workbooks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple
import requests

from streamlit_app.cloud_storage.base import CloudStorageProvider


class GoogleDriveProvider(CloudStorageProvider):
    """Provider for downloading Excel files hosted on Google Drive."""

    def get_provider_name(self) -> str:
        return "Google Drive"

    def convert_sharing_url(self, sharing_url: str) -> str:
        url = sharing_url.strip()
        if not url:
            return url

        # Already direct download
        if "drive.google.com/uc?" in url and "export=download" in url:
            return url

        # Pattern 1: https://drive.google.com/file/d/{FILE_ID}/view...
        match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Pattern 2: https://drive.google.com/open?id={FILE_ID}
        match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Pattern 3: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit...
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

        return url

    def fetch_workbook_bytes(
        self,
        url_or_path: str,
        timeout: int = 20,
    ) -> Tuple[bytes, Dict[str, Any]]:
        direct_url = self.convert_sharing_url(url_or_path)
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = session.get(direct_url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        # Handle Google Drive virus scan warning token for larger files
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                params = {"confirm": value}
                response = session.get(direct_url, headers=headers, params=params, timeout=timeout)
                response.raise_for_status()
                break

        content = response.content
        if not content:
            raise ValueError("Downloaded file from Google Drive is empty (0 bytes).")

        metadata: Dict[str, Any] = {
            "provider": self.get_provider_name(),
            "source_url": direct_url,
            "original_url": url_or_path,
            "content_length": len(content),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
            "content_type": response.headers.get("Content-Type"),
        }
        return content, metadata

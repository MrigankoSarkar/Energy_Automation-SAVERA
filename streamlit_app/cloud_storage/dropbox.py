"""
Dropbox Cloud Storage Provider for EnergyAutomation.
Translates Dropbox preview links to direct download endpoints and fetches Excel workbooks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple
import requests

from streamlit_app.cloud_storage.base import CloudStorageProvider


class DropboxProvider(CloudStorageProvider):
    """Provider for downloading Excel files hosted on Dropbox."""

    def get_provider_name(self) -> str:
        return "Dropbox"

    def convert_sharing_url(self, sharing_url: str) -> str:
        url = sharing_url.strip()
        if not url:
            return url

        # Direct download flag already set
        if "dl=1" in url or "raw=1" in url:
            return url

        # Replace dl=0 with dl=1
        if "dl=0" in url:
            return url.replace("dl=0", "dl=1")

        # Dropbox user content direct link
        if "www.dropbox.com" in url:
            if "?" in url:
                return f"{url}&dl=1"
            return f"{url}?dl=1"

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

        content = response.content
        if not content:
            raise ValueError("Downloaded file from Dropbox is empty (0 bytes).")

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

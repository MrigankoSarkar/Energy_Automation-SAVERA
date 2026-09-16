"""
Direct URL Cloud Storage Provider for EnergyAutomation.
Handles downloading workbooks directly from standard HTTP/HTTPS endpoints or pre-signed URLs.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
import requests

from streamlit_app.cloud_storage.base import CloudStorageProvider


class DirectURLProvider(CloudStorageProvider):
    """Provider for direct HTTP/HTTPS workbook URLs."""

    def get_provider_name(self) -> str:
        return "Direct URL"

    def convert_sharing_url(self, sharing_url: str) -> str:
        # Direct URLs are already direct download endpoints
        return sharing_url.strip()

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
            raise ValueError(f"Downloaded file from {direct_url} is empty (0 bytes).")

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

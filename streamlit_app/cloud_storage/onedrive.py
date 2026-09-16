"""
OneDrive & SharePoint Cloud Storage Provider for EnergyAutomation.
Translates Microsoft OneDrive and SharePoint sharing links to direct download endpoints.
"""

from __future__ import annotations

import base64
import re
from typing import Any, Dict, Tuple
import requests

from streamlit_app.cloud_storage.base import CloudStorageProvider


class OneDriveProvider(CloudStorageProvider):
    """Provider for downloading Excel files hosted on Microsoft OneDrive or SharePoint."""

    def get_provider_name(self) -> str:
        return "OneDrive / SharePoint"

    def convert_sharing_url(self, sharing_url: str) -> str:
        url = sharing_url.strip()
        if not url:
            return url

        # Direct download flag already set
        if "download=1" in url:
            return url

        # SharePoint / OneDrive sharing links with query string
        if "sharepoint.com" in url or "onedrive.live.com" in url:
            if "download.aspx" in url:
                return url
            if "?" in url:
                return f"{url}&download=1"
            return f"{url}?download=1"

        # 1drv.ms short links or generic OneDrive links can use Microsoft Graph public share endpoint
        # Formula: https://api.onedrive.com/v1.0/shares/u!{base64_url}/root/content
        try:
            encoded_bytes = base64.b64encode(url.encode("utf-8")).decode("utf-8")
            # Replace characters as required by OneDrive share API
            safe_encoded = encoded_bytes.rstrip("=").replace("/", "_").replace("+", "-")
            direct_link = f"https://api.onedrive.com/v1.0/shares/u!{safe_encoded}/root/content"
            return direct_link
        except Exception:
            if "?" in url:
                return f"{url}&download=1"
            return f"{url}?download=1"

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
            raise ValueError("Downloaded file from OneDrive is empty (0 bytes).")

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

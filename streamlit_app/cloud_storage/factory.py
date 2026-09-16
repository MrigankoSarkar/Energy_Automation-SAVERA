"""
Factory function to instantiate CloudStorageProvider implementations.
Supports explicit provider name or intelligent URL auto-detection.
"""

from __future__ import annotations

import re
from typing import Optional

from streamlit_app.cloud_storage.base import CloudStorageProvider
from streamlit_app.cloud_storage.google_drive import GoogleDriveProvider
from streamlit_app.cloud_storage.onedrive import OneDriveProvider
from streamlit_app.cloud_storage.dropbox import DropboxProvider
from streamlit_app.cloud_storage.direct_url import DirectURLProvider
from streamlit_app.cloud_storage.local_storage import LocalStorageProvider


def detect_provider(url_or_path: str) -> str:
    """Detects provider type from URL or path structure."""
    target = url_or_path.strip().lower()

    if "drive.google.com" in target or "docs.google.com" in target:
        return "google_drive"
    if "1drv.ms" in target or "onedrive.live.com" in target or "sharepoint.com" in target:
        return "onedrive"
    if "dropbox.com" in target:
        return "dropbox"
    if target.startswith("http://") or target.startswith("https://"):
        return "direct_url"
    return "local"


def get_cloud_provider(
    provider_name: Optional[str] = None,
    url_or_path: Optional[str] = None,
) -> CloudStorageProvider:
    """
    Returns the appropriate CloudStorageProvider.

    Args:
        provider_name: Explicit provider ("google_drive", "onedrive", "dropbox", "direct_url", "local").
        url_or_path: Optional URL or path used for auto-detection if provider_name is omitted or 'auto'.
    """
    name = (provider_name or "").strip().lower()

    if not name or name == "auto":
        if url_or_path:
            name = detect_provider(url_or_path)
        else:
            name = "local"

    if name in ("google_drive", "gdrive", "google"):
        return GoogleDriveProvider()
    if name in ("onedrive", "sharepoint", "microsoft"):
        return OneDriveProvider()
    if name in ("dropbox",):
        return DropboxProvider()
    if name in ("direct_url", "http", "https", "url", "direct"):
        return DirectURLProvider()
    if name in ("local", "file", "filesystem"):
        return LocalStorageProvider()

    # Fallback to direct URL if it looks like a URL, else local
    if url_or_path and (url_or_path.startswith("http://") or url_or_path.startswith("https://")):
        return DirectURLProvider()

    return LocalStorageProvider()

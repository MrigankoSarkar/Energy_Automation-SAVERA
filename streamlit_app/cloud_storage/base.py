"""
Abstract base class and protocol for Cloud Storage Providers in EnergyAutomation.
Enforces provider independence and separation between sharing URLs and direct download URLs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class CloudStorageProvider(ABC):
    """
    Abstract Cloud Storage Provider.
    Transforms sharing URLs to direct binary download URLs and downloads
    the workbook with error handling and metadata extraction.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the human-readable provider name."""
        raise NotImplementedError

    @abstractmethod
    def convert_sharing_url(self, sharing_url: str) -> str:
        """
        Converts a user-provided sharing URL into a direct downloadable URL.
        If already a direct download URL, returns it unchanged.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_workbook_bytes(
        self,
        url_or_path: str,
        timeout: int = 20,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Fetches the workbook as raw bytes along with metadata.

        Returns:
            Tuple of (file_bytes, metadata_dict)
            metadata_dict typically includes:
                - 'content_length': int
                - 'last_modified': str or datetime
                - 'etag': str
                - 'source_url': str
                - 'provider': str
        """
        raise NotImplementedError

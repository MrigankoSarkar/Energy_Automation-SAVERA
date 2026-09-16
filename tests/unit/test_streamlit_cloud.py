"""
Unit tests for Streamlit Cloud Storage Providers and URL Translators.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from streamlit_app.cloud_storage.google_drive import GoogleDriveProvider
from streamlit_app.cloud_storage.onedrive import OneDriveProvider
from streamlit_app.cloud_storage.dropbox import DropboxProvider
from streamlit_app.cloud_storage.direct_url import DirectURLProvider
from streamlit_app.cloud_storage.local_storage import LocalStorageProvider
from streamlit_app.cloud_storage.factory import get_cloud_provider, detect_provider


def test_google_drive_url_translation():
    provider = GoogleDriveProvider()
    assert provider.get_provider_name() == "Google Drive"

    # Pattern 1: /file/d/{ID}/view
    url1 = "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view?usp=sharing"
    direct1 = provider.convert_sharing_url(url1)
    assert direct1 == "https://drive.google.com/uc?export=download&id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    # Pattern 2: open?id={ID}
    url2 = "https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
    direct2 = provider.convert_sharing_url(url2)
    assert direct2 == "https://drive.google.com/uc?export=download&id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    # Pattern 3: Google Sheets export
    url3 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/edit#gid=0"
    direct3 = provider.convert_sharing_url(url3)
    assert direct3 == "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/export?format=xlsx"

    # Already direct
    already = "https://drive.google.com/uc?export=download&id=123"
    assert provider.convert_sharing_url(already) == already


def test_onedrive_url_translation():
    provider = OneDriveProvider()
    assert provider.get_provider_name() == "OneDrive / SharePoint"

    # Standard 1drv.ms link translates to Microsoft Graph public share direct download endpoint
    url1 = "https://1drv.ms/x/s!Ak7v7example"
    direct1 = provider.convert_sharing_url(url1)
    assert "shares/u!" in direct1 and "/root/content" in direct1

    # SharePoint URL with existing query param gets download=1
    url2 = "https://company.sharepoint.com/:x:/r/sites/ems/report.xlsx?e=4abcde"
    direct2 = provider.convert_sharing_url(url2)
    assert "download=1" in direct2


def test_dropbox_url_translation():
    provider = DropboxProvider()
    assert provider.get_provider_name() == "Dropbox"

    url = "https://www.dropbox.com/s/example123/report.xlsx?dl=0"
    direct = provider.convert_sharing_url(url)
    assert "dl=1" in direct


def test_direct_url_provider():
    provider = DirectURLProvider()
    assert provider.get_provider_name() == "Direct URL"
    url = "https://internal.saverams.com/reports/Test_BI_Analysis_Report_2026.xlsx"
    assert provider.convert_sharing_url(url) == url


def test_local_storage_provider(tmp_path: Path):
    provider = LocalStorageProvider()
    assert provider.get_provider_name() == "Local Storage"

    # Create dummy file
    dummy_file = tmp_path / "test.xlsx"
    dummy_file.write_bytes(b"PK\x03\x04test_content")

    content, metadata = provider.fetch_workbook_bytes(str(dummy_file))
    assert content == b"PK\x03\x04test_content"
    assert metadata["provider"] == "Local Storage"
    assert metadata["content_length"] == len(b"PK\x03\x04test_content")
    assert "last_modified" in metadata


def test_cloud_provider_factory_and_detection():
    assert detect_provider("https://drive.google.com/file/d/123") == "google_drive"
    assert detect_provider("https://1drv.ms/x/s!123") == "onedrive"
    assert detect_provider("https://www.dropbox.com/s/123/a.xlsx") == "dropbox"
    assert detect_provider("https://myserver.com/report.xlsx") == "direct_url"
    assert detect_provider("C:/reports/test.xlsx") == "local"

    assert isinstance(get_cloud_provider("google_drive"), GoogleDriveProvider)
    assert isinstance(get_cloud_provider("onedrive"), OneDriveProvider)
    assert isinstance(get_cloud_provider("dropbox"), DropboxProvider)
    assert isinstance(get_cloud_provider("direct_url"), DirectURLProvider)
    assert isinstance(get_cloud_provider("local"), LocalStorageProvider)
    assert isinstance(get_cloud_provider("auto", "https://drive.google.com/file/d/1"), GoogleDriveProvider)

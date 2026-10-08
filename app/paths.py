"""
EnergyAutomation — Enterprise Runtime & Resource Path Architecture
===================================================================
Separates:
  1. READ-ONLY APPLICATION RESOURCES (assets, packaged templates, icons)
     located in sys._MEIPASS / install directory.
  2. USER-WRITABLE APPLICATION DATA (logs, database, configs, backups)
     located in %LOCALAPPDATA%\\EnergyAutomation (in production/frozen mode)
     or in the project repository root (in development mode).

This guarantees that:
  - An application installed into "C:\\Program Files\\EnergyAutomation" will NEVER
    encounter Windows permission errors when creating logs, writing databases,
    or saving user configuration.
  - Development runs and pytest test suites continue working seamlessly in-place.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from app.version import APP_NAME


def is_frozen() -> bool:
    """Return True if running in a PyInstaller or cx_Freeze bundle."""
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """
    Return the read-only application resource root directory.

    In PyInstaller bundle: sys._MEIPASS (or directory of the executable).
    In development: the repository root.
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def get_install_dir() -> Path:
    """Return directory containing the running executable or script."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_asset_path(filename: str = "") -> Path:
    """
    Return absolute path to a read-only asset (icon, image, css, html).
    Checks both sys._MEIPASS/assets and install_dir/assets.
    """
    app_assets = get_app_dir() / "assets"
    if filename:
        cand = app_assets / filename
        if cand.exists():
            return cand

        # Fallback to install dir / assets
        install_assets = get_install_dir() / "assets"
        cand2 = install_assets / filename
        if cand2.exists():
            return cand2

    return app_assets / filename if filename else app_assets


def get_ui_asset_path(filename: str = "") -> Path:
    """Return path to UI resources (html, js, css)."""
    app_ui = get_app_dir() / "ui"
    if filename:
        cand = app_ui / filename
        if cand.exists():
            return cand
        cand2 = get_install_dir() / "ui" / filename
        if cand2.exists():
            return cand2
    return app_ui / filename if filename else app_ui


def get_user_data_root() -> Path:
    """
    Return user-writable root directory.

    If ENERGYAUTOMATION_DATA_DIR environment variable is set, it takes precedence.
    In frozen production mode: %LOCALAPPDATA%\\EnergyAutomation
    In development: repository root
    """
    override = os.environ.get("ENERGYAUTOMATION_DATA_DIR")
    if override:
        path = Path(override).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if is_frozen():
        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            str(Path.home() / "AppData" / "Local"),
        )
        data_root = Path(local_app_data) / APP_NAME
        data_root.mkdir(parents=True, exist_ok=True)
        return data_root

    return Path(__file__).resolve().parents[1]


def get_config_dir() -> Path:
    """Return directory where editable settings.json is stored."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Config"
    else:
        path = get_user_data_root() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """Return directory where application logs are stored."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Logs"
    else:
        path = get_user_data_root() / "data" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_dir() -> Path:
    """Return directory where sqlite database is stored."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Database"
    else:
        path = get_user_data_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_backups_dir() -> Path:
    """Return directory where excel and audit backups are stored."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Backups"
    else:
        path = get_user_data_root() / "data" / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_reports_dir() -> Path:
    """Return directory where downloaded PDF reports are stored."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Reports"
    else:
        path = get_user_data_root() / "data" / "downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_credentials_dir() -> Path:
    """Return directory where user Google OAuth tokens and credentials live."""
    if is_frozen() or os.environ.get("ENERGYAUTOMATION_DATA_DIR"):
        path = get_user_data_root() / "Credentials"
    else:
        path = get_user_data_root() / "credentials"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_file() -> Path:
    """
    Return path to settings.json.
    Ensures that in frozen production mode, default template config is copied
    on first run if settings.json does not yet exist.
    """
    config_dir = get_config_dir()
    settings_path = config_dir / "settings.json"

    if not settings_path.exists():
        # Check bundled template
        template_file = get_app_dir() / "config" / "settings.template.json"
        if not template_file.exists():
            template_file = get_app_dir() / "config" / "settings.json"
        if not template_file.exists():
            template_file = get_install_dir() / "config" / "settings.template.json"
        if not template_file.exists():
            template_file = get_install_dir() / "config" / "settings.json"

        if template_file.exists() and template_file != settings_path:
            try:
                shutil.copy2(template_file, settings_path)
            except Exception:
                pass

    return settings_path


def initialize_runtime_environment() -> None:
    """
    Ensure all required user-writable application directories exist
    and seed initial template files when running in frozen/packaged mode.
    """
    get_config_dir()
    get_logs_dir()
    get_database_dir()
    get_backups_dir()
    get_reports_dir()
    get_credentials_dir()
    get_settings_file()

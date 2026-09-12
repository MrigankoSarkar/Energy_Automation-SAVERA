from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# APPLICATION PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

# Keep both names for compatibility with the existing GUI.
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
CONFIG_FILE = SETTINGS_FILE


# ============================================================
# LOAD SETTINGS
# ============================================================

def load_config() -> dict[str, Any]:
    """
    Load application settings from settings.json.
    """

    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(
            f"CONFIG-001: settings.json not found: {SETTINGS_FILE}"
        )

    try:
        with SETTINGS_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            f"CONFIG-002: Invalid settings.json: {exc}"
        ) from exc

    if not isinstance(config, dict):

        raise RuntimeError(
            "CONFIG-003: settings.json root must be a JSON object."
        )

    return config


# ============================================================
# SAVE SETTINGS
# ============================================================

def save_config(
    config: dict[str, Any]
) -> None:
    """
    Save settings back to settings.json.
    """

    if not isinstance(config, dict):

        raise ValueError(
            "CONFIG-004: Configuration must be a dictionary."
        )

    with SETTINGS_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            config,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# SAFE PATH RESOLUTION
# ============================================================

def project_path(
    value: str | Path
) -> Path:
    """
    Resolve a configured path.

    Absolute paths:
        Used directly.

    Relative paths:
        Resolved relative to the application directory.

    Quotes around paths are removed automatically.
    """

    if value is None:

        raise ValueError(
            "CONFIG-005: Path value cannot be None."
        )

    # Convert to string and remove accidental quotes.
    raw_value = str(value).strip()

    raw_value = raw_value.strip('"')
    raw_value = raw_value.strip("'")

    if not raw_value:

        raise ValueError(
            "CONFIG-006: Path value is empty."
        )

    path = Path(raw_value)

    # --------------------------------------------------------
    # CRITICAL FIX
    #
    # Never prepend PROJECT_ROOT to an absolute path.
    # --------------------------------------------------------

    if path.is_absolute():

        return path.resolve()

    return (
        PROJECT_ROOT / path
    ).resolve()


# ============================================================
# EXCEL PATH
# ============================================================

def get_excel_path(
    config: dict[str, Any]
) -> Path:
    """
    Return the configured Excel workbook path.
    """

    excel_config = config.get(
        "excel",
        {}
    )

    configured_file = excel_config.get(
        "file"
    )

    if not configured_file:

        raise RuntimeError(
            "CONFIG-007: excel.file is missing "
            "from settings.json."
        )

    return project_path(
        configured_file
    )


# ============================================================
# OPTIONAL HELPERS
# ============================================================

def get_project_root() -> Path:
    return PROJECT_ROOT


def get_settings_file() -> Path:
    return SETTINGS_FILE
"""
AI engine wrapper for AI Advisory Microservice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.ai.gemini_service import GeminiService

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_ai_service() -> GeminiService:
    settings_file = REPO_ROOT / "config" / "settings.json"
    api_key = None
    model = "gemini-flash-latest"
    enabled = True

    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            gem_cfg = cfg.get("gemini", {})
            api_key = gem_cfg.get("api_key")
            model = gem_cfg.get("model", "gemini-flash-latest")
            enabled = gem_cfg.get("enabled", True)
        except Exception:
            pass

    return GeminiService(api_key=api_key, model=model, enabled=enabled)

"""
Centralized Theme Tokens for Windows 11 Fluent Design System.
Defines cohesive color palettes, surface treatments, borders, and contrast rules
for both Light and Dark themes, guaranteeing zero dark-on-dark or light-on-light text collisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from qfluentwidgets import isDarkTheme


@dataclass(frozen=True)
class ThemeTokens:
    """Color, surface, and contrast tokens for an active visual mode."""
    # Base surfaces
    bg_app: str
    bg_surface: str
    bg_card: str
    bg_card_hover: str
    bg_sidebar: str

    # Borders and dividers
    border_subtle: str
    border_strong: str
    border_focus: str

    # Typography
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverted: str

    # Brand & Accents
    accent: str
    accent_hover: str
    accent_light: str

    # Status / Semantics
    success_text: str
    success_bg: str
    success_border: str

    warning_text: str
    warning_bg: str
    warning_border: str

    error_text: str
    error_bg: str
    error_border: str

    info_text: str
    info_bg: str
    info_border: str

    neutral_text: str
    neutral_bg: str
    neutral_border: str


LIGHT_TOKENS = ThemeTokens(
    bg_app="#f8fafc",
    bg_surface="#ffffff",
    bg_card="#ffffff",
    bg_card_hover="#f1f5f9",
    bg_sidebar="#f1f5f9",

    border_subtle="#e2e8f0",
    border_strong="#cbd5e1",
    border_focus="#2563eb",

    text_primary="#0f172a",
    text_secondary="#334155",
    text_muted="#64748b",
    text_inverted="#ffffff",

    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_light="#eff6ff",

    success_text="#15803d",
    success_bg="#dcfce7",
    success_border="#86efac",

    warning_text="#b45309",
    warning_bg="#fef3c7",
    warning_border="#fcd34d",

    error_text="#b91c1c",
    error_bg="#fee2e2",
    error_border="#fca5a5",

    info_text="#0369a1",
    info_bg="#e0f2fe",
    info_border="#7dd3fc",

    neutral_text="#475569",
    neutral_bg="#f1f5f9",
    neutral_border="#cbd5e1",
)

DARK_TOKENS = ThemeTokens(
    bg_app="#0f172a",
    bg_surface="#1e293b",
    bg_card="#1e293b",
    bg_card_hover="#334155",
    bg_sidebar="#0f172a",

    border_subtle="#334155",
    border_strong="#475569",
    border_focus="#3b82f6",

    text_primary="#ffffff",
    text_secondary="#f1f5f9",
    text_muted="#cbd5e1",
    text_inverted="#ffffff",

    accent="#3b82f6",
    accent_hover="#60a5fa",
    accent_light="#1e3a8a",

    success_text="#4ade80",
    success_bg="#064e3b",
    success_border="#059669",

    warning_text="#fbbf24",
    warning_bg="#78350f",
    warning_border="#d97706",

    error_text="#f87171",
    error_bg="#7f1d1d",
    error_border="#dc2626",

    info_text="#38bdf8",
    info_bg="#0c4a6e",
    info_border="#0284c7",

    neutral_text="#cbd5e1",
    neutral_bg="#1e293b",
    neutral_border="#334155",
)


def get_current_tokens() -> ThemeTokens:
    """Returns dark tokens as the permanent application theme."""
    return DARK_TOKENS

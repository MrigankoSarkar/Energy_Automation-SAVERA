"""
Windows 11 Fluent Typography System for EnergyAutomation.
Implements a coherent type hierarchy based on Segoe UI Variable with safe system fallbacks.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

PRIMARY_FONT_FAMILY = "Segoe UI Variable Display, Segoe UI Variable Text, Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif"
MONO_FONT_FAMILY = "Cascadia Code, Consolas, Courier New, monospace"


class Typography:
    """Windows 11 Type Scale Helper."""

    @staticmethod
    def get_font(point_size: int, weight: int = QFont.Normal, italic: bool = False) -> QFont:
        font = QFont()
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Arial", "sans-serif"])
        font.setPointSize(point_size)
        font.setWeight(weight)
        font.setItalic(italic)
        return font

    @staticmethod
    def display(widget: QWidget):
        widget.setFont(Typography.get_font(24, QFont.Bold))

    @staticmethod
    def heading1(widget: QWidget):
        widget.setFont(Typography.get_font(18, QFont.Bold))

    @staticmethod
    def heading2(widget: QWidget):
        widget.setFont(Typography.get_font(14, QFont.DemiBold))

    @staticmethod
    def heading3(widget: QWidget):
        widget.setFont(Typography.get_font(12, QFont.DemiBold))

    @staticmethod
    def body(widget: QWidget):
        widget.setFont(Typography.get_font(10, QFont.Normal))

    @staticmethod
    def body_strong(widget: QWidget):
        widget.setFont(Typography.get_font(10, QFont.Bold))

    @staticmethod
    def caption(widget: QWidget):
        widget.setFont(Typography.get_font(8, QFont.Normal))

    @staticmethod
    def kpi_value(widget: QWidget):
        widget.setFont(Typography.get_font(20, QFont.ExtraBold))

    @staticmethod
    def kpi_label(widget: QWidget):
        widget.setFont(Typography.get_font(9, QFont.DemiBold))

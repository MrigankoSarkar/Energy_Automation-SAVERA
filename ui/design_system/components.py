"""
Reusable Windows 11 Fluent UI Components for EnergyAutomation.
Includes FluentCard, KPICard, StatusCard, StatusBadge, EmptyState, and Headers.
"""

from __future__ import annotations

from typing import Any, Callable, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    ElevatedCardWidget,
    SimpleCardWidget,
    PrimaryPushButton,
    PushButton,
    TransparentPushButton,
    CaptionLabel,
    BodyLabel,
    StrongBodyLabel,
    TitleLabel,
    SubtitleLabel,
)

from ui.design_system.tokens import get_current_tokens, ThemeTokens
from ui.design_system.typography import Typography


class FluentCard(ElevatedCardWidget):
    """Base Fluent Card adhering strictly to active theme tokens."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.apply_theme()

    def apply_theme(self):
        tokens = get_current_tokens()
        self.setStyleSheet(
            f"""
            FluentCard {{
                background-color: {tokens.bg_card};
                border: 1px solid {tokens.border_subtle};
                border-radius: 8px;
            }}
            FluentCard:hover {{
                border: 1px solid {tokens.border_strong};
            }}
            """
        )


class StatusBadge(QLabel):
    """Standardized Status Badge for operations and integrations."""

    def __init__(self, status: str = "NOT ACTIVE", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str):
        s_upper = status.strip().upper()

        if any(k in s_upper for k in ("CONNECTED", "HEALTHY", "READY", "ACTIVE", "RUNNING", "OK", "VALID", "SUCCESSFUL")):
            bg = "#064e3b"
            color = "#4ade80"
            border = "#059669"
            icon = "✓"
        elif any(k in s_upper for k in ("PAUSED", "STANDBY", "IDLE", "STOPPED")):
            bg = "#78350f"
            color = "#fbbf24"
            border = "#d97706"
            icon = "•"
        else:  # Not connected, missing, error, unconfigured, unpolled, locked
            bg = "#7f1d1d"
            color = "#f87171"
            border = "#dc2626"
            icon = "✖"

        clean_text = status.replace("✓", "").replace("•", "").replace("✖", "").replace("✗", "").replace("●", "").strip()
        self.setText(f"{icon} {clean_text}")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"""
            background-color: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 8.5pt;
            font-weight: 700;
            """
        )


class KPICard(ElevatedCardWidget):
    """Executive KPI card with simple attractive dark Fluent design, no colored borders, crisp white values."""

    def __init__(
        self,
        title: str,
        initial_value: str = "NOT ACTIVE",
        subtext: str = "",
        color_hex: str = "#ffffff",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._build_ui(title, initial_value, subtext)

    def _build_ui(self, title: str, initial_value: str, subtext: str):
        self.setStyleSheet("""
            ElevatedCardWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            ElevatedCardWidget:hover {
                border: 1px solid #475569;
                background-color: #243247;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(4)

        self.lbl_title = CaptionLabel(title.upper())
        self.lbl_title.setStyleSheet("color: #cbd5e1; font-size: 8pt; font-weight: 700; letter-spacing: 0.5px;")
        lay.addWidget(self.lbl_title)

        self.lbl_val = QLabel(initial_value)
        self.lbl_val.setStyleSheet("font-size: 20pt; font-weight: 800; color: #ffffff; margin: 4px 0;")
        lay.addWidget(self.lbl_val)

        self.lbl_sub = QLabel(subtext)
        self.lbl_sub.setStyleSheet("color: #e2e8f0; font-size: 8.5pt; font-weight: 500;")
        lay.addWidget(self.lbl_sub)

        # Source / Date footer
        self.lbl_footer = QLabel("")
        self.lbl_footer.setStyleSheet("color: #94a3b8; font-size: 7.8pt;")
        lay.addWidget(self.lbl_footer)

    def set_data(
        self,
        value: str,
        subtext: str = "",
        source: str = "Excel",
        report_date: str = "",
        is_active: bool = True,
    ):
        if not is_active or value.upper() in ("NOT ACTIVE", "NO DATA AVAILABLE", "—", "NONE"):
            self.lbl_val.setText("NOT ACTIVE")
            self.lbl_val.setStyleSheet("font-size: 15pt; font-weight: 700; color: #94a3b8; margin: 4px 0;")
            self.lbl_sub.setText("No data recorded")
            self.lbl_footer.setText("Source: Unavailable")
            return

        self.lbl_val.setText(value)
        self.lbl_val.setStyleSheet("font-size: 20pt; font-weight: 800; color: #ffffff; margin: 4px 0;")
        self.lbl_sub.setText(subtext)

        footer_parts = []
        if source:
            footer_parts.append(f"Source: {source}")
        if report_date:
            footer_parts.append(f"Date: {report_date}")
        self.lbl_footer.setText(" • ".join(footer_parts))


class StatusCard(SimpleCardWidget):
    """Service status card displaying dynamic health, timestamp, and details."""

    def __init__(
        self,
        title: str,
        status: str = "NOT ACTIVE",
        details: str = "",
        timestamp: str = "",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet("""
            SimpleCardWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        self.lbl_title = StrongBodyLabel(title)
        self.lbl_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 10pt;")
        hdr.addWidget(self.lbl_title)
        hdr.addStretch()

        self.badge = StatusBadge(status)
        hdr.addWidget(self.badge)
        lay.addLayout(hdr)

        self.lbl_details = QLabel(details)
        self.lbl_details.setWordWrap(True)
        self.lbl_details.setStyleSheet("color: #cbd5e1; font-size: 8.8pt;")
        lay.addWidget(self.lbl_details)

        footer = QHBoxLayout()
        self.lbl_time = QLabel(f"Last Checked: {timestamp}" if timestamp else "")
        self.lbl_time.setStyleSheet("color: #94a3b8; font-size: 7.8pt;")
        footer.addWidget(self.lbl_time)
        footer.addStretch()

        if action_text and action_callback:
            btn = PushButton(action_text, self)
            btn.clicked.connect(action_callback)
            footer.addWidget(btn)

        lay.addLayout(footer)

    def update_status(self, status: str, details: str = "", timestamp: str = ""):
        self.badge.set_status(status)
        if details:
            self.lbl_details.setText(details)
        if timestamp:
            self.lbl_time.setText(f"Last Checked: {timestamp}")


class EmptyState(QFrame):
    """Placeholder view when data or search results are absent."""

    def __init__(
        self,
        title: str = "No Data Available",
        description: str = "No recorded energy telemetry found for the selected criteria.",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(8)

        icon_lbl = QLabel("📋")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 32pt; margin-bottom: 4px;")
        lay.addWidget(icon_lbl)

        t_lbl = StrongBodyLabel(title)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet("color: #ffffff; font-size: 12pt; font-weight: 700;")
        lay.addWidget(t_lbl)

        d_lbl = CaptionLabel(description)
        d_lbl.setAlignment(Qt.AlignCenter)
        d_lbl.setStyleSheet("color: #cbd5e1; font-size: 9pt;")
        lay.addWidget(d_lbl)

        if action_text and action_callback:
            btn = PrimaryPushButton(action_text, self)
            btn.clicked.connect(action_callback)
            lay.addWidget(btn, 0, Qt.AlignCenter)


class PageHeader(QWidget):
    """Standardized top page header with Windows 11 Fluent typography."""

    def __init__(self, title: str, subtitle: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(2)

        self.lbl_title = TitleLabel(title)
        self.lbl_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 14pt;")
        lay.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_subtitle = CaptionLabel(subtitle)
            self.lbl_subtitle.setStyleSheet("color: #cbd5e1; font-size: 9.5pt;")
            lay.addWidget(self.lbl_subtitle)

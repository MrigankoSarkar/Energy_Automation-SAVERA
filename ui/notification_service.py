"""
Centralized Notification Service for EnergyAutomation Desktop Application.
Provides user-friendly toast notifications (InfoBar) and structured dialogs
with plain-language explanations for operators and expandable technical details for engineers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    TransparentPushButton,
    StrongBodyLabel,
    BodyLabel,
    CaptionLabel,
)


class NotificationSeverity(Enum):
    SUCCESS = "SUCCESS"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class UINotification:
    id: str
    severity: NotificationSeverity
    title: str
    message: str
    technical_details: Optional[str] = None
    timestamp: str = ""
    source: str = "System"
    action_text: Optional[str] = None


class FriendlyNotificationDialog(QDialog):
    """Clean, accessible dialog showing what happened, why, action items, and technical details."""

    def __init__(
        self,
        severity: NotificationSeverity,
        title: str,
        message: str,
        technical_details: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"EnergyAutomation — {title}")
        self.setMinimumWidth(500)
        self.setStyleSheet("background-color: #ffffff; color: #0f172a;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header with icon and title
        hdr = QHBoxLayout()
        icon_str = {
            NotificationSeverity.SUCCESS: "✓",
            NotificationSeverity.INFO: "ℹ",
            NotificationSeverity.WARNING: "⚠",
            NotificationSeverity.ERROR: "✗",
            NotificationSeverity.CRITICAL: "🚨",
        }.get(severity, "ℹ")

        color_str = {
            NotificationSeverity.SUCCESS: "#16a34a",
            NotificationSeverity.INFO: "#0284c7",
            NotificationSeverity.WARNING: "#d97706",
            NotificationSeverity.ERROR: "#dc2626",
            NotificationSeverity.CRITICAL: "#b91c1c",
        }.get(severity, "#0284c7")

        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet(f"font-size: 20pt; font-weight: 800; color: {color_str}; margin-right: 8px;")
        hdr.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: 800; color: #0f172a;")
        hdr.addWidget(title_lbl, 1)
        layout.addLayout(hdr)

        # User-friendly explanation
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #334155; font-size: 10pt; line-height: 1.4;")
        layout.addWidget(msg_lbl)

        # Expandable technical details
        if technical_details:
            self.btn_details = TransparentPushButton("Show Technical Details ▾", self)
            layout.addWidget(self.btn_details)

            self.tech_edit = QTextEdit(self)
            self.tech_edit.setPlainText(technical_details)
            self.tech_edit.setReadOnly(True)
            self.tech_edit.setFixedHeight(120)
            self.tech_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 8.5pt; background: #f8fafc; color: #334155; border: 1px solid #e2e8f0;")
            self.tech_edit.setVisible(False)
            layout.addWidget(self.tech_edit)

            self.btn_details.clicked.connect(self._toggle_details)

        # Action buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_ok = PrimaryPushButton("OK", self)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

    def _toggle_details(self):
        is_vis = not self.tech_edit.isVisible()
        self.tech_edit.setVisible(is_vis)
        self.btn_details.setText("Hide Technical Details ▴" if is_vis else "Show Technical Details ▾")


class UINotificationService:
    """Central notification service orchestrating InfoBar toasts and structured history."""

    def __init__(self, main_window: Optional[QWidget] = None):
        self.main_window = main_window
        self.history: List[UINotification] = []

    def set_main_window(self, window: QWidget):
        self.main_window = window

    def notify_success(self, title: str, content: str, duration: int = 3500):
        self._record(NotificationSeverity.SUCCESS, title, content)
        if self.main_window:
            InfoBar.success(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=duration,
                parent=self.main_window,
            )

    def notify_info(self, title: str, content: str, duration: int = 3500):
        self._record(NotificationSeverity.INFO, title, content)
        if self.main_window:
            InfoBar.info(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=duration,
                parent=self.main_window,
            )

    def notify_warning(self, title: str, content: str, duration: int = 4500):
        self._record(NotificationSeverity.WARNING, title, content)
        if self.main_window:
            InfoBar.warning(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=duration,
                parent=self.main_window,
            )

    def notify_error(self, title: str, content: str, technical_details: Optional[str] = None, show_dialog: bool = False):
        self._record(NotificationSeverity.ERROR, title, content, technical_details)
        if self.main_window:
            InfoBar.error(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=6000,
                parent=self.main_window,
            )
            if show_dialog:
                dlg = FriendlyNotificationDialog(
                    severity=NotificationSeverity.ERROR,
                    title=title,
                    message=content,
                    technical_details=technical_details,
                    parent=self.main_window,
                )
                dlg.exec()

    def _record(self, severity: NotificationSeverity, title: str, message: str, technical: Optional[str] = None):
        import uuid
        notif = UINotification(
            id=str(uuid.uuid4())[:8],
            severity=severity,
            title=title,
            message=message,
            technical_details=technical,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        self.history.append(notif)
        if len(self.history) > 100:
            self.history.pop(0)

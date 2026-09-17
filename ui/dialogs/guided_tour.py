"""
Interactive Guided Tour & Product Walkthrough Dialog for EnergyAutomation.
Educates users on application features using clear, accessible language,
styled with PySide6 + QFluentWidgets components.
"""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ElevatedCardWidget,
    PrimaryPushButton,
    PushButton,
    TransparentPushButton,
    ProgressBar,
    TitleLabel,
    BodyLabel,
    CaptionLabel,
    StrongBodyLabel,
)

TOUR_STOPS: List[Dict[str, str]] = [
    {
        "title": "Welcome to EnergyAutomation",
        "icon": "⚡",
        "what": "EnergyAutomation is an enterprise Energy Management System (EMS) desktop platform built for Savera MS.",
        "why": "It eliminates manual daily Excel keying by automatically downloading NBSense reports from Gmail, validating readings, preserving Excel formulas, and delivering real-time executive analytics via Streamlit BI.",
        "how": "Follow this brief 1-minute guided tour to explore the major capabilities of the platform.",
    },
    {
        "title": "1. Executive Dashboard",
        "icon": "🏠",
        "what": "Central operations hub with live system health, automation states, and daily energy KPI cards.",
        "why": "Provides executives and plant managers with an instant 10-second pulse on whether today's report was ingested successfully.",
        "how": "Check the System Readiness banner and click 'Run Automation Now' to trigger an immediate ingestion cycle.",
    },
    {
        "title": "2. System Health Matrix",
        "icon": "🩺",
        "what": "Live subsystem monitor tracking Gmail, EMS Reports, Excel, Automation Scheduler, Gemini AI, and Streamlit BI.",
        "why": "Clearly distinguishes healthy systems from services requiring credentials or attention.",
        "how": "Review the status dots. Click 'Configure...' on any warning badge to resolve credentials or connection settings.",
    },
    {
        "title": "3. Energy KPIs & Overview",
        "icon": "⚡",
        "what": "Comprehensive consumption cards showing Today (kWh), Previous Shift (kWh), Month-To-Date (MTD), and Year-To-Date (YTD).",
        "why": "Allows instant comparison of current shifts against baseline historical consumption targets.",
        "how": "Inspect the Day-over-Day variance badge to detect unexpected consumption spikes immediately.",
    },
    {
        "title": "4. Energy Trends & Analytics",
        "icon": "📊",
        "what": "Advanced mathematical analysis of daily, weekly, and monthly consumption trends.",
        "why": "Highlights baseline anomalies, average consumption per active meter, and equipment efficiency shifts.",
        "how": "Navigate to the Energy Analytics view to review historical averages and equipment rankings.",
    },
    {
        "title": "5. Meter Analysis & Plant Map",
        "icon": "🗺",
        "what": "Full catalog of all 18 industrial meters organized into 7 Savera MS manufacturing zones.",
        "why": "Ensures every machine cell (Press Shop, Machining, Welding, Compressors, Paint) is accounted for with rated power.",
        "how": "Click on any zone in the Plant Topology Map to inspect constituent meters and operational load badges.",
    },
    {
        "title": "6. Shift Reports & Audit Trail",
        "icon": "📄",
        "what": "An immutable audit ledger of every processed NBSense PDF report stored in the local SQLite database.",
        "why": "Provides full auditability with SHA-256 attachment hashes, processing timestamps, and meter counts.",
        "how": "Filter by date or attachment name to inspect verified historical reports and cell coordinates.",
    },
    {
        "title": "7. Historical Data Recovery",
        "icon": "🔄",
        "what": "Automated detection and backfilling of missing report dates across a 30-day window.",
        "why": "Prevents weekend gaps (Sundays) or machine downtime from causing month-end accounting discrepancies.",
        "how": "Click 'Scan for Missing Dates' to check for calendar gaps, then click 'Run Historical Gap Healing Now'.",
    },
    {
        "title": "8. Google Gemini AI Insights",
        "icon": "🤖",
        "what": "Conversational energy intelligence assistant powered by Google Gemini (Advisory Layer).",
        "why": "Allows managers to ask natural-language questions without writing database queries.",
        "how": "Type a query or click suggested prompt chips. Note: AI is strictly read-only and never modifies Excel formulas.",
    },
    {
        "title": "9. Streamlit Management BI",
        "icon": "📈",
        "what": "Real-time, interactive cloud or local web analytics dashboard reading directly from your synchronized Excel workbook.",
        "why": "Provides executives, plant heads, and engineers with KPI gauges, load duration curves, and shift breakdowns from any browser or mobile device without risking Excel formula corruption.",
        "how": "Navigate to the Streamlit BI page, click 'Launch in Browser' to open http://localhost:8501, or start the local background server.",
    },
    {
        "title": "10. Processing History & Logs",
        "icon": "🕘",
        "what": "Detailed operational logs and execution traces capturing every automated and manual run.",
        "why": "Assists plant engineers and IT administrators in diagnosing network delays, file locks, or parsing warnings.",
        "how": "Navigate to 'Processing History' to inspect live event streams and execution durations.",
    },
    {
        "title": "11. System Configuration & Settings",
        "icon": "⚙",
        "what": "Centralized settings managing Excel workbook paths, SQLite database paths, Gmail OAuth, and polling schedules.",
        "why": "Ensures configuration parameters and file paths can be maintained without modifying source code.",
        "how": "Use the file browser or click 'Launch Full Configuration Setup Wizard' to reconfigure credentials anytime.",
    },
    {
        "title": "12. Help Center & Support",
        "icon": "❓",
        "what": "Built-in operational documentation including 13 step-by-step guides, FAQ, and an electrical glossary.",
        "why": "Empowers non-technical operators to understand system behavior and resolve common operational questions.",
        "how": "Select any topic tab in the Help Center to review plain-language guidance, or click 'Restart Guided Tour'.",
    },
    {
        "title": "Tour Complete!",
        "icon": "🎉",
        "what": "You are fully equipped to operate EnergyAutomation.",
        "why": "All core systems are operational, fortified against formula corruption, and self-healing.",
        "how": "Click 'Finish Tour' to return to the Executive Dashboard. You can restart this tour anytime from Help & Support.",
    },
]


class GuidedTourDialog(QDialog):
    """
    Step-by-step interactive product tour with QFluentWidgets components.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("EnergyAutomation — Interactive Guided Tour")
        self.resize(680, 460)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #0f172a;
            }
            QLabel {
                color: #0f172a;
            }
        """)
        self.current_idx = 0
        self.total_stops = len(TOUR_STOPS)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Top header with Back to Dashboard button and step counter
        top_bar = QHBoxLayout()
        self.btn_top_back = TransparentPushButton("← Back to Dashboard", self)
        self.btn_top_back.setCursor(Qt.PointingHandCursor)
        self.btn_top_back.clicked.connect(self.reject)
        top_bar.addWidget(self.btn_top_back)
        top_bar.addStretch()

        self.step_counter = CaptionLabel(f"Step 1 of {self.total_stops}", self)
        top_bar.addWidget(self.step_counter)
        root.addLayout(top_bar)

        # Progress bar
        self.progress = ProgressBar(self)
        self.progress.setRange(0, self.total_stops)
        self.progress.setValue(1)
        self.progress.setFixedHeight(6)
        root.addWidget(self.progress)

        # Content card
        self.card = ElevatedCardWidget(self)
        self.card.setStyleSheet("""
            ElevatedCardWidget {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(20, 18, 20, 18)
        card_lay.setSpacing(12)

        header_box = QHBoxLayout()
        self.lbl_icon = QLabel("⚡")
        self.lbl_icon.setStyleSheet("font-size: 24pt;")
        header_box.addWidget(self.lbl_icon)

        self.lbl_title = TitleLabel(TOUR_STOPS[0]["title"], self.card)
        self.lbl_title.setStyleSheet("color: #0f172a; font-weight: 700;")
        header_box.addWidget(self.lbl_title)
        header_box.addStretch()
        card_lay.addLayout(header_box)

        # Section: What
        card_lay.addWidget(self._create_section_hdr("WHAT IS THIS?"))
        self.lbl_what = BodyLabel(TOUR_STOPS[0]["what"], self.card)
        self.lbl_what.setWordWrap(True)
        self.lbl_what.setStyleSheet("color: #334155; font-size: 10pt; line-height: 1.4;")
        card_lay.addWidget(self.lbl_what)

        # Section: Why
        card_lay.addWidget(self._create_section_hdr("WHY IS IT USEFUL?"))
        self.lbl_why = BodyLabel(TOUR_STOPS[0]["why"], self.card)
        self.lbl_why.setWordWrap(True)
        self.lbl_why.setStyleSheet("color: #334155; font-size: 10pt; line-height: 1.4;")
        card_lay.addWidget(self.lbl_why)

        # Section: How
        card_lay.addWidget(self._create_section_hdr("HOW DO I USE IT?"))
        self.lbl_how = BodyLabel(TOUR_STOPS[0]["how"], self.card)
        self.lbl_how.setWordWrap(True)
        self.lbl_how.setStyleSheet("color: #334155; font-size: 10pt; line-height: 1.4;")
        card_lay.addWidget(self.lbl_how)

        card_lay.addStretch()
        root.addWidget(self.card, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        btn_skip = TransparentPushButton("Skip Tour", self)
        btn_skip.clicked.connect(self.reject)
        nav.addWidget(btn_skip)

        nav.addStretch()

        self.btn_prev = PushButton("← Back to Dashboard", self)
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_prev.setEnabled(True)
        nav.addWidget(self.btn_prev)

        self.btn_next = PrimaryPushButton("Next →", self)
        self.btn_next.clicked.connect(self._go_next)
        nav.addWidget(self.btn_next)

        root.addLayout(nav)

    @staticmethod
    def _create_section_hdr(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 8pt; font-weight: 700; color: #2563eb; letter-spacing: 0.5px; margin-top: 4px;")
        return lbl

    def _go_next(self):
        if self.current_idx < self.total_stops - 1:
            self.current_idx += 1
            self._update_stop()
        else:
            self.accept()

    def _go_prev(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._update_stop()
        else:
            self.reject()

    def _update_stop(self):
        s = TOUR_STOPS[self.current_idx]
        self.lbl_icon.setText(s["icon"])
        self.lbl_title.setText(s["title"])
        self.lbl_what.setText(s["what"])
        self.lbl_why.setText(s["why"])
        self.lbl_how.setText(s["how"])

        self.progress.setValue(self.current_idx + 1)
        self.step_counter.setText(f"Step {self.current_idx + 1} of {self.total_stops}")
        self.btn_prev.setEnabled(True)
        if self.current_idx == 0:
            self.btn_prev.setText("← Back to Dashboard")
        else:
            self.btn_prev.setText("← Back")

        if self.current_idx == self.total_stops - 1:
            self.btn_next.setText("Finish Tour")
        else:
            self.btn_next.setText("Next →")

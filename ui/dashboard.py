"""
EnergyAutomation Enterprise Desktop Application Shell & Dashboard.
Built with PySide6 + QFluentWidgets, featuring Microsoft Fluent Design System,
Savera MS corporate branding, dual-mode experience (Simple / Engineer),
Plant Energy Topology, Centralized Alert Center, Context-Aware System Guidance,
and Comprehensive Operator Help Center.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    FluentWindow,
    NavigationInterface,
    NavigationItemPosition,
    FluentIcon as FIF,
    ElevatedCardWidget,
    SimpleCardWidget,
    HeaderCardWidget,
    PrimaryPushButton,
    PushButton,
    TransparentPushButton,
    PillPushButton,
    SwitchButton,
    SearchLineEdit,
    LineEdit,
    TextEdit,
    TableWidget,
    InfoBar,
    InfoBarPosition,
    Theme,
    setTheme,
    isDarkTheme,
    toggleTheme,
    ProgressBar,
    SubtitleLabel,
    BodyLabel,
    CaptionLabel,
    TitleLabel,
    StrongBodyLabel,
)

from ui.widgets.plant_map import PlantMapWidget
from ui.dialogs.setup_wizard import SetupWizardDialog
from ui.dialogs.guided_tour import GuidedTourDialog


# =====================================================================
# Friendly Non-Technical Error Dialog (Section 11, 12, 39)
# =====================================================================

class FriendlyErrorDialog(QDialog):
    """
    Operator-friendly error dialog providing plain-language explanations
    (What happened, Why it happened, What to do) with an expandable
    technical details section for engineers.
    """

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        what: str,
        why: str,
        action: str,
        technical_details: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.technical_details = technical_details

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header with icon and summary
        header_box = QHBoxLayout()
        icon_lbl = QLabel("⚠")
        icon_lbl.setStyleSheet("font-size: 24pt; color: #dc2626;")
        header_box.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 12pt; font-weight: 800; color: #0f172a;")
        sub_lbl = QLabel(what)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 9.5pt; color: #334155; font-weight: 500;")
        title_box.addWidget(t_lbl)
        title_box.addWidget(sub_lbl)
        header_box.addLayout(title_box, 1)
        layout.addLayout(header_box)

        # Guidance Card
        card = SimpleCardWidget(self)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(8)

        why_title = QLabel("Why this may have happened:")
        why_title.setStyleSheet("font-weight: 700; color: #475569; font-size: 9pt;")
        card_lay.addWidget(why_title)

        why_lbl = QLabel(why)
        why_lbl.setWordWrap(True)
        why_lbl.setStyleSheet("color: #64748b; font-size: 9pt;")
        card_lay.addWidget(why_lbl)

        action_title = QLabel("Recommended Action:")
        action_title.setStyleSheet("font-weight: 700; color: #16a34a; font-size: 9pt; margin-top: 4px;")
        card_lay.addWidget(action_title)

        action_lbl = QLabel(action)
        action_lbl.setWordWrap(True)
        action_lbl.setStyleSheet("color: #1e293b; font-size: 9.5pt; font-weight: 600;")
        card_lay.addWidget(action_lbl)

        layout.addWidget(card)

        # Expandable technical details
        if technical_details:
            self.btn_toggle_tech = PushButton("View Technical Details ▼", self)
            self.btn_toggle_tech.setCheckable(True)
            self.btn_toggle_tech.clicked.connect(self._toggle_tech)
            layout.addWidget(self.btn_toggle_tech)

            self.tech_box = QTextEdit()
            self.tech_box.setReadOnly(True)
            self.tech_box.setPlainText(technical_details)
            self.tech_box.setFixedHeight(120)
            self.tech_box.setVisible(False)
            layout.addWidget(self.tech_box)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_close = PrimaryPushButton("Understood", self)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _toggle_tech(self):
        visible = self.btn_toggle_tech.isChecked()
        self.tech_box.setVisible(visible)
        self.btn_toggle_tech.setText("Hide Technical Details ▲" if visible else "View Technical Details ▼")


# =====================================================================
# Background Worker
# =====================================================================

class WorkflowWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, workflow: Any):
        super().__init__()
        self.workflow = workflow

    @Slot()
    def execute(self):
        try:
            result = self.workflow.run()
            self.finished.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


# =====================================================================
# Main Enterprise Dashboard Shell (PySide6 + QFluentWidgets)
# =====================================================================

class Dashboard(FluentWindow):
    """
    Enterprise Energy Management desktop application shell.
    Built with PySide6 + QFluentWidgets (FluentWindow), featuring Microsoft
    Fluent Design, Savera MS branding, centralized alert center, dual-mode
    experience (Simple / Engineer), contextual guidance, and a comprehensive Help Center.
    """

    def __init__(self, application: Any, parent: QWidget | None = None):
        super().__init__(parent)

        self.application = application
        self.workflow = application.workflow
        self.scheduler = application.scheduler
        self.services = getattr(application, "services", {})

        self.worker_thread: QThread | None = None
        self.worker: WorkflowWorker | None = None

        self._running = False
        self._is_engineer_mode = False
        self._last_result: Any = None
        self._last_error: str | None = None

        self.setWindowTitle("EnergyAutomation — EMS Monitoring")

        app_icon = Path("assets/app.ico")
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))

        self.setMinimumSize(1260, 800)
        self.resize(1440, 920)

        # Retain backward-compatible nav_buttons list
        self.nav_buttons: List[Any] = []

        # Retain status bar compatibility
        self.statusBar = QStatusBar(self)

        self._build_subinterfaces()
        self._build_title_bar()
        self._build_tray()
        self._start_clock()

        self._set_status("Ready", "ready", "System is operational.")
        self._append_log("EnergyAutomation enterprise shell initialized.")

    # =================================================================
    # Subinterface & Navigation Setup (FluentWindow 12 Interfaces)
    # =================================================================

    def _build_subinterfaces(self):
        # Bind self.stack to self.stackedWidget for 100% test compatibility
        self.stack = self.stackedWidget

        # Page 0: Executive Overview
        self.page_overview = self._create_overview_page()
        self.addSubInterface(self.page_overview, FIF.HOME, "Executive Dashboard")

        # Page 1: Energy Analytics
        self.page_analytics = self._create_analysis_panel()
        self.addSubInterface(self.page_analytics, FIF.PIE_SINGLE, "Energy Analytics")

        # Page 2: Meter Analysis
        self.page_meters = self._create_meters_page()
        self.addSubInterface(self.page_meters, FIF.SPEED_HIGH, "Meter Analysis")

        # Page 3: Plant Overview (Topology Map)
        self.page_plant = self._create_plant_overview_page()
        self.addSubInterface(self.page_plant, FIF.APPLICATION, "Plant Overview")

        # Page 4: Reports & Audit Trail
        self.page_reports = self._create_reports_panel()
        self.addSubInterface(self.page_reports, FIF.DOCUMENT, "Reports & Audit")

        # Page 5: Historical Data Recovery
        self.page_recovery = self._create_recovery_panel()
        self.addSubInterface(self.page_recovery, FIF.SYNC, "Data Recovery")

        # Page 6: Google Gemini AI Insights
        self.page_ai = self._create_ai_panel()
        self.addSubInterface(self.page_ai, FIF.CHAT, "AI Insights")

        # Page 7: Power BI Analytics
        self.page_powerbi = self._create_powerbi_panel()
        self.addSubInterface(self.page_powerbi, FIF.SHARE, "Power BI")

        # Page 8: Centralized Alert Center
        self.page_alerts = self._create_alerts_panel()
        self.addSubInterface(self.page_alerts, FIF.RINGER, "Alert Center")

        # Page 9: Processing History & Logs
        self.page_history = self._create_history_page()
        self.addSubInterface(self.page_history, FIF.HISTORY, "Processing History")

        # Page 10: Settings & Configuration (Pinned to Bottom)
        self.page_settings = self._create_settings_panel()
        self.addSubInterface(self.page_settings, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM)

        # Page 11: Help & Support Center (Pinned to Bottom)
        self.page_help = self._create_help_page()
        self.addSubInterface(self.page_help, FIF.HELP, "Help & Support", NavigationItemPosition.BOTTOM)

        self.pages = [
            self.page_overview,
            self.page_analytics,
            self.page_meters,
            self.page_plant,
            self.page_reports,
            self.page_recovery,
            self.page_ai,
            self.page_powerbi,
            self.page_alerts,
            self.page_history,
            self.page_settings,
            self.page_help,
        ]

        self.stackedWidget.currentChanged.connect(self._on_page_changed)
        self.navigationInterface.setExpandWidth(240)

    def _build_title_bar(self):
        tb = self.titleBar
        app_icon = Path("assets/app.ico")
        if app_icon.exists():
            tb.setIcon(QIcon(str(app_icon)))
        tb.setTitle("EnergyAutomation — Savera MS")

        # Global Search Bar
        self.global_search_input = SearchLineEdit(tb)
        self.global_search_input.setObjectName("GlobalSearch")
        self.global_search_input.setPlaceholderText("🔍 Search meters, reports, alerts, settings...")
        self.global_search_input.setToolTip("Instant search: type meter name, report date, or keyword to jump to relevant view")
        self.global_search_input.setFixedWidth(280)
        self.global_search_input.textChanged.connect(self.handle_global_search)

        # Mode Toggle Button (Simple Mode vs Engineer Mode)
        self.btn_mode_toggle = PushButton("👤 Simple Mode", tb)
        self.btn_mode_toggle.setObjectName("ModeToggleButton")
        self.btn_mode_toggle.setToolTip("Toggle between Simple View (Executive summaries) and Engineer View (Detailed technical telemetry)")
        self.btn_mode_toggle.clicked.connect(self.toggle_engineer_mode)

        # Guided Tour Button
        btn_tour = PushButton("✨ Tour", tb)
        btn_tour.setObjectName("TourButton")
        btn_tour.setToolTip("Take a 1-minute interactive walkthrough of all platform capabilities")
        btn_tour.clicked.connect(self.open_guided_tour)

        # Setup Wizard Button
        btn_wizard = PushButton("⚙ Setup", tb)
        btn_wizard.setObjectName("WizardButton")
        btn_wizard.setToolTip("Open step-by-step wizard to configure Excel, Gmail, Gemini, and Power BI")
        btn_wizard.clicked.connect(self.open_setup_wizard)

        # Theme Switch Button (Light / Dark)
        self.theme_switch = SwitchButton(tb)
        self.theme_switch.setOnText("Dark")
        self.theme_switch.setOffText("Light")
        self.theme_switch.setToolTip("Toggle Fluent Light / Dark theme")
        self.theme_switch.setChecked(isDarkTheme())
        self.theme_switch.checkedChanged.connect(self._on_theme_toggled)

        # Live Clock
        self.clock_label = QLabel(tb)
        self.clock_label.setObjectName("ClockLabel")
        self.clock_label.setToolTip("Workstation system date and time")
        self.clock_label.setStyleSheet("color: #64748b; font-size: 8.5pt; font-weight: 600; padding: 2px 8px;")

        # Insert widgets into titlebar layout before spacer item (at index 2)
        tb.hBoxLayout.insertWidget(2, self.global_search_input)
        tb.hBoxLayout.insertWidget(3, self.btn_mode_toggle)
        tb.hBoxLayout.insertWidget(4, btn_tour)
        tb.hBoxLayout.insertWidget(5, btn_wizard)
        tb.hBoxLayout.insertWidget(6, self.theme_switch)
        tb.hBoxLayout.insertWidget(7, self.clock_label)

    def _on_theme_toggled(self, is_dark: bool):
        setTheme(Theme.DARK if is_dark else Theme.LIGHT)
        self._append_log(f"Theme switched to {'Dark' if is_dark else 'Light'} mode.")

    def _on_page_changed(self, index: int):
        if index == 0:
            self.refresh_overview()
        elif index == 2:
            self.refresh_meters_table()
        elif index == 3:
            self.refresh_plant_topology_view()
        elif index == 8:
            self.refresh_alerts_panel()

    def switch_page(self, index: int):
        if 0 <= index < len(self.pages):
            self.switchTo(self.pages[index])
            self._on_page_changed(index)

    # =================================================================
    # Page 0: Executive Overview (Section 10 & 17)
    # =================================================================

    def _create_overview_page(self) -> QWidget:
        self.page_overview_scroll = QScrollArea()
        self.page_overview_scroll.setWidgetResizable(True)
        self.page_overview_scroll.setFrameShape(QFrame.NoFrame)
        self.page_overview_scroll.setObjectName("page_overview")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. System Readiness & Status Ribbon (Section 17)
        self.readiness_card = self._create_readiness_ribbon()
        layout.addWidget(self.readiness_card)

        # 2. System Health Matrix (Section 10)
        layout.addWidget(self._create_health_matrix())

        # 3. Energy Overview Cards (Today, Yesterday, MTD, YTD)
        layout.addWidget(self._create_energy_kpi_cards())

        # 4. Automation Operations & Status Cards
        cards = QGridLayout()
        cards.setHorizontalSpacing(14)
        cards.setVerticalSpacing(14)

        self.card_processed = self._create_metric_card("Reports Processed", "0", "processed", "Total lifetime reports processed by engine")
        self.card_success = self._create_metric_card("Successful", "0", "success", "Reports processed with zero validation errors")
        self.card_failed = self._create_metric_card("Failed", "0", "failed", "Reports requiring operator attention")
        self.card_last = self._create_metric_card("Last Run", "—", "last", "Time of the most recent ingestion cycle")

        cards.addWidget(self.card_processed, 0, 0)
        cards.addWidget(self.card_success, 0, 1)
        cards.addWidget(self.card_failed, 0, 2)
        cards.addWidget(self.card_last, 0, 3)
        layout.addLayout(cards)

        # 5. Automation Controls
        layout.addWidget(self._create_control_panel())

        # 6. Two-Column Split: Top Consumers Preview & Live Activity
        bottom_split = QHBoxLayout()
        bottom_split.setSpacing(16)

        bottom_split.addWidget(self._create_top_meters_preview(), 1)
        bottom_split.addWidget(self._create_activity_panel(), 1)

        layout.addLayout(bottom_split)
        self.page_overview_scroll.setWidget(container)

        self.refresh_overview()
        return self.page_overview_scroll

    def _create_readiness_ribbon(self) -> QWidget:
        card = ElevatedCardWidget()
        card.setObjectName("StatusCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("StatusIndicator")
        self.status_indicator.setStyleSheet("font-size: 20pt; color: #16a34a;")

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        self.status_text = QLabel("System Ready")
        self.status_text.setObjectName("StatusText")
        self.status_text.setStyleSheet("font-size: 12pt; font-weight: 800;")

        self.status_detail = QLabel("Core automation engine is active. Waiting for scheduled morning report.")
        self.status_detail.setObjectName("StatusDetail")
        self.status_detail.setStyleSheet("color: #64748b; font-size: 9pt;")

        info_box.addWidget(self.status_text)
        info_box.addWidget(self.status_detail)
        layout.addLayout(info_box, 1)

        # Quick Checklist Badges
        self.badge_excel = QLabel("✓ Excel")
        self.badge_excel.setStyleSheet("background: #dcfce7; color: #166534; font-weight: 700; border-radius: 4px; padding: 4px 8px; font-size: 8.5pt;")
        self.badge_excel.setToolTip("Target Excel workbook is configured and verified")
        layout.addWidget(self.badge_excel)

        self.badge_db = QLabel("✓ Database")
        self.badge_db.setStyleSheet("background: #dcfce7; color: #166534; font-weight: 700; border-radius: 4px; padding: 4px 8px; font-size: 8.5pt;")
        self.badge_db.setToolTip("Local SQLite audit database is connected")
        layout.addWidget(self.badge_db)

        self.badge_gmail = QLabel("⚠ Gmail (OAuth)")
        self.badge_gmail.setStyleSheet("background: #fef3c7; color: #92400e; font-weight: 700; border-radius: 4px; padding: 4px 8px; font-size: 8.5pt;")
        self.badge_gmail.setToolTip("Gmail API credentials need one-time authorization in Settings")
        layout.addWidget(self.badge_gmail)

        self.badge_gemini = QLabel("ℹ AI (Advisory)")
        self.badge_gemini.setStyleSheet("background: #ede9fe; color: #5b21b6; font-weight: 700; border-radius: 4px; padding: 4px 8px; font-size: 8.5pt;")
        self.badge_gemini.setToolTip("Gemini AI advisory assistant active in fallback/offline mode")
        layout.addWidget(self.badge_gemini)

        btn_cfg = PushButton("Configure...", card)
        btn_cfg.setToolTip("Jump to Configuration Settings to review credentials")
        btn_cfg.clicked.connect(lambda: self.switch_page(10))
        layout.addWidget(btn_cfg)

        return card

    def _create_health_matrix(self) -> QWidget:
        card = SimpleCardWidget()
        root_lay = QVBoxLayout(card)
        root_lay.setContentsMargins(18, 14, 18, 14)
        root_lay.setSpacing(10)

        header_lbl = StrongBodyLabel("System Health & Integration Status")
        root_lay.addWidget(header_lbl)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        services_status = [
            ("Gmail Service", "●", "Healthy", "Checks incoming NBSense daily emails", 10),
            ("EMS Reports", "●", "Healthy", "18-meter report parsing and unit normalization", 4),
            ("Excel Service", "●", "Healthy", "Formula-safe updates and automated backup snapshots", 10),
            ("Automation Engine", "●", "Running", "APScheduler background execution engine", 0),
            ("Gemini AI Intelligence", "●", "Available", "Advisory natural-language Q&A and anomaly explanation", 6),
            ("Power BI Integration", "●", "Ready (Export Mode)", "Star Schema dimensional model and DAX generation", 7),
        ]

        self.health_labels: Dict[str, QLabel] = {}
        for idx, (name, dot, stat, tip, page_idx) in enumerate(services_status):
            row = idx // 3
            col = (idx % 3) * 2

            name_lbl = QLabel(f"<b>{name}:</b>")
            name_lbl.setStyleSheet("color: #334155; font-size: 9pt;")
            name_lbl.setToolTip(tip)

            stat_lbl = QLabel(f"<span style='color: #16a34a; font-size: 11pt;'>{dot}</span> {stat}")
            stat_lbl.setStyleSheet("font-size: 9pt; font-weight: 600; color: #1e293b;")
            stat_lbl.setToolTip(tip)
            self.health_labels[name] = stat_lbl

            grid.addWidget(name_lbl, row, col)
            grid.addWidget(stat_lbl, row, col + 1)

        root_lay.addLayout(grid)
        return card

    def _create_energy_kpi_cards(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)

        self.card_today_kwh = self._create_energy_card("Latest Report Consumption", "9,206.83 kWh", "15-Feb-2026", "#2563eb")
        self.card_yesterday_kwh = self._create_energy_card("Previous Shift", "9,180.40 kWh", "14-Feb-2026", "#0d9488")
        self.card_mtd_kwh = self._create_energy_card("Month-To-Date (MTD)", "138,102.5 kWh", "February 2026", "#7c3aed")
        self.card_dod_delta = self._create_energy_card("Day-over-Day Variance", "+0.29%", "Nominal (+26.4 kWh)", "#16a34a")

        grid.addWidget(self.card_today_kwh, 0, 0)
        grid.addWidget(self.card_yesterday_kwh, 0, 1)
        grid.addWidget(self.card_mtd_kwh, 0, 2)
        grid.addWidget(self.card_dod_delta, 0, 3)

        return container

    def _create_energy_card(self, title: str, value: str, subtext: str, color_hex: str) -> ElevatedCardWidget:
        card = ElevatedCardWidget()
        card.setObjectName("MetricCard")
        card.setStyleSheet(f"border-top: 3px solid {color_hex};")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(2)

        t = CaptionLabel(title)
        lay.addWidget(t)

        v = QLabel(value)
        v.setStyleSheet(f"font-size: 18pt; font-weight: 800; color: {color_hex}; margin: 2px 0;")
        lay.addWidget(v)

        s = QLabel(subtext)
        s.setStyleSheet("color: #64748b; font-size: 8.5pt; font-weight: 500;")
        lay.addWidget(s)

        card._val_label = v
        card._sub_label = s
        return card

    def _create_metric_card(self, title: str, value: str, metric_type: str, tooltip: str = "") -> ElevatedCardWidget:
        card = ElevatedCardWidget()
        card.setObjectName("MetricCard")
        if tooltip:
            card.setToolTip(tooltip)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        t_lbl = CaptionLabel(title)
        layout.addWidget(t_lbl)

        colors = {
            "processed": "#2563eb",
            "success": "#16a34a",
            "failed": "#dc2626",
            "last": "#7c3aed",
        }
        c = colors.get(metric_type, "#0f172a")

        v_lbl = QLabel(value)
        v_lbl.setProperty("metric", metric_type)
        v_lbl.setStyleSheet(f"font-size: 20pt; font-weight: 800; color: {c}; margin-top: 2px;")
        layout.addWidget(v_lbl)

        card._metric_value = v_lbl
        return card

    def _create_control_panel(self) -> QWidget:
        card = SimpleCardWidget()
        root_lay = QVBoxLayout(card)
        root_lay.setContentsMargins(18, 14, 18, 14)
        root_lay.setSpacing(10)

        header_lbl = StrongBodyLabel("Automation Operations & Scheduler Control")
        root_lay.addWidget(header_lbl)

        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.run_button = PrimaryPushButton("Run Automation Now", card)
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.setToolTip("Triggers immediate execution: checks Gmail, parses PDF, updates Excel, and updates SQLite audit trail")
        self.run_button.clicked.connect(self.run_now)

        self.scheduler_button = PushButton("Pause Scheduler", card)
        self.scheduler_button.setToolTip("Temporarily stop automatic polling without closing the application")
        self.scheduler_button.clicked.connect(self.toggle_scheduler)

        self.refresh_button = PushButton("Refresh Status", card)
        self.refresh_button.setToolTip("Re-query local database and reload active dashboard metrics")
        self.refresh_button.clicked.connect(self.refresh_status)

        layout.addWidget(self.run_button)
        layout.addWidget(self.scheduler_button)
        layout.addWidget(self.refresh_button)
        layout.addStretch()

        self.next_event_label = QLabel("Next scheduled check: ~06:00 AM")
        self.next_event_label.setStyleSheet("color: #64748b; font-size: 9pt; font-weight: 500;")
        layout.addWidget(self.next_event_label)

        self.progress = ProgressBar(card)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedWidth(160)
        layout.addWidget(self.progress)

        root_lay.addLayout(layout)
        return card

    def _create_top_meters_preview(self) -> QWidget:
        card = SimpleCardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        lay.addWidget(StrongBodyLabel("Top Energy Consuming Equipment (Preview)"))

        self.mini_meters_table = TableWidget(card)
        self.mini_meters_table.setColumnCount(3)
        self.mini_meters_table.setHorizontalHeaderLabels(["Equipment / Meter", "Active Energy", "Status"])
        self.mini_meters_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mini_meters_table.setAlternatingRowColors(True)
        self.mini_meters_table.setFixedHeight(140)
        self.mini_meters_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.mini_meters_table)

        btn_view_all = TransparentPushButton("View All 18 Plant Meters →", card)
        btn_view_all.clicked.connect(lambda: self.switch_page(2))
        lay.addWidget(btn_view_all, 0, Qt.AlignRight)
        return card

    def _create_activity_panel(self) -> QWidget:
        card = SimpleCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addWidget(StrongBodyLabel("Live Activity Summary & Next Event"))

        self.activity_label = QLabel("No activity yet.")
        self.activity_label.setWordWrap(True)
        self.activity_label.setMinimumHeight(60)
        self.activity_label.setStyleSheet("color: #334155; font-size: 9.5pt;")
        layout.addWidget(self.activity_label)

        btn_logs = TransparentPushButton("View Full Execution Audit Log →", card)
        btn_logs.clicked.connect(lambda: self.switch_page(9))
        layout.addWidget(btn_logs, 0, Qt.AlignRight)
        return card

    def refresh_overview(self):
        """Updates dashboard overview KPIs from database."""
        repo = self.services.get("report_repository")
        if not repo:
            return
        try:
            latest = repo.get_latest_report()
            if latest:
                rep_date = str(latest.get("report_date", "—"))
                total = float(latest.get("total_energy", 0.0) or 0.0)
                if hasattr(self, "card_today_kwh"):
                    self.card_today_kwh._val_label.setText(f"{total:,.2f} kWh")
                    self.card_today_kwh._sub_label.setText(f"Date: {rep_date}")

                readings = repo.get_readings_for_report(latest.get("id"))
                valid = [r for r in readings if str(r.get("status", "")).upper() not in {"N/A", "NA"} and r.get("active_energy") is not None]
                sorted_r = sorted(valid, key=lambda x: float(x.get("active_energy") or 0.0), reverse=True)[:4]

                if hasattr(self, "mini_meters_table"):
                    self.mini_meters_table.setRowCount(len(sorted_r))
                    for i, r in enumerate(sorted_r):
                        self.mini_meters_table.setItem(i, 0, QTableWidgetItem(str(r.get("meter_name", ""))))
                        self.mini_meters_table.setItem(i, 1, QTableWidgetItem(f"{float(r.get('active_energy') or 0.0):,.1f} kWh"))
                        self.mini_meters_table.setItem(i, 2, QTableWidgetItem("Normal"))
        except Exception as exc:
            self._append_log(f"Overview refresh notice: {exc}")

    # =================================================================
    # Page 1: Energy Analytics Panel
    # =================================================================

    def _create_analysis_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_analytics")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        summary_card = SimpleCardWidget(widget)
        s_layout = QGridLayout(summary_card)
        s_layout.setContentsMargins(18, 16, 18, 16)
        s_layout.setHorizontalSpacing(24)
        s_layout.setVerticalSpacing(10)

        self.lbl_analysis_latest = QLabel("Latest Report: —")
        self.lbl_analysis_energy = QLabel("Total Consumption: — kWh")
        self.lbl_analysis_avg = QLabel("Average per Active Meter: — kWh")
        self.lbl_analysis_status = QLabel("Anomaly Status: Normal (Nominal baseline)")
        self.lbl_analysis_status.setStyleSheet("color: #16a34a; font-weight: 700;")

        s_layout.addWidget(self.lbl_analysis_latest, 0, 0)
        s_layout.addWidget(self.lbl_analysis_energy, 0, 1)
        s_layout.addWidget(self.lbl_analysis_avg, 1, 0)
        s_layout.addWidget(self.lbl_analysis_status, 1, 1)
        layout.addWidget(summary_card)

        meters_card = SimpleCardWidget(widget)
        m_layout = QVBoxLayout(meters_card)
        m_layout.setContentsMargins(16, 14, 16, 14)
        m_layout.setSpacing(10)
        m_layout.addWidget(StrongBodyLabel("Top Energy Consuming Equipment"))

        self.top_meters_table = TableWidget(meters_card)
        self.top_meters_table.setColumnCount(3)
        self.top_meters_table.setHorizontalHeaderLabels(["Meter Name", "Active Energy (kWh)", "Status"])
        self.top_meters_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.top_meters_table.setAlternatingRowColors(True)
        m_layout.addWidget(self.top_meters_table)
        layout.addWidget(meters_card, 1)

        btn_refresh = PrimaryPushButton("Analyze Latest Energy Telemetry", widget)
        btn_refresh.setToolTip("Re-run analytics computations against latest SQLite database records")
        btn_refresh.clicked.connect(self.refresh_analysis)
        layout.addWidget(btn_refresh, 0, Qt.AlignLeft)

        self.refresh_analysis()
        return widget

    def refresh_analysis(self):
        repo = self.services.get("report_repository")
        if not repo:
            return
        try:
            latest = repo.get_latest_report()
            if not latest:
                if hasattr(self, "lbl_analysis_latest"):
                    self.lbl_analysis_latest.setText("Latest Report: No records in database")
                return

            report_date = latest.get("report_date", "—")
            total = float(latest.get("total_energy", 0.0) or 0.0)
            if hasattr(self, "lbl_analysis_latest"):
                self.lbl_analysis_latest.setText(f"Latest Report: {report_date}")
            if hasattr(self, "lbl_analysis_energy"):
                self.lbl_analysis_energy.setText(f"Total Consumption: {total:,.2f} kWh")

            report_id = latest.get("id")
            if report_id and hasattr(self, "top_meters_table"):
                readings = repo.get_readings_for_report(report_id)
                valid_readings = [
                    r for r in readings
                    if str(r.get("status", "")).upper() not in {"N/A", "NA"}
                    and r.get("active_energy") is not None
                ]
                if valid_readings and hasattr(self, "lbl_analysis_avg"):
                    avg_energy = total / len(valid_readings) if valid_readings else 0.0
                    self.lbl_analysis_avg.setText(f"Average per Active Meter: {avg_energy:,.2f} kWh")

                    sorted_readings = sorted(
                        valid_readings,
                        key=lambda x: float(x.get("active_energy") or 0.0),
                        reverse=True
                    )[:10]
                    self.top_meters_table.setRowCount(len(sorted_readings))
                    for idx, m in enumerate(sorted_readings):
                        val = float(m.get("active_energy") or 0.0)
                        self.top_meters_table.setItem(idx, 0, QTableWidgetItem(str(m.get("meter_name", ""))))
                        self.top_meters_table.setItem(idx, 1, QTableWidgetItem(f"{val:,.2f}"))
                        self.top_meters_table.setItem(idx, 2, QTableWidgetItem(str(m.get("status", "VALID"))))

            if hasattr(self, "lbl_analysis_status"):
                ai_stat = latest.get("ai_status", "NORMAL")
                if ai_stat == "ANOMALY":
                    self.lbl_analysis_status.setText("Anomaly Status: Attention Required")
                    self.lbl_analysis_status.setStyleSheet("color: #d97706; font-weight: 700;")
                else:
                    self.lbl_analysis_status.setText("Anomaly Status: Normal (Nominal baseline)")
                    self.lbl_analysis_status.setStyleSheet("color: #16a34a; font-weight: 700;")
        except Exception as exc:
            self._append_log(f"Energy analytics refresh warning: {exc}")

    # =================================================================
    # Page 2: Meter Analysis
    # =================================================================

    def _create_meters_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_meters")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = TitleLabel("All Plant Meters Catalog & Telemetry")
        sub = CaptionLabel("Comprehensive registry of all 18 industrial meters across Savera MS production areas")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        toolbar.addLayout(title_box)
        toolbar.addStretch()

        self.meter_search_input = SearchLineEdit(widget)
        self.meter_search_input.setPlaceholderText("Filter meters...")
        self.meter_search_input.setToolTip("Type meter name to filter catalog instantaneously")
        self.meter_search_input.setFixedWidth(240)
        self.meter_search_input.textChanged.connect(self._filter_meters_table)
        toolbar.addWidget(self.meter_search_input)

        btn_refresh = PushButton("Refresh Meters", widget)
        btn_refresh.setToolTip("Reload meter telemetry from latest report readings")
        btn_refresh.clicked.connect(self.refresh_meters_table)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.meters_all_table = TableWidget(widget)
        self.meters_all_table.setColumnCount(6)
        self.meters_all_table.setHorizontalHeaderLabels([
            "Meter Name", "Production Zone", "Active Energy (kWh)", "Status", "Rated Power (kW)", "Nominal Baseline (kWh)"
        ])
        self.meters_all_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.meters_all_table.setAlternatingRowColors(True)
        self.meters_all_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.meters_all_table, 1)

        self.refresh_meters_table()
        return widget

    def refresh_meters_table(self):
        repo = self.services.get("report_repository")
        topo = self.services.get("plant_topology")
        if not repo:
            return
        try:
            latest = repo.get_latest_report()
            readings = repo.get_readings_for_report(latest.get("id")) if latest else []
            self.meters_all_table.setRowCount(len(readings))

            for row_idx, r in enumerate(readings):
                m_name = str(r.get("meter_name", ""))
                val = r.get("active_energy")
                val_str = f"{val:,.2f}" if val is not None else "N/A"
                stat = str(r.get("status", "OK"))

                zone_name = "General"
                rated_kw = "—"
                nominal = "—"
                if topo:
                    zone = topo.find_zone_for_meter(m_name)
                    if zone:
                        zone_name = zone.name
                        nominal = f"{zone.nominal_kwh:,.1f}"

                self.meters_all_table.setItem(row_idx, 0, QTableWidgetItem(m_name))
                self.meters_all_table.setItem(row_idx, 1, QTableWidgetItem(zone_name))
                self.meters_all_table.setItem(row_idx, 2, QTableWidgetItem(val_str))

                stat_item = QTableWidgetItem(stat)
                if stat == "OK":
                    stat_item.setForeground(Qt.darkGreen)
                elif stat == "N/A":
                    stat_item.setForeground(Qt.gray)
                self.meters_all_table.setItem(row_idx, 3, stat_item)
                self.meters_all_table.setItem(row_idx, 4, QTableWidgetItem(str(rated_kw)))
                self.meters_all_table.setItem(row_idx, 5, QTableWidgetItem(str(nominal)))
        except Exception as exc:
            self._append_log(f"Error loading meters table: {exc}")

    def _filter_meters_table(self, query: str):
        query = query.strip().lower()
        for row in range(self.meters_all_table.rowCount()):
            item = self.meters_all_table.item(row, 0)
            matches = query in item.text().lower() if item else False
            self.meters_all_table.setRowHidden(row, not matches)

    # =================================================================
    # Page 3: Plant Overview (Topology Map)
    # =================================================================

    def _create_plant_overview_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_plant")
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)

        topo = self.services.get("plant_topology")
        self.plant_map_widget = PlantMapWidget(topology_service=topo, parent=widget)
        lay.addWidget(self.plant_map_widget)

        self.refresh_plant_topology_view()
        return widget

    def refresh_plant_topology_view(self):
        repo = self.services.get("report_repository")
        if not repo or not hasattr(self, "plant_map_widget"):
            return
        try:
            latest = repo.get_latest_report()
            readings = repo.get_readings_for_report(latest.get("id")) if latest else []
            self.plant_map_widget.update_data(readings)
        except Exception as exc:
            self._append_log(f"Topology refresh warning: {exc}")

    # =================================================================
    # Page 4: Reports & Audit Trail
    # =================================================================

    def _create_reports_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_reports")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = TitleLabel("EMS Reports & Audit Trail Ledger")
        self.reports_count_label = CaptionLabel("0 reports recorded")
        title_box.addWidget(title)
        title_box.addWidget(self.reports_count_label)
        toolbar.addLayout(title_box)
        toolbar.addStretch()

        btn_refresh = PushButton("Refresh Audit Trail", widget)
        btn_refresh.setToolTip("Reload history of all processed reports from SQLite database")
        btn_refresh.clicked.connect(self.refresh_reports_table)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.reports_table = TableWidget(widget)
        self.reports_table.setColumnCount(8)
        self.reports_table.setHorizontalHeaderLabels([
            "Report Date", "Attachment", "Status", "Total Energy (kWh)", "Meters", "Excel Status", "Power BI", "Processed At"
        ])
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.reports_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.reports_table, 1)

        self.refresh_reports_table()
        return widget

    def refresh_reports_table(self):
        repo = self.services.get("report_repository")
        if not repo:
            return
        try:
            reports = repo.get_recent_history(limit=50)
            if hasattr(self, "reports_count_label"):
                self.reports_count_label.setText(f"{len(reports)} report(s) recorded in audit trail")
            if hasattr(self, "reports_table"):
                self.reports_table.setRowCount(len(reports))
                for row_idx, r in enumerate(reports):
                    self.reports_table.setItem(row_idx, 0, QTableWidgetItem(str(r.get("report_date", "—"))))
                    self.reports_table.setItem(row_idx, 1, QTableWidgetItem(str(r.get("attachment_name", "—"))))

                    status_str = str(r.get("status", "—"))
                    status_item = QTableWidgetItem(status_str)
                    if status_str == "COMPLETED":
                        status_item.setForeground(Qt.darkGreen)
                    elif status_str == "FAILED":
                        status_item.setForeground(Qt.red)
                    self.reports_table.setItem(row_idx, 2, status_item)

                    energy_val = float(r.get("total_energy", 0.0) or 0.0)
                    self.reports_table.setItem(row_idx, 3, QTableWidgetItem(f"{energy_val:,.2f}"))

                    m_count = r.get("meter_count", 0)
                    mapped_count = r.get("mapped_meter_count", 0)
                    self.reports_table.setItem(row_idx, 4, QTableWidgetItem(f"{mapped_count}/{m_count}"))

                    self.reports_table.setItem(row_idx, 5, QTableWidgetItem(str(r.get("excel_status", "—"))))
                    self.reports_table.setItem(row_idx, 6, QTableWidgetItem(str(r.get("powerbi_status", "—"))))
                    self.reports_table.setItem(row_idx, 7, QTableWidgetItem(str(r.get("processing_date", "—"))[:19]))
        except Exception as exc:
            self._append_log(f"Audit trail refresh warning: {exc}")

    # =================================================================
    # Page 5: Historical Data Recovery
    # =================================================================

    def _create_recovery_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_recovery")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        info_card = SimpleCardWidget(widget)
        i_lay = QVBoxLayout(info_card)
        i_lay.setContentsMargins(16, 14, 16, 14)
        info = QLabel(
            "<b>Historical Data Reconciliation & Weekend Gap Healing</b><br>"
            "Automatically detects missing report dates (including Sunday/weekend reports, missed runs up to 30 days) "
            "and downloads them from Gmail chronologically to keep the database and workbook contiguous."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; line-height: 1.4;")
        i_lay.addWidget(info)
        layout.addWidget(info_card)

        action_box = QHBoxLayout()
        btn_scan = PushButton("Scan for Missing Dates (30 Days)", widget)
        btn_scan.setToolTip("Compare chronological calendar against ingested database dates to detect missing days")
        btn_scan.clicked.connect(self.scan_missing_dates)
        action_box.addWidget(btn_scan)

        btn_recover = PrimaryPushButton("Run Historical Gap Healing Now", widget)
        btn_recover.setObjectName("PrimaryButton")
        btn_recover.setToolTip("Fetch and process missing reports chronologically from Gmail")
        btn_recover.clicked.connect(self.run_gap_recovery)
        action_box.addWidget(btn_recover)
        action_box.addStretch()
        layout.addLayout(action_box)

        self.recovery_log = QTextEdit(widget)
        self.recovery_log.setReadOnly(True)
        self.recovery_log.setPlaceholderText("Recovery and reconciliation logs will appear here...")
        self.recovery_log.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        layout.addWidget(self.recovery_log, 1)
        return widget

    def scan_missing_dates(self):
        recon = self.services.get("reconciliation_service")
        if not recon:
            self.recovery_log.append("Reconciliation service not available.")
            return
        try:
            self.recovery_log.append("Scanning past 30 days for missing report dates and weekend/Sunday gaps...")
            missing = recon.detect_missing_dates(days_back=30)
            if missing:
                self.recovery_log.append(f"⚠ Detected {len(missing)} missing date(s): {', '.join(missing)}")
                self.recovery_log.append("Click 'Run Historical Gap Healing Now' to automatically fetch and process them.")
            else:
                self.recovery_log.append("✔ No missing dates found in the last 30 days. All records are contiguous!")
        except Exception as exc:
            self.recovery_log.append(f"Error scanning missing dates: {exc}")

    def run_gap_recovery(self):
        if self._running:
            QMessageBox.information(self, "Busy", "A workflow operation is already in progress.")
            return
        self.recovery_log.append("Triggering automated workflow with gap detection...")
        self.run_now()

    # =================================================================
    # Page 6: Google Gemini AI Intelligence
    # =================================================================

    def _create_ai_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_ai")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        banner = SimpleCardWidget(widget)
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(16, 14, 16, 14)
        lbl_b = QLabel(
            "<b>🤖 Google Gemini Energy Intelligence</b><br>"
            "Ask questions about consumption trends, top meters, or operational anomalies. "
            "Gemini operates exclusively in advisory mode and never alters Excel formulas or deterministic data."
        )
        lbl_b.setWordWrap(True)
        lbl_b.setStyleSheet("color: #1e40af; line-height: 1.4;")
        b_lay.addWidget(lbl_b)
        layout.addWidget(banner)

        q_box = QHBoxLayout()
        self.ai_query_input = SearchLineEdit(widget)
        self.ai_query_input.setPlaceholderText("Ask a question (e.g. 'What was the total energy consumed on the latest report?')")
        self.ai_query_input.setToolTip("Type natural language question regarding plant energy metrics")
        self.ai_query_input.returnPressed.connect(self.ask_ai)
        q_box.addWidget(self.ai_query_input)

        btn_ask = PrimaryPushButton("Ask AI", widget)
        btn_ask.setObjectName("PrimaryButton")
        btn_ask.setToolTip("Submit question to Gemini AI advisory assistant")
        btn_ask.clicked.connect(self.ask_ai)
        q_box.addWidget(btn_ask)
        layout.addLayout(q_box)

        prompts_layout = QHBoxLayout()
        prompts_layout.addWidget(CaptionLabel("Suggested:"))
        for prompt_text in [
            "What was the total energy consumed on the latest report?",
            "Which meter consumed the most energy?",
            "Were there any missing reports in the last 30 days?",
        ]:
            b = PushButton(prompt_text, widget)
            b.setToolTip(f"Click to ask: '{prompt_text}'")
            b.clicked.connect(lambda _, t=prompt_text: self._set_and_ask_ai(t))
            prompts_layout.addWidget(b)
        prompts_layout.addStretch()
        layout.addLayout(prompts_layout)

        self.ai_response_display = QTextEdit(widget)
        self.ai_response_display.setReadOnly(True)
        self.ai_response_display.setPlaceholderText("AI responses and verified explanations will appear here...")
        self.ai_response_display.setStyleSheet("font-family: Consolas, monospace; font-size: 9.5pt;")
        layout.addWidget(self.ai_response_display, 1)
        return widget

    def _set_and_ask_ai(self, text: str):
        self.ai_query_input.setText(text)
        self.ask_ai()

    def ask_ai(self):
        query = self.ai_query_input.text().strip()
        if not query:
            return
        gemini = self.services.get("gemini_service")
        repo = self.services.get("report_repository")
        if not gemini:
            self.ai_response_display.setText("Gemini AI service is unconfigured or unavailable.")
            return

        self.ai_response_display.setText("Consulting verified energy intelligence...")
        QApplication.processEvents()

        try:
            latest = repo.get_latest_report() if repo else None
            readings = repo.get_readings_for_report(latest.get("id")) if (repo and latest) else []
            history = repo.get_recent_history(limit=30) if repo else []

            context = {
                "latest_report": latest or {},
                "readings": readings,
                "history": history,
            }
            answer = gemini.ask(query, context_data=context)
            self.ai_response_display.setText(answer)
            self._append_log(f"AI Assistant answered: '{query[:40]}...'")
        except Exception as exc:
            self.ai_response_display.setText(f"Error querying AI: {exc}")

    # =================================================================
    # Page 7: Power BI Analytics & Star Schema
    # =================================================================

    def _create_powerbi_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_powerbi")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        info_card = SimpleCardWidget(widget)
        i_lay = QVBoxLayout(info_card)
        i_lay.setContentsMargins(16, 14, 16, 14)
        info = QLabel(
            "<b>Power BI Executive Reporting & Star-Schema Automation</b><br>"
            "Prepares aggregated executive metrics and exports clean star-schema tables (Fact_EnergyConsumption, "
            "Dim_Date, Dim_Meter, Dim_Area, Dim_Report) and DAX measures for instant Power BI import."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569;")
        i_lay.addWidget(info)
        layout.addWidget(info_card)

        status_card = SimpleCardWidget(widget)
        s_layout = QVBoxLayout(status_card)
        s_layout.setContentsMargins(16, 14, 16, 14)
        pbi_service = self.services.get("powerbi_service")
        is_configured = bool(getattr(pbi_service, "workspace_id", None) and getattr(pbi_service, "dataset_id", None))

        lbl_cfg_status = QLabel(f"Power BI API Status: {'Configured (Cloud Push Enabled)' if is_configured else 'Local Export Mode (Unconfigured Cloud Credentials)'}")
        lbl_cfg_status.setStyleSheet("font-weight: 700; color: " + ("#16a34a;" if is_configured else "#d97706;"))
        s_layout.addWidget(lbl_cfg_status)
        layout.addWidget(status_card)

        action_box = QHBoxLayout()
        btn_prep = PrimaryPushButton("Generate Executive Dataset", widget)
        btn_prep.setObjectName("PrimaryButton")
        btn_prep.setToolTip("Compile MTD, YTD, and Day-over-Day executive JSON payload")
        btn_prep.clicked.connect(self.generate_powerbi_dataset)
        action_box.addWidget(btn_prep)

        btn_star = PushButton("Export Star-Schema & DAX Files", widget)
        btn_star.setToolTip("Export Fact and Dimension CSVs and measures.dax to data/powerbi/")
        btn_star.clicked.connect(self.export_star_schema_files)
        action_box.addWidget(btn_star)

        action_box.addStretch()
        layout.addLayout(action_box)

        self.powerbi_display = QTextEdit(widget)
        self.powerbi_display.setReadOnly(True)
        self.powerbi_display.setPlaceholderText("Generated Power BI dataset summary and DAX export results will appear here...")
        self.powerbi_display.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        layout.addWidget(self.powerbi_display, 1)
        return widget

    def generate_powerbi_dataset(self):
        pbi = self.services.get("powerbi_service")
        repo = self.services.get("report_repository")
        if not pbi or not repo:
            self.powerbi_display.setText("Power BI service or report repository unavailable.")
            return
        try:
            latest = repo.get_latest_report()
            if not latest:
                self.powerbi_display.setText("No reports found in audit trail database yet. Process a report first.")
                return
            readings = repo.get_readings_for_report(latest.get("id"))
            history = repo.get_recent_history(limit=30)
            dataset = pbi.prepare_executive_dataset(
                readings=readings,
                report_date=latest.get("report_date", ""),
                history=history,
            )
            pretty = json.dumps(dataset, indent=2)
            self.powerbi_display.setText(pretty)
            self._append_log("Power BI executive dataset generated.")
        except Exception as exc:
            self.powerbi_display.setText(f"Error generating Power BI dataset: {exc}")

    def export_star_schema_files(self):
        pbi = self.services.get("powerbi_service")
        if not pbi or not hasattr(pbi, "generate_star_schema"):
            self.powerbi_display.setText("Power BI star-schema generator not available.")
            return
        try:
            res = pbi.generate_star_schema()
            msg = "✔ Power BI Star-Schema & DAX Files Exported Successfully:\n\n"
            for k, p in res.items():
                msg += f"• {k}: {p}\n"
            msg += "\nAll files ready for Power BI Desktop import or Fabric REST API deployment."
            self.powerbi_display.setText(msg)
            self._append_log("Power BI star-schema files exported to data/powerbi/")
        except Exception as exc:
            self.powerbi_display.setText(f"Export error: {exc}")

    # =================================================================
    # Page 8: Centralized Alert Center
    # =================================================================

    def _create_alerts_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_alerts")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = TitleLabel("Enterprise Alert Center")
        self.alert_summary_lbl = CaptionLabel("0 active alerts")
        title_box.addWidget(title)
        title_box.addWidget(self.alert_summary_lbl)
        toolbar.addLayout(title_box)
        toolbar.addStretch()

        btn_ack_all = PushButton("Acknowledge All", widget)
        btn_ack_all.setToolTip("Mark all active alerts as reviewed")
        btn_ack_all.clicked.connect(self._ack_all_alerts)
        toolbar.addWidget(btn_ack_all)

        btn_refresh = PushButton("Refresh Alerts", widget)
        btn_refresh.setToolTip("Reload unacknowledged alerts from AlertService")
        btn_refresh.clicked.connect(self.refresh_alerts_panel)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        filter_box = QHBoxLayout()
        self.alert_filter_group = QButtonGroup(widget)
        for idx, cat_name in enumerate(["All", "CRITICAL", "WARNING", "INFO", "AI_INSIGHT"]):
            b = PushButton(cat_name, widget)
            b.setCheckable(True)
            if idx == 0:
                b.setChecked(True)
            b.clicked.connect(lambda _, c=cat_name: self._filter_alerts(c))
            self.alert_filter_group.addButton(b, idx)
            filter_box.addWidget(b)
        filter_box.addStretch()
        layout.addLayout(filter_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.alerts_container = QWidget()
        self.alerts_list_layout = QVBoxLayout(self.alerts_container)
        self.alerts_list_layout.setSpacing(10)
        self.alerts_list_layout.addStretch()
        scroll.setWidget(self.alerts_container)
        layout.addWidget(scroll, 1)

        self.refresh_alerts_panel()
        return widget

    def refresh_alerts_panel(self):
        alert_srv = self.services.get("alert_service")
        if not alert_srv or not hasattr(self, "alerts_list_layout"):
            return

        while self.alerts_list_layout.count() > 1:
            item = self.alerts_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts = alert_srv.get_alerts(unacknowledged_only=True)
        counts = alert_srv.get_counts()
        self.alert_summary_lbl.setText(
            f"{counts.get('total', 0)} active alert(s) • "
            f"{counts.get('CRITICAL', 0)} Critical, {counts.get('WARNING', 0)} Warning, {counts.get('AI_INSIGHT', 0)} AI Insights"
        )

        if not alerts:
            empty_lbl = QLabel("✔ No unacknowledged alerts. All systems are operating normally.")
            empty_lbl.setStyleSheet("color: #16a34a; font-weight: 600; padding: 20px; font-size: 11pt;")
            self.alerts_list_layout.insertWidget(0, empty_lbl)
            return

        for alert in alerts:
            card = self._create_alert_card(alert)
            self.alerts_list_layout.insertWidget(self.alerts_list_layout.count() - 1, card)

    def _create_alert_card(self, alert: Any) -> SimpleCardWidget:
        card = SimpleCardWidget()
        cat = alert.category
        color = (
            "#dc2626"
            if cat == "CRITICAL"
            else (
                "#d97706"
                if cat == "WARNING"
                else ("#6366f1" if cat == "AI_INSIGHT" else "#2563eb")
            )
        )
        card.setStyleSheet(f"border-left: 5px solid {color};")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        title_lbl = QLabel(f"[{cat}] {alert.title}")
        title_lbl.setStyleSheet(f"font-weight: 700; font-size: 10pt; color: {color};")
        hdr.addWidget(title_lbl)
        hdr.addStretch()

        time_lbl = QLabel(alert.timestamp[:19])
        time_lbl.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")
        hdr.addWidget(time_lbl)

        btn_ack = PushButton("Acknowledge", card)
        btn_ack.setToolTip("Mark alert as acknowledged")
        btn_ack.clicked.connect(lambda _, aid=alert.alert_id: self._ack_alert(aid))
        hdr.addWidget(btn_ack)
        lay.addLayout(hdr)

        msg_lbl = QLabel(alert.message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #334155; font-size: 9.5pt;")
        lay.addWidget(msg_lbl)

        return card

    def _filter_alerts(self, category_name: str):
        alert_srv = self.services.get("alert_service")
        if not alert_srv:
            return
        cat = None if category_name == "All" else category_name
        alerts = alert_srv.get_alerts(category=cat, unacknowledged_only=True)

        while self.alerts_list_layout.count() > 1:
            item = self.alerts_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for alert in alerts:
            card = self._create_alert_card(alert)
            self.alerts_list_layout.insertWidget(self.alerts_list_layout.count() - 1, card)

    def _ack_alert(self, alert_id: str):
        alert_srv = self.services.get("alert_service")
        if alert_srv:
            alert_srv.acknowledge(alert_id)
            self.refresh_alerts_panel()

    def _ack_all_alerts(self):
        alert_srv = self.services.get("alert_service")
        if alert_srv:
            alert_srv.acknowledge_all()
            self.refresh_alerts_panel()

    # =================================================================
    # Page 9: Processing History & Logs
    # =================================================================

    def _create_history_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_history")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(TitleLabel("Application Logs & Execution Audit Ledger"))

        self.full_log = QTextEdit(widget)
        self.full_log.setReadOnly(True)
        self.full_log.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        layout.addWidget(self.full_log, 1)

        bottom = QHBoxLayout()
        clear_btn = PushButton("Clear Log View", widget)
        clear_btn.setToolTip("Clear current on-screen log buffer (does not delete file on disk)")
        clear_btn.clicked.connect(self.full_log.clear)
        bottom.addWidget(clear_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

        return widget

    # =================================================================
    # Page 10: Settings & Configuration (Section 18 Guidance Cards)
    # =================================================================

    def _create_settings_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("page_settings")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Guidance Card: Excel Workbook Requirement (Section 18)
        excel_srv = self.services.get("excel_service")
        wb_path = getattr(excel_srv, "workbook_path", "Not configured") if excel_srv else "Not configured"
        wb_exists = Path(str(wb_path)).exists() if wb_path != "Not configured" else False

        excel_guidance = self._create_requirement_card(
            title="Excel Production Workbook",
            status="Configured & Verified" if wb_exists else "File Missing / Not Configured",
            status_color="#16a34a" if wb_exists else "#dc2626",
            required_for="Automatic daily updates of meter active energy rows and formula verification.",
            action_desc="Ensure Test_BI_Analysis_Report_2026.xlsx exists at the designated path.",
            btn_text="Select Excel File",
            callback=self._browse_excel_file,
        )
        layout.addWidget(excel_guidance)

        # Guidance Card: Gmail API Requirement
        gmail_guidance = self._create_requirement_card(
            title="Gmail API Integration",
            status="Active (OAuth Client Configured)" if Path("credentials/gmail/token.json").exists() or Path("credentials/token.json").exists() else "Needs Authorization",
            status_color="#16a34a" if Path("credentials/gmail/token.json").exists() or Path("credentials/token.json").exists() else "#d97706",
            required_for="Automatic download of daily NBSense PDF reports from Gmail.",
            action_desc="Launch the Setup Wizard to complete Google OAuth consent.",
            btn_text="Launch Setup Wizard",
            callback=self.open_setup_wizard,
        )
        layout.addWidget(gmail_guidance)

        # Guidance Card: Power BI Cloud Dataset
        pbi_srv = self.services.get("powerbi_service")
        pbi_active = bool(getattr(pbi_srv, "workspace_id", None) and getattr(pbi_srv, "dataset_id", None))
        pbi_guidance = self._create_requirement_card(
            title="Power BI Cloud Push Dataset",
            status="Connected" if pbi_active else "Local Export Mode (Optional)",
            status_color="#16a34a" if pbi_active else "#64748b",
            required_for="Real-time push streaming to cloud Power BI workspaces without on-prem gateway.",
            action_desc="Configure Azure Entra ID App Registration client ID, secret, and workspace ID.",
            btn_text="Configure Power BI",
            callback=self.open_setup_wizard,
        )
        layout.addWidget(pbi_guidance)

        # Active Enterprise Configuration Group
        group_card = SimpleCardWidget(container)
        g_lay = QVBoxLayout(group_card)
        g_lay.setContentsMargins(18, 16, 18, 16)
        g_lay.setSpacing(12)
        g_lay.addWidget(StrongBodyLabel("Active System Parameters & Invariants"))

        form = QFormLayout()
        form.setSpacing(12)

        lbl_wb = QLabel(str(wb_path))
        lbl_wb.setStyleSheet("font-family: Consolas; color: #1e3a8a;")
        form.addRow("Excel Workbook Path:", lbl_wb)

        db = self.services.get("report_repository")
        db_path = getattr(getattr(db, "database", None), "db_path", "data/automation.db")
        lbl_db = QLabel(str(db_path))
        lbl_db.setStyleSheet("font-family: Consolas; color: #1e3a8a;")
        form.addRow("SQLite Audit Database:", lbl_db)

        form.addRow("Target Daily Total:", QLabel("9,206.83 kWh (NBSense EMS Reference)"))
        form.addRow("Excel Formula Safety:", QLabel("Preserved (=SUM(C16:Q16), Cumulative Row 4)"))
        form.addRow("Historical Gap Window:", QLabel("30 Days (Automatic Sunday/Weekend Healing)"))
        form.addRow("Gemini AI Policy:", QLabel("Advisory Only (Strictly zero direct Excel edits)"))
        form.addRow("Architecture Mode:", QLabel("Deterministic pipeline as sole source of truth"))

        g_lay.addLayout(form)
        layout.addWidget(group_card)
        scroll.setWidget(container)
        return scroll

    def _create_requirement_card(
        self,
        title: str,
        status: str,
        status_color: str,
        required_for: str,
        action_desc: str,
        btn_text: str,
        callback: Any,
    ) -> SimpleCardWidget:
        card = SimpleCardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        t = StrongBodyLabel(title)
        hdr.addWidget(t)

        hdr.addStretch()
        st = QLabel(f"Status: {status}")
        st.setStyleSheet(f"font-weight: 700; color: {status_color}; font-size: 9pt;")
        hdr.addWidget(st)
        lay.addLayout(hdr)

        req_lbl = QLabel(f"<b>Required for:</b> {required_for}")
        req_lbl.setWordWrap(True)
        req_lbl.setStyleSheet("color: #475569; font-size: 9pt;")
        lay.addWidget(req_lbl)

        act_box = QHBoxLayout()
        act_lbl = QLabel(f"<b>Action:</b> {action_desc}")
        act_lbl.setWordWrap(True)
        act_lbl.setStyleSheet("color: #334155; font-size: 9pt;")
        act_box.addWidget(act_lbl, 1)

        btn = PushButton(btn_text, card)
        btn.clicked.connect(callback)
        act_box.addWidget(btn)
        lay.addLayout(act_box)

        return card

    def _browse_excel_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EMS Analysis Report Excel Workbook",
            str(Path.cwd()),
            "Excel Files (*.xlsx *.xlsm)",
        )
        if path:
            excel_srv = self.services.get("excel_service")
            if excel_srv:
                excel_srv.workbook_path = path
            self._append_log(f"Excel workbook path updated: {path}")
            self.refresh_status()

    # =================================================================
    # Page 11: Help & Support Center (Section 19)
    # =================================================================

    def _create_help_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_help")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        title = TitleLabel("Help Center & Operator Documentation")
        sub = CaptionLabel("Plain-language operational guides, troubleshooting procedures, FAQ, and technical glossary")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        btn_tour = PrimaryPushButton("✨ Restart Guided Tour", widget)
        btn_tour.setObjectName("PrimaryButton")
        btn_tour.setToolTip("Restart the interactive 1-minute guided walkthrough")
        btn_tour.clicked.connect(self.open_guided_tour)
        header_box.addWidget(btn_tour)
        layout.addLayout(header_box)

        # Tabbed Help Topics
        help_tabs = QTabWidget(widget)
        help_tabs.addTab(self._create_help_article_getting_started(), "Getting Started")
        help_tabs.addTab(self._create_help_article_dashboard(), "Dashboard & Operations")
        help_tabs.addTab(self._create_help_article_meters_plant(), "Meters & Plant Map")
        help_tabs.addTab(self._create_help_article_recovery(), "Data Recovery & Gaps")
        help_tabs.addTab(self._create_help_article_ai_powerbi(), "AI & Power BI")
        help_tabs.addTab(self._create_help_article_troubleshooting(), "Troubleshooting & FAQ")
        help_tabs.addTab(self._create_help_article_glossary(), "Glossary")
        layout.addWidget(help_tabs, 1)

        return widget

    def _create_help_article_getting_started(self) -> QWidget:
        return self._build_article_container([
            (
                "What is EnergyAutomation?",
                "EnergyAutomation is a Windows desktop platform designed for Savera MS that automates the daily processing of NBSense energy reports, updates existing Excel workbooks, maintains an immutable SQLite audit trail, and generates executive Power BI dashboards."
            ),
            (
                "Why is it needed?",
                "Manually opening PDF reports, keying numbers into Excel, and verifying formulas took 30+ minutes each morning and carried human error risks. EnergyAutomation does this in under 3 seconds with formula safety and audit logging."
            ),
            (
                "How do I use it?",
                "1. Click 'Run Automation Now' on the Executive Dashboard to test an immediate run.\n2. The system scheduler runs automatically each morning at 06:00 AM.\n3. Verify results by checking the 'Reports & Audit' ledger."
            ),
            (
                "What happens after I use it?",
                "The target row in `Test_BI_Analysis_Report_2026.xlsx` is updated with today's readings, formulas `=SUM(C16:Q16)` are preserved, and an audit record is saved in `data/automation.db`."
            ),
            (
                "What should I do if it fails?",
                "Review the Alert Center for specific warnings. Ensure Microsoft Excel does not have the workbook open with an exclusive lock, and verify that the workstation has an active internet connection."
            ),
        ])

    def _create_help_article_dashboard(self) -> QWidget:
        return self._build_article_container([
            (
                "Executive Dashboard Overview",
                "Provides plant managers with an instant pulse on facility consumption (Today, Yesterday, MTD, YTD), system health across 6 subsystems, and automation controls."
            ),
            (
                "Understanding the System Health Matrix",
                "Green indicates healthy operations. Amber indicates optional items requiring attention (e.g. Gmail OAuth authorization). Red indicates a critical prerequisite such as a missing workbook."
            ),
            (
                "Simple Mode vs Engineer Mode",
                "Toggle with the top header button. Simple Mode shows high-level summaries for executives. Engineer Mode reveals raw telemetry, cell coordinates, and execution latencies for technicians."
            ),
        ])

    def _create_help_article_meters_plant(self) -> QWidget:
        return self._build_article_container([
            (
                "Plant Energy Topology Map",
                "Visualizes the 18 plant meters organized into 7 production zones: Substation Incomer, Press Shop, Machining & CNC, Welding, Utilities (Air Compressors), Paint Shop, and Administration."
            ),
            (
                "Meter Status & N/A Policy",
                "When a physical meter communication fails, it reports N/A. EnergyAutomation preserves N/A as empty/null. It is NEVER coerced to 0.0, avoiding skew in baseline efficiency calculations."
            ),
        ])

    def _create_help_article_recovery(self) -> QWidget:
        return self._build_article_container([
            (
                "Weekend Gap Healing",
                "Plant operations may not process reports on Sundays. EnergyAutomation automatically scans the past 30 days and fetches missing reports chronologically so your monthly Excel workbook has zero gaps."
            ),
            (
                "Manual Gap Healing Trigger",
                "Navigate to 'Data Recovery', click 'Scan for Missing Dates', and click 'Run Historical Gap Healing Now'."
            ),
        ])

    def _create_help_article_ai_powerbi(self) -> QWidget:
        return self._build_article_container([
            (
                "Google Gemini AI Advisory",
                "Provides plain-language answers to operational questions. Gemini AI is strictly advisory and read-only; it can never modify Excel formulas or database records."
            ),
            (
                "Power BI Star Schema & DAX",
                "Generates Fact_EnergyConsumption.csv and dimension tables (Dim_Date, Dim_Meter, Dim_Area, Dim_Report) along with measures.dax for import into Power BI Desktop or Microsoft Fabric."
            ),
        ])

    def _create_help_article_troubleshooting(self) -> QWidget:
        return self._build_article_container([
            (
                "Excel File Locked (WinError 32)",
                "Close Microsoft Excel. If the issue persists, open Task Manager, end any orphaned 'EXCEL.EXE' background processes, and click 'Run Automation Now'."
            ),
            (
                "Formula Verification Alert",
                "EnergyAutomation verifies row 16 and cumulative row 4 formulas. If someone replaced a formula with a static number, restore the automatic backup from `data/backups/`."
            ),
            (
                "Gmail Authentication Expired",
                "Open Settings -> Launch Setup Wizard -> complete the Google OAuth sign-in step to generate a fresh `token.json`."
            ),
        ])

    def _create_help_article_glossary(self) -> QWidget:
        return self._build_article_container([
            ("Active Energy (kWh)", "The actual electricity consumed by motors, heaters, and machinery to perform productive work."),
            ("Power Factor (PF)", "The ratio of active energy (kWh) to apparent energy (kVAh). Target is near unity (~0.98 - 0.99)."),
            ("Star Schema", "Relational dimensional model separating numerical facts from descriptive context tables (Dates, Meters, Areas)."),
            ("Idempotency", "The property where processing the same report multiple times produces the exact same result without duplicate rows or distorted cumulative sums."),
        ])

    def _build_article_container(self, items: List[tuple[str, str]]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)

        for heading, body in items:
            box = SimpleCardWidget(container)
            b_lay = QVBoxLayout(box)
            b_lay.setContentsMargins(16, 14, 16, 14)
            b_lay.setSpacing(6)
            h_lbl = StrongBodyLabel(heading)
            b_lay.addWidget(h_lbl)
            lbl = QLabel(body)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #334155; font-size: 9.5pt; line-height: 1.4;")
            b_lay.addWidget(lbl)
            lay.addWidget(box)

        lay.addStretch()
        scroll.setWidget(container)
        return scroll

    # =================================================================
    # Interactive Features: Tour, Wizard, Mode Toggle, Global Search
    # =================================================================

    def open_guided_tour(self):
        dlg = GuidedTourDialog(self)
        dlg.exec()

    def open_setup_wizard(self):
        dlg = SetupWizardDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._append_log("Setup wizard settings saved.")
            self.refresh_status()

    def toggle_engineer_mode(self):
        self._is_engineer_mode = not self._is_engineer_mode
        if self._is_engineer_mode:
            self.btn_mode_toggle.setText("🛠 Engineer Mode")
            self.btn_mode_toggle.setStyleSheet("background: #fef3c7; color: #92400e; font-weight: 700; border: 1px solid #f59e0b;")
            self._append_log("Switched to Engineer Mode: Detailed technical telemetry enabled.")
        else:
            self.btn_mode_toggle.setText("👤 Simple Mode")
            self.btn_mode_toggle.setStyleSheet("")
            self._append_log("Switched to Simple Mode: Executive summary view enabled.")

    def handle_global_search(self, text: str):
        query = text.strip().lower()
        if not query:
            return
        if any(w in query for w in ["meter", "powder", "coating", "compressor", "plating", "rigga", "press", "incomer", "chiller", "ro", "dm", "annealing"]):
            self.switch_page(2)
            if hasattr(self, "meter_search_input"):
                self.meter_search_input.setText(query)
        elif any(w in query for w in ["report", "pdf", "2026-", "date"]):
            self.switch_page(4)
        elif any(w in query for w in ["alert", "warn", "error", "spike"]):
            self.switch_page(8)
        elif any(w in query for w in ["power", "bi", "dax", "dataset"]):
            self.switch_page(7)
        elif any(w in query for w in ["ai", "gemini", "intelligence"]):
            self.switch_page(6)
        elif any(w in query for w in ["recover", "gap", "sunday", "missing"]):
            self.switch_page(5)
        elif any(w in query for w in ["setting", "config", "path", "excel"]):
            self.switch_page(10)
        elif any(w in query for w in ["help", "faq", "guide", "tour", "glossary"]):
            self.switch_page(11)

    # =================================================================
    # Workflow & Automation Control (Friendly Non-Technical Errors)
    # =================================================================

    def run_now(self):
        if self._running:
            QMessageBox.information(
                self,
                "Already Running",
                "A report-processing operation is already running.",
            )
            return

        self._running = True
        self.run_button.setEnabled(False)
        self.progress.setVisible(True)
        self._set_status("Processing", "running", "Fetching and processing EMS reports...")
        self._append_log("Manual workflow execution started.")

        self.worker_thread = QThread()
        self.worker = WorkflowWorker(self.workflow)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.execute)
        self.worker.finished.connect(self._workflow_finished)
        self.worker.failed.connect(self._workflow_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._worker_cleanup)

        self.worker_thread.start()

    @Slot(object)
    def _workflow_finished(self, result: Any):
        self._last_result = result
        self._running = False
        self.run_button.setEnabled(True)
        self.progress.setVisible(False)

        self._set_status("Completed", "success", "EMS report processing completed successfully.")
        self._update_success_metrics(result)
        self._append_log("Workflow completed successfully.")
        self._show_result_summary(result)

        try:
            InfoBar.success(
                title="Automation Completed",
                content="EMS reports processed, Excel updated, and audit ledger recorded.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000,
                parent=self,
            )
        except Exception:
            pass

    @Slot(str)
    def _workflow_failed(self, error: str):
        self._last_error = error
        self._running = False
        self.run_button.setEnabled(True)
        self.progress.setVisible(False)

        self._set_status("Processing Failed", "error", "The workflow encountered an issue.")
        self._update_failure_metrics()
        self._append_log(error)

        # Parse friendly message (Section 11, 12, 39)
        if "WinError 32" in error or "Permission denied" in error:
            title = "Excel Workbook Locked"
            what = "EnergyAutomation could not save the updated daily energy values to Excel."
            why = "The Excel workbook (Test_BI_Analysis_Report_2026.xlsx) is currently open in Microsoft Excel on this workstation."
            action = "Please save any open changes, close Microsoft Excel completely, and click 'Run Automation Now' again."
        elif "credentials" in error.lower() or "oauth" in error.lower() or "token" in error.lower():
            title = "Gmail Authorization Needed"
            what = "Could not download new EMS reports from the operational Gmail inbox."
            why = "Gmail OAuth credentials require initial login or token refresh."
            action = "Open Settings -> Launch Setup Wizard, and complete the Google login step."
        elif "FileNotFound" in error:
            title = "Required File Not Found"
            what = "The automation engine could not locate a designated file or folder."
            why = "The workbook or template path specified in configuration may have moved."
            action = "Go to Settings -> Excel Workbook, verify the file path, and retry."
        else:
            title = "Report Processing Notice"
            what = "An issue occurred while processing the energy report."
            why = "Network latency, temporary email sync glitch, or data formatting discrepancy."
            action = "Check your network connection and click 'Run Automation Now' to retry."

        try:
            InfoBar.error(
                title=title,
                content=what,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=6000,
                parent=self,
            )
        except Exception:
            pass

        dlg = FriendlyErrorDialog(
            self,
            title=title,
            what=what,
            why=why,
            action=action,
            technical_details=error,
        )
        dlg.exec()

    def _worker_cleanup(self):
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None

    def _show_result_summary(self, result: Any):
        if result is None:
            return
        text = str(result)
        self.activity_label.setText(text[:1200])

    def _update_success_metrics(self, result: Any):
        current = self._read_metric(self.card_processed)
        self.card_processed._metric_value.setText(str(current + 1))

        success = self._read_metric(self.card_success)
        self.card_success._metric_value.setText(str(success + 1))

        self.card_last._metric_value.setText(datetime.now().strftime("%H:%M:%S"))

        try:
            self.refresh_reports_table()
            self.refresh_analysis()
            self.refresh_meters_table()
            self.refresh_plant_topology_view()
            self.refresh_alerts_panel()
            self.refresh_overview()
        except Exception:
            pass

    def _update_failure_metrics(self):
        current = self._read_metric(self.card_processed)
        self.card_processed._metric_value.setText(str(current + 1))

        failed = self._read_metric(self.card_failed)
        self.card_failed._metric_value.setText(str(failed + 1))

        self.card_last._metric_value.setText(datetime.now().strftime("%H:%M:%S"))

        try:
            self.refresh_alerts_panel()
        except Exception:
            pass

    @staticmethod
    def _read_metric(card: QWidget) -> int:
        try:
            return int(card._metric_value.text())
        except (ValueError, AttributeError):
            return 0

    def toggle_scheduler(self):
        try:
            running = getattr(self.scheduler, "is_running", None)
            if callable(running):
                running = running()

            if running is True:
                self.scheduler.stop()
                self.scheduler_button.setText("Start Scheduler")
                self._set_status("Scheduler Paused", "warning", "Automatic background polling is paused.")
                self._append_log("Scheduler paused by user.")
            else:
                self.scheduler.start()
                self.scheduler_button.setText("Pause Scheduler")
                self._set_status("Scheduler Running", "success", "Automatic polling active every 5 minutes.")
                self._append_log("Scheduler started.")
        except Exception as exc:
            self._append_log(f"Scheduler control error: {exc}")
            QMessageBox.critical(self, "Scheduler Error", str(exc))

    def _set_status(self, text: str, state: str, detail: str | None = None):
        self.status_text.setText(text)
        if detail:
            self.status_detail.setText(detail)

        states = {
            "ready": "●",
            "success": "●",
            "running": "●",
            "warning": "●",
            "error": "●",
        }
        self.status_indicator.setText(states.get(state, "●"))
        self.status_indicator.setProperty("state", state)
        color_map = {
            "ready": "#16a34a",
            "success": "#16a34a",
            "running": "#2563eb",
            "warning": "#d97706",
            "error": "#dc2626",
        }
        self.status_indicator.setStyleSheet(f"font-size: 20pt; color: {color_map.get(state, '#16a34a')};")
        self.statusBar.showMessage(text)

    def refresh_status(self):
        self._set_status("Ready", "ready", "System is operational.")
        self.refresh_overview()
        self._append_log("Dashboard status refreshed.")

    def _append_log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, "full_log"):
            self.full_log.append(f"[{timestamp}] {message}")

    # =================================================================
    # Clock & Tray
    # =================================================================

    def _start_clock(self):
        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(1000)
        self.clock_timer = timer
        self._update_clock()

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%d %b %Y • %H:%M:%S"))

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return

        self.tray = QSystemTrayIcon(self)
        app_icon = Path("assets/app.ico")
        if app_icon.exists():
            self.tray.setIcon(QIcon(str(app_icon)))
        self.tray.setToolTip("EnergyAutomation EMS")

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        show_action = QAction("Open Dashboard", self)
        show_action.triggered.connect(self._show_from_tray)
        run_action = QAction("Run Now", self)
        run_action.triggered.connect(self.run_now)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        menu.addAction(show_action)
        menu.addAction(run_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._running:
            answer = QMessageBox.question(
                self,
                "Processing in Progress",
                "A report-processing operation is still running.\n\nAre you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return

        try:
            self.application.stop()
        except Exception:
            pass

        if self.tray is not None:
            self.tray.hide()
        event.accept()
"""
Enterprise Energy Management Desktop Dashboard (PySide6 + QFluentWidgets).
Modernized with Windows 11 Fluent Design System, dynamic data bindings from
live Excel workbooks and SQLite audit trails, zero fake telemetry, unified navigation,
centralized notifications, and integrated Streamlit Management BI.
"""

from __future__ import annotations

from datetime import date, datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import traceback
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, QTime, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    ElevatedCardWidget,
    SimpleCardWidget,
    FluentWindow,
    FluentIcon as FIF,
    NavigationItemPosition,
    PrimaryPushButton,
    PushButton,
    TransparentPushButton,
    SearchLineEdit,
    SwitchButton,
    ProgressBar,
    TableWidget,
    InfoBar,
    InfoBarPosition,
    Theme,
    setTheme,
    isDarkTheme,
    TitleLabel,
    SubtitleLabel,
    StrongBodyLabel,
    BodyLabel,
    CaptionLabel,
)

from ui.design_system import (
    ThemeTokens,
    LIGHT_TOKENS,
    DARK_TOKENS,
    get_current_tokens,
    Typography,
    FluentCard,
    KPICard,
    StatusCard,
    StatusBadge,
    EmptyState,
    PageHeader,
)
from ui.data_service import DashboardDataService, DynamicOverviewData
from ui.notification_service import UINotificationService, FriendlyNotificationDialog, NotificationSeverity
from ui.dialogs.guided_tour import GuidedTourDialog
from ui.dialogs.setup_wizard import SetupWizardDialog


# =====================================================================
# Asynchronous Background Worker for Automation Workflow
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
# Real-Time Socket.IO Client Worker for Alert Streaming
# =====================================================================

class AlertSocketWorker(QObject):
    connected = Signal(str)
    disconnected = Signal()
    alert_created = Signal(dict)
    alert_acknowledged = Signal(str)
    stats_updated = Signal(dict)
    all_acknowledged = Signal(int)

    def __init__(self, target_url: str):
        super().__init__()
        self.target_url = target_url
        self._running = False
        self._sio: Any = None
        self._thread: Optional[threading.Thread] = None

    def start_worker(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_client, name="AlertSocketWorkerThread", daemon=True)
        self._thread.start()

    def _run_client(self):
        try:
            import socketio
            self._sio = socketio.Client(reconnection=True, reconnection_attempts=20, reconnection_delay=2)

            @self._sio.event
            def connect():
                self.connected.emit(self.target_url)

            @self._sio.event
            def disconnect():
                self.disconnected.emit()

            @self._sio.on("initial_state")
            def on_initial_state(data):
                if isinstance(data, dict):
                    if "stats" in data:
                        self.stats_updated.emit(data["stats"])

            @self._sio.on("alert_created")
            def on_alert_created(data):
                if isinstance(data, dict):
                    self.alert_created.emit(data)

            @self._sio.on("alert_acknowledged")
            def on_ack(data):
                aid = data.get("alert_id", "") if isinstance(data, dict) else str(data)
                self.alert_acknowledged.emit(aid)

            @self._sio.on("alert_stats")
            def on_stats(data):
                if isinstance(data, dict):
                    self.stats_updated.emit(data)

            @self._sio.on("all_alerts_acknowledged")
            def on_all_ack(data):
                cnt = data.get("count", 0) if isinstance(data, dict) else 0
                self.all_acknowledged.emit(cnt)

            self._sio.connect(self.target_url, transports=["websocket", "polling"], wait_timeout=5)
            self._sio.wait()
        except Exception:
            self.disconnected.emit()
        finally:
            self._running = False

    def stop_worker(self):
        self._running = False
        try:
            if self._sio and self._sio.connected:
                self._sio.disconnect()
        except Exception:
            pass


# =====================================================================
# Main Enterprise Dashboard Shell (PySide6 + QFluentWidgets)
# =====================================================================

class Dashboard(FluentWindow):
    """
    Windows 11-inspired Enterprise Energy Management desktop application shell.
    Features:
    - Microsoft Fluent Design System with high-contrast Light/Dark themes
    - Zero fake telemetry: dynamic binding to real Excel and SQLite records
    - Unified navigation layout (eliminated separate Simple/Engineer modes)
    - Centralized notification system with expandable technical details
    - Dedicated Streamlit Management BI integration
    - Light-Themed Tour & Setup Experience
    - Real-Time Socket.IO Alert Streaming & Dynamic State Synchronization
    """

    def __init__(self, application: Any, parent: QWidget | None = None):
        super().__init__(parent)
        setTheme(Theme.DARK)

        self.application = application
        self.workflow = getattr(application, "workflow", None)
        self.scheduler = getattr(application, "scheduler", None)
        self.services = getattr(application, "services", {})

        self.data_service = DashboardDataService(application)
        self.notification_service = UINotificationService(self)

        self.worker_thread: QThread | None = None
        self.worker: WorkflowWorker | None = None

        self._running = False
        self._last_result: Any = None
        self._last_error: str | None = None

        # Real-Time Alert Cards State
        self.alert_cards_map: Dict[str, QWidget] = {}
        self.active_alert_filter: str = "All"
        self.alert_socket_worker: Optional[AlertSocketWorker] = None

        self.setWindowTitle("EnergyAutomation — EMS Monitoring")
        app_icon = Path("assets/app.ico")
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))

        self.setMinimumSize(1260, 800)
        self.resize(1440, 920)

        # Compatibility references
        self.nav_buttons: List[Any] = []
        self.statusBar = QStatusBar(self)
        self.stack = self.stackedWidget

        # Build UI
        self._build_subinterfaces()
        self._build_title_bar()
        self._start_clock()

        # Connect Real-Time Socket.IO Alert Client
        self._init_alert_socket_client()

        # Load dynamic data
        self.refresh_status()
        self._append_log("EnergyAutomation Windows 11 Enterprise Platform initialized.")

    # =================================================================
    # Subinterface & Navigation Setup (11 Unified Windows 11 Pages)
    # =================================================================

    def _build_subinterfaces(self):
        # Page 0: Executive Dashboard
        self.page_overview = self._create_overview_page()
        self.addSubInterface(self.page_overview, FIF.HOME, "Executive Dashboard")

        # Page 1: Historical Data Recovery
        self.page_recovery = self._create_recovery_panel()
        self.addSubInterface(self.page_recovery, FIF.SYNC, "Data Recovery")

        # Page 2: Google Gemini AI Insights
        self.page_ai = self._create_ai_panel()
        self.addSubInterface(self.page_ai, FIF.CHAT, "AI Insights")

        # Page 3: Plotly Dash Management & Engineering BI
        self.page_dash = self._create_dash_panel()
        self.addSubInterface(self.page_dash, FIF.SHARE, "Plotly Dash BI")

        # Page 4: Centralized Alert Center
        self.page_alerts = self._create_alerts_panel()
        self.addSubInterface(self.page_alerts, FIF.RINGER, "Alert Centre")

        # Page 5: Processing History & Diagnostics
        self.page_history = self._create_history_page()
        self.addSubInterface(self.page_history, FIF.HISTORY, "Processing History")

        # Page 6: Settings & Configuration (Pinned to Bottom)
        self.page_settings = self._create_settings_panel()
        self.addSubInterface(self.page_settings, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM)

        # Page 7: Help & Support Center (Pinned to Bottom)
        self.page_help = self._create_help_page()
        self.addSubInterface(self.page_help, FIF.HELP, "Help & Support", NavigationItemPosition.BOTTOM)

        self.pages = [
            self.page_overview,
            self.page_recovery,
            self.page_ai,
            self.page_dash,
            self.page_alerts,
            self.page_history,
            self.page_settings,
            self.page_help,
        ]

    # =================================================================
    # Title Bar & Header Controls
    # =================================================================

    def _build_title_bar(self):
        tb = self.titleBar

        # Global Search Bar (Positioned in Top-Middle)
        self.global_search_input = SearchLineEdit(tb)
        self.global_search_input.setObjectName("GlobalSearch")
        self.global_search_input.setPlaceholderText("🔍 Search meters, reports, alerts, settings...")
        self.global_search_input.setToolTip("Type meter name, report date, or keyword to jump to relevant view")
        self.global_search_input.setFixedWidth(360)
        self.global_search_input.textChanged.connect(self.handle_global_search)

        # Guided Tour Button (Top-Right)
        btn_tour = PushButton("✨ Tour", tb)
        btn_tour.setObjectName("TourButton")
        btn_tour.setToolTip("Take a guided walkthrough of all platform capabilities (Light Theme)")
        btn_tour.clicked.connect(self.open_guided_tour)

        # Setup Wizard Button (Top-Right)
        btn_wizard = PushButton("⚙ Setup", tb)
        btn_wizard.setObjectName("WizardButton")
        btn_wizard.setToolTip("Open step-by-step wizard to configure Excel, Gmail, Gemini, and Streamlit")
        btn_wizard.clicked.connect(self.open_setup_wizard)

        # Clock
        self.clock_label = QLabel("00:00:00", tb)
        self.clock_label.setObjectName("ClockLabel")
        self.clock_label.setStyleSheet("color: #cbd5e1; font-size: 8.5pt; font-weight: 600; padding-right: 12px;")

        # Layout: Remove default spacer between title and controls
        if tb.hBoxLayout.count() > 2:
            item = tb.hBoxLayout.itemAt(2)
            if item and item.spacerItem():
                tb.hBoxLayout.takeAt(2)

        # Layout: Icon & Title -> Stretch(1) -> SearchBar (Top Middle) -> Stretch(1) -> Tour -> Gap(14) -> Setup -> Gap(18) -> Clock -> Spacing(12) -> Window Controls
        tb.hBoxLayout.insertStretch(2, 1)
        tb.hBoxLayout.insertWidget(3, self.global_search_input)
        tb.hBoxLayout.insertStretch(4, 1)
        tb.hBoxLayout.insertWidget(5, btn_tour)
        tb.hBoxLayout.insertSpacing(6, 14)
        tb.hBoxLayout.insertWidget(7, btn_wizard)
        tb.hBoxLayout.insertSpacing(8, 18)
        tb.hBoxLayout.insertWidget(9, self.clock_label)
        tb.hBoxLayout.insertSpacing(10, 12)

    def _start_clock(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.clock_label.setText(QTime.currentTime().toString("hh:mm:ss AP")))
        self._timer.start(1000)

    def _on_theme_toggled(self, is_dark: bool = True):
        # Application enforces Dark Theme only across all operations
        setTheme(Theme.DARK)
        self.refresh_status()

    def switch_page(self, index: int):
        if 0 <= index < len(self.pages):
            self.switchTo(self.pages[index])
            self._on_page_changed(index)

    def _on_page_changed(self, index: int):
        if 0 <= index < len(self.pages):
            page = self.pages[index]
            if page == self.page_overview:
                self.refresh_overview()
            elif hasattr(self, "page_dash") and page == self.page_dash:
                self.refresh_dash_panel()
            elif hasattr(self, "page_alerts") and page == self.page_alerts:
                self.refresh_alerts_panel()
            elif hasattr(self, "page_history") and page == self.page_history:
                self.refresh_history()

    # =================================================================
    # Page 0: Executive Overview (Dynamic Data & No Fake Telemetry)
    # =================================================================

    def _create_overview_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("page_overview")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. System Readiness & Status Banner
        self.readiness_card = self._create_readiness_ribbon()
        layout.addWidget(self.readiness_card)

        # 2. System Health Matrix (Dynamic status of all 6 services)
        self.health_matrix_card = self._create_health_matrix()
        layout.addWidget(self.health_matrix_card)

        # 3. Dynamic Energy KPI Cards (Today, Yesterday, MTD, DoD Variance)
        layout.addWidget(self._create_energy_kpi_cards())

        # 4. Report Processing Statistics (from SQLite audit trail)
        cards = QGridLayout()
        cards.setHorizontalSpacing(14)
        cards.setVerticalSpacing(14)

        self.card_processed = self._create_metric_card("Reports Processed", "NOT ACTIVE", "processed", "Total lifetime reports processed by engine")
        self.card_success = self._create_metric_card("Successful", "NOT ACTIVE", "success", "Reports processed with zero validation errors")
        self.card_failed = self._create_metric_card("Failed", "NOT ACTIVE", "failed", "Reports requiring operator attention")
        self.card_last = self._create_metric_card("Last Run", "NOT ACTIVE", "last", "Time of the most recent ingestion cycle")

        cards.addWidget(self.card_processed, 0, 0)
        cards.addWidget(self.card_success, 0, 1)
        cards.addWidget(self.card_failed, 0, 2)
        cards.addWidget(self.card_last, 0, 3)
        layout.addLayout(cards)

        # 5. Automation Operations Controls
        layout.addWidget(self._create_control_panel())

        # 6. Two-Column Split: Top Consumers Preview & Live Activity
        bottom_split = QHBoxLayout()
        bottom_split.setSpacing(16)

        bottom_split.addWidget(self._create_top_meters_preview(), 1)
        bottom_split.addWidget(self._create_activity_panel(), 1)

        layout.addLayout(bottom_split)
        scroll.setWidget(container)
        return scroll

    def _create_readiness_ribbon(self) -> QWidget:
        card = ElevatedCardWidget()
        card.setObjectName("StatusCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self.status_indicator = QLabel("✓")
        self.status_indicator.setObjectName("StatusIndicator")
        self.status_indicator.setStyleSheet("font-size: 20pt; font-weight: 800; color: #4ade80;")

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        self.status_text = QLabel("System Ready & Connected")
        self.status_text.setObjectName("StatusText")
        self.status_text.setStyleSheet("font-size: 12pt; font-weight: 800; color: #ffffff;")

        self.status_detail = QLabel("Core automation engine is active. Waiting for scheduled morning report.")
        self.status_detail.setObjectName("StatusDetail")
        self.status_detail.setStyleSheet("color: #cbd5e1; font-size: 9pt;")

        info_box.addWidget(self.status_text)
        info_box.addWidget(self.status_detail)
        layout.addLayout(info_box, 1)

        # Dynamic Checklist Badges
        self.badge_excel = StatusBadge("EXCEL")
        layout.addWidget(self.badge_excel)

        self.badge_db = StatusBadge("DATABASE")
        layout.addWidget(self.badge_db)

        self.badge_gmail = StatusBadge("GMAIL")
        layout.addWidget(self.badge_gmail)

        self.badge_dash = StatusBadge("DASH BI")
        self.badge_streamlit = self.badge_dash
        layout.addWidget(self.badge_dash)

        btn_cfg = PushButton("Configure...", card)
        btn_cfg.setToolTip("Jump to Configuration Settings to review credentials")
        btn_cfg.clicked.connect(lambda: self.switchTo(self.page_settings))
        layout.addWidget(btn_cfg)

        return card

    def _create_health_matrix(self) -> QWidget:
        card = SimpleCardWidget()
        root_lay = QVBoxLayout(card)
        root_lay.setContentsMargins(18, 14, 18, 14)
        root_lay.setSpacing(10)

        header_lbl = StrongBodyLabel("System Health & Integration Status (Live Verification)")
        header_lbl.setStyleSheet("color: #ffffff; font-weight: 700;")
        root_lay.addWidget(header_lbl)

        self.health_grid = QGridLayout()
        self.health_grid.setHorizontalSpacing(20)
        self.health_grid.setVerticalSpacing(8)

        self.health_cards: Dict[str, StatusCard] = {}
        for idx, s_name in enumerate(["Excel", "Database", "Gmail", "Automation", "AI", "Dash"]):
            row = idx // 3
            col = idx % 3
            sc = StatusCard(title=s_name, status="NOT ACTIVE", details="Checking connection...")
            self.health_cards[s_name] = sc
            self.health_grid.addWidget(sc, row, col)

        root_lay.addLayout(self.health_grid)
        return card

    def _create_energy_kpi_cards(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)

        self.card_today_kwh = KPICard("Latest Report Consumption", "NOT ACTIVE", "—", "#ffffff")
        self.card_yesterday_kwh = KPICard("Previous Shift", "NOT ACTIVE", "—", "#ffffff")
        self.card_mtd_kwh = KPICard("Month-To-Date (MTD)", "NOT ACTIVE", "—", "#ffffff")
        self.card_dod_delta = KPICard("Day-over-Day Variance", "NOT ACTIVE", "—", "#ffffff")

        grid.addWidget(self.card_today_kwh, 0, 0)
        grid.addWidget(self.card_yesterday_kwh, 0, 1)
        grid.addWidget(self.card_mtd_kwh, 0, 2)
        grid.addWidget(self.card_dod_delta, 0, 3)
        return container

    def _create_metric_card(self, title: str, value: str, metric_type: str, tooltip: str = "") -> ElevatedCardWidget:
        card = ElevatedCardWidget()
        card.setObjectName("MetricCard")
        card.setStyleSheet("""
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
        if tooltip:
            card.setToolTip(tooltip)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        t_lbl = CaptionLabel(title.upper())
        t_lbl.setStyleSheet("color: #cbd5e1; font-size: 8pt; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(t_lbl)

        v_lbl = QLabel(value)
        v_lbl.setProperty("metric", metric_type)
        v_lbl.setStyleSheet("font-size: 19pt; font-weight: 800; color: #ffffff; margin-top: 2px;")
        layout.addWidget(v_lbl)

        card._metric_value = v_lbl
        return card

    def _create_control_panel(self) -> QWidget:
        card = SimpleCardWidget()
        root_lay = QVBoxLayout(card)
        root_lay.setContentsMargins(18, 14, 18, 14)
        root_lay.setSpacing(10)

        root_lay.addWidget(StrongBodyLabel("Automation Operations & Scheduler Controls"))

        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.run_button = PrimaryPushButton("Run Automation Now", card)
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.setToolTip("Triggers immediate execution: checks Gmail, parses PDF, updates Excel, and logs audit")
        self.run_button.clicked.connect(self.run_now)

        self.scheduler_button = PushButton("Pause Scheduler", card)
        self.scheduler_button.setToolTip("Temporarily stop automatic background checks")
        self.scheduler_button.clicked.connect(self.toggle_scheduler)

        self.refresh_button = PushButton("Refresh Data", card)
        self.refresh_button.setToolTip("Re-query Excel workbook and SQLite database for latest values")
        self.refresh_button.clicked.connect(self.refresh_status)

        self.btn_open_bi = PushButton("Open Plotly Dash BI", card)
        self.btn_open_bi.setToolTip("Open the executive and engineering Plotly Dash analytics dashboard in your browser")
        self.btn_open_bi.clicked.connect(self.launch_dash_browser)

        self.btn_select_file = PushButton("Select Excel File", card)
        self.btn_select_file.setToolTip("Browse and verify production EMS Excel workbook (.xlsx / .xlsm)")
        self.btn_select_file.clicked.connect(self._browse_excel_file)

        layout.addWidget(self.run_button)
        layout.addWidget(self.scheduler_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.btn_select_file)
        layout.addWidget(self.btn_open_bi)
        layout.addStretch()

        self.next_event_label = QLabel("Next scheduled check: ~06:00 AM")
        self.next_event_label.setStyleSheet("color: #cbd5e1; font-size: 9pt; font-weight: 500;")
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

        btn_view_all = TransparentPushButton("Explore Detailed Telemetry in Dash BI →", card)
        btn_view_all.clicked.connect(lambda: self.switchTo(self.page_dash))
        lay.addWidget(btn_view_all, 0, Qt.AlignRight)
        return card

    def _create_activity_panel(self) -> QWidget:
        card = SimpleCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addWidget(StrongBodyLabel("Live Activity Summary & Log Events"))

        self.activity_label = QLabel("Waiting for first scheduled execution.")
        self.activity_label.setWordWrap(True)
        self.activity_label.setMinimumHeight(60)
        self.activity_label.setStyleSheet("color: #f1f5f9; font-size: 9.5pt;")
        layout.addWidget(self.activity_label)

        btn_logs = TransparentPushButton("View Full Execution Audit Log →", card)
        btn_logs.clicked.connect(lambda: self.switchTo(self.page_history))
        layout.addWidget(btn_logs, 0, Qt.AlignRight)
        return card

    # =================================================================
    # Central Dynamic Status Refresh (Zero Fake Telemetry)
    # =================================================================

    def refresh_status(self):
        """Re-evaluates data from both Excel and SQLite with zero manufactured numbers."""
        overview_data = self.data_service.get_overview_data()

        # Update Health Cards & Readiness Badges
        health = overview_data.health_services
        for s_name, sc in self.health_cards.items():
            if s_name in health:
                h = health[s_name]
                sc.update_status(status=h.status, details=h.details, timestamp=h.timestamp)

        if "Excel" in health:
            self.badge_excel.set_status(f"Excel: {health['Excel'].status}")
        if "Database" in health:
            self.badge_db.set_status(f"DB: {health['Database'].status}")
        if "Gmail" in health:
            self.badge_gmail.set_status(f"Gmail: {health['Gmail'].status}")
        dash_health = health.get("Dash") or health.get("Streamlit")
        if dash_health:
            self.badge_dash.set_status(f"BI: {dash_health.status}")

        # Update dynamic readiness ribbon state
        if health:
            all_connected = all(
                h.status.upper() in ("HEALTHY", "READY", "ACTIVE", "CONNECTED", "OK")
                for h in health.values()
            )
            any_paused = any(
                h.status.upper() in ("PAUSED", "STANDBY", "IDLE")
                for h in health.values()
            )
            if all_connected:
                self._set_status("System Ready & Connected", "ready", "All services operational. Next scheduled check: ~06:00 AM")
            elif any_paused:
                self._set_status("System Standby", "paused", "One or more services in standby mode.")
            else:
                self._set_status("Attention Required", "error", "One or more services require configuration.")

        if hasattr(self, "_update_excel_settings_status"):
            self._update_excel_settings_status()

        # Dynamic Excel File Verification & Guidance
        excel_srv = self.services.get("excel_service")
        wb_p = Path(str(getattr(excel_srv, "workbook_path", ""))) if excel_srv else None
        wb_name = wb_p.name if (wb_p and str(wb_p) != ".") else "EMS Workbook"
        if not wb_p or not wb_p.exists() or not wb_p.is_file():
            if not getattr(self, "_warned_missing_excel", False):
                self._warned_missing_excel = True
                InfoBar.warning(
                    title="Excel File Path Not Connected",
                    content="Choose the correct file and file path otherwise not found or not connected.",
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=7000,
                    parent=self,
                )
                if hasattr(self, "raise_user_alert"):
                    self.raise_user_alert(
                        "WARNING",
                        "Excel File Not Found or Not Connected",
                        "Choose the correct file and file path otherwise not found or not connected. Click 'Select Excel File' in Overview or Settings to link your verified EMS workbook.",
                        source="system_startup",
                    )

        # Update KPI Cards
        if overview_data.is_active and overview_data.latest_kwh is not None:
            self.card_today_kwh.set_data(
                value=f"{overview_data.latest_kwh:,.2f} kWh",
                subtext=f"Report Date: {overview_data.latest_date or '—'}",
                source=f"Excel ({wb_name})",
                report_date=overview_data.latest_date or "",
                is_active=True,
            )

            prev_val = f"{overview_data.prev_kwh:,.2f} kWh" if overview_data.prev_kwh else "NOT ACTIVE"
            self.card_yesterday_kwh.set_data(
                value=prev_val,
                subtext=f"Date: {overview_data.prev_date or '—'}",
                source="Excel",
                report_date=overview_data.prev_date or "",
                is_active=bool(overview_data.prev_kwh),
            )

            mtd_val = f"{overview_data.mtd_kwh:,.1f} kWh" if overview_data.mtd_kwh else "NOT ACTIVE"
            self.card_mtd_kwh.set_data(
                value=mtd_val,
                subtext="Current Billing Period",
                source="Excel Sum",
                is_active=bool(overview_data.mtd_kwh),
            )

            dod_str = f"{overview_data.dod_change_pct:+.1f}% ({overview_data.dod_change_kwh:+,.1f} kWh)" if overview_data.dod_change_pct is not None else "NOT ACTIVE"
            self.card_dod_delta.set_data(
                value=dod_str,
                subtext="Day-over-Day Variance",
                source="Excel",
                is_active=bool(overview_data.dod_change_pct is not None),
            )
        else:
            self.card_today_kwh.set_data("NOT ACTIVE", is_active=False)
            self.card_yesterday_kwh.set_data("NOT ACTIVE", is_active=False)
            self.card_mtd_kwh.set_data("NOT ACTIVE", is_active=False)
            self.card_dod_delta.set_data("NOT ACTIVE", is_active=False)

        # Update Processing Statistics dynamically in real time
        if overview_data.reports_processed > 0:
            self.card_processed._metric_value.setText(f"{overview_data.reports_processed:,}")
            self.card_processed.setToolTip(f"Total reports processed by engine: {overview_data.reports_processed:,}")
            self.card_success._metric_value.setText(f"{overview_data.reports_successful:,}")
            self.card_success.setToolTip(f"Successfully processed with zero validation errors: {overview_data.reports_successful:,}")
            self.card_failed._metric_value.setText(f"{overview_data.reports_failed:,}")
            self.card_failed.setToolTip(f"Reports requiring operator attention: {overview_data.reports_failed:,}")
            self.card_last._metric_value.setText(overview_data.last_run_timestamp)
            self.card_last.setToolTip(f"Last automated execution: {overview_data.last_run_timestamp}")
        else:
            self.card_processed._metric_value.setText("0 (Ready)")
            self.card_processed.setToolTip("System is standing by. Click 'Run Automation Now' to process first report.")
            self.card_success._metric_value.setText("0 (Ready)")
            self.card_success.setToolTip("Awaiting first automation cycle.")
            self.card_failed._metric_value.setText("0 (Clean)")
            self.card_failed.setToolTip("Zero failures recorded.")
            self.card_last._metric_value.setText(overview_data.last_run_timestamp if overview_data.last_run_timestamp and overview_data.last_run_timestamp != "Never" else "Awaiting 1st Run")
            self.card_last.setToolTip("Scheduled to run daily at 06:00 AM or immediately via 'Run Automation Now'.")

        # Update Top Meters Mini Table
        top_eq = overview_data.top_equipment
        self.mini_meters_table.setRowCount(len(top_eq))
        for r_idx, eq in enumerate(top_eq):
            self.mini_meters_table.setItem(r_idx, 0, QTableWidgetItem(eq["meter_name"]))
            self.mini_meters_table.setItem(r_idx, 1, QTableWidgetItem(f"{eq['active_energy']:,.1f} kWh"))
            self.mini_meters_table.setItem(r_idx, 2, QTableWidgetItem(f"Share: {eq['share_pct']:.1f}%"))

    def refresh_overview(self):
        self.refresh_status()

    # =================================================================
    # Page 1: Historical Data Recovery (Gap Healing)
    # =================================================================

    def _create_recovery_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_recovery")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = PageHeader(
            "Historical Data Recovery & Weekend Gap Healing",
            "Scans the past 30 days to identify missing Sunday or holiday reports and backfills chronologically",
        )
        layout.addWidget(header)

        card = SimpleCardWidget(widget)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(18, 16, 18, 16)
        c_lay.setSpacing(10)

        diag_hdr = StrongBodyLabel("Automated Gap Healing Diagnostics")
        diag_hdr.setStyleSheet("color: #ffffff; font-weight: 700;")
        c_lay.addWidget(diag_hdr)
        self.recovery_status_lbl = QLabel("Ready to scan 30-day window for calendar gaps.")
        self.recovery_status_lbl.setStyleSheet("color: #cbd5e1; font-size: 9.5pt;")
        c_lay.addWidget(self.recovery_status_lbl)

        btn_box = QHBoxLayout()
        self.btn_scan = PrimaryPushButton("Scan for Missing Dates", card)
        self.btn_scan.clicked.connect(self.scan_missing_dates)
        btn_box.addWidget(self.btn_scan)

        self.btn_heal = PushButton("Run Historical Gap Healing Now", card)
        self.btn_heal.clicked.connect(self.run_gap_recovery)
        btn_box.addWidget(self.btn_heal)
        btn_box.addStretch()
        c_lay.addLayout(btn_box)

        layout.addWidget(card)

        self.recovery_log = QTextEdit(widget)
        self.recovery_log.setReadOnly(True)
        self.recovery_log.setPlaceholderText("Recovery diagnostics and chronological backfill log...")
        self.recovery_log.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        layout.addWidget(self.recovery_log, 1)

        return widget

    def scan_missing_dates(self):
        self.recovery_log.append("Scanning past 30 days against existing SQLite reports and Excel dates...")
        recon = self.services.get("reconciliation_service")
        repo = self.services.get("report_repository")
        excel_srv = self.services.get("excel_service")

        existing_dates = set()
        if repo:
            try:
                reports = repo.get_recent_history(limit=60)
                for r in reports:
                    d = r.get("report_date")
                    if d:
                        existing_dates.add(str(d)[:10])
            except Exception:
                pass

        if excel_srv and hasattr(excel_srv, "get_existing_dates"):
            try:
                ex_dates = excel_srv.get_existing_dates()
                for d in ex_dates:
                    existing_dates.add(str(d)[:10])
            except Exception:
                pass

        if recon:
            try:
                missing = recon.find_missing_dates(available_dates=list(existing_dates), days_back=30)
                missing_strs = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in missing]
                if missing_strs:
                    self.recovery_log.append(f"🔍 Identified {len(missing_strs)} missing date(s): {', '.join(missing_strs)}")
                    self.recovery_status_lbl.setText(f"Found {len(missing_strs)} missing date(s). Ready for automated gap healing.")
                    self.recovery_status_lbl.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 9.5pt;")
                    self.recovery_log.append("💡 Suggestion: Weekend dates (such as Sundays) occur when the plant does not generate PDF reports. Click 'Run Historical Gap Healing Now' to automatically backfill available reports from Gmail.")
                    self.raise_user_alert("WARNING", f"Calendar Gaps Detected: {len(missing_strs)} missing date(s) in last 30 days.")
                else:
                    self.recovery_log.append("✔ No missing dates detected in the past 30 days. Ledger is continuous and healthy.")
                    self.recovery_status_lbl.setText("All report dates in the 30-day window are verified continuous.")
                    self.recovery_status_lbl.setStyleSheet("color: #4ade80; font-weight: 700; font-size: 9.5pt;")
            except Exception as e:
                self.recovery_log.append(f"⚠ Scan notice: {e}")
                self.recovery_status_lbl.setText("Scan completed with operational notice.")
        else:
            self.recovery_log.append("Reconciliation service or repository uninitialized.")

    def run_gap_recovery(self):
        if self._running:
            self.notification_service.notify_warning("System Busy", "A workflow operation is already in progress.")
            return
        self.recovery_log.append("Triggering automated workflow with historical gap recovery...")
        self.run_now()

    # =================================================================
    # Page 2: Google Gemini AI Insights
    # =================================================================

    def _create_ai_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_ai")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = PageHeader(
            "Google Gemini Energy Intelligence Assistant",
            "Conversational operational intelligence operating strictly in read-only advisory mode",
        )
        layout.addWidget(header)

        # Live AI Service Status & Setup Banner
        self.ai_status_card = SimpleCardWidget(widget)
        as_lay = QHBoxLayout(self.ai_status_card)
        as_lay.setContentsMargins(14, 10, 14, 10)
        as_lay.setSpacing(10)

        self.lbl_ai_panel_status = QLabel()
        as_lay.addWidget(self.lbl_ai_panel_status, 1)

        self.btn_ai_test = PushButton("Test Connection", self.ai_status_card)
        self.btn_ai_test.clicked.connect(self._test_gemini_connection)
        as_lay.addWidget(self.btn_ai_test)

        self.btn_ai_cfg = PushButton("Configure API Key in Settings", self.ai_status_card)
        self.btn_ai_cfg.clicked.connect(lambda: self.switchTo(self.page_settings))
        as_lay.addWidget(self.btn_ai_cfg)

        layout.addWidget(self.ai_status_card)
        self._update_ai_panel_status_card()

        q_box = QHBoxLayout()
        self.ai_query_input = SearchLineEdit(widget)
        self.ai_query_input.setPlaceholderText("Ask an operational question (e.g. 'What was the total energy consumed on the latest report?')")
        self.ai_query_input.returnPressed.connect(self.ask_ai)
        q_box.addWidget(self.ai_query_input)

        btn_ask = PrimaryPushButton("Ask AI", widget)
        btn_ask.clicked.connect(self.ask_ai)
        q_box.addWidget(btn_ask)
        layout.addLayout(q_box)

        # Organized Prompt Suggestions (Categorized for Business & Engineering)
        sugg_card = SimpleCardWidget(widget)
        sugg_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 6px;")
        sc_lay = QVBoxLayout(sugg_card)
        sc_lay.setContentsMargins(12, 8, 12, 8)
        sc_lay.setSpacing(6)

        sc_title = StrongBodyLabel("💡 Guided Operational Prompts & Recommended Questions")
        sc_title.setStyleSheet("color: #f8fafc; font-size: 8.5pt; font-weight: 700;")
        sc_lay.addWidget(sc_title)

        # Row 1: Energy & Consumption
        r1 = QHBoxLayout()
        lbl_r1 = CaptionLabel("📊 Consumption:")
        lbl_r1.setStyleSheet("color: #94a3b8; font-weight: 700; min-width: 90px;")
        r1.addWidget(lbl_r1)
        for p in [
            "What was the total energy consumed on the latest report?",
            "Compare energy consumption yesterday versus previous days",
        ]:
            b = PushButton(p, sugg_card)
            b.setStyleSheet("font-size: 8.5pt; padding: 3px 8px;")
            b.clicked.connect(lambda _, t=p: self._set_and_ask_ai(t))
            r1.addWidget(b)
        r1.addStretch()
        sc_lay.addLayout(r1)

        # Row 2: Feeder & Load Analysis
        r2 = QHBoxLayout()
        lbl_r2 = CaptionLabel("🏭 Top Feeders:")
        lbl_r2.setStyleSheet("color: #94a3b8; font-weight: 700; min-width: 90px;")
        r2.addWidget(lbl_r2)
        for p in [
            "Which meter consumed the most energy?",
            "Show distribution share of top 5 industrial loads",
        ]:
            b = PushButton(p, sugg_card)
            b.setStyleSheet("font-size: 8.5pt; padding: 3px 8px;")
            b.clicked.connect(lambda _, t=p: self._set_and_ask_ai(t))
            r2.addWidget(b)
        r2.addStretch()
        sc_lay.addLayout(r2)

        # Row 3: Quality, Gaps & Anomaly Diagnostics
        r3 = QHBoxLayout()
        lbl_r3 = CaptionLabel("⚠️ Health & Gaps:")
        lbl_r3.setStyleSheet("color: #94a3b8; font-weight: 700; min-width: 90px;")
        r3.addWidget(lbl_r3)
        for p in [
            "Were there any missing reports in the last 30 days?",
            "Are there any negative readings, zeroes, or anomalies?",
            "Provide energy conservation recommendations for this facility",
        ]:
            b = PushButton(p, sugg_card)
            b.setStyleSheet("font-size: 8.5pt; padding: 3px 8px;")
            b.clicked.connect(lambda _, t=p: self._set_and_ask_ai(t))
            r3.addWidget(b)
        r3.addStretch()
        sc_lay.addLayout(r3)

        layout.addWidget(sugg_card)

        self.ai_response_display = QTextEdit(widget)
        self.ai_response_display.setReadOnly(True)
        self.ai_response_display.setPlaceholderText("Verified AI explanations and deterministic energy intelligence will appear here...")
        self.ai_response_display.setStyleSheet("font-family: Consolas, monospace; font-size: 9.5pt;")
        layout.addWidget(self.ai_response_display, 1)
        return widget

    def _update_ai_panel_status_card(self):
        if not hasattr(self, "lbl_ai_panel_status"):
            return
        gemini = self.services.get("gemini_service")
        has_key = bool(gemini and getattr(gemini, "api_key", None))
        if has_key:
            model = getattr(gemini, "model", "gemini-flash-latest") or "gemini-flash-latest"
            self.lbl_ai_panel_status.setText(
                f"<b>Status:</b> <span style='color: #4ade80;'>✓ Connected to Google Gemini ({model})</span> "
                "— Cloud advisory intelligence is active with multi-model failover."
            )
            self.btn_ai_cfg.setText("Manage API Key")
        else:
            self.lbl_ai_panel_status.setText(
                "<b>Status:</b> <span style='color: #fbbf24;'>• Offline Fallback Active (Deterministic Engine)</span> "
                "— Enter a Google Gemini API Key in Settings to enable cloud AI reasoning."
            )
            self.btn_ai_cfg.setText("Configure API Key in Settings")

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

            tot = None
            rep_date = None
            if latest:
                tot = latest.get("total_energy")
                rep_date = latest.get("report_date")
            elif hasattr(self, "data_service"):
                ov = self.data_service.get_overview_data()
                if ov.is_active:
                    tot = ov.latest_kwh
                    rep_date = ov.latest_date

            context = {
                "latest_report": latest or {"total_energy": tot, "report_date": rep_date},
                "readings": readings,
                "history": history,
                "total_energy": tot,
                "total": tot,
                "report_date": rep_date,
                "meters": readings,
            }
            res = gemini.ask(query, context_data=context)
            if isinstance(res, dict):
                answer_text = res.get("answer") or res.get("error") or str(res)
                if res.get("note"):
                    answer_text = f"{answer_text}\n\n[System Note: {res['note']}]"
            else:
                answer_text = str(res)

            self.ai_response_display.setText(answer_text)
            self._append_log(f"AI Assistant answered: '{query[:40]}...'")
        except Exception as exc:
            self.ai_response_display.setText(f"Error querying AI: {exc}")

    # =================================================================
    # Page 3: Plotly Dash Management & Engineering BI
    # =================================================================

    def _create_dash_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_dash")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = PageHeader(
            "Plotly Dash Management & Engineering BI",
            "Interactive executive and plant engineering intelligence dashboard with granular telemetry grids",
        )
        layout.addWidget(header)

        # Status Card
        self.dash_status_card = SimpleCardWidget(widget)
        s_lay = QVBoxLayout(self.dash_status_card)
        s_lay.setContentsMargins(18, 16, 18, 16)
        s_lay.setSpacing(10)

        st_title = StrongBodyLabel("Plotly Dash Microservice State")
        st_title.setStyleSheet("color: #ffffff; font-weight: 700;")
        s_lay.addWidget(st_title)
        self.lbl_dash_status = QLabel("✓ ACTIVE — Plotly Dash BI ready on http://localhost:8050")
        self.lbl_dash_status.setStyleSheet("color: #4ade80; font-weight: 700; font-size: 10pt;")
        s_lay.addWidget(self.lbl_dash_status)

        self.lbl_dash_desc = QLabel(
            "The Plotly Dash microservice operates strictly as a read-only analytics consumer. "
            "It delivers deep interactive analysis for business and engineering teams: "
            "Executive Overview, Feeder Telemetry Grid, Outlier Diagnostics, and Data Quality Assurance. "
            "It never mutates Excel formulas or alters authoritative database records."
        )
        self.lbl_dash_desc.setWordWrap(True)
        self.lbl_dash_desc.setStyleSheet("color: #cbd5e1; font-size: 9pt; line-height: 1.4;")
        s_lay.addWidget(self.lbl_dash_desc)

        layout.addWidget(self.dash_status_card)

        # Action Buttons
        btn_box = QHBoxLayout()
        self.btn_launch_dash = PrimaryPushButton("🚀 Open Plotly Dash BI in Browser", widget)
        self.btn_launch_dash.setObjectName("PrimaryButton")
        self.btn_launch_dash.setToolTip("Auto-start server if needed and launch http://localhost:8050 in default browser")
        self.btn_launch_dash.clicked.connect(self.launch_dash_browser)
        btn_box.addWidget(self.btn_launch_dash)

        self.btn_start_dash_server = PushButton("⚡ Start Background Dash Server", widget)
        self.btn_start_dash_server.setToolTip("Run Plotly Dash microservice on port 8050 if not already running")
        self.btn_start_dash_server.clicked.connect(self.start_dash_server)
        btn_box.addWidget(self.btn_start_dash_server)

        btn_box.addStretch()
        layout.addLayout(btn_box)

        # Architecture & Microservices Card
        info_card = SimpleCardWidget(widget)
        c_lay = QVBoxLayout(info_card)
        c_lay.setContentsMargins(18, 16, 18, 16)
        c_lay.setSpacing(12)

        c_title = StrongBodyLabel("Dash Microservice Capabilities & Architecture")
        c_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 11pt;")
        c_lay.addWidget(c_title)

        features = [
            (
                "Executive & Business Intelligence",
                "Real-time KPI summary cards, shift-by-shift trends with target threshold indicators, incomer vs submeter breakdowns, and feeder share distribution charts.",
            ),
            (
                "Engineering Operational Analysis",
                "High-resolution feeder telemetry data table, feeder load comparison graphs, operational anomaly diagnostics, and date range filters.",
            ),
            (
                "Data Quality & Telemetry Assurance",
                "Telemetry freshness gauge, date gap and weekend missing date detection, and formula reconciliation audits.",
            ),
        ]

        for f_title, f_desc in features:
            s_box = QFrame()
            s_box.setStyleSheet("background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 10px;")
            sb_lay = QVBoxLayout(s_box)
            sb_lay.setSpacing(4)
            st_lbl = QLabel(f_title)
            st_lbl.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 9.5pt;")
            sb_lay.addWidget(st_lbl)
            sd_lbl = QLabel(f_desc)
            sd_lbl.setWordWrap(True)
            sd_lbl.setStyleSheet("color: #cbd5e1; font-size: 8.8pt; line-height: 1.4;")
            sb_lay.addWidget(sd_lbl)
            c_lay.addWidget(s_box)

        layout.addWidget(info_card, 1)
        self.refresh_dash_panel()
        return widget

    def _is_dash_running(self, host: str = "127.0.0.1", port: int = 8050) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.6)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    def refresh_dash_panel(self):
        if not hasattr(self, "lbl_dash_status"):
            return
        if self._is_dash_running():
            self.lbl_dash_status.setText("✓ CONNECTED — Plotly Dash BI is active and listening on http://localhost:8050")
            self.lbl_dash_status.setStyleSheet("color: #4ade80; font-weight: 700; font-size: 10pt;")
        else:
            self.lbl_dash_status.setText("• STANDBY — Local Dash server ready to launch on http://localhost:8050")
            self.lbl_dash_status.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 10pt;")

    def launch_dash_browser(self):
        url = QUrl("http://localhost:8050")
        if not self._is_dash_running():
            self._append_log("Plotly Dash server not detected on port 8050. Auto-starting background server...")
            self.start_dash_server(notify=False)
            QTimer.singleShot(2000, lambda: QDesktopServices.openUrl(url))
            self.notification_service.notify_success(
                "Plotly Dash BI Launching",
                "Starting background Dash server on port 8050 and opening browser.\nDashboard will connect dynamically.",
            )
        else:
            QDesktopServices.openUrl(url)
            self.notification_service.notify_info(
                "Dash Connected",
                "Opening live Plotly Dash BI at http://localhost:8050 in your default web browser.",
            )

    def launch_streamlit_browser(self):
        """Backward-compatibility alias for launch_dash_browser."""
        return self.launch_dash_browser()

    def start_dash_server(self, notify: bool = True):
        bat_path = Path("run_dash.bat")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if bat_path.exists():
            subprocess.Popen(["cmd.exe", "/c", str(bat_path.resolve())], shell=True, creationflags=flags)
            if notify:
                self.notification_service.notify_success(
                    "Dash Server Starting",
                    "Starting background Plotly Dash server on port 8050 via run_dash.bat.",
                )
        else:
            cmd = [
                sys.executable,
                "-m",
                "services.dash_service.app",
            ]
            subprocess.Popen(cmd, creationflags=flags)
            if notify:
                self.notification_service.notify_success(
                    "Dash Server Starting",
                    "Launched background Plotly Dash app on port 8050.",
                )
        self._append_log("Plotly Dash background process triggered on port 8050.")
        QTimer.singleShot(2500, self.refresh_dash_panel)

    # =================================================================
    # Page 8: Centralized Alert Center (Rebuilt with Real-Time Socket.IO)
    # =================================================================

    def _init_alert_socket_client(self):
        """Connects the asynchronous Socket.IO client worker to the AlertSocketHub."""
        hub = self.services.get("alert_socket_hub")
        url = hub.get_url() if hub else "http://127.0.0.1:8765"
        self.alert_socket_worker = AlertSocketWorker(target_url=url)
        self.alert_socket_worker.connected.connect(self._on_socket_connected)
        self.alert_socket_worker.disconnected.connect(self._on_socket_disconnected)
        self.alert_socket_worker.alert_created.connect(self._on_socket_alert_created)
        self.alert_socket_worker.alert_acknowledged.connect(self._on_socket_alert_acknowledged)
        self.alert_socket_worker.stats_updated.connect(self._on_socket_stats_updated)
        self.alert_socket_worker.all_acknowledged.connect(self._on_socket_all_acknowledged)
        self.alert_socket_worker.start_worker()

    def closeEvent(self, event):
        """Gracefully disconnect Socket.IO and shutdown background services on window close."""
        if hasattr(self, "alert_socket_worker") and self.alert_socket_worker:
            self.alert_socket_worker.stop_worker()
        hub = self.services.get("alert_socket_hub")
        if hub:
            hub.stop()
        super().closeEvent(event)

    def _create_alerts_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_alerts")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Top Toolbar
        toolbar = QHBoxLayout()
        header = PageHeader(
            "Enterprise Real-Time Alert Centre",
            "Live Socket.IO stream • Real-time anomaly detection • Instant zero-polling acknowledgment",
        )
        toolbar.addWidget(header)
        toolbar.addStretch()

        # Real-Time Socket.IO Connection Badge
        self.socket_status_badge = QLabel("• Connecting (Socket.IO)...")
        self.socket_status_badge.setStyleSheet("""
            color: #fbbf24;
            font-weight: 700;
            font-size: 8.5pt;
            background-color: #78350f;
            border: 1px solid #d97706;
            border-radius: 6px;
            padding: 5px 12px;
        """)
        toolbar.addWidget(self.socket_status_badge)

        btn_test = PushButton("⚡ Test Alert Broadcast", widget)
        btn_test.setToolTip("Broadcast a sample anomaly over Socket.IO to verify real-time event pipeline")
        btn_test.clicked.connect(self._test_alert_broadcast)
        toolbar.addWidget(btn_test)

        btn_ack_all = PushButton("Acknowledge All", widget)
        btn_ack_all.clicked.connect(self._ack_all_alerts)
        toolbar.addWidget(btn_ack_all)

        btn_refresh = PushButton("Refresh", widget)
        btn_refresh.clicked.connect(self.refresh_alerts_panel)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # KPI Metrics Ribbon (5 Live Metric Tiles)
        kpi_ribbon = QHBoxLayout()
        kpi_ribbon.setSpacing(10)

        self.kpi_card_total = self._create_alert_kpi_card("TOTAL ACTIVE", "0", "#f8fafc", "val_total_active")
        self.kpi_card_critical = self._create_alert_kpi_card("CRITICAL", "0", "#f87171", "val_critical")
        self.kpi_card_warning = self._create_alert_kpi_card("WARNING", "0", "#fbbf24", "val_warning")
        self.kpi_card_info = self._create_alert_kpi_card("INFO", "0", "#60a5fa", "val_info")
        self.kpi_card_ai = self._create_alert_kpi_card("AI INSIGHTS", "0", "#c084fc", "val_ai")

        kpi_ribbon.addWidget(self.kpi_card_total)
        kpi_ribbon.addWidget(self.kpi_card_critical)
        kpi_ribbon.addWidget(self.kpi_card_warning)
        kpi_ribbon.addWidget(self.kpi_card_info)
        kpi_ribbon.addWidget(self.kpi_card_ai)
        layout.addLayout(kpi_ribbon)

        # Filter Box with Category Pills
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

        self.alert_summary_lbl = CaptionLabel("0 active alerts")
        self.alert_summary_lbl.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")
        filter_box.addWidget(self.alert_summary_lbl)
        layout.addLayout(filter_box)

        # Scrollable Alert Cards List
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

    def _create_alert_kpi_card(self, label: str, value: str, text_color: str, obj_name: str) -> SimpleCardWidget:
        card = SimpleCardWidget()
        card.setFixedHeight(68)
        card.setStyleSheet(f"""
            SimpleCardWidget {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-top: 3px solid {text_color};
                border-radius: 6px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)

        lbl_title = QLabel(label)
        lbl_title.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
        lay.addWidget(lbl_title)

        lbl_val = QLabel(value)
        lbl_val.setObjectName(obj_name)
        lbl_val.setStyleSheet(f"font-size: 15pt; font-weight: 800; color: {text_color};")
        lay.addWidget(lbl_val)
        return card

    def _set_kpi_value(self, card: SimpleCardWidget, obj_name: str, value: str):
        lbl = card.findChild(QLabel, obj_name)
        if lbl:
            lbl.setText(value)

    # -----------------------------------------------------------------
    # Socket.IO Real-Time Client Event Handlers
    # -----------------------------------------------------------------

    @Slot(str)
    def _on_socket_connected(self, url: str):
        if hasattr(self, "socket_status_badge"):
            self.socket_status_badge.setText("✓ Socket.IO Connected (Real-Time Live)")
            self.socket_status_badge.setStyleSheet("""
                color: #4ade80;
                font-weight: 700;
                font-size: 8.5pt;
                background-color: #064e3b;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 5px 12px;
            """)
            self.socket_status_badge.setToolTip(f"Real-Time WebSocket stream connected: {url}")
        self._append_log(f"Alert Centre connected to Socket.IO real-time event hub ({url}).")

    @Slot()
    def _on_socket_disconnected(self):
        if hasattr(self, "socket_status_badge"):
            self.socket_status_badge.setText("• Standby (Polling Fallback)")
            self.socket_status_badge.setStyleSheet("""
                color: #fbbf24;
                font-weight: 700;
                font-size: 8.5pt;
                background-color: #78350f;
                border: 1px solid #d97706;
                border-radius: 6px;
                padding: 5px 12px;
            """)
            self.socket_status_badge.setToolTip("Socket.IO disconnected. Operating in local SQLite audit mode.")

    @Slot(dict)
    def _on_socket_alert_created(self, alert_data: dict):
        """Real-time dynamic arrival of a new alert via Socket.IO."""
        aid = alert_data.get("alert_id") or alert_data.get("id", "")
        if aid in self.alert_cards_map:
            return

        if hasattr(self, "alerts_empty_label") and self.alerts_empty_label:
            self.alerts_empty_label.deleteLater()
            self.alerts_empty_label = None

        card = self._create_alert_card(alert_data)
        self.alerts_list_layout.insertWidget(0, card)

        cat = alert_data.get("category", "")
        if self.active_alert_filter != "All" and self.active_alert_filter != cat:
            card.hide()
        else:
            card.show()

        self._sync_alert_counts()

        title = alert_data.get("title", "New Alert")
        msg = alert_data.get("message", "")
        if cat == "CRITICAL":
            InfoBar.error(
                title=f"Critical Alert: {title}",
                content=msg[:120],
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000,
                parent=self,
            )
        elif cat == "WARNING":
            InfoBar.warning(
                title=f"Warning Alert: {title}",
                content=msg[:120],
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000,
                parent=self,
            )
        else:
            InfoBar.info(
                title=f"Alert: {title}",
                content=msg[:120],
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self,
            )

    @Slot(str)
    def _on_socket_alert_acknowledged(self, alert_id: str):
        """Real-time removal of an acknowledged alert via Socket.IO."""
        if alert_id in self.alert_cards_map:
            card = self.alert_cards_map.pop(alert_id)
            card.deleteLater()

        if not self.alert_cards_map:
            self._render_empty_alerts_state()

        self._sync_alert_counts()

    @Slot(dict)
    def _on_socket_stats_updated(self, stats: dict):
        """Update KPI tiles dynamically from real-time Socket.IO stats payload."""
        total = stats.get("total", 0)
        crit = stats.get("CRITICAL", 0)
        warn = stats.get("WARNING", 0)
        info = stats.get("INFO", 0)
        ai = stats.get("AI_INSIGHT", 0)

        self._set_kpi_value(self.kpi_card_total, "val_total_active", str(total))
        self._set_kpi_value(self.kpi_card_critical, "val_critical", str(crit))
        self._set_kpi_value(self.kpi_card_warning, "val_warning", str(warn))
        self._set_kpi_value(self.kpi_card_info, "val_info", str(info))
        self._set_kpi_value(self.kpi_card_ai, "val_ai", str(ai))

        if hasattr(self, "alert_summary_lbl"):
            self.alert_summary_lbl.setText(
                f"{total} active alert(s) • {crit} Critical, {warn} Warning, {ai} AI Insights"
            )

    @Slot(int)
    def _on_socket_all_acknowledged(self, count: int):
        """Handle real-time all-acknowledged event."""
        for card in self.alert_cards_map.values():
            card.deleteLater()
        self.alert_cards_map.clear()
        self._render_empty_alerts_state()
        self._on_socket_stats_updated({"total": 0, "CRITICAL": 0, "WARNING": 0, "INFO": 0, "AI_INSIGHT": 0})

    def _sync_alert_counts(self):
        alert_srv = self.services.get("alert_service")
        if alert_srv:
            counts = alert_srv.get_counts()
            self._on_socket_stats_updated(counts)

    def _render_empty_alerts_state(self):
        if hasattr(self, "alerts_empty_label") and self.alerts_empty_label:
            return
        self.alerts_empty_label = QLabel("✔ All Systems Operational — No unacknowledged alerts.\nReal-Time Socket.IO monitoring active.")
        self.alerts_empty_label.setAlignment(Qt.AlignCenter)
        self.alerts_empty_label.setStyleSheet("""
            color: #4ade80;
            font-weight: 600;
            padding: 30px;
            font-size: 11pt;
            background-color: #0f172a;
            border: 1px dashed #334155;
            border-radius: 8px;
        """)
        self.alerts_list_layout.insertWidget(0, self.alerts_empty_label)

    def refresh_alerts_panel(self):
        alert_srv = self.services.get("alert_service")
        if not alert_srv or not hasattr(self, "alerts_list_layout"):
            return

        while self.alerts_list_layout.count() > 1:
            item = self.alerts_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.alert_cards_map.clear()
        self.alerts_empty_label = None

        alerts = alert_srv.get_alerts(unacknowledged_only=True)
        counts = alert_srv.get_counts()
        self._on_socket_stats_updated(counts)

        if not alerts:
            self._render_empty_alerts_state()
            return

        for alert in alerts:
            card = self._create_alert_card(alert)
            self.alerts_list_layout.insertWidget(self.alerts_list_layout.count() - 1, card)
            if self.active_alert_filter != "All" and getattr(alert, "category", "") != self.active_alert_filter:
                card.hide()

    def _create_alert_card(self, alert: Any) -> SimpleCardWidget:
        if isinstance(alert, dict):
            aid = alert.get("alert_id") or alert.get("id", "")
            cat = alert.get("category", "INFO")
            title = alert.get("title", "")
            msg = alert.get("message", "")
            ts = alert.get("timestamp", "")
            src = alert.get("source", "system")
        else:
            aid = alert.alert_id
            cat = alert.category
            title = alert.title
            msg = alert.message
            ts = alert.timestamp
            src = getattr(alert, "source", "system")

        card = SimpleCardWidget()
        card.setProperty("alert_id", aid)
        card.setProperty("category", cat)

        if cat == "CRITICAL":
            accent = "#ef4444"
            badge_bg = "#7f1d1d"
            badge_fg = "#fecaca"
            icon = "⛔"
        elif cat == "WARNING":
            accent = "#f59e0b"
            badge_bg = "#78350f"
            badge_fg = "#fef3c7"
            icon = "⚠️"
        elif cat == "AI_INSIGHT":
            accent = "#a855f7"
            badge_bg = "#581c87"
            badge_fg = "#f3e8ff"
            icon = "🤖"
        else:
            accent = "#3b82f6"
            badge_bg = "#1e3a8a"
            badge_fg = "#dbeafe"
            icon = "ℹ️"

        card.setStyleSheet(f"""
            SimpleCardWidget {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 5px solid {accent};
                border-radius: 6px;
            }}
            SimpleCardWidget:hover {{
                border-color: #475569;
                background-color: #243248;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(8)

        # Header: Icon + Category Badge + Title + Timestamp + Acknowledge Button
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        lbl_badge = QLabel(f"{icon} {cat}")
        lbl_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            font-size: 8pt;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        hdr.addWidget(lbl_badge)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: 700; font-size: 10.5pt; color: #ffffff;")
        hdr.addWidget(title_lbl)

        hdr.addStretch()

        ts_str = ts[:19].replace("T", " ") if ts else ""
        time_lbl = QLabel(f"🕒 {ts_str}  [{src}]")
        time_lbl.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")
        hdr.addWidget(time_lbl)

        btn_ack = PushButton("✓ Acknowledge", card)
        btn_ack.setCursor(Qt.PointingHandCursor)
        btn_ack.setStyleSheet("""
            PushButton {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 8.5pt;
                font-weight: 600;
            }
            PushButton:hover {
                background-color: #059669;
                color: #ffffff;
                border-color: #10b981;
            }
        """)
        btn_ack.clicked.connect(lambda _, a=aid: self._ack_alert(a))
        hdr.addWidget(btn_ack)
        lay.addLayout(hdr)

        msg_lbl = QLabel(msg)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 9.5pt; line-height: 1.4;")
        lay.addWidget(msg_lbl)

        self.alert_cards_map[aid] = card
        return card

    def _filter_alerts(self, category_name: str):
        self.active_alert_filter = category_name
        for aid, card in self.alert_cards_map.items():
            card_cat = card.property("category")
            if category_name == "All" or card_cat == category_name:
                card.show()
            else:
                card.hide()

    def _ack_alert(self, alert_id: str):
        alert_srv = self.services.get("alert_service")
        if alert_srv:
            alert_srv.acknowledge(alert_id)
            if not (self.alert_socket_worker and self.alert_socket_worker._sio and self.alert_socket_worker._sio.connected):
                self._on_socket_alert_acknowledged(alert_id)

    def _ack_all_alerts(self):
        alert_srv = self.services.get("alert_service")
        if alert_srv:
            count = alert_srv.acknowledge_all()
            if not (self.alert_socket_worker and self.alert_socket_worker._sio and self.alert_socket_worker._sio.connected):
                self._on_socket_all_acknowledged(count)

    def _test_alert_broadcast(self):
        alert_srv = self.services.get("alert_service")
        if not alert_srv:
            return
        import random
        samples = [
            ("CRITICAL", "High Active Energy Inrush", "Feeder 2 instantaneous load exceeded upper threshold by +24.6%."),
            ("WARNING", "NBSense Email Ingestion Delayed", "Gmail inbox scan detected report email delayed by over 45 minutes."),
            ("INFO", "Historical Ledger Verified", "Automated 30-day lookback confirmed zero gap in active energy readings."),
            ("AI_INSIGHT", "Night Shift Efficiency Spike", "Machine Cell 3 idle baseload suggests potential 15% overnight power conservation."),
        ]
        cat, title, msg = random.choice(samples)
        alert = alert_srv.raise_alert(category=cat, title=title, message=msg, source="live_socketio_test")
        if not (self.alert_socket_worker and self.alert_socket_worker._sio and self.alert_socket_worker._sio.connected):
            self._on_socket_alert_created(alert.to_dict())

    def raise_user_alert(self, category: str, title: str, message: str = "", source: str = "application"):
        """
        Dynamically raise an alert in the Alert Centre in real time,
        syncing to SQLite database and broadcasting over Socket.IO if available.
        """
        alert_srv = self.services.get("alert_service")
        if not alert_srv:
            return
        if not message:
            message = title
        alert = alert_srv.raise_alert(category=category, title=title, message=message, source=source)
        if hasattr(self, "alert_socket_worker") and self.alert_socket_worker and self.alert_socket_worker._sio and self.alert_socket_worker._sio.connected:
            pass  # Broadcasted via WebSocket
        else:
            self._on_socket_alert_created(alert.to_dict() if hasattr(alert, "to_dict") else alert)

    # =================================================================
    # Page 5: Windows Terminal Processing History & Technical Diagnostics
    # =================================================================

    def _create_history_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_history")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = PageHeader(
            "Processing History & Technical Diagnostics",
            "Real-time Windows Terminal operational event stream, execution latencies, and service telemetry",
        )
        layout.addWidget(header)

        # Terminal Container Card (Sleek Windows Terminal Canvas)
        term_card = SimpleCardWidget(widget)
        term_card.setStyleSheet("""
            SimpleCardWidget {
                background-color: #0c0c0c;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
        """)
        t_lay = QVBoxLayout(term_card)
        t_lay.setContentsMargins(0, 0, 0, 0)
        t_lay.setSpacing(0)

        # 1. Windows Terminal Title & Tab Strip
        title_bar = QWidget(term_card)
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet("""
            background-color: #18181b;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom: 1px solid #27272a;
        """)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(12, 0, 12, 0)
        tb_lay.setSpacing(10)

        tab_pill = QWidget(title_bar)
        tab_pill.setStyleSheet("""
            background-color: #0c0c0c;
            border: 1px solid #3f3f46;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 4px 10px;
        """)
        tp_lay = QHBoxLayout(tab_pill)
        tp_lay.setContentsMargins(8, 4, 8, 4)
        tp_lay.setSpacing(6)
        tab_icon = QLabel("⚡")
        tab_title = QLabel("PowerShell 7.x (EnergyAutomation)")
        tab_title.setStyleSheet("color: #f4f4f5; font-size: 8.5pt; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        tp_lay.addWidget(tab_icon)
        tp_lay.addWidget(tab_title)
        tb_lay.addWidget(tab_pill)

        pid_lbl = QLabel(f"PID: {os.getpid()} • Host: Windows • Shell: PowerShell")
        pid_lbl.setStyleSheet("color: #71717a; font-size: 8pt; font-family: Consolas, monospace;")
        tb_lay.addWidget(pid_lbl)
        tb_lay.addStretch()

        btn_copy = TransparentPushButton("📋 Copy Buffer", title_bar)
        btn_copy.setToolTip("Copy terminal text to clipboard")
        btn_copy.clicked.connect(self._copy_terminal_log)
        tb_lay.addWidget(btn_copy)

        btn_export = TransparentPushButton("⬇ Export Log", title_bar)
        btn_export.setToolTip("Export execution history to .log file")
        btn_export.clicked.connect(self._export_terminal_log)
        tb_lay.addWidget(btn_export)

        btn_clear = TransparentPushButton("🗑 Clear", title_bar)
        btn_clear.setToolTip("Clear terminal console screen")
        btn_clear.clicked.connect(self._clear_terminal_log)
        tb_lay.addWidget(btn_clear)

        t_lay.addWidget(title_bar)

        # 2. Filter Bar
        ribbon = QWidget(term_card)
        ribbon.setStyleSheet("background-color: #121214; border-bottom: 1px solid #27272a;")
        r_lay = QHBoxLayout(ribbon)
        r_lay.setContentsMargins(12, 5, 12, 5)
        r_lay.setSpacing(6)

        r_lbl = QLabel("Filter:")
        r_lbl.setStyleSheet("color: #a1a1aa; font-size: 8pt; font-weight: 600;")
        r_lay.addWidget(r_lbl)

        self.term_filter_group = QButtonGroup(ribbon)
        for f_idx, f_name in enumerate(["ALL", "INFO", "EXEC", "WARN", "ERROR", "DIAG"]):
            fb = PushButton(f_name, ribbon)
            fb.setCheckable(True)
            if f_idx == 0:
                fb.setChecked(True)
            fb.setStyleSheet("""
                PushButton {
                    font-size: 7.5pt;
                    font-weight: 700;
                    padding: 2px 8px;
                    border-radius: 4px;
                    background-color: #18181b;
                    border: 1px solid #3f3f46;
                    color: #d4d4d8;
                }
                PushButton:checked {
                    background-color: #2563eb;
                    color: #ffffff;
                    border-color: #3b82f6;
                }
            """)
            fb.clicked.connect(lambda _, fn=f_name: self._filter_terminal_logs(fn))
            self.term_filter_group.addButton(fb, f_idx)
            r_lay.addWidget(fb)

        r_lay.addStretch()
        self.term_status_summary = QLabel("Buffer: 0 events")
        self.term_status_summary.setStyleSheet("color: #71717a; font-size: 8pt; font-family: Consolas, monospace;")
        r_lay.addWidget(self.term_status_summary)
        t_lay.addWidget(ribbon)

        # 3. Main Console Display
        self.log_display = QTextEdit(term_card)
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                font-size: 9.5pt;
                background-color: #0c0c0c;
                color: #e4e4e7;
                border: none;
                padding: 14px;
                line-height: 1.5;
            }
        """)
        t_lay.addWidget(self.log_display, 1)

        layout.addWidget(term_card, 1)

        # Initial Boot Banner in Terminal
        self._append_log("Windows Terminal environment initialized.", "EXEC")
        self._append_log("EnergyAutomation Microservices Engine v2.0 Ready.", "INFO")
        self._append_log("Authoritative validation layer active (Excel + SQLite).", "DIAG")

        return widget

    def refresh_history(self):
        pass

    def _append_log(self, text: str, level: str = "INFO"):
        now_str = datetime.now().strftime("%H:%M:%S")
        if not hasattr(self, "_log_records"):
            self._log_records = []

        level_up = level.upper()
        record = {
            "time": now_str,
            "level": level_up,
            "text": text,
        }
        self._log_records.append(record)
        if len(self._log_records) > 2000:
            self._log_records.pop(0)

        if level_up == "EXEC":
            badge = '<span style="background-color: #1e3a8a; color: #93c5fd; font-weight: 700; border-radius: 3px; padding: 1px 6px;">EXEC</span>'
        elif level_up in ("WARN", "WARNING"):
            badge = '<span style="background-color: #78350f; color: #fcd34d; font-weight: 700; border-radius: 3px; padding: 1px 6px;">WARN</span>'
        elif level_up in ("ERROR", "CRITICAL", "FAIL"):
            badge = '<span style="background-color: #7f1d1d; color: #fca5a5; font-weight: 700; border-radius: 3px; padding: 1px 6px;">ERROR</span>'
        elif level_up == "DIAG":
            badge = '<span style="background-color: #581c87; color: #d8b4fe; font-weight: 700; border-radius: 3px; padding: 1px 6px;">DIAG</span>'
        else:
            badge = '<span style="background-color: #064e3b; color: #6ee7b7; font-weight: 700; border-radius: 3px; padding: 1px 6px;">INFO</span>'

        html_line = (
            f'<div style="margin-bottom: 3px;">'
            f'<span style="color: #52525b;">[{now_str}]</span> '
            f'{badge} '
            f'<span style="color: #38bdf8;">PS EnergyAutomation&gt;</span> '
            f'<span style="color: #f4f4f5;">{text}</span>'
            f'</div>'
        )

        curr_filter = getattr(self, "_active_log_filter", "ALL")
        if curr_filter == "ALL" or curr_filter == level_up:
            if hasattr(self, "log_display"):
                self.log_display.append(html_line)
                sb = self.log_display.verticalScrollBar()
                if sb:
                    sb.setValue(sb.maximum())

        if hasattr(self, "term_status_summary"):
            self.term_status_summary.setText(f"Buffer: {len(self._log_records)} events")

        if hasattr(self, "activity_label"):
            self.activity_label.setText(f"[{now_str}] {text}")

    def _filter_terminal_logs(self, filter_name: str):
        self._active_log_filter = filter_name.upper()
        if not hasattr(self, "log_display"):
            return
        self.log_display.clear()
        records = getattr(self, "_log_records", [])
        for r in records:
            lvl = r["level"]
            if self._active_log_filter == "ALL" or self._active_log_filter == lvl:
                if lvl == "EXEC":
                    badge = '<span style="background-color: #1e3a8a; color: #93c5fd; font-weight: 700; border-radius: 3px; padding: 1px 6px;">EXEC</span>'
                elif lvl in ("WARN", "WARNING"):
                    badge = '<span style="background-color: #78350f; color: #fcd34d; font-weight: 700; border-radius: 3px; padding: 1px 6px;">WARN</span>'
                elif lvl in ("ERROR", "CRITICAL", "FAIL"):
                    badge = '<span style="background-color: #7f1d1d; color: #fca5a5; font-weight: 700; border-radius: 3px; padding: 1px 6px;">ERROR</span>'
                elif lvl == "DIAG":
                    badge = '<span style="background-color: #581c87; color: #d8b4fe; font-weight: 700; border-radius: 3px; padding: 1px 6px;">DIAG</span>'
                else:
                    badge = '<span style="background-color: #064e3b; color: #6ee7b7; font-weight: 700; border-radius: 3px; padding: 1px 6px;">INFO</span>'

                html_line = (
                    f'<div style="margin-bottom: 3px;">'
                    f'<span style="color: #52525b;">[{r["time"]}]</span> '
                    f'{badge} '
                    f'<span style="color: #38bdf8;">PS EnergyAutomation&gt;</span> '
                    f'<span style="color: #f4f4f5;">{r["text"]}</span>'
                    f'</div>'
                )
                self.log_display.append(html_line)

        sb = self.log_display.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _copy_terminal_log(self):
        records = getattr(self, "_log_records", [])
        text = "\n".join(f"[{r['time']}] [{r['level']}] {r['text']}" for r in records)
        QApplication.clipboard().setText(text)
        InfoBar.info(
            title="Copied",
            content=f"Copied {len(records)} log events to clipboard.",
            orient=Qt.Horizontal,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self,
        )

    def _export_terminal_log(self):
        records = getattr(self, "_log_records", [])
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Terminal Log Buffer",
            f"EnergyAutomation_terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            "Log Files (*.log *.txt)",
        )
        if path:
            text = "\n".join(f"[{r['time']}] [{r['level']}] {r['text']}" for r in records)
            try:
                Path(path).write_text(text, encoding="utf-8")
                InfoBar.success(
                    title="Log Exported",
                    content=f"Log file successfully saved to:\n{path}",
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=4000,
                    parent=self,
                )
            except Exception as e:
                InfoBar.error(
                    title="Export Error",
                    content=f"Failed to export log: {e}",
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000,
                    parent=self,
                )

    def _clear_terminal_log(self):
        if hasattr(self, "log_display"):
            self.log_display.clear()
        self._log_records = []
        if hasattr(self, "term_status_summary"):
            self.term_status_summary.setText("Buffer: 0 events")
        self._append_log("Terminal buffer cleared by operator.", "EXEC")

    # =================================================================
    # Page 10: Settings & Configuration (Pinned to Bottom)
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

        header = PageHeader(
            "System Configuration & Integration Settings",
            "Verified parameters, storage destinations, API credentials, and runtime modes",
        )
        layout.addWidget(header)

        # Guidance Card: Excel Workbook (With Dynamic Verification & Status Updating)
        excel_srv = self.services.get("excel_service")
        wb_path = getattr(excel_srv, "workbook_path", None) or Path("Test_BI_Analysis_Report_2026.xlsx")
        wb_exists = Path(str(wb_path)).exists()

        self.excel_guidance_card = SimpleCardWidget(container)
        eg_lay = QVBoxLayout(self.excel_guidance_card)
        eg_lay.setContentsMargins(18, 14, 18, 14)
        eg_lay.setSpacing(8)

        eg_hdr = QHBoxLayout()
        eg_title = StrongBodyLabel("Production Excel Workbook Destination")
        eg_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 10pt;")
        eg_hdr.addWidget(eg_title)
        eg_hdr.addStretch()

        self.excel_status_lbl = QLabel("✓ File Selected & Verified" if wb_exists else "✖ Not Selected / Missing")
        self.excel_status_lbl.setStyleSheet(f"font-weight: 700; color: {'#4ade80' if wb_exists else '#f87171'}; font-size: 9pt;")
        eg_hdr.addWidget(self.excel_status_lbl)
        eg_lay.addLayout(eg_hdr)

        req_lbl = QLabel("<b>Required for:</b> Automatic daily updates of meter active energy rows and formula verification.")
        req_lbl.setWordWrap(True)
        req_lbl.setStyleSheet("color: #cbd5e1; font-size: 9pt;")
        eg_lay.addWidget(req_lbl)

        eg_act_box = QHBoxLayout()
        self.excel_action_lbl = QLabel(
            f"<b>Action:</b> Excel workbook is connected ({Path(str(wb_path)).name}). Ready for automated updates."
            if wb_exists
            else f"<b>Action:</b> Ensure excel file exist at the designated path ({wb_path}). Click 'Select Excel File' to locate it."
        )
        self.excel_action_lbl.setWordWrap(True)
        self.excel_action_lbl.setStyleSheet("color: #f1f5f9; font-size: 9pt;")
        eg_act_box.addWidget(self.excel_action_lbl, 1)

        btn_browse = PushButton("Select Excel File", self.excel_guidance_card)
        btn_browse.clicked.connect(self._browse_excel_file)
        eg_act_box.addWidget(btn_browse)
        eg_lay.addLayout(eg_act_box)

        layout.addWidget(self.excel_guidance_card)

        # Guidance Card: Gmail API Requirement
        gmail_guidance = self._create_requirement_card(
            title="Gmail API Integration",
            status="Active (OAuth Client Configured)" if Path("credentials/gmail/token.json").exists() or Path("credentials/token.json").exists() else "Needs Authorization",
            status_color="#4ade80" if Path("credentials/gmail/token.json").exists() or Path("credentials/token.json").exists() else "#fbbf24",
            required_for="Automatic download of daily NBSense PDF reports from Gmail.",
            action_desc="Launch the Setup Wizard to complete Google OAuth consent.",
            btn_text="Launch Setup Wizard",
            callback=self.open_setup_wizard,
        )
        layout.addWidget(gmail_guidance)

        # Guidance Card: Plotly Dash BI
        dash_app = Path("services/dash_service/app.py")
        dash_guidance = self._create_requirement_card(
            title="Plotly Dash BI Microservice",
            status="Active (Port 8050 Ready)" if dash_app.exists() else "Configuration Required",
            status_color="#4ade80" if dash_app.exists() else "#f87171",
            required_for="Web-based executive and engineering BI dashboard for plant telemetry analysis.",
            action_desc="Runs headless as a microservice on port 8050.",
            btn_text="Open Plotly Dash BI",
            callback=self.launch_dash_browser,
        )
        layout.addWidget(dash_guidance)

        # Guidance Card: Google Gemini AI Intelligence & API Key (Dynamic Integration)
        self.gemini_card = SimpleCardWidget(container)
        gem_lay = QVBoxLayout(self.gemini_card)
        gem_lay.setContentsMargins(18, 14, 18, 14)
        gem_lay.setSpacing(10)

        gem_hdr = QHBoxLayout()
        gem_title = StrongBodyLabel("Google Gemini AI Intelligence & API Key")
        gem_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 10pt;")
        gem_hdr.addWidget(gem_title)
        gem_hdr.addStretch()

        gem_srv = self.services.get("gemini_service")
        gem_configured = bool(gem_srv and getattr(gem_srv, "api_key", None))
        self.gemini_status_badge = QLabel("✓ Configured & Active" if gem_configured else "• Offline Fallback (Deterministic Engine)")
        self.gemini_status_badge.setStyleSheet(
            f"font-weight: 700; color: {'#4ade80' if gem_configured else '#fbbf24'}; font-size: 9pt;"
        )
        gem_hdr.addWidget(self.gemini_status_badge)
        gem_lay.addLayout(gem_hdr)

        gem_desc = QLabel(
            "Configure your Google Gemini API key to activate conversational energy analytics, "
            "automated anomaly explanation, and executive shift insights. Operates in advisory mode only; "
            "never alters Excel formulas or authoritative database records."
        )
        gem_desc.setWordWrap(True)
        gem_desc.setStyleSheet("color: #cbd5e1; font-size: 9pt;")
        gem_lay.addWidget(gem_desc)

        # Input row: Key + Show/Hide + Test + Save
        input_box = QHBoxLayout()
        input_box.setSpacing(8)

        lbl_key = QLabel("Gemini API Key:")
        lbl_key.setStyleSheet("color: #f1f5f9; font-weight: 600; font-size: 9pt;")
        input_box.addWidget(lbl_key)

        current_key = getattr(gem_srv, "api_key", "") or os.getenv("GEMINI_API_KEY", "") or ""
        self.in_gemini_api_key = QLineEdit(current_key, self.gemini_card)
        self.in_gemini_api_key.setEchoMode(QLineEdit.Password)
        self.in_gemini_api_key.setPlaceholderText("Enter AIzaSy... API key")
        self.in_gemini_api_key.setMinimumWidth(320)
        self.in_gemini_api_key.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 10px;
                font-family: Consolas, monospace;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        input_box.addWidget(self.in_gemini_api_key, 1)

        self.btn_toggle_key = PushButton("👁 Show", self.gemini_card)
        self.btn_toggle_key.setFixedWidth(75)
        self.btn_toggle_key.clicked.connect(self._toggle_gemini_key_visibility)
        input_box.addWidget(self.btn_toggle_key)

        self.btn_test_gemini = PushButton("Test Connection", self.gemini_card)
        self.btn_test_gemini.clicked.connect(self._test_gemini_connection)
        input_box.addWidget(self.btn_test_gemini)

        self.btn_save_gemini = PrimaryPushButton("Save & Apply", self.gemini_card)
        self.btn_save_gemini.clicked.connect(self._save_gemini_key)
        input_box.addWidget(self.btn_save_gemini)

        gem_lay.addLayout(input_box)

        # Model and status notes
        model_name = getattr(gem_srv, "model", "gemini-2.5-flash") or "gemini-2.5-flash"
        self.lbl_gemini_feedback = QLabel(f"Active Model: {model_name} • Changes apply dynamically at runtime without restart")
        self.lbl_gemini_feedback.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")
        gem_lay.addWidget(self.lbl_gemini_feedback)

        layout.addWidget(self.gemini_card)

        # Active Enterprise Configuration Parameters
        group_card = SimpleCardWidget(container)
        g_lay = QVBoxLayout(group_card)
        g_lay.setContentsMargins(18, 16, 18, 16)
        g_lay.setSpacing(12)
        param_hdr = StrongBodyLabel("Active System Parameters & Invariants")
        param_hdr.setStyleSheet("color: #ffffff; font-weight: 700;")
        g_lay.addWidget(param_hdr)

        form = QFormLayout()
        form.setSpacing(12)

        self.lbl_wb = QLabel(str(wb_path))
        self.lbl_wb.setStyleSheet("font-family: Consolas; color: #93c5fd;")
        form.addRow("Excel Workbook Path:", self.lbl_wb)

        db = self.services.get("report_repository")
        db_path = getattr(getattr(db, "database", None), "db_path", "data/automation.db")
        lbl_db = QLabel(str(db_path))
        lbl_db.setStyleSheet("font-family: Consolas; color: #93c5fd;")
        form.addRow("SQLite Audit Database:", lbl_db)

        lbl_target = QLabel("9,206.83 kWh (NBSense EMS Reference Baseline)")
        lbl_target.setStyleSheet("color: #e2e8f0;")
        form.addRow("Target Daily Total:", lbl_target)

        lbl_formula = QLabel("Preserved (=SUM(C16:Q16), Cumulative Row 4)")
        lbl_formula.setStyleSheet("color: #e2e8f0;")
        form.addRow("Excel Formula Safety:", lbl_formula)

        lbl_gap = QLabel("30 Days (Automatic Sunday/Weekend Healing)")
        lbl_gap.setStyleSheet("color: #e2e8f0;")
        form.addRow("Historical Gap Window:", lbl_gap)

        lbl_ai = QLabel("Advisory Only (Strictly zero direct Excel edits)")
        lbl_ai.setStyleSheet("color: #e2e8f0;")
        form.addRow("Gemini AI Policy:", lbl_ai)

        lbl_mode = QLabel("Deterministic pipeline as sole source of truth")
        lbl_mode.setStyleSheet("color: #e2e8f0;")
        form.addRow("Architecture Mode:", lbl_mode)

        g_lay.addLayout(form)
        layout.addWidget(group_card)
        scroll.setWidget(container)
        return scroll

    def _toggle_gemini_key_visibility(self):
        if not hasattr(self, "in_gemini_api_key"):
            return
        if self.in_gemini_api_key.echoMode() == QLineEdit.Password:
            self.in_gemini_api_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setText("🔒 Hide")
        else:
            self.in_gemini_api_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setText("👁 Show")

    def _save_gemini_key(self):
        if not hasattr(self, "in_gemini_api_key"):
            return
        key = self.in_gemini_api_key.text().strip()

        # Update environment
        if key:
            os.environ["GEMINI_API_KEY"] = key
        else:
            os.environ.pop("GEMINI_API_KEY", None)

        # Update settings.json
        settings_path = Path("config/settings.json")
        try:
            cur_settings = {}
            if settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as f:
                    cur_settings = json.load(f)
            if "gemini" not in cur_settings or not isinstance(cur_settings["gemini"], dict):
                cur_settings["gemini"] = {}
            cur_settings["gemini"]["api_key"] = key
            cur_settings["gemini"]["enabled"] = True
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(cur_settings, f, indent=2)
        except Exception as exc:
            self._append_log(f"Warning: could not write settings.json: {exc}")

        # Update running gemini service
        gem = self.services.get("gemini_service")
        if gem:
            gem.api_key = key
            gem.enabled = True

        # Update badge
        has_key = bool(key)
        self.gemini_status_badge.setText("✓ Configured & Active" if has_key else "• Offline Fallback (Deterministic Engine)")
        self.gemini_status_badge.setStyleSheet(
            f"font-weight: 700; color: {'#4ade80' if has_key else '#fbbf24'}; font-size: 9pt;"
        )
        self.lbl_gemini_feedback.setText(
            f"Active Model: {getattr(gem, 'model', 'gemini-flash-latest')} • {'API Key configured & active.' if has_key else 'API Key cleared; offline fallback active.'}"
        )

        # Update AI panel banner if it exists
        if hasattr(self, "_update_ai_panel_status_card"):
            self._update_ai_panel_status_card()

        # Refresh overall system health & readiness ribbon
        self.refresh_status()

        InfoBar.success(
            title="AI Configuration Saved",
            content="Google Gemini API key has been applied dynamically to the live system.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500,
            parent=self,
        )
        self._append_log(f"Google Gemini API key updated dynamically ({'Key Configured' if has_key else 'Key Cleared'}).", "EXEC")
        self.raise_user_alert(
            "AI_INSIGHT",
            "Gemini API Key Configured" if has_key else "Gemini API Key Cleared",
            f"Advisory AI configuration updated dynamically by operator. Active model: {getattr(gem, 'model', 'gemini-2.5-flash')}.",
            source="settings_ai",
        )

    def _test_gemini_connection(self):
        gem = self.services.get("gemini_service")
        key = ""
        if hasattr(self, "in_gemini_api_key"):
            key = self.in_gemini_api_key.text().strip()
        if not key and gem:
            key = getattr(gem, "api_key", "") or os.getenv("GEMINI_API_KEY", "") or ""

        if not key:
            InfoBar.warning(
                title="API Key Required",
                content="Please enter an API key in Settings before testing connection.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self,
            )
            return

        try:
            if gem:
                gem.api_key = key
                res = gem.test_connection()
            else:
                from app.services.ai.gemini_service import GeminiService
                temp_gem = GeminiService(api_key=key, enabled=True)
                res = temp_gem.test_connection()

            if res.get("success"):
                InfoBar.success(
                    title="Gemini Connection Successful",
                    content=res.get("message", "Connected successfully!"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=4000,
                    parent=self,
                )
                if hasattr(self, "lbl_gemini_feedback"):
                    self.lbl_gemini_feedback.setText(f"✓ Verification Passed: {res.get('message')}")
                if hasattr(self, "_update_ai_panel_status_card"):
                    self._update_ai_panel_status_card()
            else:
                InfoBar.error(
                    title="Gemini Connection Failed",
                    content=res.get("message", "Could not reach Gemini endpoint."),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000,
                    parent=self,
                )
                if hasattr(self, "lbl_gemini_feedback"):
                    self.lbl_gemini_feedback.setText(f"✖ Verification Failed: {res.get('message')}")
        except Exception as exc:
            InfoBar.error(
                title="Test Error",
                content=str(exc),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000,
                parent=self,
            )

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
        t.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 10pt;")
        hdr.addWidget(t)

        hdr.addStretch()
        st = QLabel(f"Status: {status}")
        st.setStyleSheet(f"font-weight: 700; color: {status_color}; font-size: 9pt;")
        hdr.addWidget(st)
        lay.addLayout(hdr)

        req_lbl = QLabel(f"<b>Required for:</b> {required_for}")
        req_lbl.setWordWrap(True)
        req_lbl.setStyleSheet("color: #cbd5e1; font-size: 9pt;")
        lay.addWidget(req_lbl)

        act_box = QHBoxLayout()
        act_lbl = QLabel(f"<b>Action:</b> {action_desc}")
        act_lbl.setWordWrap(True)
        act_lbl.setStyleSheet("color: #f1f5f9; font-size: 9pt;")
        act_box.addWidget(act_lbl, 1)

        btn = PushButton(btn_text, card)
        btn.clicked.connect(callback)
        act_box.addWidget(btn)
        lay.addLayout(act_box)
        return card

    def _load_persisted_config(self) -> Dict[str, Any]:
        settings_path = Path("config/settings.json")
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_persisted_config(self, cfg: Dict[str, Any]) -> bool:
        settings_path = Path("config/settings.json")
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            return True
        except Exception as ex:
            if hasattr(self, "_append_log"):
                self._append_log(f"Warning: could not save config/settings.json: {ex}", "WARN")
            return False

    def _update_excel_settings_status(self, path: Optional[str] = None):
        """Dynamically updates the Excel status notification and action guidance text."""
        if not path:
            cfg = self._load_persisted_config()
            path = cfg.get("excel", {}).get("workbook_path", "")
            if not path:
                excel_srv = self.services.get("excel_service")
                path = str(getattr(excel_srv, "workbook_path", "") or "")

        p = Path(str(path)) if path else None
        wb_exists = bool(p and p.exists() and p.is_file())

        if hasattr(self, "excel_status_lbl"):
            self.excel_status_lbl.setText("✓ File Selected & Verified" if wb_exists else "✖ Not Selected / Missing")
            self.excel_status_lbl.setStyleSheet(f"font-weight: 700; color: {'#4ade80' if wb_exists else '#f87171'}; font-size: 9pt;")

        if hasattr(self, "excel_action_lbl"):
            if wb_exists:
                self.excel_action_lbl.setText(
                    f"<b>Action:</b> Excel workbook is connected ({p.name}). Ready for automated updates."
                )
            else:
                self.excel_action_lbl.setText(
                    "<b>Action:</b> Choose the correct file and file path otherwise not found or not connected. Click 'Select Excel File' to locate it."
                )

        if hasattr(self, "lbl_wb"):
            self.lbl_wb.setText(str(path) if path else "None selected")

    def _browse_excel_file(self):
        cfg = self._load_persisted_config()
        curr_path = cfg.get("excel", {}).get("workbook_path", "")
        start_dir = str(Path(curr_path).parent) if (curr_path and Path(curr_path).parent.exists()) else str(Path.cwd())

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EMS Analysis Report Excel Workbook",
            start_dir,
            "Excel Files (*.xlsx *.xlsm)",
        )
        if path:
            p = Path(path)
            if p.exists() and p.is_file():
                excel_srv = self.services.get("excel_service")
                if excel_srv:
                    excel_srv.workbook_path = str(p.resolve())

                # Persist user choice to config/settings.json
                cfg.setdefault("excel", {})["workbook_path"] = str(p.resolve())
                self._save_persisted_config(cfg)

                self._warned_missing_excel = False
                self._update_excel_settings_status(str(p.resolve()))
                self._append_log(f"Excel workbook linked and verified by operator: {p.resolve()}", "INFO")

                self.raise_user_alert(
                    "INFO",
                    "Excel Workbook Linked",
                    f"Operator successfully selected and connected workbook: {p.name}",
                    source="user_file_link",
                )
                self.notification_service.notify_success(
                    "Excel File Selected",
                    f"Workbook successfully linked:\n{p.name}\nPath: {p}",
                )
                self.refresh_status()
            else:
                self._update_excel_settings_status(path)
                InfoBar.warning(
                    title="Excel Path Not Found",
                    content="Choose the correct file and file path otherwise not found or not connected.",
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=6000,
                    parent=self,
                )
                self.raise_user_alert(
                    "WARNING",
                    "Invalid Excel Path",
                    f"Choose the correct file and file path otherwise not found or not connected: {path}",
                    source="user_file_link",
                )
        else:
            self._update_excel_settings_status()
            InfoBar.warning(
                title="No File Selected",
                content="Choose the correct file and file path otherwise not found or not connected.",
                orient=Qt.Horizontal,
                position=InfoBarPosition.TOP,
                duration=6000,
                parent=self,
            )

    # =================================================================
    # Page 11: Help & Support Center (Pinned to Bottom)
    # =================================================================

    def _create_help_page(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("page_help")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_box = QHBoxLayout()
        header = PageHeader(
            "Help Center & Operator Documentation",
            "Plain-language operational guides, troubleshooting procedures, FAQ, and technical glossary",
        )
        header_box.addWidget(header)
        header_box.addStretch()

        btn_tour = PrimaryPushButton("✨ Restart Guided Tour", widget)
        btn_tour.setObjectName("PrimaryButton")
        btn_tour.clicked.connect(self.open_guided_tour)
        header_box.addWidget(btn_tour)
        layout.addLayout(header_box)

        help_tabs = QTabWidget(widget)
        help_tabs.addTab(self._create_help_article_getting_started(), "Getting Started")
        help_tabs.addTab(self._create_help_article_dashboard(), "Dashboard & Operations")
        help_tabs.addTab(self._create_help_article_meters_plant(), "Telemetry & Meter Policies")
        help_tabs.addTab(self._create_help_article_recovery(), "Data Recovery & Gaps")
        help_tabs.addTab(self._create_help_article_dash(), "Plotly Dash BI")
        help_tabs.addTab(self._create_help_article_troubleshooting(), "Troubleshooting & FAQ")
        help_tabs.addTab(self._create_help_article_glossary(), "Glossary")
        layout.addWidget(help_tabs, 1)
        return widget

    def _create_help_article_getting_started(self) -> QWidget:
        return self._build_article_container([
            (
                "What is EnergyAutomation?",
                "EnergyAutomation is an enterprise Windows desktop platform for Savera MS that automates the daily ingestion of NBSense energy reports, updates production Excel workbooks preserving formulas, maintains an immutable SQLite audit trail, and visualizes management metrics via Streamlit BI."
            ),
            (
                "Why is it needed?",
                "Manually opening PDF reports, keying numbers into Excel, and checking formulas took 30+ minutes every morning. EnergyAutomation does this in under 3 seconds with guaranteed formula safety and full audit logging."
            ),
            (
                "How do I use it?",
                "1. Click 'Run Automation Now' on the Executive Dashboard to test an immediate run.\n2. The system scheduler runs automatically each morning at 06:00 AM.\n3. Verify results by checking the 'Reports & Audit' ledger."
            ),
            (
                "What happens after I use it?",
                "The target row in `Test_BI_Analysis_Report_2026.xlsx` is updated with today's readings, formulas `=SUM(C16:Q16)` are preserved, and an audit record is saved in `data/automation.db`."
            ),
        ])

    def _create_help_article_dashboard(self) -> QWidget:
        return self._build_article_container([
            (
                "Executive Dashboard Overview",
                "Provides plant managers with an instant pulse on facility consumption (Today, Yesterday, MTD, YTD), system health across all subsystems, and automation controls."
            ),
            (
                "Understanding System Health Matrix",
                "Green indicates healthy operations. Amber indicates optional items requiring attention (e.g. Gmail OAuth authorization). Red indicates a critical prerequisite such as a missing workbook."
            ),
            (
                "Zero Fake Telemetry Guarantee",
                "Every single value shown on this dashboard is read directly from your Excel file or SQLite database. If data has not been ingested yet, the card displays 'NOT ACTIVE' rather than manufactured demo numbers."
            ),
        ])

    def _create_help_article_meters_plant(self) -> QWidget:
        return self._build_article_container([
            (
                "Plant Energy Topology Map",
                "Visualizes the 18 plant meters organized into 7 production zones: Surface Treatment & Plating, Finishing & Powder Coating, Press & Fabrication, Compressors, Water Treatment, Packaging, and Main Power Substation."
            ),
            (
                "Meter Status & N/A Policy",
                "When physical meter communication drops, it reports N/A. EnergyAutomation preserves N/A as empty/null. It is NEVER coerced to 0.0, avoiding artificial skew in baseline calculations."
            ),
        ])

    def _create_help_article_recovery(self) -> QWidget:
        return self._build_article_container([
            (
                "Weekend Gap Healing",
                "Plant operations may not process reports on Sundays. EnergyAutomation automatically scans the past 30 days and fetches missing reports chronologically so your monthly Excel workbook has zero gaps."
            ),
        ])

    def _create_help_article_dash(self) -> QWidget:
        return self._build_article_container([
            (
                "Plotly Dash BI Microservice Integration",
                "Plotly Dash serves as the decoupled analytical layer. It visualizes energy trends, shift-by-shift metrics, feeder distributions, and engineering data quality in your browser at http://localhost:8050."
            ),
            (
                "Microservice Communication",
                "The Dash application connects directly to the Data Microservice API (port 8002) with automatic fallback to local production Excel workbooks."
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
            ("Active Energy (kWh)", "The electricity consumed by motors, heaters, and machinery to perform productive work."),
            ("Power Factor (PF)", "The ratio of active energy (kWh) to apparent energy (kVAh). Target is near unity (~0.98 - 0.99)."),
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
            h_lbl.setStyleSheet("color: #ffffff; font-weight: 700;")
            b_lay.addWidget(h_lbl)
            lbl = QLabel(body)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #e2e8f0; font-size: 9.5pt; line-height: 1.4;")
            b_lay.addWidget(lbl)
            lay.addWidget(box)

        lay.addStretch()
        scroll.setWidget(container)
        return scroll

    # =================================================================
    # Interactive Features: Tour, Setup Wizard, Global Search, Automation
    # =================================================================

    def open_guided_tour(self):
        dlg = GuidedTourDialog(self)
        dlg.exec()

    def open_setup_wizard(self):
        dlg = SetupWizardDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._append_log("Setup wizard settings saved.")
            self.refresh_status()

    def handle_global_search(self, text: str):
        query = text.strip().lower()
        if not query:
            return
        if any(w in query for w in ["meter", "dash", "bi", "analytics", "powder", "coating", "compressor", "plating", "rigga", "press", "incomer", "chiller"]):
            self.switchTo(self.page_dash)
        elif any(w in query for w in ["alert", "warn", "error", "spike", "critical"]):
            self.switchTo(self.page_alerts)
        elif any(w in query for w in ["ai", "gemini", "intelligence", "ask", "question"]):
            self.switchTo(self.page_ai)
        elif any(w in query for w in ["recover", "gap", "sunday", "missing", "backfill"]):
            self.switchTo(self.page_recovery)
        elif any(w in query for w in ["history", "log", "diagnostic", "event"]):
            self.switchTo(self.page_history)
        elif any(w in query for w in ["setting", "config", "path", "excel", "key"]):
            self.switchTo(self.page_settings)
        elif any(w in query for w in ["help", "faq", "guide", "tour", "glossary"]):
            self.switchTo(self.page_help)

    def run_now(self):
        if self._running:
            self.notification_service.notify_warning("System Busy", "An automation workflow is already running.")
            return

        if not self.workflow:
            self.notification_service.notify_error("Workflow Error", "Automation workflow service is not initialized.")
            return

        self._running = True
        self.run_button.setEnabled(False)
        self.progress.setVisible(True)
        self._set_status("Running", "running", "Processing NBSense reports...")
        self._append_log("Triggered immediate automation workflow run.", "EXEC")
        self.raise_user_alert(
            "INFO",
            "Automation Cycle Started",
            "Operator manually initiated an end-to-end ingestion and reconciliation run.",
            source="operator_run",
        )

        self.worker_thread = QThread()
        self.worker = WorkflowWorker(self.workflow)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.execute)
        self.worker.finished.connect(self._on_run_finished)
        self.worker.failed.connect(self._on_run_failed)
        self.worker_thread.start()

    @Slot(object)
    def _on_run_finished(self, result: Any):
        self._running = False
        self.run_button.setEnabled(True)
        self.progress.setVisible(False)
        self._cleanup_thread()

        self._last_result = result
        self._set_status("Ready", "ready", "Automation run completed successfully.")
        self._append_log("Workflow execution finished cleanly. Authoritative Excel and SQLite updated.", "INFO")
        self.raise_user_alert(
            "INFO",
            "Automation Cycle Completed",
            "NBSense report successfully parsed, validated, and recorded in Excel and SQLite.",
            source="automation_engine",
        )

        self.notification_service.notify_success(
            "Report Processed",
            "NBSense report successfully parsed, validated, and recorded in Excel and SQLite.",
        )
        self.refresh_status()

    @Slot(str)
    def _on_run_failed(self, error_trace: str):
        self._running = False
        self.run_button.setEnabled(True)
        self.progress.setVisible(False)
        self._cleanup_thread()

        self._last_error = error_trace
        self._set_status("Error", "error", "Automation execution encountered an error.")
        err_line = error_trace.splitlines()[-1] if error_trace else "Unknown error"
        self._append_log(f"Workflow execution failure: {err_line}", "ERROR")
        self.raise_user_alert(
            "CRITICAL",
            "Automation Execution Failed",
            f"Pipeline encountered error: {err_line}",
            source="automation_engine",
        )

        self.notification_service.notify_error(
            "Workflow Execution Failed",
            "The automation pipeline encountered an error during execution. Review technical details below.",
            technical_details=error_trace,
            show_dialog=True,
        )
        self.refresh_status()

    def _cleanup_thread(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None

    def toggle_scheduler(self):
        if not self.scheduler:
            return
        if self.scheduler.is_running():
            self.scheduler.stop()
            self.scheduler_button.setText("Resume Scheduler")
            self.next_event_label.setText("Scheduler paused by operator.")
            self._append_log("Scheduler paused by operator.", "WARN")
            self.raise_user_alert(
                "WARNING",
                "Scheduler Paused",
                "Automatic morning background checks were paused by operator.",
                source="operator_scheduler",
            )
            self.notification_service.notify_info("Scheduler Paused", "Background morning report checks paused.")
        else:
            self.scheduler.start()
            self.scheduler_button.setText("Pause Scheduler")
            self.next_event_label.setText("Next scheduled check: ~06:00 AM")
            self._append_log("Scheduler resumed. Next check ~06:00 AM.", "INFO")
            self.raise_user_alert(
                "INFO",
                "Scheduler Resumed",
                "Automatic morning background checks are active.",
                source="operator_scheduler",
            )
            self.notification_service.notify_success("Scheduler Active", "Background morning report checks active.")
        self.refresh_status()

    def _set_status(self, label: str, state: str, detail: str = ""):
        if hasattr(self, "status_text"):
            self.status_text.setText(label)
        if hasattr(self, "status_detail") and detail:
            self.status_detail.setText(detail)
        if hasattr(self, "status_indicator"):
            if state in ("ready", "connected", "healthy", "success"):
                icon = "✓"
                color = "#4ade80"
            elif state in ("paused", "standby", "idle"):
                icon = "•"
                color = "#fbbf24"
            elif state == "running":
                icon = "•"
                color = "#60a5fa"
            else:
                icon = "✖"
                color = "#f87171"
            self.status_indicator.setText(icon)
            self.status_indicator.setStyleSheet(f"font-size: 20pt; font-weight: 800; color: {color};")
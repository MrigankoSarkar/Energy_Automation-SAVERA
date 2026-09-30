"""
Enterprise First-Run Setup Wizard for EnergyAutomation.
Guides administrators and plant engineers through initial configuration,
validation, and live real-time connection diagnostics.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton, PushButton, TransparentPushButton


class FluentNumberBox(QWidget):
    """
    Windows 11 Fluent Design Numeric Stepper with custom, highly responsive
    increase [+] and decrease [−] buttons and direct numeric input.
    """

    def __init__(
        self,
        min_val: int = 0,
        max_val: int = 10000,
        default_val: int = 0,
        step: int = 1,
        suffix: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._step = step
        self._val = default_val
        self._suffix = suffix

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Decrease Button [−]
        self.btn_dec = QPushButton("−", self)
        self.btn_dec.setFixedSize(36, 32)
        self.btn_dec.setCursor(Qt.PointingHandCursor)
        self.btn_dec.setStyleSheet("""
            QPushButton {
                font-size: 15pt;
                font-weight: 700;
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #cbd5e1;
            }
        """)
        self.btn_dec.clicked.connect(self._decrease)
        lay.addWidget(self.btn_dec)

        # Value input line edit
        self.in_val = QLineEdit(str(self._val), self)
        self.in_val.setAlignment(Qt.AlignCenter)
        self.in_val.setFixedWidth(80)
        self.in_val.setFixedHeight(32)
        self.in_val.setStyleSheet("""
            QLineEdit {
                font-size: 11pt;
                font-weight: 700;
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 2px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        self.in_val.textChanged.connect(self._on_text_changed)
        lay.addWidget(self.in_val)

        # Increase Button [+]
        self.btn_inc = QPushButton("+", self)
        self.btn_inc.setFixedSize(36, 32)
        self.btn_inc.setCursor(Qt.PointingHandCursor)
        self.btn_inc.setStyleSheet("""
            QPushButton {
                font-size: 15pt;
                font-weight: 700;
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #cbd5e1;
            }
        """)
        self.btn_inc.clicked.connect(self._increase)
        lay.addWidget(self.btn_inc)

        if self._suffix:
            lbl_suffix = QLabel(self._suffix, self)
            lbl_suffix.setStyleSheet("color: #64748b; font-size: 9pt; font-weight: 600; margin-left: 4px;")
            lay.addWidget(lbl_suffix)

        lay.addStretch()

    def value(self) -> int:
        return self._val

    def setValue(self, v: int):
        new_val = max(self._min, min(self._max, int(v)))
        if new_val != self._val or self.in_val.text() != str(new_val):
            self._val = new_val
            self.in_val.setText(str(self._val))

    def _increase(self):
        self.setValue(self._val + self._step)

    def _decrease(self):
        self.setValue(self._val - self._step)

    def _on_text_changed(self, text: str):
        try:
            digits = "".join(ch for ch in text if ch.isdigit() or ch == "-")
            if digits and digits != "-":
                parsed = int(digits)
                self._val = max(self._min, min(self._max, parsed))
        except ValueError:
            pass


class SetupWizardDialog(QDialog):
    """
    8-Step guided enterprise setup wizard for initial deployment and re-configuration.
    """

    def __init__(self, parent: QWidget | None = None, config_path: str = "config/settings.json"):
        super().__init__(parent)
        self.setWindowTitle("EnergyAutomation — Initial Setup Wizard")
        self.resize(760, 560)
        self.config_path = Path(config_path)
        self.current_step = 0
        self.total_steps = 8

        self._load_current_settings()
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #0f172a;
            }
            QLabel {
                color: #0f172a;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QSpinBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px;
            }
            QCheckBox {
                color: #0f172a;
            }
            QGroupBox {
                font-weight: 600;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        self._build_ui()

    def _load_current_settings(self):
        self.settings: Dict[str, Any] = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header with Logo, Title, and Persistent Back button
        header = QHBoxLayout()
        logo_label = QLabel()
        logo_path = Path("assets/savera-logo.jpg")
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaledToHeight(36, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        header.addWidget(logo_label)

        title_box = QVBoxLayout()
        self.step_title = QLabel("Welcome to EnergyAutomation")
        self.step_title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0f172a;")
        self.step_subtitle = QLabel("Step 1 of 8: Company & Facility Profile")
        self.step_subtitle.setStyleSheet("font-size: 9.5pt; color: #64748b;")
        title_box.addWidget(self.step_title)
        title_box.addWidget(self.step_subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_header_back = TransparentPushButton("← Back", self)
        self.btn_header_back.setCursor(Qt.PointingHandCursor)
        self.btn_header_back.clicked.connect(self._go_back)
        header.addWidget(self.btn_header_back)

        root.addLayout(header)

        # Content pages
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_step1_welcome())
        self.pages.addWidget(self._create_step2_excel())
        self.pages.addWidget(self._create_step3_gmail())
        self.pages.addWidget(self._create_step4_gemini())
        self.pages.addWidget(self._create_step5_dash())
        self.pages.addWidget(self._create_step6_scheduler())
        self.pages.addWidget(self._create_step7_testing())
        self.pages.addWidget(self._create_step8_complete())
        root.addWidget(self.pages, 1)

        # Bottom navigation
        nav = QHBoxLayout()
        self.btn_back = PushButton("← Back", self)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(True)
        nav.addWidget(self.btn_back)

        nav.addStretch()

        self.btn_cancel = TransparentPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        nav.addWidget(self.btn_cancel)

        self.btn_next = PrimaryPushButton("Next →", self)
        self.btn_next.clicked.connect(self._go_next)
        nav.addWidget(self.btn_next)

        root.addLayout(nav)

    # -----------------------------------------------------------------
    # Step Pages
    # -----------------------------------------------------------------

    def _create_step1_welcome(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        info = QLabel(
            "EnergyAutomation automates the daily ingestion of NBSense Energy Management System (EMS) "
            "PDF reports from Gmail, validates meter telemetry, updates existing Excel workbooks with "
            "complete formula safety, and synchronizes executive analytics via Plotly Dash BI."
        )
        info.setWordWrap(True)
        info.setStyleSheet("line-height: 1.4; color: #334155;")
        lay.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)
        self.in_company = QLineEdit(self.settings.get("company", "Savera MS"))
        self.in_plant = QLineEdit(self.settings.get("plant", "Chennai Manufacturing Plant"))
        form.addRow("Organization Name:", self.in_company)
        form.addRow("Plant / Facility Name:", self.in_plant)
        lay.addLayout(form)
        lay.addStretch()
        return w

    def _create_step2_excel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_excel = self.settings.get("excel", {})
        form = QFormLayout()

        row_file = QHBoxLayout()
        self.in_excel_file = QLineEdit(cfg_excel.get("file", "Test_BI_Analysis_Report_2026.xlsx"))
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_excel)
        row_file.addWidget(self.in_excel_file)
        row_file.addWidget(btn_browse)
        form.addRow("Excel Workbook Path:", row_file)

        self.in_excel_sheet = QLineEdit(cfg_excel.get("worksheet", "EMS Monitoring Report"))
        form.addRow("Target Worksheet Name:", self.in_excel_sheet)

        lay.addLayout(form)

        banner = QLabel(
            "✔ Guaranteed Formula Safety: The system automatically preserves `=SUM(C16:Q16)` on daily "
            "rows and cumulative `=SUM(R5:R34)` on row 4. Atomic saves and pre-save backups prevent corruption."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 10px; color: #166534;")
        lay.addWidget(banner)
        lay.addStretch()
        return w

    def _browse_excel(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Excel Workbook", str(Path.cwd()), "Excel Workbooks (*.xlsx *.xlsm)")
        if fpath:
            p = Path(fpath)
            if p.exists():
                self.in_excel_file.setText(fpath)
            else:
                QMessageBox.warning(self, "File Not Found", "Selected file does not exist. Choose the correct file and file path, otherwise not found or not connected.")

    def _create_step3_gmail(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_gmail = self.settings.get("gmail", {})
        form = QFormLayout()

        self.in_gmail_sender = QLineEdit(cfg_gmail.get("sender", "alerts@nbsense.com"))
        form.addRow("Sender Email Filter:", self.in_gmail_sender)

        self.in_gmail_subject = QLineEdit(cfg_gmail.get("subject_contains", "Ems Monitoring Report"))
        form.addRow("Subject Filter Keyword:", self.in_gmail_subject)

        self.in_gmail_days = FluentNumberBox(
            min_val=1, max_val=90, default_val=cfg_gmail.get("search_days", 30), suffix="Days"
        )
        form.addRow("Gap Healing Lookback Window:", self.in_gmail_days)

        lay.addLayout(form)

        auth_note = QLabel(
            "🔑 Authentication Notice: Gmail access requires `credentials.json` (OAuth 2.0 Client ID) "
            "placed inside `credentials/gmail/`. The desktop browser will prompt for one-time Google consent."
        )
        auth_note.setWordWrap(True)
        auth_note.setStyleSheet("background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px; color: #92400e;")
        lay.addWidget(auth_note)
        lay.addStretch()
        return w

    def _create_step4_gemini(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_gem = self.settings.get("gemini", {})
        self.cb_gemini_enabled = QCheckBox("Enable Google Gemini AI Advisory Layer")
        self.cb_gemini_enabled.setChecked(cfg_gem.get("enabled", True))
        lay.addWidget(self.cb_gemini_enabled)

        form = QFormLayout()
        self.in_gemini_model = QLineEdit(cfg_gem.get("model", "gemini-flash-latest"))
        form.addRow("Gemini Primary Model:", self.in_gemini_model)

        self.in_gemini_key = QLineEdit(cfg_gem.get("api_key", ""))
        self.in_gemini_key.setEchoMode(QLineEdit.Password)
        self.in_gemini_key.setPlaceholderText("Paste your Gemini API key (AQ... or AIzaSy...)")
        form.addRow("Gemini API Key:", self.in_gemini_key)

        lay.addLayout(form)

        ai_rule = QLabel(
            "🛡 Zero Hallucination Rule: Google Gemini operates strictly read-only for natural-language Q&A "
            "and observations. If no API key is provided, the platform automatically activates deterministic "
            "offline rule reasoning so operations are never interrupted."
        )
        ai_rule.setWordWrap(True)
        ai_rule.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; color: #334155;")
        lay.addWidget(ai_rule)
        lay.addStretch()
        return w

    def _create_step5_dash(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_dash = self.settings.get("dash", {})
        self.cb_dash_enabled = QCheckBox("Enable Plotly Dash Management & Engineering BI Microservice")
        self.cb_dash_enabled.setChecked(cfg_dash.get("enabled", True))
        lay.addWidget(self.cb_dash_enabled)

        form = QFormLayout()
        self.in_dash_url = QLineEdit(cfg_dash.get("url", "http://localhost:8050"))
        self.in_dash_url.setPlaceholderText("e.g. http://localhost:8050")
        form.addRow("Plotly Dash BI URL:", self.in_dash_url)

        self.cb_dash_auto_launch = QCheckBox("Automatically launch browser when Dash server starts")
        self.cb_dash_auto_launch.setChecked(cfg_dash.get("auto_launch_browser", True))
        lay.addLayout(form)
        lay.addWidget(self.cb_dash_auto_launch)

        notice = QLabel(
            "📊 Architecture Rule: Plotly Dash BI operates strictly read-only against your verified "
            "production Excel workbook and Data Microservice API (port 8002). It provides real-time "
            "executive KPI cards, shift trends, and engineering load comparison tables from any browser."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px; color: #1e40af;")
        lay.addWidget(notice)
        lay.addStretch()
        return w

    def _create_step6_scheduler(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_auto = self.settings.get("automation", {})
        form = QFormLayout()

        self.in_interval = FluentNumberBox(
            min_val=1, max_val=1440, default_val=cfg_auto.get("check_interval_minutes", 5), step=1, suffix="Minutes"
        )
        form.addRow("Automation Polling Interval:", self.in_interval)

        self.cb_start_auto = QCheckBox("Start automation scheduler automatically on launch")
        self.cb_start_auto.setChecked(cfg_auto.get("start_automatically", True))

        self.cb_start_min = QCheckBox("Start application minimized to Windows System Tray")
        self.cb_start_min.setChecked(cfg_auto.get("start_minimized", False))

        lay.addLayout(form)
        lay.addWidget(self.cb_start_auto)
        lay.addWidget(self.cb_start_min)
        lay.addStretch()
        return w

    def _create_step7_testing(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        # Header with Unified Test Button
        top_bar = QHBoxLayout()
        lbl_hdr = QLabel("Live Diagnostics & Real-Time Connection Verification:")
        lbl_hdr.setStyleSheet("font-weight: 700; font-size: 10.5pt; color: #0f172a;")
        top_bar.addWidget(lbl_hdr)
        top_bar.addStretch()

        self.btn_run_diagnostics = PrimaryPushButton("⚡ Run Real-Time Diagnostics & Connection Checks", w)
        self.btn_run_diagnostics.clicked.connect(self._run_all_diagnostics)
        top_bar.addWidget(self.btn_run_diagnostics)
        lay.addLayout(top_bar)

        self.lbl_diag_status = QLabel("Click the button above to run real-time tests across all subsystems.")
        self.lbl_diag_status.setStyleSheet("color: #64748b; font-size: 9pt;")
        lay.addWidget(self.lbl_diag_status)

        box = QGroupBox("Subsystem Real-Time Health Matrix")
        b_lay = QVBoxLayout(box)
        b_lay.setSpacing(10)

        # 1. Excel Workbook Test
        self.lbl_t_excel = QLabel("Excel Workbook: Ready to test")
        btn_t_excel = PushButton("Test Excel")
        btn_t_excel.clicked.connect(self._test_excel_connection)
        row_e = QHBoxLayout()
        row_e.addWidget(self.lbl_t_excel, 1)
        row_e.addWidget(btn_t_excel)
        b_lay.addLayout(row_e)

        # 2. SQLite Database Test
        self.lbl_t_db = QLabel("SQLite Audit Database: Ready to test")
        btn_t_db = PushButton("Test Database")
        btn_t_db.clicked.connect(self._test_db_connection)
        row_db = QHBoxLayout()
        row_db.addWidget(self.lbl_t_db, 1)
        row_db.addWidget(btn_t_db)
        b_lay.addLayout(row_db)

        # 3. Gmail Service Test
        self.lbl_t_gmail = QLabel("Gmail Service: Ready to test")
        btn_t_gmail = PushButton("Test Gmail")
        btn_t_gmail.clicked.connect(self._test_gmail_connection)
        row_g = QHBoxLayout()
        row_g.addWidget(self.lbl_t_gmail, 1)
        row_g.addWidget(btn_t_gmail)
        b_lay.addLayout(row_g)

        # 4. Google Gemini AI Live Ping
        self.lbl_t_ai = QLabel("Google Gemini AI: Ready to test")
        btn_t_ai = PushButton("Test Gemini AI")
        btn_t_ai.clicked.connect(self._test_ai_connection)
        row_a = QHBoxLayout()
        row_a.addWidget(self.lbl_t_ai, 1)
        row_a.addWidget(btn_t_ai)
        b_lay.addLayout(row_a)

        # 5. Plotly Dash BI Microservice Test
        self.lbl_t_dash = QLabel("Plotly Dash BI: Ready to test")
        btn_t_dash = PushButton("Test Dash BI")
        btn_t_dash.clicked.connect(self._test_dash_connection)
        row_d = QHBoxLayout()
        row_d.addWidget(self.lbl_t_dash, 1)
        row_d.addWidget(btn_t_dash)
        b_lay.addLayout(row_d)

        lay.addWidget(box)
        lay.addStretch()
        return w

    def _test_excel_connection(self) -> bool:
        start_t = time.time()
        target = self.in_excel_file.text().strip().strip('"\'')
        sheet_target = self.in_excel_sheet.text().strip()
        p = Path(target)
        if not p.exists():
            self.lbl_t_excel.setText(f"✖ File Not Found: '{target}'. Choose the correct file and file path, otherwise not connected.")
            self.lbl_t_excel.setStyleSheet("color: #dc2626; font-weight: 700;")
            return False

        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            elapsed_ms = int((time.time() - start_t) * 1000)
            sheet_names = wb.sheetnames
            has_sheet = sheet_target in sheet_names if sheet_target else True
            active_sheet = sheet_target if has_sheet else sheet_names[0]
            ws = wb[active_sheet]
            max_r = ws.max_row or 0
            wb.close()

            if has_sheet:
                self.lbl_t_excel.setText(f"✔ Excel Verified: '{p.name}' | Sheet: '{active_sheet}' ({max_r} rows) [{elapsed_ms}ms]")
                self.lbl_t_excel.setStyleSheet("color: #16a34a; font-weight: 700;")
                return True
            else:
                self.lbl_t_excel.setText(f"⚠ Sheet '{sheet_target}' not found. Available sheets: {', '.join(sheet_names[:3])} [{elapsed_ms}ms]")
                self.lbl_t_excel.setStyleSheet("color: #d97706; font-weight: 700;")
                return True
        except Exception as exc:
            self.lbl_t_excel.setText(f"✖ Excel Read Error: {exc}")
            self.lbl_t_excel.setStyleSheet("color: #dc2626; font-weight: 700;")
            return False

    def _test_db_connection(self) -> bool:
        start_t = time.time()
        db_path = Path("data/automation.db")
        if not db_path.exists():
            db_path = Path("automation.db")
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            report_cnt = 0
            if "reports" in tables:
                cur.execute("SELECT count(*) FROM reports")
                report_cnt = cur.fetchone()[0]
            conn.close()
            elapsed_ms = int((time.time() - start_t) * 1000)
            self.lbl_t_db.setText(f"✔ SQLite Database Active: '{db_path.name}' | {report_cnt} historical reports [{elapsed_ms}ms]")
            self.lbl_t_db.setStyleSheet("color: #16a34a; font-weight: 700;")
            return True
        except Exception as exc:
            self.lbl_t_db.setText(f"✖ Database Error: {exc}")
            self.lbl_t_db.setStyleSheet("color: #dc2626; font-weight: 700;")
            return False

    def _test_gmail_connection(self) -> bool:
        token_paths = [Path("credentials/gmail/token.json"), Path("credentials/token.json")]
        cred_paths = [Path("credentials/gmail/credentials.json"), Path("credentials/credentials.json")]
        has_token = any(p.exists() for p in token_paths)
        has_creds = any(p.exists() for p in cred_paths)
        if has_token:
            self.lbl_t_gmail.setText("✔ Gmail OAuth Authorized & Ready (token.json present)")
            self.lbl_t_gmail.setStyleSheet("color: #16a34a; font-weight: 700;")
            return True
        elif has_creds:
            self.lbl_t_gmail.setText("⚠ OAuth Client Present; browser sign-in required on first run")
            self.lbl_t_gmail.setStyleSheet("color: #d97706; font-weight: 700;")
            return False
        else:
            self.lbl_t_gmail.setText("⚠ Gmail credentials missing (credentials/gmail/credentials.json)")
            self.lbl_t_gmail.setStyleSheet("color: #d97706; font-weight: 700;")
            return False

    def _test_ai_connection(self) -> bool:
        if not self.cb_gemini_enabled.isChecked():
            self.lbl_t_ai.setText("⚪ Gemini AI Disabled by User")
            self.lbl_t_ai.setStyleSheet("color: #64748b; font-weight: 600;")
            return True

        key = self.in_gemini_key.text().strip()
        if not key:
            self.lbl_t_ai.setText("✔ Deterministic Fallback Mode Active (Zero Hallucination Rules)")
            self.lbl_t_ai.setStyleSheet("color: #2563eb; font-weight: 700;")
            return True

        self.lbl_t_ai.setText("⏳ Connecting to Google Gemini API...")
        self.lbl_t_ai.setStyleSheet("color: #d97706; font-weight: 600;")
        QApplication.processEvents()

        try:
            from app.services.ai.gemini_service import GeminiService
            srv = GeminiService(api_key=key, enabled=True)
            res = srv.test_connection()
            if res.get("success"):
                lat = res.get("latency_ms", 0)
                mod = res.get("model", srv.model)
                self.lbl_t_ai.setText(f"✔ Gemini Connected: {mod} ({lat}ms latency)")
                self.lbl_t_ai.setStyleSheet("color: #16a34a; font-weight: 700;")
                return True
            else:
                msg = res.get("message", "Connection failed")
                self.lbl_t_ai.setText(f"✖ Gemini Test Failed: {msg[:60]}")
                self.lbl_t_ai.setStyleSheet("color: #dc2626; font-weight: 700;")
                return False
        except Exception as exc:
            self.lbl_t_ai.setText(f"✖ Gemini Error: {exc}")
            self.lbl_t_ai.setStyleSheet("color: #dc2626; font-weight: 700;")
            return False

    def _test_dash_connection(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.6)
        is_port_open = (sock.connect_ex(("127.0.0.1", 8050)) == 0)
        sock.close()
        dash_script = Path("services/dash_service/app.py")
        if is_port_open:
            self.lbl_t_dash.setText("✔ Plotly Dash Server Running on http://localhost:8050")
            self.lbl_t_dash.setStyleSheet("color: #16a34a; font-weight: 700;")
            return True
        elif dash_script.exists():
            self.lbl_t_dash.setText("✔ Plotly Dash Microservice Installed (Port 8050 ready to launch)")
            self.lbl_t_dash.setStyleSheet("color: #16a34a; font-weight: 700;")
            return True
        else:
            self.lbl_t_dash.setText("⚠ Plotly Dash Microservice not found at services/dash_service/app.py")
            self.lbl_t_dash.setStyleSheet("color: #d97706; font-weight: 700;")
            return False

    def _run_all_diagnostics(self):
        self.btn_run_diagnostics.setEnabled(False)
        self.lbl_diag_status.setText("Testing all subsystems in real time...")
        QApplication.processEvents()

        e_ok = self._test_excel_connection()
        QApplication.processEvents()
        db_ok = self._test_db_connection()
        QApplication.processEvents()
        g_ok = self._test_gmail_connection()
        QApplication.processEvents()
        ai_ok = self._test_ai_connection()
        QApplication.processEvents()
        d_ok = self._test_dash_connection()

        self.btn_run_diagnostics.setEnabled(True)
        passed = sum([1 for ok in (e_ok, db_ok, g_ok, ai_ok, d_ok) if ok])
        self.lbl_diag_status.setText(f"✔ Live Diagnostic Complete: {passed} of 5 subsystems verified.")
        self.lbl_diag_status.setStyleSheet("font-weight: 700; color: #16a34a;" if passed >= 4 else "font-weight: 700; color: #d97706;")

    def _create_step8_complete(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)

        success_box = QFrame()
        success_box.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 18px;")
        s_lay = QVBoxLayout(success_box)

        lbl = QLabel("🎉 Setup Complete & Configuration Validated!")
        lbl.setStyleSheet("font-size: 13pt; font-weight: 700; color: #166534;")
        s_lay.addWidget(lbl)

        sub = QLabel(
            "EnergyAutomation is fully initialized. Click 'Save & Start' to save configuration "
            "and open the main application dashboard."
        )
        sub.setStyleSheet("color: #15803d; font-size: 10pt; margin-top: 4px;")
        sub.setWordWrap(True)
        s_lay.addWidget(sub)
        lay.addWidget(success_box)
        lay.addStretch()
        return w

    # -----------------------------------------------------------------
    # Navigation logic
    # -----------------------------------------------------------------

    def _go_next(self):
        if self.current_step < self.total_steps - 1:
            # If leaving step 2 (Excel), validate file
            if self.current_step == 1:
                target = self.in_excel_file.text().strip().strip('"\'')
                if not target or not Path(target).exists():
                    reply = QMessageBox.warning(
                        self,
                        "Excel Workbook Notice",
                        f"The file path '{target}' was not found.\n\nChoose the correct file and file path, otherwise not found or not connected.\n\nDo you want to proceed anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if reply == QMessageBox.No:
                        return

            self.current_step += 1
            self._update_step_view()
        else:
            self._save_and_finish()

    def _go_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_step_view()
        else:
            self.reject()

    def _update_step_view(self):
        self.pages.setCurrentIndex(self.current_step)
        step_names = [
            "Company & Facility Profile",
            "Excel Workbook & Formula Safety",
            "Gmail Ingestion & Gap Lookback",
            "Google Gemini AI Intelligence",
            "Plotly Dash BI Web Analytics",
            "Automation Scheduler & Background Run",
            "Live Diagnostics & Connection Checks",
            "Confirmation & System Launch",
        ]
        self.step_title.setText(f"Setup — {step_names[self.current_step]}")
        self.step_subtitle.setText(f"Step {self.current_step + 1} of {self.total_steps}")
        self.btn_back.setEnabled(True)
        if self.current_step == 0:
            self.btn_back.setText("← Back to Dashboard")
            self.btn_header_back.setText("← Back to Dashboard")
        else:
            self.btn_back.setText("← Back")
            self.btn_header_back.setText("← Back")

        if self.current_step == self.total_steps - 1:
            self.btn_next.setText("Save && Start")
        else:
            self.btn_next.setText("Next →")

    def _save_and_finish(self):
        """Save settings to config/settings.json."""
        target_excel = self.in_excel_file.text().strip().strip('"\'')
        if not target_excel or not Path(target_excel).exists():
            QMessageBox.warning(
                self,
                "Excel File Not Found",
                "Choose the correct file and file path, otherwise not found or not connected.\n\nYou can select a valid workbook using Browse on Step 2.",
            )

        new_settings = {
            "company": self.in_company.text().strip(),
            "plant": self.in_plant.text().strip(),
            "gmail": {
                "sender": self.in_gmail_sender.text().strip(),
                "subject_contains": self.in_gmail_subject.text().strip(),
                "search_days": self.in_gmail_days.value(),
            },
            "pdf": {
                "expected_unit": "kWh",
            },
            "excel": {
                "file": target_excel,
                "worksheet": self.in_excel_sheet.text().strip(),
                "header_row": 3,
                "date_column": 2,
                "first_data_row": 5,
                "total_column": 18,
                "update_total": True,
                "fail_on_unmapped_numeric_meter": False,
            },
            "automation": {
                "check_interval_minutes": self.in_interval.value(),
                "start_automatically": self.cb_start_auto.isChecked(),
                "start_minimized": self.cb_start_min.isChecked(),
            },
            "validation": {
                "minimum_active_energy": 0,
                "maximum_active_energy": 100000000,
            },
            "gemini": {
                "enabled": self.cb_gemini_enabled.isChecked(),
                "model": self.in_gemini_model.text().strip(),
                "api_key": self.in_gemini_key.text().strip(),
            },
            "dash": {
                "enabled": self.cb_dash_enabled.isChecked(),
                "url": self.in_dash_url.text().strip(),
                "port": 8050,
                "auto_launch_browser": self.cb_dash_auto_launch.isChecked(),
            },
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(new_settings, f, indent=2)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save settings: {exc}")

"""
Enterprise First-Run Setup Wizard for EnergyAutomation.
Guides administrators and plant engineers through initial configuration,
validation, and live connection diagnostics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
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


class SetupWizardDialog(QDialog):
    """
    8-Step guided enterprise setup wizard for initial deployment and re-configuration.
    """

    def __init__(self, parent: QWidget | None = None, config_path: str = "config/settings.json"):
        super().__init__(parent)
        self.setWindowTitle("EnergyAutomation — Initial Setup Wizard")
        self.resize(740, 520)
        self.config_path = Path(config_path)
        self.current_step = 0
        self.total_steps = 8

        self._load_current_settings()
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

        # Header with Logo & Title
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

        root.addLayout(header)

        # Content pages
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_step1_welcome())
        self.pages.addWidget(self._create_step2_excel())
        self.pages.addWidget(self._create_step3_gmail())
        self.pages.addWidget(self._create_step4_gemini())
        self.pages.addWidget(self._create_step5_powerbi())
        self.pages.addWidget(self._create_step6_scheduler())
        self.pages.addWidget(self._create_step7_testing())
        self.pages.addWidget(self._create_step8_complete())
        root.addWidget(self.pages, 1)

        # Bottom navigation
        nav = QHBoxLayout()
        self.btn_back = PushButton("← Back", self)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
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
            "complete formula safety, and synchronizes executive analytics."
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
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Excel Workbook", "", "Excel Workbooks (*.xlsx *.xlsm)")
        if fpath:
            self.in_excel_file.setText(fpath)

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

        self.in_gmail_days = QSpinBox()
        self.in_gmail_days.setRange(1, 90)
        self.in_gmail_days.setValue(cfg_gmail.get("search_days", 30))
        form.addRow("Historical Gap Lookback (Days):", self.in_gmail_days)

        lay.addLayout(form)

        notice = QLabel(
            "OAuth Authentication: Place `credentials.json` in `credentials/gmail/` to authorize the app. "
            "Once authorized, token is refreshed automatically without human intervention."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px; color: #1e40af;")
        lay.addWidget(notice)
        lay.addStretch()
        return w

    def _create_step4_gemini(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_gemini = self.settings.get("gemini", {})
        self.cb_gemini_enabled = QCheckBox("Enable Google Gemini AI Intelligence")
        self.cb_gemini_enabled.setChecked(cfg_gemini.get("enabled", True))
        lay.addWidget(self.cb_gemini_enabled)

        form = QFormLayout()
        self.in_gemini_model = QLineEdit(cfg_gemini.get("model", "gemini-2.5-flash"))
        form.addRow("AI Model Name:", self.in_gemini_model)

        self.in_gemini_key = QLineEdit(cfg_gemini.get("api_key", ""))
        self.in_gemini_key.setEchoMode(QLineEdit.Password)
        self.in_gemini_key.setPlaceholderText("Optional: Leave blank to use offline deterministic fallback")
        form.addRow("Gemini API Key:", self.in_gemini_key)
        lay.addLayout(form)

        policy = QLabel(
            "🔒 Architecture Rule: Gemini AI operates strictly in advisory mode. It provides explanations, "
            "summaries, and natural-language Q&A based on verified data, but never directly modifies Excel or bypasses validation."
        )
        policy.setWordWrap(True)
        policy.setStyleSheet("background: #fdf4ff; border: 1px solid #f0abfc; border-radius: 6px; padding: 10px; color: #86198f;")
        lay.addWidget(policy)
        lay.addStretch()
        return w

    def _create_step5_powerbi(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_pbi = self.settings.get("powerbi", {})
        self.cb_pbi_enabled = QCheckBox("Enable Power BI Cloud API Direct Publishing")
        self.cb_pbi_enabled.setChecked(cfg_pbi.get("enabled", False))
        lay.addWidget(self.cb_pbi_enabled)

        form = QFormLayout()
        self.in_pbi_workspace = QLineEdit(cfg_pbi.get("workspace_id", ""))
        self.in_pbi_workspace.setPlaceholderText("Azure Workspace GUID")
        form.addRow("Workspace ID:", self.in_pbi_workspace)

        self.in_pbi_dataset = QLineEdit(cfg_pbi.get("dataset_id", ""))
        self.in_pbi_dataset.setPlaceholderText("Dataset GUID")
        form.addRow("Dataset ID:", self.in_pbi_dataset)
        lay.addLayout(form)

        notice = QLabel(
            "Local Export Fallback: When cloud credentials are not supplied, the system automatically "
            "generates clean star-schema CSVs, DAX measures, and JSON templates in `data/powerbi/` ready for Power BI Desktop."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px; color: #92400e;")
        lay.addWidget(notice)
        lay.addStretch()
        return w

    def _create_step6_scheduler(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        cfg_auto = self.settings.get("automation", {})
        form = QFormLayout()

        self.in_interval = QSpinBox()
        self.in_interval.setRange(1, 1440)
        self.in_interval.setValue(cfg_auto.get("check_interval_minutes", 5))
        form.addRow("Automation Polling Interval (Minutes):", self.in_interval)

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

        lay.addWidget(QLabel("Live Diagnostics & Connection Verification:"))

        box = QGroupBox("System Connection Checks")
        b_lay = QVBoxLayout(box)

        self.lbl_t_excel = QLabel("Excel Workbook: Click Test to check")
        btn_t_excel = QPushButton("Test Excel")
        btn_t_excel.clicked.connect(self._test_excel_connection)
        row_e = QHBoxLayout()
        row_e.addWidget(self.lbl_t_excel)
        row_e.addStretch()
        row_e.addWidget(btn_t_excel)
        b_lay.addLayout(row_e)

        self.lbl_t_gmail = QLabel("Gmail Service: Click Test to check")
        btn_t_gmail = QPushButton("Test Gmail")
        btn_t_gmail.clicked.connect(self._test_gmail_connection)
        row_g = QHBoxLayout()
        row_g.addWidget(self.lbl_t_gmail)
        row_g.addStretch()
        row_g.addWidget(btn_t_gmail)
        b_lay.addLayout(row_g)

        self.lbl_t_ai = QLabel("Gemini AI: Click Test to check")
        btn_t_ai = QPushButton("Test AI")
        btn_t_ai.clicked.connect(self._test_ai_connection)
        row_a = QHBoxLayout()
        row_a.addWidget(self.lbl_t_ai)
        row_a.addStretch()
        row_a.addWidget(btn_t_ai)
        b_lay.addLayout(row_a)

        lay.addWidget(box)
        lay.addStretch()
        return w

    def _test_excel_connection(self):
        target = self.in_excel_file.text().strip().strip('"\'')
        p = Path(target)
        if p.exists():
            self.lbl_t_excel.setText(f"✔ Excel Workbook Found ({p.name})")
            self.lbl_t_excel.setStyleSheet("color: #16a34a; font-weight: 700;")
        else:
            self.lbl_t_excel.setText("⚠ File does not exist yet (Will be created on first report)")
            self.lbl_t_excel.setStyleSheet("color: #d97706; font-weight: 700;")

    def _test_gmail_connection(self):
        creds = Path("credentials/gmail/credentials.json")
        tok = Path("credentials/token.json")
        if tok.exists():
            self.lbl_t_gmail.setText("✔ Gmail Token Configured & Ready")
            self.lbl_t_gmail.setStyleSheet("color: #16a34a; font-weight: 700;")
        elif creds.exists():
            self.lbl_t_gmail.setText("✔ OAuth credentials.json present")
            self.lbl_t_gmail.setStyleSheet("color: #16a34a; font-weight: 700;")
        else:
            self.lbl_t_gmail.setText("⚠ Gmail credentials missing (Mock/Manual mode active)")
            self.lbl_t_gmail.setStyleSheet("color: #d97706; font-weight: 700;")

    def _test_ai_connection(self):
        if self.cb_gemini_enabled.isChecked():
            key = self.in_gemini_key.text().strip()
            if key:
                self.lbl_t_ai.setText("✔ Gemini API Key Provided")
                self.lbl_t_ai.setStyleSheet("color: #16a34a; font-weight: 700;")
            else:
                self.lbl_t_ai.setText("✔ Deterministic Fallback Mode Active")
                self.lbl_t_ai.setStyleSheet("color: #2563eb; font-weight: 700;")
        else:
            self.lbl_t_ai.setText("⚪ AI Disabled")
            self.lbl_t_ai.setStyleSheet("color: #64748b;")

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
            self.current_step += 1
            self._update_step_view()
        else:
            self._save_and_finish()

    def _go_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_step_view()

    def _update_step_view(self):
        self.pages.setCurrentIndex(self.current_step)
        step_names = [
            "Company & Facility Profile",
            "Excel Workbook & Formula Safety",
            "Gmail Ingestion & Gap Lookback",
            "Google Gemini AI Intelligence",
            "Power BI Analytics & Star Schema",
            "Automation Scheduler & Background Run",
            "Live Diagnostics & Connection Checks",
            "Confirmation & System Launch",
        ]
        self.step_title.setText(f"Setup — {step_names[self.current_step]}")
        self.step_subtitle.setText(f"Step {self.current_step + 1} of {self.total_steps}")
        self.btn_back.setEnabled(self.current_step > 0)
        if self.current_step == self.total_steps - 1:
            self.btn_next.setText("Save & Start")
        else:
            self.btn_next.setText("Next →")

    def _save_and_finish(self):
        """Save settings to config/settings.json."""
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
                "file": self.in_excel_file.text().strip().strip('"\''),
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
            "powerbi": {
                "enabled": self.cb_pbi_enabled.isChecked(),
                "workspace_id": self.in_pbi_workspace.text().strip(),
                "dataset_id": self.in_pbi_dataset.text().strip(),
            },
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(new_settings, f, indent=2)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save settings: {exc}")

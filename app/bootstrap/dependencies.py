"""
EnergyAutomation
Application Dependency Composition Root

This module is responsible only for constructing and wiring application
dependencies.

Important architecture rule
----------------------------
GmailService:
    Low-level Gmail API integration.

GmailRepository:
    Report-oriented interface used by the workflow.
    Provides find_reports() and download_reports().

AutomationWorkflow:
    Must receive GmailRepository for report discovery.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.monitoring.logger import get_logger
from app.monitoring.metrics import Metrics
from app.monitoring.health import HealthMonitor

from app.persistence.database import Database
from app.persistence.repositories.report_repository import ReportRepository

from app.services.gmail.service import GmailService
from app.services.gmail.repository import GmailRepository

from app.services.pdf.service import PDFService
from app.services.validation.service import ValidationService
from app.services.excel.service import ExcelService
from app.services.reconciliation.service import ReconciliationService

from app.services.ai.gemini_service import GeminiService
from app.services.ai.analyzer import EnergyAnalyzer
from app.services.ai.decision_engine import AIDecisionEngine

from app.services.notification.service import NotificationService
from app.events.bus import get_event_bus
from app.services.alert.service import AlertService
from app.services.alert.socket_hub import AlertSocketHub
from app.services.analytics.plant_topology import PlantTopologyService

from app.orchestration.retry import RetryService
from app.orchestration.workflow import AutomationWorkflow
from app.orchestration.scheduler import AutomationScheduler


logger = get_logger(__name__)


# ============================================================================
# PROJECT PATH
# ============================================================================

def _project_root() -> Path:
    """
    Return the EnergyAutomation project root.
    """
    return Path(__file__).resolve().parents[2]


# ============================================================================
# CONFIGURATION
# ============================================================================

def _load_config() -> Dict[str, Any]:
    """
    Load application configuration.

    Preferred source:
        config.load_config()

    Fallback:
        config/settings.json
    """

    settings_file = (
        _project_root()
        / "config"
        / "settings.json"
    )

    if settings_file.exists():
        try:
            with settings_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                loaded = json.load(file)
            if isinstance(loaded, dict) and loaded:
                return loaded
        except Exception as exc:
            logger.warning(
                "Unable to load settings.json: %s",
                exc,
            )

    try:
        from archive.config import load_config

        loaded = load_config()
        if isinstance(loaded, dict):
            return loaded
    except ImportError:
        pass
    except Exception as exc:
        logger.warning(
            "config.load_config() fallback failed: %s",
            exc,
        )

    return {}


def _get_section(
    config: Dict[str, Any],
    name: str,
) -> Dict[str, Any]:

    value = config.get(
        name,
        {},
    )

    if isinstance(value, dict):
        return value

    return {}


def _ensure_directory(
    value: str | Path,
) -> Path:

    path = Path(value)

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


# ============================================================================
# SAFE CONSTRUCTOR
# ============================================================================

def _construct(
    cls: Any,
    candidates: Optional[Dict[str, Any]] = None,
    positional: Optional[list[Any]] = None,
) -> Any:
    """
    Safely construct a class using only constructor-compatible arguments.

    Prevents errors such as:

        got multiple values for argument 'database'

    and:

        unexpected keyword argument 'settings'

    Positional arguments always take precedence over keyword candidates.
    """

    candidates = dict(
        candidates or {}
    )

    positional = list(
        positional or []
    )

    try:

        signature = inspect.signature(
            cls.__init__
        )

    except (
        TypeError,
        ValueError,
    ):

        return cls(
            *positional,
            **{
                key: value
                for key, value in candidates.items()
                if value is not None
            },
        )

    parameters = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.name != "self"
    ]

    parameter_map = {
        parameter.name: parameter
        for parameter in parameters
    }

    accepts_kwargs = any(
        parameter.kind
        == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )

    # Determine constructor parameters already consumed by positional args.
    positional_parameter_names: list[str] = []

    positional_index = 0

    for parameter in parameters:

        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):

            if positional_index < len(positional):

                positional_parameter_names.append(
                    parameter.name
                )

                positional_index += 1

        elif parameter.kind == inspect.Parameter.VAR_POSITIONAL:

            positional_index = len(positional)

            break

    filtered: Dict[str, Any] = {}

    for key, value in candidates.items():

        if value is None:
            continue

        # Never pass a parameter twice.
        if key in positional_parameter_names:
            continue

        # Normal named constructor parameter.
        if key in parameter_map:

            parameter = parameter_map[key]

            if parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):

                filtered[key] = value

            continue

        # **kwargs constructor.
        if accepts_kwargs:
            filtered[key] = value

    return cls(
        *positional,
        **filtered,
    )


# ============================================================================
# BUILD SERVICES
# ============================================================================

def build_services(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if config is None:
        config = _load_config()

    # ------------------------------------------------------------------------
    # Configuration sections
    # ------------------------------------------------------------------------

    gmail_settings = _get_section(
        config,
        "gmail",
    )

    pdf_settings = _get_section(
        config,
        "pdf",
    )

    excel_settings = _get_section(
        config,
        "excel",
    )

    validation_settings = _get_section(
        config,
        "validation",
    )

    automation_settings = _get_section(
        config,
        "automation",
    )

    gemini_settings = _get_section(
        config,
        "gemini",
    )

    powerbi_settings = _get_section(
        config,
        "powerbi",
    )

    database_settings = _get_section(
        config,
        "database",
    )

    # =========================================================================
    # DIRECTORIES
    # =========================================================================

    credentials_dir = _ensure_directory(
        gmail_settings.get(
            "credentials_dir",
            "credentials/gmail",
        )
    )

    download_dir = _ensure_directory(
        gmail_settings.get(
            "download_dir",
            "data/downloads",
        )
    )

    data_dir = _ensure_directory(
        database_settings.get(
            "data_dir",
            "data",
        )
    )

    # =========================================================================
    # DATABASE
    # =========================================================================

    database_path = (
        database_settings.get("file")
        or database_settings.get("path")
        or str(
            data_dir
            / "automation.db"
        )
    )

    database = _construct(
        Database,
        candidates={
            "database_path": database_path,
            "db_path": database_path,
            "path": database_path,
        },
    )

    initialize = getattr(
        database,
        "initialize",
        None,
    )

    if callable(initialize):

        try:
            initialize()

        except TypeError:
            pass

    # =========================================================================
    # REPORT REPOSITORY
    # =========================================================================

    report_repository = _construct(
        ReportRepository,
        candidates={
            "database": database,
            "db": database,
        },
        positional=[
            database
        ],
    )

    # =========================================================================
    # GMAIL SERVICE
    # =========================================================================

    gmail_sender = gmail_settings.get(
        "sender",
        "alerts@nbsense.com",
    )

    gmail_subject = gmail_settings.get(
        "subject_contains",
        "Ems Monitoring Report",
    )

    gmail_search_days = int(
        gmail_settings.get(
            "search_days",
            2,
        )
    )

    gmail = _construct(
        GmailService,
        candidates={
            "sender": gmail_sender,
            "subject_contains": gmail_subject,
            "search_days": gmail_search_days,
            "credentials_dir": credentials_dir,
            "download_dir": download_dir,
            "logger": logger,
        },
    )

    # =========================================================================
    # GMAIL REPOSITORY
    #
    # THIS IS THE IMPORTANT FIX.
    #
    # GmailRepository wraps GmailService and exposes:
    #
    #     find_reports()
    #     download_reports()
    #
    # AutomationWorkflow must use this object when working with reports.
    # =========================================================================

    gmail_repository = _construct(
        GmailRepository,
        candidates={
            "gmail_service": gmail,
            "gmail": gmail,
        },
        positional=[
            gmail
        ],
    )

    # =========================================================================
    # PDF SERVICE
    # =========================================================================

    # PDFService does not accept expected_unit.
    pdf_service = _construct(
        PDFService,
        candidates={},
    )

    # =========================================================================
    # VALIDATION SERVICE
    # =========================================================================

    minimum_active_energy = validation_settings.get(
        "minimum_active_energy",
        0,
    )

    maximum_active_energy = validation_settings.get(
        "maximum_active_energy",
        100000000,
    )

    fail_on_unmapped_numeric_meter = bool(
        excel_settings.get(
            "fail_on_unmapped_numeric_meter",
            False,
        )
    )

    validation_service = _construct(
        ValidationService,
        candidates={
            "minimum_active_energy": minimum_active_energy,
            "maximum_active_energy": maximum_active_energy,
            "fail_on_unmapped_numeric_meter":
                fail_on_unmapped_numeric_meter,
        },
    )

    # =========================================================================
    # EXCEL SERVICE
    # =========================================================================

    workbook_path = (
        excel_settings.get("file")
        or excel_settings.get("workbook_path")
        or excel_settings.get("path")
    )

    worksheet_name = (
        excel_settings.get("worksheet")
        or excel_settings.get("worksheet_name")
        or "EMS Monitoring Report"
    )

    header_row = int(
        excel_settings.get(
            "header_row",
            3,
        )
    )

    date_column = int(
        excel_settings.get(
            "date_column",
            2,
        )
    )

    first_data_row = int(
        excel_settings.get(
            "first_data_row",
            5,
        )
    )

    total_column = int(
        excel_settings.get(
            "total_column",
            18,
        )
    )

    update_total = bool(
        excel_settings.get(
            "update_total",
            True,
        )
    )

    excel_service = _construct(
        ExcelService,
        candidates={
            "workbook_path": workbook_path,
            "excel_file": workbook_path,
            "file_path": workbook_path,
            "path": workbook_path,

            "worksheet": worksheet_name,
            "worksheet_name": worksheet_name,
            "sheet_name": worksheet_name,

            "header_row": header_row,
            "date_column": date_column,

            "first_data_row": first_data_row,

            "total_column": total_column,

            "update_total": update_total,

            "fail_on_unmapped_numeric_meter":
                fail_on_unmapped_numeric_meter,
        },
    )

    # =========================================================================
    # RECONCILIATION SERVICE
    # =========================================================================

    reconciliation_service = _construct(
        ReconciliationService,
        candidates={
            "gmail_service": gmail,
            "gmail": gmail,

            "gmail_repository":
                gmail_repository,

            "excel_service":
                excel_service,

            "excel":
                excel_service,

            "report_repository":
                report_repository,

            "repository":
                report_repository,

            "database":
                database,
        },
    )

    # =========================================================================
    # GEMINI
    # =========================================================================

    gemini_enabled = bool(
        gemini_settings.get(
            "enabled",
            False,
        )
    )

    gemini_api_key = (
        gemini_settings.get("api_key")
        or gemini_settings.get("GEMINI_API_KEY")
        or None
    )

    gemini_model = gemini_settings.get(
        "model",
        "gemini-2.5-flash",
    )

    gemini_service = _construct(
        GeminiService,
        candidates={
            "api_key": gemini_api_key,
            "model": gemini_model,
            "enabled": gemini_enabled,
        },
    )

    # =========================================================================
    # ENERGY ANALYZER
    # =========================================================================

    energy_analyzer = _construct(
        EnergyAnalyzer,
        candidates={},
    )

    # =========================================================================
    # AI DECISION ENGINE
    # =========================================================================

    ai_decision_engine = _construct(
        AIDecisionEngine,
        candidates={
            "gemini_service":
                gemini_service,

            "gemini":
                gemini_service,

            "analyzer":
                energy_analyzer,

            "energy_analyzer":
                energy_analyzer,
        },
    )

    # Power BI removed in favor of Streamlit Management BI
    powerbi_service = None
    powerbi_publisher = None
    powerbi_refresh_service = None

    # =========================================================================
    # NOTIFICATION
    # =========================================================================

    notification_service = _construct(
        NotificationService,
        candidates={},
    )

    # =========================================================================
    # RETRY
    # =========================================================================

    retry_service = _construct(
        RetryService,
        candidates={},
    )

    # =========================================================================
    # METRICS
    # =========================================================================

    metrics = Metrics()

    # =========================================================================
    # HEALTH
    # =========================================================================

    health_monitor = _construct(
        HealthMonitor,
        candidates={},
    )

    # =========================================================================
    # AUTOMATION WORKFLOW
    #
    # IMPORTANT:
    #
    # "gmail" points to GmailRepository.
    #
    # "gmail_repository" also points to GmailRepository.
    #
    # "gmail_service" remains available as the raw GmailService.
    #
    # This prevents:
    #
    #     'GmailService' object has no attribute 'find_reports'
    #
    # =========================================================================

    event_bus = get_event_bus()
    alert_socket_hub = AlertSocketHub()
    try:
        alert_socket_hub.start()
    except Exception as exc:
        logger.warning(f"Could not start AlertSocketHub: {exc}")

    alert_service = AlertService(
        database=database,
        event_bus=event_bus,
        socket_hub=alert_socket_hub,
    )
    plant_topology = PlantTopologyService()

    workflow = _construct(
        AutomationWorkflow,

        candidates={

            # -----------------------------------------------------------------
            # Gmail
            # -----------------------------------------------------------------

            "gmail":
                gmail_repository,

            "gmail_repository":
                gmail_repository,

            "gmail_service":
                gmail,

            # -----------------------------------------------------------------
            # PDF
            # -----------------------------------------------------------------

            "pdf":
                pdf_service,

            "pdf_service":
                pdf_service,

            # -----------------------------------------------------------------
            # Validation
            # -----------------------------------------------------------------

            "validation":
                validation_service,

            "validation_service":
                validation_service,

            # -----------------------------------------------------------------
            # Reconciliation
            # -----------------------------------------------------------------

            "reconciliation":
                reconciliation_service,

            "reconciliation_service":
                reconciliation_service,

            # -----------------------------------------------------------------
            # Excel
            # -----------------------------------------------------------------

            "excel":
                excel_service,

            "excel_service":
                excel_service,

            # -----------------------------------------------------------------
            # Gemini / AI
            # -----------------------------------------------------------------

            "gemini":
                gemini_service,

            "gemini_service":
                gemini_service,

            "analyzer":
                energy_analyzer,

            "energy_analyzer":
                energy_analyzer,

            "ai_decision_engine":
                ai_decision_engine,

            # -----------------------------------------------------------------
            # Power BI
            # -----------------------------------------------------------------

            "powerbi":
                powerbi_service,

            "powerbi_service":
                powerbi_service,

            "powerbi_publisher":
                powerbi_publisher,

            "powerbi_refresh":
                powerbi_refresh_service,

            "powerbi_refresh_service":
                powerbi_refresh_service,

            # -----------------------------------------------------------------
            # Notifications
            # -----------------------------------------------------------------

            "notification":
                notification_service,

            "notification_service":
                notification_service,

            # -----------------------------------------------------------------
            # Persistence
            # -----------------------------------------------------------------

            "database":
                database,

            "report_repository":
                report_repository,

            # -----------------------------------------------------------------
            # Infrastructure
            # -----------------------------------------------------------------

            "retry":
                retry_service,

            "retry_service":
                retry_service,

            "metrics":
                metrics,

            "health":
                health_monitor,

            "health_monitor":
                health_monitor,

            "event_bus":
                event_bus,

            "alert_service":
                alert_service,

            "alert_socket_hub":
                alert_socket_hub,
        },
    )

    # =========================================================================
    # SCHEDULER
    # =========================================================================

    check_interval_minutes = int(
        automation_settings.get(
            "check_interval_minutes",
            5,
        )
    )

    scheduler = _construct(
        AutomationScheduler,
        candidates={
            "workflow":
                workflow,

            "automation_workflow":
                workflow,

            "interval_minutes":
                check_interval_minutes,

            "check_interval_minutes":
                check_interval_minutes,
        },
    )

    # =========================================================================
    # SERVICE CONTAINER
    # =========================================================================

    services: Dict[str, Any] = {

        # Database
        "database":
            database,

        "report_repository":
            report_repository,

        # Gmail
        "gmail":
            gmail,

        "gmail_service":
            gmail,

        "gmail_repository":
            gmail_repository,

        # PDF
        "pdf":
            pdf_service,

        "pdf_service":
            pdf_service,

        # Validation
        "validation":
            validation_service,

        "validation_service":
            validation_service,

        # Reconciliation
        "reconciliation":
            reconciliation_service,

        "reconciliation_service":
            reconciliation_service,

        # Excel
        "excel":
            excel_service,

        "excel_service":
            excel_service,

        # AI
        "gemini":
            gemini_service,

        "gemini_service":
            gemini_service,

        "analyzer":
            energy_analyzer,

        "energy_analyzer":
            energy_analyzer,

        "ai_decision_engine":
            ai_decision_engine,

        # Notifications
        "notification":
            notification_service,

        "notification_service":
            notification_service,

        # Infrastructure
        "retry":
            retry_service,

        "retry_service":
            retry_service,

        "metrics":
            metrics,

        "health":
            health_monitor,

        "health_monitor":
            health_monitor,

        # Orchestration
        "workflow":
            workflow,

        "scheduler":
            scheduler,

        # Enterprise Features
        "event_bus":
            event_bus,

        "alert_service":
            alert_service,

        "alert_socket_hub":
            alert_socket_hub,

        "plant_topology":
            plant_topology,
    }

    logger.info(
        "EnergyAutomation dependency container built successfully."
    )

    return services


__all__ = [
    "build_services",
]
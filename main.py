"""
EnergyAutomation — Enterprise Entry Point & Microservices CLI.
Supports running the Desktop Client or independent decoupled Microservices:
  python main.py                  -> Launches Windows 11 Fluent Desktop GUI
  python main.py --service=dash   -> Launches Plotly Dash Web BI (:8050)
  python main.py --service=core   -> Launches Core Automation API (:8001)
  python main.py --service=data   -> Launches Data & Telemetry API (:8002)
  python main.py --service=ai     -> Launches Gemini AI Advisory API (:8003)
  python main.py --service=gateway-> Launches Unified Gateway API (:8000)
  python main.py --service=all    -> Supervises all microservices together
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Auto-switch to virtual environment python if available (only in development)
if not getattr(sys, "frozen", False):
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        sys.exit(subprocess.call([str(venv_python)] + sys.argv))


def main() -> None:
    from app.paths import initialize_runtime_environment
    initialize_runtime_environment()

    parser = argparse.ArgumentParser(description="EnergyAutomation Microservices Platform")
    parser.add_argument(
        "--service",
        "-s",
        choices=["desktop", "dash", "core", "data", "ai", "gateway", "all"],
        default="desktop",
        help="Specify which component or microservice to start (default: desktop)",
    )
    args, unknown = parser.parse_known_args()

    if args.service == "desktop":
        from app.bootstrap.qt_app import run_application
        run_application()

    elif args.service == "dash":
        from services.dash_service.app import main as run_dash
        run_dash()

    elif args.service == "core":
        from services.core_automation.api import start as run_core
        run_core()

    elif args.service == "data":
        from services.data_service.api import start as run_data
        run_data()

    elif args.service == "ai":
        from services.ai_service.api import start as run_ai
        run_ai()

    elif args.service == "gateway":
        from services.gateway.app import start as run_gateway
        run_gateway()

    elif args.service == "all":
        from services.service_manager import MicroservicesManager
        mgr = MicroservicesManager()
        mgr.start_all()


if __name__ == "__main__":
    main()
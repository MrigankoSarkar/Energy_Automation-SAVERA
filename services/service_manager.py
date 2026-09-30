"""
Microservices Orchestrator & Supervisor for EnergyAutomation.
Modeled after AutoCAD and MATLAB multi-process decoupled service managers.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("services.service_manager")
REPO_ROOT = Path(__file__).resolve().parent.parent


class MicroservicesManager:
    """
    Manages process lifecycles for decoupled EnergyAutomation microservices:
    - Gateway (Port 8000)
    - Core Automation (Port 8001)
    - Data & Telemetry (Port 8002)
    - AI Advisory (Port 8003)
    - Plotly Dash BI (Port 8050)
    """

    SERVICES_MAP = {
        "core": ("services.core_automation.api", 8001),
        "data": ("services.data_service.api", 8002),
        "ai": ("services.ai_service.api", 8003),
        "gateway": ("services.gateway.app", 8000),
        "dash": ("services.dash_service.app", 8050),
    }

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}

    def start_service(self, name: str, detached: bool = False) -> Optional[subprocess.Popen]:
        if name not in self.SERVICES_MAP:
            print(f"Unknown service: {name}. Available: {list(self.SERVICES_MAP.keys())}")
            return None

        module_path, port = self.SERVICES_MAP[name]
        print(f"[*] Starting {name} microservice on port {port} ({module_path})...")

        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        cmd = [sys.executable, "-m", module_path]

        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            creationflags=flags if detached else 0,
        )
        self.processes[name] = proc
        print(f"[+] Service '{name}' started (PID: {proc.pid}, Port: {port}).")
        return proc

    def start_all(self):
        print("=" * 65)
        print("EnergyAutomation — Starting Decoupled Microservices Architecture")
        print("Inspired by AutoCAD / MATLAB Modular Service Architecture")
        print("=" * 65)

        # Launch services in logical dependency order: data -> core -> ai -> gateway -> dash
        order = ["data", "core", "ai", "gateway", "dash"]
        for s in order:
            self.start_service(s, detached=False)
            time.sleep(1.0)

        print("\nAll microservices launched:")
        print("  - Unified Gateway:       http://localhost:8000")
        print("  - Core Automation API:   http://localhost:8001")
        print("  - Data & Telemetry API:  http://localhost:8002")
        print("  - AI Advisory API:       http://localhost:8003")
        print("  - Plotly Dash Web BI:    http://localhost:8050")
        print("Press Ctrl+C to terminate all services.\n")

        try:
            while True:
                time.sleep(1.0)
                for name, p in list(self.processes.items()):
                    if p.poll() is not None:
                        print(f"[!] Warning: Microservice '{name}' stopped unexpectedly with code {p.returncode}")
        except KeyboardInterrupt:
            self.stop_all()

    def stop_all(self):
        print("\n[*] Stopping all running microservices...")
        for name, p in self.processes.items():
            if p.poll() is None:
                p.terminate()
                print(f"[-] Terminated service '{name}' (PID: {p.pid}).")
        print("[✓] All microservices stopped.")


if __name__ == "__main__":
    mgr = MicroservicesManager()
    if len(sys.argv) > 1 and sys.argv[1] in mgr.SERVICES_MAP:
        mgr.start_service(sys.argv[1])
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            mgr.stop_all()
    else:
        mgr.start_all()

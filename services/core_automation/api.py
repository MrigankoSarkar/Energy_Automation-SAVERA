"""
FastAPI REST API for Core Automation Microservice (Port 8001).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.core_automation.pipeline import CoreAutomationEngine

app = FastAPI(
    title="EnergyAutomation — Core Automation Service",
    description="Headless ingestion, parsing, validation, and Excel persistence microservice",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecoveryRequest(BaseModel):
    lookback_days: int = 30


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "core_automation",
        "port": 8001,
    }


@app.get("/api/v1/automation/status")
def get_status():
    engine = CoreAutomationEngine.get_instance()
    return engine.get_status()


@app.post("/api/v1/automation/run-cycle")
def run_cycle():
    engine = CoreAutomationEngine.get_instance()
    return engine.run_cycle()


@app.post("/api/v1/automation/recover-gaps")
def recover_gaps(req: RecoveryRequest):
    engine = CoreAutomationEngine.get_instance()
    return engine.run_gap_healing(days=req.lookback_days)


def start():
    port = int(os.getenv("AUTOMATION_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    start()

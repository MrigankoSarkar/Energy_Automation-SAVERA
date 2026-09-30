"""
FastAPI REST API for AI Advisory Microservice (Port 8003).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.ai_service.engine import get_ai_service

app = FastAPI(
    title="EnergyAutomation — AI Advisory Service",
    description="Google Gemini AI conversational energy intelligence and anomaly advisory service",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None


class AnomalyRequest(BaseModel):
    readings: Any


@app.get("/health")
def health():
    ai = get_ai_service()
    return {
        "status": "healthy",
        "service": "ai_service",
        "port": 8003,
        "configured": ai.is_configured(),
        "model": ai.model,
    }


@app.get("/api/v1/ai/status")
def status():
    ai = get_ai_service()
    st = ai.status()
    st["fallback_models"] = getattr(ai, "FALLBACK_MODELS", [])
    return st


@app.post("/api/v1/ai/ask")
def ask(req: AskRequest):
    ai = get_ai_service()
    return ai.ask(req.question, context_data=req.context)


@app.post("/api/v1/ai/test-connection")
@app.post("/api/v1/ai/test")
def test_connection():
    ai = get_ai_service()
    return ai.test_connection()


@app.post("/api/v1/ai/anomaly")
def anomaly_check(req: AnomalyRequest):
    ai = get_ai_service()
    return ai.local_anomaly_check(req.readings)


def start():
    port = int(os.getenv("AI_SERVICE_PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    start()

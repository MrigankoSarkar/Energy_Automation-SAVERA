"""
FastAPI REST API for Data & Telemetry Microservice (Port 8002).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
import os
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from services.data_service.provider import TelemetryDataProvider

app = FastAPI(
    title="EnergyAutomation — Data & Telemetry Service",
    description="Independent telemetry query and validation microservice",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = TelemetryDataProvider()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "data_service",
        "port": 8002,
        "workbook": str(provider.excel_path),
        "workbook_exists": provider.excel_path.exists(),
    }


@app.get("/api/v1/data/summary")
def get_summary(force_refresh: bool = False):
    summary = provider.get_summary(force_refresh=force_refresh)
    return asdict(summary)


@app.get("/api/v1/data/readings")
def get_readings(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000),
):
    df = provider.get_daily_dataframe()
    if df.empty:
        return {"count": 0, "records": []}

    df_filtered = df.copy()
    if start_date:
        df_filtered = df_filtered[df_filtered["Date"] >= start_date]
    if end_date:
        df_filtered = df_filtered[df_filtered["Date"] <= end_date]

    df_filtered = df_filtered.tail(limit)

    # Convert Date to string
    df_filtered["Date"] = df_filtered["Date"].dt.strftime("%Y-%m-%d")
    records = df_filtered.to_dict(orient="records")
    return {"count": len(records), "records": records}


@app.get("/api/v1/data/feeders")
def get_feeders():
    feeders = provider.get_feeders_catalog()
    return {"count": len(feeders), "feeders": feeders}


@app.get("/api/v1/data/quality")
def get_quality():
    return provider.get_data_quality()


def start():
    port = int(os.getenv("DATA_SERVICE_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    start()

"""
Unit tests for EnergyAutomation Microservices REST APIs.
Tests FastAPI applications for Data Service, AI Service, Core Automation, and API Gateway.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.data_service.api import app as data_app
from services.ai_service.api import app as ai_app
from services.core_automation.api import app as core_app
from services.gateway.app import app as gateway_app


# =========================================================================
# Data Service (Port 8002) Tests
# =========================================================================

def test_data_service_health():
    client = TestClient(data_app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data_service"
    assert data["port"] == 8002
    assert "workbook" in data


def test_data_service_summary():
    client = TestClient(data_app)
    response = client.get("/api/v1/data/summary")
    assert response.status_code == 200
    data = response.json()
    assert "is_active" in data
    assert "latest_kwh" in data
    assert "active_meters_count" in data


def test_data_service_readings():
    client = TestClient(data_app)
    response = client.get("/api/v1/data/readings", params={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "records" in data
    assert isinstance(data["records"], list)
    if data["count"] > 0:
        record = data["records"][0]
        assert "Date" in record


def test_data_service_feeders():
    client = TestClient(data_app)
    response = client.get("/api/v1/data/feeders")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "feeders" in data
    assert data["count"] > 0


def test_data_service_quality():
    client = TestClient(data_app)
    response = client.get("/api/v1/data/quality")
    assert response.status_code == 200
    data = response.json()
    assert "freshness_status" in data
    assert "formula_reconciliation_ok" in data


# =========================================================================
# AI Advisory Service (Port 8003) Tests
# =========================================================================

def test_ai_service_health():
    client = TestClient(ai_app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai_service"
    assert data["port"] == 8003
    assert "configured" in data


def test_ai_service_status():
    client = TestClient(ai_app)
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "model" in data
    assert "fallback_models" in data
    assert isinstance(data["fallback_models"], list)


def test_ai_service_test_connection():
    client = TestClient(ai_app)
    response = client.post("/api/v1/ai/test")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "model" in data
    assert "latency_ms" in data


def test_ai_service_ask():
    client = TestClient(ai_app)
    payload = {
        "question": "What is the peak energy consumption pattern?",
        "context": {"latest_kwh": 1250.0, "report_date": "2026-09-15"},
    }
    response = client.post("/api/v1/ai/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


# =========================================================================
# Core Automation Service (Port 8001) Tests
# =========================================================================

def test_core_automation_health():
    client = TestClient(core_app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "core_automation"
    assert data["port"] == 8001


def test_core_automation_status():
    client = TestClient(core_app)
    response = client.get("/api/v1/automation/status")
    assert response.status_code == 200
    data = response.json()
    assert "engine" in data
    assert "scheduler_running" in data
    assert "storage_path" in data


# =========================================================================
# API Gateway (Port 8000) Tests
# =========================================================================

def test_gateway_health():
    client = TestClient(gateway_app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["gateway_port"] == 8000
    assert "services" in data


def test_gateway_service_directory():
    client = TestClient(gateway_app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert data["gateway_port"] == 8000
    services = data["services"]
    assert "core_automation" in services
    assert "data_service" in services
    assert "ai_service" in services
    assert "dash_service" in services
    assert services["core_automation"]["port"] == 8001
    assert services["data_service"]["port"] == 8002
    assert services["ai_service"]["port"] == 8003
    assert services["dash_service"]["port"] == 8050

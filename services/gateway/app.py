"""
Unified API Gateway for EnergyAutomation (Port 8000).
Aggregates and proxies all microservice endpoints under a single reverse proxy.
"""

from __future__ import annotations

import os
import uvicorn
import requests
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="EnergyAutomation — Unified API Gateway",
    description="Central router and reverse proxy for EnergyAutomation microservices",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = {
    "core_automation": os.getenv("AUTOMATION_URL", "http://127.0.0.1:8001"),
    "data_service": os.getenv("DATA_URL", "http://127.0.0.1:8002"),
    "ai_service": os.getenv("AI_URL", "http://127.0.0.1:8003"),
    "dash_service": os.getenv("DASH_URL", "http://127.0.0.1:8050"),
}


@app.get("/health")
def health():
    results = {}
    overall = True

    for name, base_url in [
        ("core_automation", SERVICES["core_automation"]),
        ("data_service", SERVICES["data_service"]),
        ("ai_service", SERVICES["ai_service"]),
    ]:
        try:
            r = requests.get(f"{base_url}/health", timeout=1.5)
            if r.status_code == 200:
                results[name] = r.json()
            else:
                results[name] = {"status": "unhealthy", "code": r.status_code}
                overall = False
        except Exception as exc:
            results[name] = {"status": "offline", "error": str(exc)}
            overall = False

    return {
        "status": "healthy" if overall else "degraded",
        "gateway_port": 8000,
        "services": results,
    }


@app.get("/api/v1/services")
def list_services():
    return {
        "gateway_port": 8000,
        "services": {
            "core_automation": {"url": SERVICES["core_automation"], "port": 8001, "role": "Automation Engine"},
            "data_service": {"url": SERVICES["data_service"], "port": 8002, "role": "Telemetry & Validation"},
            "ai_service": {"url": SERVICES["ai_service"], "port": 8003, "role": "AI Advisor"},
            "dash_service": {"url": SERVICES["dash_service"], "port": 8050, "role": "Plotly Dash BI"},
        }
    }


async def proxy_request(service_url: str, path: str, request: Request):
    target_url = f"{service_url}{path}"
    try:
        req_headers = dict(request.headers)
        req_headers.pop("host", None)
        body = None
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()

        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=req_headers,
            params=dict(request.query_params),
            data=body,
            timeout=30,
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as exc:
        return JSONResponse(status_code=502, content={"error": f"Bad Gateway: {exc}"})


@app.api_route("/api/v1/automation/{full_path:path}", methods=["GET", "POST"])
async def automation_proxy(full_path: str, request: Request):
    return await proxy_request(SERVICES["core_automation"], f"/api/v1/automation/{full_path}", request)


@app.api_route("/api/v1/data/{full_path:path}", methods=["GET", "POST"])
async def data_proxy(full_path: str, request: Request):
    return await proxy_request(SERVICES["data_service"], f"/api/v1/data/{full_path}", request)


@app.api_route("/api/v1/ai/{full_path:path}", methods=["GET", "POST"])
async def ai_proxy(full_path: str, request: Request):
    return await proxy_request(SERVICES["ai_service"], f"/api/v1/ai/{full_path}", request)



def start():
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    start()

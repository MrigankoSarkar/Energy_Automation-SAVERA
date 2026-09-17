"""
Socket.IO Real-Time Alert Event Hub for EnergyAutomation.
Hosts an embedded ASGI Socket.IO server via python-socketio + uvicorn,
broadcasting alert creations, acknowledgments, and statistics in real-time.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import socketio
import uvicorn

logger = logging.getLogger(__name__)


class AlertSocketHub:
    """
    Real-Time Socket.IO Server Hub.
    Runs asynchronously in a background daemon thread and bridges
    AlertService events directly to connected desktop and web clients.
    """

    DEFAULT_PORT = 8765

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.active_port = port
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._lock = threading.Lock()

        # External service delegates
        self.get_alerts_handler: Optional[Callable[[], List[Dict[str, Any]]]] = None
        self.get_stats_handler: Optional[Callable[[], Dict[str, Any]]] = None
        self.ack_handler: Optional[Callable[[str], bool]] = None
        self.ack_all_handler: Optional[Callable[[], int]] = None

        # Socket.IO Async Server
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
        )
        self.app = socketio.ASGIApp(self.sio)
        self._register_events()

    def _find_free_port(self, start_port: int, max_attempts: int = 10) -> int:
        for p in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.host, p))
                    return p
            except OSError:
                continue
        return start_port

    def _register_events(self) -> None:
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"[Socket.IO Hub] Client connected: {sid}")
            try:
                stats = self.get_stats_handler() if self.get_stats_handler else {}
                alerts = self.get_alerts_handler() if self.get_alerts_handler else []
                await self.sio.emit("initial_state", {"stats": stats, "alerts": alerts}, to=sid)
            except Exception as exc:
                logger.warning(f"[Socket.IO Hub] Error sending initial state: {exc}")

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"[Socket.IO Hub] Client disconnected: {sid}")

        @self.sio.on("request_alerts")
        async def on_request_alerts(sid, data=None):
            alerts = self.get_alerts_handler() if self.get_alerts_handler else []
            await self.sio.emit("alerts_list", alerts, to=sid)

        @self.sio.on("request_stats")
        async def on_request_stats(sid, data=None):
            stats = self.get_stats_handler() if self.get_stats_handler else {}
            await self.sio.emit("alert_stats", stats, to=sid)

        @self.sio.on("acknowledge")
        async def on_acknowledge(sid, data):
            alert_id = data.get("alert_id") if isinstance(data, dict) else str(data)
            success = False
            if self.ack_handler and alert_id:
                success = self.ack_handler(alert_id)
            if success:
                await self.sio.emit("alert_acknowledged", {"alert_id": alert_id})
                stats = self.get_stats_handler() if self.get_stats_handler else {}
                await self.sio.emit("alert_stats", stats)

        @self.sio.on("acknowledge_all")
        async def on_acknowledge_all(sid, data=None):
            count = 0
            if self.ack_all_handler:
                count = self.ack_all_handler()
            await self.sio.emit("all_alerts_acknowledged", {"count": count})
            stats = self.get_stats_handler() if self.get_stats_handler else {}
            await self.sio.emit("alert_stats", stats)

    def start(self) -> bool:
        """Start the background Socket.IO server daemon."""
        with self._lock:
            if self._running:
                return True

            self.active_port = self._find_free_port(self.port)
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.active_port,
                log_level="warning",
                access_log=False,
            )
            self._server = uvicorn.Server(config)

            def _run():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._running = True
                try:
                    self._loop.run_until_complete(self._server.serve())
                except Exception as exc:
                    logger.warning(f"[Socket.IO Hub] Server ended: {exc}")
                finally:
                    self._running = False

            self._thread = threading.Thread(target=_run, name="AlertSocketHubWorker", daemon=True)
            self._thread.start()

            for _ in range(15):
                if self._running and self._loop and self._loop.is_running():
                    break
                time.sleep(0.05)

            logger.info(f"[Socket.IO Hub] Server running on http://{self.host}:{self.active_port}")
            return True

    def stop(self) -> None:
        """Gracefully stop the Socket.IO server."""
        with self._lock:
            if not self._running:
                return
            if self._server:
                self._server.should_exit = True
            self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_url(self) -> str:
        return f"http://{self.host}:{self.active_port}"

    def broadcast_alert(self, alert_data: Dict[str, Any]) -> None:
        """Thread-safe broadcast of a newly raised alert."""
        if not self._running or not self._loop or not self._loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.sio.emit("alert_created", alert_data),
                self._loop,
            )
            if self.get_stats_handler:
                stats = self.get_stats_handler()
                asyncio.run_coroutine_threadsafe(
                    self.sio.emit("alert_stats", stats),
                    self._loop,
                )
        except Exception as exc:
            logger.warning(f"[Socket.IO Hub] Failed to broadcast alert: {exc}")

    def broadcast_ack(self, alert_id: str) -> None:
        """Thread-safe broadcast of an alert acknowledgment."""
        if not self._running or not self._loop or not self._loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.sio.emit("alert_acknowledged", {"alert_id": alert_id}),
                self._loop,
            )
            if self.get_stats_handler:
                stats = self.get_stats_handler()
                asyncio.run_coroutine_threadsafe(
                    self.sio.emit("alert_stats", stats),
                    self._loop,
                )
        except Exception as exc:
            logger.warning(f"[Socket.IO Hub] Failed to broadcast ack: {exc}")

    def broadcast_ack_all(self, count: int) -> None:
        """Thread-safe broadcast of all-acknowledged event."""
        if not self._running or not self._loop or not self._loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.sio.emit("all_alerts_acknowledged", {"count": count}),
                self._loop,
            )
            if self.get_stats_handler:
                stats = self.get_stats_handler()
                asyncio.run_coroutine_threadsafe(
                    self.sio.emit("alert_stats", stats),
                    self._loop,
                )
        except Exception as exc:
            logger.warning(f"[Socket.IO Hub] Failed to broadcast ack-all: {exc}")

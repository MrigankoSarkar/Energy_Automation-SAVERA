"""
EnergyAutomation Event System.
Provides an in-process thread-safe event bus for decoupling services.
"""

from app.events.bus import Event, EventBus, EventType, get_event_bus

__all__ = ["Event", "EventBus", "EventType", "get_event_bus"]

from app.events.bus import Event, EventBus, EventType


def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    def handler(evt: Event):
        received.append(evt)

    unsub = bus.subscribe(EventType.EXCEL_UPDATED, handler)
    bus.publish(EventType.EXCEL_UPDATED, {"cells": 16})

    assert len(received) == 1
    assert received[0].event_type == EventType.EXCEL_UPDATED.value
    assert received[0].data["cells"] == 16

    # Test unsubscribe
    unsub()
    bus.publish(EventType.EXCEL_UPDATED, {"cells": 10})
    assert len(received) == 1


def test_event_bus_error_isolation():
    bus = EventBus()
    results = []

    def failing_handler(evt: Event):
        raise RuntimeError("Power BI network timeout simulation")

    def successful_handler(evt: Event):
        results.append(evt.data.get("status"))

    bus.subscribe(EventType.PROCESSING_COMPLETED, failing_handler)
    bus.subscribe(EventType.PROCESSING_COMPLETED, successful_handler)

    # Should not raise exception even if failing_handler explodes
    bus.publish(EventType.PROCESSING_COMPLETED, {"status": "ok"})
    assert results == ["ok"]


def test_event_bus_wildcard_and_history():
    bus = EventBus(max_history=5)
    wildcard_events = []

    bus.subscribe("*", lambda e: wildcard_events.append(e.event_type))

    for i in range(7):
        bus.publish(f"test.event.{i}")

    assert len(wildcard_events) == 7
    history = bus.get_history()
    assert len(history) == 5
    assert history[-1].event_type == "test.event.6"

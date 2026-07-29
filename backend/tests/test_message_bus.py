"""Unit tests for the in-memory message bus (no external dependencies)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.bus.message_bus import MessageBus
from app.schemas.sensor_packet import SensorPacket


def _packet(sensor_type: str = "people_location") -> SensorPacket:
    return SensorPacket(
        timestamp=datetime.now(timezone.utc),
        device_name="test_device",
        sensor_type=sensor_type,
        selected_zone="Kitchener",
        selected_business_type="Coffee Shop / Cafe",
        radius_km=5,
        indicator="green",
        summary_text="test packet",
        metrics=[],
        meta={},
    )


def test_register_and_query_sensor():
    bus = MessageBus()
    bus.register_sensor("people_location", "people_location_monitor")
    assert bus.is_registered("people_location")
    assert bus.get_registered_sensors()["people_location"] == "people_location_monitor"


def test_publish_updates_latest_and_history():
    bus = MessageBus()
    bus.register_sensor("people_location", "people_location_monitor")
    packet = _packet()
    bus.publish(packet)
    assert bus.get_latest_packet("people_location") is packet
    assert bus.get_packet_history("people_location") == [packet]


def test_publish_unregistered_sensor_raises():
    bus = MessageBus()
    with pytest.raises(ValueError):
        bus.publish(_packet("unregistered_type"))


def test_unknown_sensor_queries_are_safe():
    bus = MessageBus()
    assert bus.get_latest_packet("nope") is None
    assert bus.get_packet_history("nope") == []


def test_history_is_bounded():
    """History is capped so the in-memory bus cannot grow without bound."""
    bus = MessageBus(history_maxlen=3)
    bus.register_sensor("people_location", "people_location_monitor")
    for _ in range(10):
        bus.publish(_packet())
    history = bus.get_packet_history("people_location")
    assert len(history) == 3  # only the most recent 3 are retained

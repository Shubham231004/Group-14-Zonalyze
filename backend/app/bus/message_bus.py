import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from app.schemas.sensor_packet import SensorPacket

# Cap per-sensor history so the in-memory bus cannot grow without bound
# (previously an unbounded list -> memory-exhaustion risk over time / under load).
DEFAULT_HISTORY_MAXLEN = 500


class MessageBus:
    def __init__(self, history_maxlen: int = DEFAULT_HISTORY_MAXLEN):
        self._history_maxlen = history_maxlen
        # A single lock guards all mutable state; the bus is a process-wide
        # singleton shared across requests, so access must be thread-safe.
        self._lock = threading.Lock()
        self._registered_sensors: Dict[str, str] = {}
        self._latest_packets: Dict[str, SensorPacket] = {}
        self._packet_history: Dict[str, Deque[SensorPacket]] = {}

    def register_sensor(self, sensor_type: str, device_name: str) -> None:
        with self._lock:
            self._registered_sensors[sensor_type] = device_name
            if sensor_type not in self._packet_history:
                self._packet_history[sensor_type] = deque(maxlen=self._history_maxlen)

    def is_registered(self, sensor_type: str) -> bool:
        with self._lock:
            return sensor_type in self._registered_sensors

    def publish(self, packet: SensorPacket) -> None:
        sensor_type = packet.sensor_type
        with self._lock:
            if sensor_type not in self._registered_sensors:
                raise ValueError(
                    f"Sensor type '{sensor_type}' is not registered in the message bus."
                )
            self._latest_packets[sensor_type] = packet
            self._packet_history[sensor_type].append(packet)

    def get_latest_packet(self, sensor_type: str) -> Optional[SensorPacket]:
        with self._lock:
            return self._latest_packets.get(sensor_type)

    def get_registered_sensors(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._registered_sensors)

    def get_packet_history(self, sensor_type: str) -> List[SensorPacket]:
        with self._lock:
            history = self._packet_history.get(sensor_type)
            return list(history) if history else []

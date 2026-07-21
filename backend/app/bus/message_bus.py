from typing import Dict, List, Optional
from app.schemas.sensor_packet import SensorPacket


class MessageBus:
    def __init__(self):
        self._registered_sensors: Dict[str, str] = {}
        self._latest_packets: Dict[str, SensorPacket] = {}
        self._packet_history: Dict[str, List[SensorPacket]] = {}

    def register_sensor(self, sensor_type: str, device_name: str) -> None:
        self._registered_sensors[sensor_type] = device_name

        if sensor_type not in self._packet_history:
            self._packet_history[sensor_type] = []

    def is_registered(self, sensor_type: str) -> bool:
        return sensor_type in self._registered_sensors

    def publish(self, packet: SensorPacket) -> None:
        sensor_type = packet.sensor_type

        if sensor_type not in self._registered_sensors:
            raise ValueError(
                f"Sensor type '{sensor_type}' is not registered in the message bus."
            )

        self._latest_packets[sensor_type] = packet
        self._packet_history[sensor_type].append(packet)

    def get_latest_packet(self, sensor_type: str) -> Optional[SensorPacket]:
        return self._latest_packets.get(sensor_type)

    def get_registered_sensors(self) -> Dict[str, str]:
        return self._registered_sensors

    def get_packet_history(self, sensor_type: str) -> List[SensorPacket]:
        return self._packet_history.get(sensor_type, [])
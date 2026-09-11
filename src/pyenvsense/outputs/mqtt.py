from __future__ import annotations

import json
import socket
from datetime import datetime

import paho.mqtt.client as mqtt

from pyenvsense.config import MqttConfig
from pyenvsense.reading import flat_payload


def mqtt_topic(hostname: str, sensor_id: str) -> str:
    return f"{hostname}/envsense/{sensor_id}/json"


class MqttOutput:
    def __init__(self, config: MqttConfig, hostname: str | None = None) -> None:
        self._qos = config.qos
        self._hostname = hostname or socket.gethostname()
        self._client = _make_client()
        self._client.connect(config.host, config.port)
        self._client.loop_start()

    def emit(
        self,
        sensor_id: str,
        sensor_type: str,
        when: datetime,
        fields: dict[str, dict[str, float | str]],
    ) -> None:
        del sensor_type
        payload = flat_payload(when, fields)
        topic = mqtt_topic(self._hostname, sensor_id)
        self._client.publish(topic, json.dumps(payload), qos=self._qos)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


def _make_client() -> mqtt.Client:
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        return mqtt.Client(callback_api.VERSION2)
    return mqtt.Client()

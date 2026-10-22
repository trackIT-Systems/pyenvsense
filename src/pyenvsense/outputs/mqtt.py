from __future__ import annotations

import json
import logging
import socket
from datetime import datetime

import paho.mqtt.client as mqtt

from pyenvsense.config import MqttConfig
from pyenvsense.reading import flat_payload

log = logging.getLogger(__name__)


def mqtt_topic(hostname: str, sensor_id: str) -> str:
    return f"{hostname}/envsense/{sensor_id}/json"


class MqttOutput:
    def __init__(self, config: MqttConfig, hostname: str | None = None) -> None:
        self._qos = config.qos
        self._hostname = hostname or socket.gethostname()
        self._broker = f"{config.host}:{config.port}"
        self._connected = False
        self._was_connected = False
        self._refused: str | None = None
        self._client = _make_client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
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

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        del client, userdata, flags, properties
        if _is_failure(reason_code):
            if self._refused != str(reason_code):
                log.warning("MQTT broker %s refused the connection: %s", self._broker, reason_code)
            else:
                log.debug("MQTT broker %s refused the connection again: %s", self._broker, reason_code)
            self._refused = str(reason_code)
            return
        self._refused = None
        self._connected = True
        if self._was_connected:
            log.info("Reconnected to MQTT broker %s", self._broker)
        else:
            log.info("Connected to MQTT broker %s", self._broker)
        self._was_connected = True

    def _on_disconnect(self, client, userdata, *args) -> None:
        # paho's VERSION2 callback passes (flags, reason_code, properties), VERSION1 only (rc).
        del client, userdata
        reason_code = args[1] if len(args) >= 2 else args[0]
        was_connected, self._connected = self._connected, False
        if was_connected and _is_failure(reason_code):
            log.warning("Lost connection to MQTT broker %s: %s", self._broker, reason_code)
        else:
            log.debug("Disconnected from MQTT broker %s: %s", self._broker, reason_code)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


def _is_failure(reason_code: object) -> bool:
    is_failure = getattr(reason_code, "is_failure", None)
    if is_failure is not None:
        return bool(is_failure)
    return reason_code != 0


def _make_client() -> mqtt.Client:
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        return mqtt.Client(callback_api.VERSION2)
    return mqtt.Client()

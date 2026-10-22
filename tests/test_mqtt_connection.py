from __future__ import annotations

import logging

import pytest
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

import pyenvsense.outputs.mqtt as mqtt_output
from pyenvsense.config import MqttConfig
from pyenvsense.outputs.mqtt import MqttOutput


class FakeClient:
    def connect(self, host, port) -> None:
        return

    def loop_start(self) -> None:
        return


SUCCESS = ReasonCode(PacketTypes.CONNACK, "Success")
REFUSED = ReasonCode(PacketTypes.CONNACK, "Not authorized")
LOST = ReasonCode(PacketTypes.DISCONNECT, "Unspecified error")
NORMAL = ReasonCode(PacketTypes.DISCONNECT, "Normal disconnection")


@pytest.fixture
def output(monkeypatch, caplog) -> MqttOutput:
    caplog.set_level(logging.DEBUG, logger="pyenvsense.outputs.mqtt")
    monkeypatch.setattr(mqtt_output, "_make_client", FakeClient)
    return MqttOutput(MqttConfig(enabled=True, host="broker", port=1883, qos=0), hostname="node")


def _logged(caplog) -> list[tuple[int, str]]:
    return [(r.levelno, r.getMessage()) for r in caplog.records if r.levelno > logging.DEBUG]


def test_connect_lose_reconnect(output, caplog) -> None:
    output._on_connect(None, None, None, SUCCESS, None)
    output._on_disconnect(None, None, None, LOST, None)
    output._on_disconnect(None, None, None, LOST, None)
    output._on_connect(None, None, None, SUCCESS, None)

    assert _logged(caplog) == [
        (logging.INFO, "Connected to MQTT broker broker:1883"),
        (logging.WARNING, "Lost connection to MQTT broker broker:1883: Unspecified error"),
        (logging.INFO, "Reconnected to MQTT broker broker:1883"),
    ]


def test_normal_disconnect_is_debug(output, caplog) -> None:
    output._on_connect(None, None, None, SUCCESS, None)
    output._on_disconnect(None, None, None, NORMAL, None)

    assert _logged(caplog) == [(logging.INFO, "Connected to MQTT broker broker:1883")]


def test_refused_connection_is_logged_once(output, caplog) -> None:
    for _ in range(3):
        output._on_connect(None, None, None, REFUSED, None)
    output._on_connect(None, None, None, SUCCESS, None)

    assert _logged(caplog) == [
        (logging.WARNING, "MQTT broker broker:1883 refused the connection: Not authorized"),
        (logging.INFO, "Connected to MQTT broker broker:1883"),
    ]

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from pyenvsense.outputs.mqtt import mqtt_topic
from pyenvsense.reading import flat_payload, local_iso


def test_mqtt_topic_format() -> None:
    assert mqtt_topic("node-01", "ambient") == "node-01/envsense/ambient/json"


def test_mqtt_payload_is_flat_without_sensor_id() -> None:
    when = datetime(2026, 6, 1, 9, 10, 21, 994007, tzinfo=timezone(timedelta(hours=2)))
    payload = flat_payload(
        when,
        {
            "temperature": {"value": 21.5, "unit": "C"},
            "humidity": {"value": 48.0, "unit": "%"},
        },
    )
    assert payload == {
        "_time": "2026-06-01 09:10:21.994007+02:00",
        "Temperature (°C)": 21.5,
        "Humidity (%)": 48.0,
    }
    assert "sensor_id" not in payload
    assert "fields" not in payload
    assert "type" not in payload


def test_cli_payload_includes_sensor_id() -> None:
    when = datetime(2026, 6, 1, 9, 10, 21, 994007, tzinfo=timezone(timedelta(hours=2)))
    payload = flat_payload(
        when,
        {"temperature": {"value": 21.5, "unit": "C"}},
        sensor_id="inside",
    )
    assert payload["sensor_id"] == "inside"
    assert payload["Temperature (°C)"] == 21.5
    assert payload["_time"] == "2026-06-01 09:10:21.994007+02:00"


def test_local_iso_uses_space_and_offset() -> None:
    when = datetime(2026, 6, 1, 9, 10, 21, 994007, tzinfo=ZoneInfo("Europe/Berlin"))
    assert local_iso(when) == "2026-06-01 09:10:21.994007+02:00"

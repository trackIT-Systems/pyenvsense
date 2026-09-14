from __future__ import annotations

from datetime import datetime, timezone

KNOWN_FIELD_KEYS = {
    "temperature": "Temperature (°C)",
    "humidity": "Humidity (%)",
    "in1": "In1 (V)",
    "in2": "In2 (V)",
    "in3": "In3 (V)",
    "in4": "In4 (V)",
}


def utc_iso(when: datetime) -> str:
    return (
        when.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def local_iso(when: datetime) -> str:
    return when.astimezone().isoformat(sep=" ")


def field_display_key(name: str, unit: str) -> str:
    mapped = KNOWN_FIELD_KEYS.get(name)
    if mapped is not None:
        return mapped
    label = name.replace("_", " ").title()
    return f"{label} ({unit})"


def flat_payload(
    when: datetime,
    fields: dict[str, dict[str, float | str]],
    *,
    sensor_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {}
    if sensor_id is not None:
        payload["sensor_id"] = sensor_id
    payload["_time"] = local_iso(when)
    for name, field in fields.items():
        payload[field_display_key(name, str(field["unit"]))] = field["value"]
    return payload


def fields_from_measurements(measurements) -> dict[str, dict[str, float | str]]:
    return {
        name: {"value": measurement.value, "unit": measurement.unit}
        for name, measurement in measurements.items()
    }

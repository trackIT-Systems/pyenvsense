from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pyenvsense.errors import ConfigError

DEFAULT_CONFIG_PATH = Path("/boot/firmware/envsense.yml")
DEFAULT_I2C_BUS = 1
DEFAULT_INTERVAL_S = 60.0
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_QOS = 0
DEFAULT_CSV_PATH = Path("/data")


@dataclass(frozen=True)
class SensorConfig:
    id: str
    type: str
    address: int
    i2c_bus: int
    interval_s: float


@dataclass(frozen=True)
class CsvConfig:
    enabled: bool
    path: Path


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool
    host: str
    port: int
    qos: int


@dataclass(frozen=True)
class DaemonConfig:
    csv: CsvConfig
    mqtt: MqttConfig


@dataclass(frozen=True)
class AppConfig:
    path: Path
    sensors: tuple[SensorConfig, ...]
    daemon: DaemonConfig


def resolve_config_path(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser()
    return DEFAULT_CONFIG_PATH


def load_config(path: Path | None = None) -> AppConfig:
    resolved = resolve_config_path(path)
    if not resolved.is_file():
        raise ConfigError(f"Config file not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {resolved}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Config root must be a mapping: {resolved}")
    return parse_config(raw, resolved)


def parse_config(raw: dict[str, Any], path: Path) -> AppConfig:
    hardware = _require_mapping(raw.get("hardware"), "hardware")
    default_bus = _parse_int(hardware.get("i2c_bus", DEFAULT_I2C_BUS), "hardware.i2c_bus")
    default_interval = _parse_positive_float(
        hardware.get("interval_s", DEFAULT_INTERVAL_S), "hardware.interval_s"
    )
    sensors_raw = hardware.get("sensors")
    if not isinstance(sensors_raw, list) or not sensors_raw:
        raise ConfigError("hardware.sensors must be a non-empty list")

    sensors: list[SensorConfig] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(sensors_raw):
        prefix = f"hardware.sensors[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{prefix} must be a mapping")
        sensor = _parse_sensor(item, prefix, default_bus, default_interval)
        if sensor.id in seen_ids:
            raise ConfigError(f"Duplicate sensor id '{sensor.id}'")
        seen_ids.add(sensor.id)
        sensors.append(sensor)

    daemon_raw = raw.get("daemon", {})
    if daemon_raw is None:
        daemon_raw = {}
    daemon = _parse_daemon(_require_mapping(daemon_raw, "daemon"))
    return AppConfig(path=path, sensors=tuple(sensors), daemon=daemon)


def _parse_sensor(
    item: dict[str, Any],
    prefix: str,
    default_bus: int,
    default_interval: float,
) -> SensorConfig:
    sensor_id = item.get("id")
    if not isinstance(sensor_id, str) or not sensor_id.strip():
        raise ConfigError(f"{prefix}.id must be a non-empty string")
    sensor_type = item.get("type")
    if not isinstance(sensor_type, str) or not sensor_type.strip():
        raise ConfigError(f"{prefix}.type must be a non-empty string")
    if "address" not in item:
        raise ConfigError(f"{prefix}.address is required")
    return SensorConfig(
        id=sensor_id.strip(),
        type=sensor_type.strip(),
        address=_parse_address(item["address"], f"{prefix}.address"),
        i2c_bus=_parse_int(item.get("i2c_bus", default_bus), f"{prefix}.i2c_bus"),
        interval_s=_parse_positive_float(
            item.get("interval_s", default_interval), f"{prefix}.interval_s"
        ),
    )


def _parse_daemon(raw: dict[str, Any]) -> DaemonConfig:
    csv_raw = raw.get("csv", {})
    if csv_raw is None:
        csv_raw = {}
    csv_raw = _require_mapping(csv_raw, "daemon.csv")
    mqtt_raw = raw.get("mqtt", {})
    if mqtt_raw is None:
        mqtt_raw = {}
    mqtt_raw = _require_mapping(mqtt_raw, "daemon.mqtt")

    csv_path = csv_raw.get("path", DEFAULT_CSV_PATH)
    if not isinstance(csv_path, (str, Path)):
        raise ConfigError("daemon.csv.path must be a directory path")

    return DaemonConfig(
        csv=CsvConfig(
            enabled=_parse_bool(csv_raw.get("enabled", True), "daemon.csv.enabled"),
            path=Path(csv_path),
        ),
        mqtt=MqttConfig(
            enabled=_parse_bool(mqtt_raw.get("enabled", True), "daemon.mqtt.enabled"),
            host=_parse_str(mqtt_raw.get("host", DEFAULT_MQTT_HOST), "daemon.mqtt.host"),
            port=_parse_int(mqtt_raw.get("port", DEFAULT_MQTT_PORT), "daemon.mqtt.port"),
            qos=_parse_mqtt_qos(mqtt_raw.get("qos", DEFAULT_MQTT_QOS)),
        ),
    )


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _parse_address(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be an I2C address")
    if isinstance(value, int):
        return _check_address(value, name)
    if isinstance(value, str):
        try:
            return _check_address(int(value, 0), name)
        except ValueError as exc:
            raise ConfigError(f"{name} is not a valid address: {value!r}") from exc
    raise ConfigError(f"{name} must be an int or hex string")


def _check_address(value: int, name: str) -> int:
    if not 0 <= value <= 0x7F:
        raise ConfigError(f"{name} must be a 7-bit I2C address (0-127)")
    return value


def _parse_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer")
    return value


def _parse_positive_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number")
    result = float(value)
    if result <= 0:
        raise ConfigError(f"{name} must be > 0")
    return result


def _parse_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _parse_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _parse_mqtt_qos(value: Any) -> int:
    qos = _parse_int(value, "daemon.mqtt.qos")
    if qos not in (0, 1, 2):
        raise ConfigError("daemon.mqtt.qos must be 0, 1, or 2")
    return qos

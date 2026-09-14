from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pyenvsense.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_I2C_BUS,
    DEFAULT_INTERVAL_S,
    load_config,
    parse_config,
    resolve_config_path,
)
from pyenvsense.errors import ConfigError

MINIMAL = {
    "hardware": {
        "sensors": [
            {"id": "ambient", "type": "sht4x", "address": "0x44"},
        ]
    }
}


def test_default_config_path() -> None:
    assert resolve_config_path(None) == DEFAULT_CONFIG_PATH
    assert resolve_config_path(Path("/tmp/custom.yml")) == Path("/tmp/custom.yml")


def test_load_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    with pytest.raises(ConfigError, match="not found"):
        load_config(missing)


def test_parse_defaults() -> None:
    cfg = parse_config(MINIMAL, Path("mem.yml"))
    sensor = cfg.sensors[0]
    assert sensor.i2c_bus == DEFAULT_I2C_BUS
    assert sensor.interval_s == DEFAULT_INTERVAL_S
    assert sensor.address == 0x44
    assert cfg.daemon.csv.enabled is True
    assert cfg.daemon.csv.path == Path("/data")
    assert cfg.daemon.mqtt.enabled is True
    assert cfg.daemon.mqtt.host == "localhost"


def test_per_sensor_bus_and_interval() -> None:
    raw = {
        "hardware": {
            "i2c_bus": 1,
            "interval_s": 60,
            "sensors": [
                {
                    "id": "ambient",
                    "type": "sht4x",
                    "address": 0x44,
                    "interval_s": 30,
                },
                {
                    "id": "loft",
                    "type": "sht3x",
                    "address": "0x45",
                    "i2c_bus": 3,
                    "interval_s": 120,
                },
            ],
        }
    }
    cfg = parse_config(raw, Path("mem.yml"))
    assert cfg.sensors[0].i2c_bus == 1
    assert cfg.sensors[0].interval_s == 30
    assert cfg.sensors[1].i2c_bus == 3
    assert cfg.sensors[1].address == 0x45
    assert cfg.sensors[1].interval_s == 120


def test_duplicate_ids() -> None:
    raw = {
        "hardware": {
            "sensors": [
                {"id": "ambient", "type": "sht4x", "address": 0x44},
                {"id": "ambient", "type": "sht3x", "address": 0x45},
            ]
        }
    }
    with pytest.raises(ConfigError, match="Duplicate"):
        parse_config(raw, Path("mem.yml"))


def test_rpi_sensors_omit_address() -> None:
    raw = {
        "hardware": {
            "i2c_bus": 1,
            "sensors": [
                {"id": "soc", "type": "rpi_cpu"},
                {"id": "rp1", "type": "rpi_rp1", "interval_s": 10},
                {"id": "pmic", "type": "rpi_pmic"},
            ],
        }
    }
    cfg = parse_config(raw, Path("mem.yml"))
    assert [s.type for s in cfg.sensors] == ["rpi_cpu", "rpi_rp1", "rpi_pmic"]
    assert all(s.address is None and s.i2c_bus is None for s in cfg.sensors)
    assert cfg.sensors[1].interval_s == 10


def test_rpi_rejects_i2c_fields() -> None:
    raw = {
        "hardware": {
            "sensors": [
                {"id": "soc", "type": "rpi_cpu", "address": 0x44},
            ]
        }
    }
    with pytest.raises(ConfigError, match="must not be set"):
        parse_config(raw, Path("mem.yml"))


def test_unknown_type_still_requires_address() -> None:
    raw = {
        "hardware": {
            "sensors": [{"id": "mystery", "type": "not-a-sensor"}]
        }
    }
    with pytest.raises(ConfigError, match="address is required"):
        parse_config(raw, Path("mem.yml"))


def test_sht_still_requires_address() -> None:
    with pytest.raises(ConfigError, match="address is required"):
        parse_config(
            {"hardware": {"sensors": [{"id": "ambient", "type": "sht4x"}]}},
            Path("mem.yml"),
        )


def test_empty_sensors() -> None:
    with pytest.raises(ConfigError, match="non-empty"):
        parse_config({"hardware": {"sensors": []}}, Path("mem.yml"))


def test_load_yaml_file(tmp_path: Path) -> None:
    path = tmp_path / "envsense.yml"
    path.write_text(yaml.safe_dump(MINIMAL), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.path == path
    assert cfg.sensors[0].id == "ambient"


def test_mqtt_qos_invalid() -> None:
    raw = {
        "hardware": MINIMAL["hardware"],
        "daemon": {"mqtt": {"qos": 5}},
    }
    with pytest.raises(ConfigError, match="qos"):
        parse_config(raw, Path("mem.yml"))


def test_example_config_parses() -> None:
    example = Path(__file__).resolve().parents[1] / "config" / "envsense.yml"
    cfg = load_config(example)
    assert [s.id for s in cfg.sensors] == ["inside", "outside"]
    assert all(s.type == "sht3x" for s in cfg.sensors)
    assert all(s.i2c_bus == 0 for s in cfg.sensors)
    assert all(s.interval_s == cfg.sensors[0].interval_s for s in cfg.sensors)
    assert cfg.sensors[0].interval_s > 0
    assert cfg.sensors[0].address == 0x44
    assert cfg.sensors[1].address == 0x45

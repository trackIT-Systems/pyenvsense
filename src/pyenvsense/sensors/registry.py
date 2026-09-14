from __future__ import annotations

from importlib import import_module
from importlib.metadata import entry_points

from pyenvsense.config import SensorConfig
from pyenvsense.errors import (
    DriverNotInstalledError,
    SensorUnavailableError,
    UnknownSensorTypeError,
)
from pyenvsense.sensors.base import Sensor

BUILTIN_SENSORS = {
    "sht4x": "pyenvsense.sensors.sht4x:Sht4xSensor",
    "sht3x": "pyenvsense.sensors.sht3x:Sht3xSensor",
    "rpi_cpu": "pyenvsense.sensors.rpi:RpiCpuSensor",
    "rpi_rp1": "pyenvsense.sensors.rpi:RpiRp1Sensor",
    "rpi_pmic": "pyenvsense.sensors.rpi:RpiPmicSensor",
}


def sensor_types() -> dict[str, type[Sensor]]:
    loaded: dict[str, type[Sensor]] = {}
    for name, spec in BUILTIN_SENSORS.items():
        loaded[name] = _load_spec(spec)
    for entry in entry_points(group="pyenvsense.sensors"):
        loaded[entry.name] = entry.load()
    return loaded


def get_sensor_class(sensor_type: str) -> type[Sensor]:
    types = sensor_types()
    try:
        return types[sensor_type]
    except KeyError as exc:
        raise UnknownSensorTypeError(sensor_type) from exc


def create_sensor(config: SensorConfig) -> Sensor:
    cls = get_sensor_class(config.type)
    if not cls.driver_available():
        extra = getattr(cls, "extra", "")
        if extra:
            raise DriverNotInstalledError(extra)
        raise SensorUnavailableError(config.type)
    return cls(config)


def driver_available(sensor_type: str) -> bool:
    try:
        return get_sensor_class(sensor_type).driver_available()
    except UnknownSensorTypeError:
        return False


def _load_spec(spec: str) -> type[Sensor]:
    module_name, _, attr = spec.partition(":")
    module = import_module(module_name)
    return getattr(module, attr)

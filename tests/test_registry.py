from pyenvsense.errors import UnknownSensorTypeError
from pyenvsense.sensors.registry import driver_available, get_sensor_class, sensor_types
from pyenvsense.sensors.sht3x import Sht3xSensor
from pyenvsense.sensors.sht4x import Sht4xSensor


def test_builtin_types() -> None:
    types = sensor_types()
    assert types["sht4x"] is Sht4xSensor
    assert types["sht3x"] is Sht3xSensor


def test_unknown_type() -> None:
    try:
        get_sensor_class("not-a-sensor")
    except UnknownSensorTypeError as exc:
        assert exc.sensor_type == "not-a-sensor"
    else:
        raise AssertionError("expected UnknownSensorTypeError")


def test_driver_available_without_extras() -> None:
    assert driver_available("sht4x") is Sht4xSensor.driver_available()
    assert driver_available("unknown") is False

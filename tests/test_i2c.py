from types import SimpleNamespace

from pyenvsense.sensors.i2c import (
    i2c_device_path,
    sht_humidity,
    sht_temperature,
    signal_value,
)


def test_i2c_device_path() -> None:
    assert i2c_device_path(0) == "/dev/i2c-0"
    assert i2c_device_path(1) == "/dev/i2c-1"


def test_signal_value_from_object_or_float() -> None:
    assert signal_value(21.5) == 21.5
    assert signal_value(SimpleNamespace(value=48.0)) == 48.0


def test_sht_values_match_datasheet_resolution() -> None:
    assert sht_temperature(23.417892345) == 23.42
    assert sht_humidity(SimpleNamespace(value=48.001234)) == 48.0
    assert sht_humidity(41.996) == 42.0

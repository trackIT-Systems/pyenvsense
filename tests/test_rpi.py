from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from pyenvsense.config import SensorConfig
from pyenvsense.errors import SensorUnavailableError
from pyenvsense.sensors.registry import create_sensor, driver_available
from pyenvsense.sensors.rpi import RpiCpuSensor, RpiPmicSensor, RpiRp1Sensor


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rpi_config(sensor_type: str) -> SensorConfig:
    return SensorConfig(
        id="board",
        type=sensor_type,
        address=None,
        i2c_bus=None,
        interval_s=60.0,
    )


def test_cpu_prefers_hwmon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hwmon = tmp_path / "hwmon"
    _write(hwmon / "hwmon2" / "name", "cpu_thermal\n")
    _write(hwmon / "hwmon2" / "temp1_input", "54830\n")
    thermal = tmp_path / "thermal_zone0" / "temp"
    _write(thermal, "10000\n")
    monkeypatch.setattr("pyenvsense.sensors.rpi.HWMON_ROOT", hwmon)
    monkeypatch.setattr("pyenvsense.sensors.rpi.THERMAL_ZONE0_TEMP", thermal)
    sensor = RpiCpuSensor(_rpi_config("rpi_cpu"))
    reading = sensor.read()
    assert reading["temperature"].value == pytest.approx(54.83)
    assert reading["temperature"].unit == "C"
    assert RpiCpuSensor.driver_available() is True


def test_cpu_falls_back_to_thermal_zone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hwmon = tmp_path / "hwmon"
    hwmon.mkdir()
    thermal = tmp_path / "thermal_zone0" / "temp"
    _write(thermal, "41250\n")
    monkeypatch.setattr("pyenvsense.sensors.rpi.HWMON_ROOT", hwmon)
    monkeypatch.setattr("pyenvsense.sensors.rpi.THERMAL_ZONE0_TEMP", thermal)
    sensor = RpiCpuSensor(_rpi_config("rpi_cpu"))
    assert sensor.read()["temperature"].value == pytest.approx(41.25)


def test_rp1_temp_and_partial_voltages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hwmon = tmp_path / "hwmon"
    chip = hwmon / "hwmon4"
    _write(chip / "name", "rp1_adc\n")
    _write(chip / "temp1_input", "53100\n")
    _write(chip / "in1_input", "2030\n")
    _write(chip / "in3_input", "1360\n")
    monkeypatch.setattr("pyenvsense.sensors.rpi.HWMON_ROOT", hwmon)
    sensor = RpiRp1Sensor(_rpi_config("rpi_rp1"))
    reading = sensor.read()
    assert reading["temperature"].value == pytest.approx(53.1)
    assert reading["in1"].value == pytest.approx(2.03)
    assert reading["in1"].unit == "V"
    assert reading["in3"].value == pytest.approx(1.36)
    assert "in2" not in reading
    assert "in4" not in reading
    assert RpiRp1Sensor.driver_available() is True


def test_rp1_unavailable_on_empty_sysfs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hwmon = tmp_path / "hwmon"
    hwmon.mkdir()
    monkeypatch.setattr("pyenvsense.sensors.rpi.HWMON_ROOT", hwmon)
    assert RpiRp1Sensor.driver_available() is False
    assert driver_available("rpi_rp1") is False
    with pytest.raises(SensorUnavailableError, match="rpi_rp1"):
        create_sensor(_rpi_config("rpi_rp1"))


def test_pmic_parses_vcgencmd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyenvsense.sensors.rpi.shutil.which", lambda _cmd: "/usr/bin/vcgencmd")

    def fake_run(*_args, **_kwargs):
        return CompletedProcess(
            args=["vcgencmd", "measure_temp", "pmic"],
            returncode=0,
            stdout="temp=51.3'C\n",
            stderr="",
        )

    monkeypatch.setattr("pyenvsense.sensors.rpi.subprocess.run", fake_run)
    sensor = RpiPmicSensor(_rpi_config("rpi_pmic"))
    assert sensor.read()["temperature"].value == pytest.approx(51.3)
    assert RpiPmicSensor.driver_available() is True


def test_pmic_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyenvsense.sensors.rpi.shutil.which", lambda _cmd: None)
    assert RpiPmicSensor.driver_available() is False
    with pytest.raises(SensorUnavailableError, match="rpi_pmic"):
        create_sensor(_rpi_config("rpi_pmic"))

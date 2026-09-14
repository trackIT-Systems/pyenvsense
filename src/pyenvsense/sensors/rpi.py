from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pyenvsense.errors import SensorUnavailableError
from pyenvsense.sensors.base import BaseSensor, Measurement

HWMON_ROOT = Path("/sys/class/hwmon")
THERMAL_ZONE0_TEMP = Path("/sys/class/thermal/thermal_zone0/temp")
VCGENCMD = "vcgencmd"
_PMIC_TEMP = re.compile(r"temp=([0-9]+(?:\.[0-9]+)?)")


def find_hwmon(name: str, root: Path | None = None) -> Path | None:
    hwmon_root = HWMON_ROOT if root is None else root
    if not hwmon_root.is_dir():
        return None
    for entry in sorted(hwmon_root.iterdir()):
        name_file = entry / "name"
        if not name_file.is_file():
            continue
        if name_file.read_text(encoding="utf-8").strip() == name:
            return entry
    return None


def read_milli(path: Path) -> float:
    return int(path.read_text(encoding="utf-8").strip()) / 1000.0


def cpu_temp_path() -> Path | None:
    hwmon = find_hwmon("cpu_thermal")
    if hwmon is not None:
        temp = hwmon / "temp1_input"
        if temp.is_file():
            return temp
    if THERMAL_ZONE0_TEMP.is_file():
        return THERMAL_ZONE0_TEMP
    return None


class RpiCpuSensor(BaseSensor):
    extra = ""
    requires_i2c = False

    def read(self) -> dict[str, Measurement]:
        path = cpu_temp_path()
        if path is None:
            raise SensorUnavailableError(self.type)
        return {"temperature": Measurement(read_milli(path), "C")}

    @classmethod
    def driver_available(cls) -> bool:
        return cpu_temp_path() is not None


class RpiRp1Sensor(BaseSensor):
    extra = ""
    requires_i2c = False

    def read(self) -> dict[str, Measurement]:
        hwmon = find_hwmon("rp1_adc")
        if hwmon is None:
            raise SensorUnavailableError(self.type)
        temp = hwmon / "temp1_input"
        if not temp.is_file():
            raise SensorUnavailableError(self.type)
        fields: dict[str, Measurement] = {
            "temperature": Measurement(read_milli(temp), "C"),
        }
        for index in range(1, 5):
            voltage = hwmon / f"in{index}_input"
            if voltage.is_file():
                fields[f"in{index}"] = Measurement(read_milli(voltage), "V")
        return fields

    @classmethod
    def driver_available(cls) -> bool:
        hwmon = find_hwmon("rp1_adc")
        return hwmon is not None and (hwmon / "temp1_input").is_file()


class RpiPmicSensor(BaseSensor):
    extra = ""
    requires_i2c = False

    def read(self) -> dict[str, Measurement]:
        if not vcgencmd_available():
            raise SensorUnavailableError(self.type)
        try:
            result = subprocess.run(
                [VCGENCMD, "measure_temp", "pmic"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SensorUnavailableError(self.type) from exc
        match = _PMIC_TEMP.search(result.stdout)
        if match is None:
            raise SensorUnavailableError(self.type)
        return {"temperature": Measurement(float(match.group(1)), "C")}

    @classmethod
    def driver_available(cls) -> bool:
        return vcgencmd_available()


def vcgencmd_available() -> bool:
    return shutil.which(VCGENCMD) is not None

from __future__ import annotations

from pyenvsense.config import SensorConfig
from pyenvsense.errors import DriverNotInstalledError
from pyenvsense.sensors.base import BaseSensor, Measurement
from pyenvsense.sensors.i2c import linux_i2c_available, open_sht_channel, signal_value


class Sht3xSensor(BaseSensor):
    extra = "sht3x"

    def __init__(self, config: SensorConfig) -> None:
        super().__init__(config)
        try:
            from sensirion_i2c_sht3x.commands import Repeatability
            from sensirion_i2c_sht3x.device import Sht3xDevice
        except ImportError as exc:
            raise DriverNotInstalledError(self.extra) from exc
        channel = open_sht_channel(config.i2c_bus, config.address, self.extra)
        self._repeatability = Repeatability.HIGH
        self._device = Sht3xDevice(channel)

    def read(self) -> dict[str, Measurement]:
        temperature, humidity = self._device.measure_single_shot(
            self._repeatability, False
        )
        return {
            "temperature": Measurement(signal_value(temperature), "C"),
            "humidity": Measurement(signal_value(humidity), "%"),
        }

    @classmethod
    def driver_available(cls) -> bool:
        if not linux_i2c_available():
            return False
        try:
            import sensirion_i2c_sht3x  # noqa: F401
        except ImportError:
            return False
        return True

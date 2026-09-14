from __future__ import annotations

from pyenvsense.config import SensorConfig
from pyenvsense.errors import DriverNotInstalledError
from pyenvsense.sensors.base import BaseSensor, Measurement
from pyenvsense.sensors.i2c import linux_i2c_available, open_sht_channel, sht_humidity, sht_temperature


class Sht4xSensor(BaseSensor):
    extra = "sht4x"

    def __init__(self, config: SensorConfig) -> None:
        super().__init__(config)
        try:
            from sensirion_i2c_sht4x.device import Sht4xDevice
        except ImportError as exc:
            raise DriverNotInstalledError(self.extra) from exc
        assert config.i2c_bus is not None
        assert config.address is not None
        channel = open_sht_channel(config.i2c_bus, config.address, self.extra)
        self._device = Sht4xDevice(channel)

    def read(self) -> dict[str, Measurement]:
        temperature, humidity = self._device.measure_high_precision()
        return {
            "temperature": Measurement(sht_temperature(temperature), "C"),
            "humidity": Measurement(sht_humidity(humidity), "%"),
        }

    @classmethod
    def driver_available(cls) -> bool:
        if not linux_i2c_available():
            return False
        try:
            import sensirion_i2c_sht4x  # noqa: F401
        except ImportError:
            return False
        return True

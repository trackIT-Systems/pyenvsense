from __future__ import annotations

import threading
from typing import Any

from pyenvsense.errors import DriverNotInstalledError

_BUSES: dict[int, Any] = {}
_LOCK = threading.Lock()
_SHT_CRC = (8, 0x31, 0xFF, 0x0)


def i2c_device_path(bus: int) -> str:
    return f"/dev/i2c-{bus}"


def open_sht_channel(bus: int, address: int, extra: str):
    try:
        from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
        from sensirion_i2c_driver import CrcCalculator, I2cConnection, LinuxI2cTransceiver
    except ImportError as exc:
        raise DriverNotInstalledError(extra) from exc

    transceiver = _transceiver(bus, LinuxI2cTransceiver)
    return I2cChannel(
        I2cConnection(transceiver),
        slave_address=address,
        crc=CrcCalculator(*_SHT_CRC),
    )


def linux_i2c_available() -> bool:
    try:
        from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel  # noqa: F401
        from sensirion_i2c_driver import LinuxI2cTransceiver  # noqa: F401
    except ImportError:
        return False
    return True


def signal_value(signal: Any) -> float:
    return float(getattr(signal, "value", signal))


def _transceiver(bus: int, linux_i2c_transceiver):
    with _LOCK:
        if bus not in _BUSES:
            _BUSES[bus] = linux_i2c_transceiver(i2c_device_path(bus))
        return _BUSES[bus]

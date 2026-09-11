from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pyenvsense.config import SensorConfig


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str


@runtime_checkable
class Sensor(Protocol):
    extra: str
    id: str
    type: str
    interval_s: float

    def read(self) -> dict[str, Measurement]: ...

    @classmethod
    def driver_available(cls) -> bool: ...


class BaseSensor:
    extra: str = ""

    def __init__(self, config: SensorConfig) -> None:
        self.config = config
        self.id = config.id
        self.type = config.type
        self.interval_s = config.interval_s

    def read(self) -> dict[str, Measurement]:
        raise NotImplementedError

    @classmethod
    def driver_available(cls) -> bool:
        return False

class EnvsenseError(Exception):
    """Base error for pyenvsense."""


class ConfigError(EnvsenseError):
    """Invalid or missing configuration."""


class DriverNotInstalledError(EnvsenseError):
    def __init__(self, extra: str) -> None:
        self.extra = extra
        super().__init__(
            f"Optional extra '{extra}' is not installed. "
            f"Install it with: pip install pyenvsense[{extra}]"
        )


class SensorUnavailableError(EnvsenseError):
    def __init__(self, sensor_type: str) -> None:
        self.sensor_type = sensor_type
        super().__init__(f"Sensor type '{sensor_type}' is not available on this system")


class UnknownSensorTypeError(EnvsenseError):
    def __init__(self, sensor_type: str) -> None:
        self.sensor_type = sensor_type
        super().__init__(f"Unknown sensor type '{sensor_type}'")

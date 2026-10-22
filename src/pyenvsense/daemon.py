from __future__ import annotations

import argparse
import logging
import signal
import threading
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from pyenvsense import __version__
from pyenvsense.config import AppConfig, load_config
from pyenvsense.errors import EnvsenseError
from pyenvsense.journal import log_handler
from pyenvsense.outputs import Output
from pyenvsense.outputs.csv import CsvOutput, csv_session_path
from pyenvsense.outputs.mqtt import MqttOutput
from pyenvsense.reading import fields_from_measurements
from pyenvsense.sensors.base import Sensor
from pyenvsense.sensors.registry import create_sensor

log = logging.getLogger(__name__)


def build_outputs(config: AppConfig) -> list[Output]:
    outputs: list[Output] = []
    if config.daemon.csv.enabled:
        csv_path = csv_session_path(config.daemon.csv.path)
        log.info("Writing CSV to %s", csv_path)
        outputs.append(CsvOutput(csv_path))
    if config.daemon.mqtt.enabled:
        outputs.append(MqttOutput(config.daemon.mqtt))
    if not outputs:
        log.warning("No outputs enabled, readings are only logged at DEBUG")
    return outputs


def build_sensors(config: AppConfig) -> list[Sensor]:
    return [create_sensor(sensor) for sensor in config.sensors]


def run_daemon(
    config: AppConfig,
    *,
    sensors: Sequence[Sensor] | None = None,
    outputs: Sequence[Output] | None = None,
    sleep: Callable[[float], bool] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    handle_signals: bool = True,
) -> None:
    devices = list(sensors) if sensors is not None else build_sensors(config)
    if not devices:
        raise ValueError("no sensors configured")
    sinks = list(outputs) if outputs is not None else build_outputs(config)
    stop = threading.Event()

    def request_stop(*_args: object) -> None:
        stop.set()

    if handle_signals:
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    sleep_fn = sleep if sleep is not None else (lambda seconds: stop.wait(seconds))
    due_at = {sensor.id: monotonic() for sensor in devices}
    failures = Failures()

    log.info(
        "Started with %s sensor(s), CSV %s, MQTT %s",
        len(devices),
        "on" if config.daemon.csv.enabled else "off",
        "on" if config.daemon.mqtt.enabled else "off",
    )

    try:
        while not stop.is_set():
            now = monotonic()
            due = [sensor for sensor in devices if due_at[sensor.id] <= now]
            if due:
                for sensor in due:
                    _read_and_emit(sensor, sinks, failures)
                    due_at[sensor.id] = now + sensor.interval_s
                continue
            wait_s = min(due_at[sensor.id] for sensor in devices) - now
            if sleep_fn(max(wait_s, 0.0)):
                break
    finally:
        for sink in sinks:
            sink.close()
        log.info("Stopped")


class Failures:
    """What is failing, so a failure is logged when it starts, changes and ends, not on every repeat."""

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    def failed(self, what: str, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        if self._errors.get(what) != message:
            log.error("%s failed: %s", what, message)
        else:
            log.debug("%s failed again: %s", what, message)
        log.debug("%s traceback", what, exc_info=error)
        self._errors[what] = message

    def succeeded(self, what: str) -> None:
        if self._errors.pop(what, None) is not None:
            log.info("%s works again", what)


def _read_and_emit(sensor: Sensor, outputs: Sequence[Output], failures: Failures) -> None:
    when = datetime.now().astimezone()
    reading = f"Sensor {sensor.id} ({sensor.type})"
    try:
        measurements = sensor.read()
    except Exception as exc:  # noqa: BLE001 - a failing sensor must not stop the others
        failures.failed(reading, exc)
        return
    failures.succeeded(reading)
    fields = fields_from_measurements(measurements)
    log.debug("Read sensor %s: %s", sensor.id, fields)
    for output in outputs:
        emitting = f"Output {type(output).__name__} for sensor {sensor.id}"
        try:
            output.emit(sensor.id, sensor.type, when, fields)
        except Exception as exc:  # noqa: BLE001 - a failing output must not stop the others
            failures.failed(emitting, exc)
        else:
            failures.succeeded(emitting)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envsensed",
        description="Poll environmental sensors and write CSV / MQTT.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Config file (default: /boot/firmware/envsense.yml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="More output: -v for INFO, -vv for DEBUG (default: WARNING)",
    )
    args = parser.parse_args(argv)
    level = {0: logging.WARNING, 1: logging.INFO}.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, handlers=[log_handler("envsensed")])
    try:
        run_daemon(load_config(args.config))
    except EnvsenseError as exc:
        log.critical("Cannot run envsensed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

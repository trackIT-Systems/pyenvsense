from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from pyenvsense import __version__
from pyenvsense.config import AppConfig, load_config
from pyenvsense.errors import EnvsenseError
from pyenvsense.outputs import Output
from pyenvsense.outputs.csv import CsvOutput, csv_session_path
from pyenvsense.outputs.mqtt import MqttOutput
from pyenvsense.reading import fields_from_measurements
from pyenvsense.sensors.base import Sensor
from pyenvsense.sensors.registry import create_sensor

log = logging.getLogger("envsensed")


def build_outputs(config: AppConfig) -> list[Output]:
    outputs: list[Output] = []
    if config.daemon.csv.enabled:
        csv_path = csv_session_path(config.daemon.csv.path)
        log.info("csv file %s", csv_path)
        outputs.append(CsvOutput(csv_path))
    if config.daemon.mqtt.enabled:
        outputs.append(MqttOutput(config.daemon.mqtt))
    if not outputs:
        log.warning("No outputs enabled; readings will only be logged")
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

    log.info(
        "daemon started; %s sensor(s), csv=%s mqtt=%s",
        len(devices),
        config.daemon.csv.enabled,
        config.daemon.mqtt.enabled,
    )

    try:
        while not stop.is_set():
            now = monotonic()
            due = [sensor for sensor in devices if due_at[sensor.id] <= now]
            if due:
                for sensor in due:
                    _read_and_emit(sensor, sinks)
                    due_at[sensor.id] = now + sensor.interval_s
                continue
            wait_s = min(due_at[sensor.id] for sensor in devices) - now
            if sleep_fn(max(wait_s, 0.0)):
                break
    finally:
        for sink in sinks:
            sink.close()
        log.info("daemon stopped")


def _read_and_emit(sensor: Sensor, outputs: Sequence[Output]) -> None:
    when = datetime.now().astimezone()
    try:
        measurements = sensor.read()
    except Exception:
        log.exception("read failed for sensor %s (%s)", sensor.id, sensor.type)
        return
    fields = fields_from_measurements(measurements)
    log.info("read %s: %s", sensor.id, fields)
    for output in outputs:
        try:
            output.emit(sensor.id, sensor.type, when, fields)
        except Exception:
            log.exception("output %s failed for sensor %s", type(output).__name__, sensor.id)


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
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        run_daemon(load_config(args.config))
    except EnvsenseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

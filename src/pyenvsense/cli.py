from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from pyenvsense import __version__
from pyenvsense.config import AppConfig, load_config
from pyenvsense.errors import EnvsenseError, UnknownSensorTypeError
from pyenvsense.reading import fields_from_measurements, flat_payload
from pyenvsense.sensors.registry import create_sensor, driver_available, get_sensor_class


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envsense",
        description="Read environmental sensors from a YAML hardware config.",
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
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List configured sensors")
    sub.add_parser("read", help="Read all configured sensors once")

    args = parser.parse_args(argv)
    _configure_logging()
    try:
        config = load_config(args.config)
        if args.command == "list":
            return cmd_list(config)
        return cmd_read(config)
    except EnvsenseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_list(config: AppConfig) -> int:
    rows = [("ID", "TYPE", "BUS", "ADDR", "INTERVAL", "DRIVER")]
    for sensor in config.sensors:
        try:
            get_sensor_class(sensor.type)
            known = True
        except UnknownSensorTypeError:
            known = False
        present = driver_available(sensor.type) if known else False
        if not known:
            driver = "unknown"
        elif present:
            driver = "yes"
        else:
            driver = "missing"
        bus = "-" if sensor.i2c_bus is None else str(sensor.i2c_bus)
        addr = "-" if sensor.address is None else f"0x{sensor.address:02x}"
        rows.append(
            (
                sensor.id,
                sensor.type,
                bus,
                addr,
                str(sensor.interval_s),
                driver,
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return 0


def cmd_read(config: AppConfig) -> int:
    when = datetime.now().astimezone()
    readings = []
    for sensor_cfg in config.sensors:
        sensor = create_sensor(sensor_cfg)
        fields = fields_from_measurements(sensor.read())
        readings.append(flat_payload(when, fields, sensor_id=sensor.id))
    json.dump(readings, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())

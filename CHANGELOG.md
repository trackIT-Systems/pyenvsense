# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/)
(`YYYY.M.MICRO`). `M` is the calendar month without a leading zero (PEP 440).
`MICRO` starts at `1` and resets each month.

## [Unreleased]

### Changed

- `hardware.sensors` may be empty (`[]` or null). `envsensed` then logs `No sensors configured in …, exiting` at INFO and exits with status 0, before opening a CSV file. An empty list was a config error (exit 1), so a unit with `Restart=on-failure` restarted forever.

- `envsensed` logs at WARNING by default (was always INFO, logging every reading); `-v` gives INFO, `-vv` DEBUG.
- Under systemd, `envsensed` and `envsense` log to the journal over its native protocol, with the syslog priority, `SYSLOG_IDENTIFIER` (`envsensed` for the daemon) and `CODE_FILE` / `CODE_LINE` / `CODE_FUNC`. Previously every line was stored as `info`. On a terminal they still log to stderr.
- `envsensed` logs changes of state, not every reading: a sensor or output that keeps failing is logged once at ERROR (exception type and text) when it starts failing, again only when the error changes, and once at INFO when it works again (`Sensor inside (sht3x) works again`). Repeats and tracebacks go to DEBUG, and so does each reading (was INFO).
- `envsensed` logs connecting to the MQTT broker at INFO, a lost connection at WARNING and reconnecting at INFO.
- Fatal errors of `envsensed` (CRITICAL) and `envsense` (ERROR) go through logging, and so reach the journal with their priority, instead of `print()` to stderr.
- Loggers are named after their module (`pyenvsense.daemon`, was `envsensed`), and messages follow the tsOS logging convention (capitalized, one sentence, e.g. `Writing CSV to …`).

## [2026.9.2] - 2026-09-14

### Added

- Raspberry Pi onboard sensors: `rpi_cpu` (SoC temperature), `rpi_rp1` (RP1 temperature and ADC voltages), and `rpi_pmic` (`vcgencmd measure_temp pmic`). These types do not use I2C `address` / `i2c_bus`.
- GitHub Actions CI to run `pytest` on Python 3.11, 3.12, and 3.13 for pushes and pull requests.
- CI status badge in the README.

### Changed

- SHT3x and SHT4x readings are rounded to 0.01 °C and 0.01 %RH (datasheet resolution).
- Example systemd unit renamed to [`systemd/envsense.service`](systemd/envsense.service).

### Fixed

- MQTT `_time` tests pin `Europe/Berlin` so they do not depend on the host timezone (CI is UTC).

## [2026.9.1] - 2026-09-11

### Added

- `envsense` (`list`, `read`) and `envsensed`; config at `/boot/firmware/envsense.yml` (`--config` overrides).
- Optional Sensirion SHT3x/SHT4x extras; `paho-mqtt` is a core dependency.
- Example: two SHT31s (`inside` 0x44, `outside` 0x45) on I2C bus 0, 60 s interval.
- CSV under `/data/<hostname>/envsense/<hostname>_<UTC>-envsense.csv`.
- MQTT topic `{hostname}/envsense/{sensor_id}/json`. Flat JSON: `_time`, `Temperature (°C)`, `Humidity (%)` (CLI also has `sensor_id`).
- Example systemd unit.

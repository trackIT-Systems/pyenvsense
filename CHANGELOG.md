# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/)
(`YYYY.M.MICRO`). `M` is the calendar month without a leading zero (PEP 440).
`MICRO` starts at `1` and resets each month.

## [Unreleased]

### Added

- GitHub Actions CI to run `pytest` on Python 3.11, 3.12, and 3.13 for pushes and pull requests.
- CI status badge in the README.

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

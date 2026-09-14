# pyenvsense

[![Tests](https://github.com/trackIT-Systems/pyenvsense/actions/workflows/ci.yml/badge.svg)](https://github.com/trackIT-Systems/pyenvsense/actions/workflows/ci.yml)

Read environmental / ambient sensors (SHT3x, SHT4x) and Raspberry Pi onboard sources (`rpi_cpu`, `rpi_rp1`, `rpi_pmic`) on autonomous sensor nodes. The same YAML file drives `envsensed` (CSV + MQTT) and the `envsense` CLI, which only uses the hardware section.

Driver libraries for I2C families are **optional extras** (`sensirion-i2c-sht3x`, `sensirion-i2c-sht4x`). Install only the families you have wired up. Onboard Raspberry Pi types are part of the core package. `paho-mqtt` is always installed with the core package.

## Install

Python 3.11+ is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Add sensor extras as needed:

```bash
pip install -e ".[sht4x,sht3x]"
```

I2C on Raspberry Pi typically needs the user in the `i2c` group (`sudo usermod -aG i2c "$USER"`).

## Configuration

The daemon and CLI load **`/boot/firmware/envsense.yml`** unless you pass `--config`. Copy the example:

```bash
sudo cp config/envsense.yml /boot/firmware/envsense.yml
```

```yaml
hardware:
  i2c_bus: 0
  interval_s: 60
  sensors:
    - id: inside
      type: sht3x
      address: 0x44    # ADDR to GND
    - id: outside
      type: sht3x
      address: 0x45    # ADDR to VDD
    - id: soc
      type: rpi_cpu
    - id: rp1
      type: rpi_rp1
    - id: pmic
      type: rpi_pmic

daemon:
  csv:
    enabled: true
    path: /data
  mqtt:
    enabled: true
    host: localhost
    port: 1883
    qos: 0
```

`envsense list` and `envsense read` ignore the `daemon` section. MQTT topic is `{hostname}/envsense/{sensor_id}/json`. The JSON body is flat: `_time` (local ISO, e.g. `2026-06-01 09:10:21.994007+02:00`), `Temperature (°C)`, and `Humidity (%)` (SHT). `rpi_rp1` also includes `In1 (V)`–`In4 (V)` when those ADC channels exist. MQTT omits `sensor_id` (it is in the topic); `envsense read` includes it.

CSV files are created under `daemon.csv.path` (default `/data`) as `<hostname>/envsense/<hostname>_<timestamp>-envsense.csv`, with a UTC timestamp like `2026-09-11T125654`. The directories are created if they are missing. Each daemon start opens a new file.

## Commands

```bash
envsense list
envsense read
envsensed
envsense --config ./config/envsense.yml list
```

`envsense list` shows id, type, I2C bus, address, interval, and whether the driver is available. Non-I2C types (`rpi_cpu`, `rpi_rp1`, `rpi_pmic`) show `-` for bus and address. `envsense read` prints a JSON array of flat readings to stdout. `envsensed` is the long-running daemon.

## systemd

An example unit is in [`systemd/envsense.service`](systemd/envsense.service). It starts `envsensed` with the default config path. Adjust `ExecStart` if the console script is not on `PATH`.

```bash
sudo cp systemd/envsense.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pyenvsense
```

## Adding a sensor family

Register an entry point in `pyproject.toml`:

```toml
[project.entry-points."pyenvsense.sensors"]
myfamily = "mypkg.sensors:MySensor"
```

The class should accept a `SensorConfig`, implement `read()`, set `extra` to the pip extra name (empty string if the driver is built in), set `requires_i2c = False` when `address` is not used, and provide `driver_available()`.

## Versioning

This project uses [Calendar Versioning](https://calver.org/) (`YYYY.M.MICRO`, e.g. `2026.9.1`) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Set the version in [`src/pyenvsense/__init__.py`](src/pyenvsense/__init__.py) and record changes in [`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` until the next release.

## Development

```bash
pip install -e ".[dev]"
pytest
```

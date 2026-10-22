from __future__ import annotations

import logging
from pathlib import Path

import pytest

from pyenvsense.config import parse_config
from pyenvsense.daemon import main, run_daemon
from pyenvsense.sensors.base import BaseSensor, Measurement


class FakeSensor(BaseSensor):
    extra = "fake"

    def __init__(self, sensor_id: str, interval_s: float, values: dict[str, Measurement]) -> None:
        self.id = sensor_id
        self.type = "fake"
        self.interval_s = interval_s
        self._values = values
        self.reads = 0

    def read(self) -> dict[str, Measurement]:
        self.reads += 1
        return self._values

    @classmethod
    def driver_available(cls) -> bool:
        return True


class FakeOutput:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def emit(self, sensor_id, sensor_type, ts, fields) -> None:
        self.events.append((sensor_id, sensor_type))

    def close(self) -> None:
        return


def test_scheduler_reads_due_sensors() -> None:
    cfg = parse_config(
        {
            "hardware": {
                "sensors": [{"id": "ambient", "type": "sht4x", "address": 0x44}]
            },
            "daemon": {"csv": {"enabled": False}, "mqtt": {"enabled": False}},
        },
        Path("mem.yml"),
    )
    fast = FakeSensor("fast", 10, {"temperature": Measurement(1.0, "C")})
    slow = FakeSensor("slow", 100, {"temperature": Measurement(2.0, "C")})
    output = FakeOutput()
    clock = {"now": 0.0}

    def monotonic() -> float:
        return clock["now"]

    calls = {"n": 0}

    def sleep(_seconds: float) -> bool:
        calls["n"] += 1
        clock["now"] += 10
        return calls["n"] >= 2

    run_daemon(
        cfg,
        sensors=[fast, slow],
        outputs=[output],
        sleep=sleep,
        monotonic=monotonic,
        handle_signals=False,
    )

    assert fast.reads >= 1
    assert slow.reads == 1
    assert any(event[0] == "fast" for event in output.events)
    assert any(event[0] == "slow" for event in output.events)


def test_envsensed_help(capsys) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    out = capsys.readouterr().out
    assert "envsensed" in out
    assert "--config" in out



@pytest.mark.parametrize(
    ("args", "level"),
    [([], logging.WARNING), (["-v"], logging.INFO), (["-vv"], logging.DEBUG)],
)
def test_envsensed_log_level(monkeypatch, args, level) -> None:
    import pyenvsense.daemon as daemon

    seen = {}
    monkeypatch.setattr(daemon.logging, "basicConfig", lambda **kwargs: seen.update(kwargs))
    monkeypatch.setattr(daemon, "load_config", lambda path: None)
    monkeypatch.setattr(daemon, "run_daemon", lambda config: None)

    assert main(args) == 0
    assert seen["level"] == level
    for handler in seen["handlers"]:
        handler.close()


class FlakySensor(FakeSensor):
    """Raises the queued errors, one per read, then reads normally."""

    def __init__(self, errors: list[Exception]) -> None:
        super().__init__("inside", 10, {"temperature": Measurement(1.0, "C")})
        self._errors = list(errors)

    def read(self) -> dict[str, Measurement]:
        self.reads += 1
        if self._errors:
            raise self._errors.pop(0)
        return self._values


class FailingOutput(FakeOutput):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self._failures = failures

    def emit(self, sensor_id, sensor_type, ts, fields) -> None:
        if self._failures:
            self._failures -= 1
            raise OSError("disk full")
        super().emit(sensor_id, sensor_type, ts, fields)


def _run(sensor: FakeSensor, outputs: list, reads: int) -> None:
    cfg = parse_config(
        {
            "hardware": {"sensors": [{"id": "inside", "type": "sht4x", "address": 0x44}]},
            "daemon": {"csv": {"enabled": False}, "mqtt": {"enabled": False}},
        },
        Path("mem.yml"),
    )
    clock = {"now": 0.0}

    def sleep(_seconds: float) -> bool:
        clock["now"] += sensor.interval_s
        return sensor.reads >= reads

    run_daemon(
        cfg,
        sensors=[sensor],
        outputs=outputs,
        sleep=sleep,
        monotonic=lambda: clock["now"],
        handle_signals=False,
    )
    assert sensor.reads == reads


def _records(caplog, level: int) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno == level and r.name == "pyenvsense.daemon"]


def test_repeated_read_failure_logs_one_error_and_one_recovery(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="pyenvsense.daemon")
    sensor = FlakySensor([OSError("no ack")] * 3)

    _run(sensor, [FakeOutput()], reads=5)

    assert _records(caplog, logging.ERROR) == ["Sensor inside (fake) failed: OSError: no ack"]
    assert _records(caplog, logging.INFO).count("Sensor inside (fake) works again") == 1
    assert _records(caplog, logging.DEBUG).count("Sensor inside (fake) failed again: OSError: no ack") == 2
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert all(r.exc_info is None for r in errors)
    assert any(r.exc_info for r in caplog.records if r.levelno == logging.DEBUG)


def test_changed_read_error_is_logged_again(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="pyenvsense.daemon")
    sensor = FlakySensor([OSError("no ack"), OSError("no ack"), TimeoutError("bus busy")])

    _run(sensor, [FakeOutput()], reads=4)

    assert _records(caplog, logging.ERROR) == [
        "Sensor inside (fake) failed: OSError: no ack",
        "Sensor inside (fake) failed: TimeoutError: bus busy",
    ]


def test_repeated_output_failure_logs_one_error_and_one_recovery(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="pyenvsense.daemon")
    sensor = FlakySensor([])
    output = FailingOutput(failures=3)

    _run(sensor, [output], reads=4)

    assert _records(caplog, logging.ERROR) == [
        "Output FailingOutput for sensor inside failed: OSError: disk full"
    ]
    assert _records(caplog, logging.INFO).count("Output FailingOutput for sensor inside works again") == 1
    assert len(output.events) == 1


def test_readings_are_logged_at_debug_only(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="pyenvsense.daemon")

    _run(FlakySensor([]), [FakeOutput()], reads=3)

    assert sum(m.startswith("Read sensor inside") for m in _records(caplog, logging.DEBUG)) == 3
    assert not any("inside" in m for m in _records(caplog, logging.INFO))


def test_envsensed_logs_fatal_error(monkeypatch, caplog, capsys) -> None:
    from pyenvsense import daemon
    from pyenvsense.errors import EnvsenseError

    def fail(path):
        raise EnvsenseError("config file /x.yml not found")

    monkeypatch.setattr(daemon.logging, "basicConfig", lambda **kwargs: None)
    monkeypatch.setattr(daemon, "log_handler", lambda identifier: None)
    monkeypatch.setattr(daemon, "load_config", fail)

    assert main([]) == 1
    assert _records(caplog, logging.CRITICAL) == ["Cannot run envsensed: config file /x.yml not found"]
    assert capsys.readouterr().err == ""

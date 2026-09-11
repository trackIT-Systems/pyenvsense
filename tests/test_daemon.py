from __future__ import annotations

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


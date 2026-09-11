from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from pyenvsense.outputs.csv import CSV_FIELDS, CsvOutput, csv_session_path

WHEN = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def test_csv_writes_header_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "readings.csv"
    output = CsvOutput(path)
    output.emit(
        "ambient",
        "sht4x",
        WHEN,
        {
            "temperature": {"value": 21.5, "unit": "C"},
            "humidity": {"value": 48.0, "unit": "%"},
        },
    )
    output.close()

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == list(CSV_FIELDS)
    assert rows[0]["sensor_id"] == "ambient"
    assert rows[0]["ts"] == "2026-09-11T12:00:00.000Z"
    assert rows[0]["key"] == "temperature"
    assert rows[1]["key"] == "humidity"
    assert len(rows) == 2


def test_csv_does_not_duplicate_header(tmp_path: Path) -> None:
    path = tmp_path / "readings.csv"
    first = CsvOutput(path)
    first.emit("a", "sht4x", WHEN, {"temperature": {"value": 1.0, "unit": "C"}})
    first.close()
    second = CsvOutput(path)
    second.emit("a", "sht4x", WHEN, {"temperature": {"value": 2.0, "unit": "C"}})
    second.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("ts,")
    assert sum(1 for line in lines if line.startswith("ts,")) == 1
    assert len(lines) == 3


def test_csv_session_path_format(tmp_path: Path) -> None:
    when = datetime(2026, 9, 11, 12, 56, 54, tzinfo=timezone.utc)
    path = csv_session_path(tmp_path, hostname="node-01", when=when)
    assert path == tmp_path / "node-01" / "envsense" / "node-01_2026-09-11T125654-envsense.csv"


def test_csv_session_creates_directories(tmp_path: Path) -> None:
    when = datetime(2026, 9, 11, 12, 56, 54, tzinfo=timezone.utc)
    path = csv_session_path(tmp_path, hostname="node-01", when=when)
    output = CsvOutput(path)
    output.close()
    assert path.is_file()
    assert path.parent.is_dir()

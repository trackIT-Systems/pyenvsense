from __future__ import annotations

import csv
import socket
from datetime import datetime, timezone
from pathlib import Path

from pyenvsense.reading import utc_iso

CSV_FIELDS = ("ts", "sensor_id", "type", "key", "value", "unit")
CSV_FILENAME_TIMESTAMP = "%Y-%m-%dT%H%M%S"


def csv_session_path(
    base: Path,
    hostname: str | None = None,
    when: datetime | None = None,
) -> Path:
    """`<base>/<hostname>/envsense/<hostname>_<timestamp>-envsense.csv`."""
    host = hostname if hostname is not None else socket.gethostname()
    ts = (when or datetime.now(timezone.utc)).strftime(CSV_FILENAME_TIMESTAMP)
    return Path(base) / host / "envsense" / f"{host}_{ts}-envsense.csv"


class CsvOutput:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.path.is_file() and self.path.stat().st_size > 0:
            return
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()

    def emit(
        self,
        sensor_id: str,
        sensor_type: str,
        when: datetime,
        fields: dict[str, dict[str, float | str]],
    ) -> None:
        ts = utc_iso(when)
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            for key, field in fields.items():
                writer.writerow(
                    {
                        "ts": ts,
                        "sensor_id": sensor_id,
                        "type": sensor_type,
                        "key": key,
                        "value": field["value"],
                        "unit": field["unit"],
                    }
                )

    def close(self) -> None:
        return

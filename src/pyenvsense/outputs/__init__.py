from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Output(Protocol):
    def emit(
        self,
        sensor_id: str,
        sensor_type: str,
        when: datetime,
        fields: dict[str, dict[str, float | str]],
    ) -> None: ...

    def close(self) -> None: ...

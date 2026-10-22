from __future__ import annotations

from pathlib import Path

import pytest

from pyenvsense.cli import cmd_list, main
from pyenvsense.config import parse_config


def test_list_uses_resolved_hardware(capsys) -> None:
    cfg = parse_config(
        {
            "hardware": {
                "i2c_bus": 1,
                "sensors": [
                    {
                        "id": "ambient",
                        "type": "sht4x",
                        "address": "0x44",
                        "i2c_bus": 3,
                        "interval_s": 15,
                    }
                ],
            }
        },
        Path("mem.yml"),
    )
    assert cmd_list(cfg) == 0
    out = capsys.readouterr().out
    assert "ambient" in out
    assert "sht4x" in out
    assert "3" in out
    assert "0x44" in out
    assert "15" in out


def test_list_uses_dash_for_non_i2c(capsys) -> None:
    cfg = parse_config(
        {
            "hardware": {
                "sensors": [
                    {"id": "soc", "type": "rpi_cpu", "interval_s": 15},
                ]
            }
        },
        Path("mem.yml"),
    )
    assert cmd_list(cfg) == 0
    out = capsys.readouterr().out
    assert "soc" in out
    assert "rpi_cpu" in out
    assert "0x" not in out
    data = out.splitlines()[1]
    assert " - " in data
    assert "15" in out


def test_envsense_help_lists_cli_commands(capsys) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    out = capsys.readouterr().out
    assert "list" in out
    assert "read" in out
    assert "daemon" not in out
    assert "envsense" in out


def test_envsense_logs_error(monkeypatch, caplog, capsys) -> None:
    import logging

    from pyenvsense import cli
    from pyenvsense.errors import EnvsenseError

    def fail(path):
        raise EnvsenseError("config file /x.yml not found")

    monkeypatch.setattr(cli, "_configure_logging", lambda identifier: None)
    monkeypatch.setattr(cli, "load_config", fail)

    assert main(["list"]) == 1
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert errors == ["Cannot run envsense list: config file /x.yml not found"]
    assert capsys.readouterr().out == ""

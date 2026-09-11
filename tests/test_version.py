from pathlib import Path
import re

from pyenvsense import __version__

REPO = Path(__file__).resolve().parents[1]


def test_version_is_year_month_release() -> None:
    assert re.fullmatch(r"20\d{2}\.(1[0-2]|[1-9])\.[1-9]\d*", __version__)


def test_changelog_contains_current_version() -> None:
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog
    assert "## [Unreleased]" in changelog

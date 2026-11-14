"""`daily stats` の達成率にバーを添える(Issue #37)。"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.commands.daily import _bar
from task_cli.cli.main import app
from task_cli.services.daily_service import DailyService

runner = CliRunner()


@pytest.mark.parametrize(
    ("rate", "filled"),
    [(0.0, 0), (0.04, 0), (0.25, 3), (0.35, 4), (0.5, 5), (0.96, 10), (1.0, 10), (1.5, 10), (-0.2, 0)],
)
def test_bar_has_fixed_width(rate: float, filled: int) -> None:
    bar = _bar(rate)
    assert len(bar) == 10
    assert bar.count("█") == filled
    assert bar.count("░") == 10 - filled


def test_stats_shows_bar_next_to_percentage_and_dashes_for_no_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "120")
    entries = [
        {"date": "2026-11-03", "done": 2, "total": 2, "rate": 1.0},
        {"date": "2026-11-02", "done": 1, "total": 2, "rate": 0.5},
        {"date": "2026-11-01", "done": 0, "total": 0, "rate": None},
    ]
    monkeypatch.setattr(DailyService, "stats", lambda self: entries)

    lines = runner.invoke(app, ["daily", "stats"]).output.splitlines()

    full = next(line for line in lines if "2026-11-03" in line)
    half = next(line for line in lines if "2026-11-02" in line)
    none = next(line for line in lines if "2026-11-01" in line)
    assert "██████████" in full and "100%" in full
    assert "█████░░░░░" in half and "50%" in half
    assert "--" in none and "█" not in none and "░" not in none

"""`show` が解禁日を表示する(Issue #35)。"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.deps import get_use_case
from task_cli.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "120")
    return tmp_path


def _today(offset_days: int = 0) -> str:
    # `start` の判定(services/task_manager.py)と同じ「今日」の定義
    now = datetime.now(timezone.utc).astimezone() + timedelta(days=offset_days)
    return now.strftime("%Y-%m-%d")


def _show(scheduled: str | None) -> str:
    task = get_use_case().add_task("t", project=None, scheduled_date=scheduled)
    result = runner.invoke(app, ["show", str(task.id)])
    assert result.exit_code == 0, result.output
    return result.output


def test_no_scheduled_date_shows_no_row() -> None:
    assert "Sched" not in _show(None)


def test_future_scheduled_date_is_shown_with_warning() -> None:
    out = _show(_today(+3))
    assert "Sched" in out
    assert _today(+3) in out
    assert "着手できません" in out


@pytest.mark.parametrize("offset", [0, -5])
def test_today_or_past_scheduled_date_is_shown_without_warning(offset: int) -> None:
    out = _show(_today(offset))
    assert _today(offset) in out
    assert "着手できません" not in out


def test_warning_agrees_with_start_gate() -> None:
    """表示が「着手できない」と言うとき、実際に `start` も断る(判定のずれを作らない)。"""
    task = get_use_case().add_task("t", project=None, scheduled_date=_today(+3))
    assert "着手できません" in runner.invoke(app, ["show", str(task.id)]).output
    assert runner.invoke(app, ["start", str(task.id)]).exit_code == 1

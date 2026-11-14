"""`list` / `search` の表の列と、期限切れの赤(Issue #65)。"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from task_cli.cli import renderer
from task_cli.cli.deps import get_use_case
from task_cli.cli.main import app
from task_cli.models.task import Priority

runner = CliRunner()
RED = "\x1b[1;31m"  # 期限切れは太字の赤(優先度 high の赤と見分けるため)


def day(offset: int) -> str:
    return (datetime.now(timezone.utc).astimezone() + timedelta(days=offset)).strftime("%Y-%m-%d")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    # 色を残して検査する(CliRunner の出力は端末ではなく、通常は色が落ちる)
    monkeypatch.setattr(renderer, "console", Console(force_terminal=True, color_system="standard", width=160))
    return tmp_path


def line_of(output: str, title: str) -> str:
    return next(line for line in output.splitlines() if title in line)


def test_columns_are_id_status_priority_title_due() -> None:
    get_use_case().add_task("t1", priority=Priority.HIGH, due_date="2030-01-02", project=None)

    out = runner.invoke(app, ["list", "--inbox"]).output

    header = out.splitlines()[1]
    for column in ("ID", "Status", "Priority", "Title", "Due"):
        assert column in header
    row = line_of(out, "t1")
    assert "high" in row and "2030-01-02" in row


def test_task_without_due_date_shows_a_dash() -> None:
    get_use_case().add_task("no-due", project=None)
    row = line_of(runner.invoke(app, ["list", "--inbox"]).output, "no-due")
    assert row.split("no-due")[1].split() == ["-"]  # Title の右の Due 列が `-` だけ


class TestOverdueIsRed:
    def test_open_task_past_due_is_red(self) -> None:
        get_use_case().add_task("late", due_date=day(-3), project=None)
        row = line_of(runner.invoke(app, ["list", "--inbox"]).output, "late")
        assert f"{RED}{day(-3)}" in row

    def test_in_progress_task_past_due_is_red(self) -> None:
        uc = get_use_case()
        uc.add_task("late-ip", due_date=day(-3), project=None)
        uc.start_task(1, project=None)
        assert f"{RED}{day(-3)}" in line_of(runner.invoke(app, ["list", "--inbox"]).output, "late-ip")

    @pytest.mark.parametrize("offset", [0, 1, 30])
    def test_due_today_or_later_is_not_red(self, offset: int) -> None:
        get_use_case().add_task("ontime", due_date=day(offset), project=None)
        row = line_of(runner.invoke(app, ["list", "--inbox"]).output, "ontime")
        assert day(offset) in row and f"{RED}{day(offset)}" not in row

    def test_completed_task_past_due_is_not_red(self) -> None:
        uc = get_use_case()
        uc.add_task("done-late", due_date=day(-3), project=None)
        uc.start_task(1, project=None)
        uc.complete_task(1, project=None)
        row = line_of(runner.invoke(app, ["list", "--inbox", "--all-status"]).output, "done-late")
        assert day(-3) in row and f"{RED}{day(-3)}" not in row


def test_search_uses_the_same_columns() -> None:
    get_use_case().add_task("findme", priority=Priority.LOW, due_date="2030-05-05", project=None)

    out = runner.invoke(app, ["search", "findme"]).output

    assert "Priority" in out and "Due" in out
    assert "low" in line_of(out, "findme") and "2030-05-05" in line_of(out, "findme")

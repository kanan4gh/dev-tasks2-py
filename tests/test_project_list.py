import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.commands.project import project_app

runner = CliRunner()

LONG_NAME = "a-project-name-well-over-twenty-chars"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "120")
    return tmp_path


def _create(name: str) -> None:
    assert runner.invoke(project_app, ["create", name]).exit_code == 0


def _list_lines() -> list[str]:
    result = runner.invoke(project_app, ["list"])
    assert result.exit_code == 0
    return [line for line in result.output.splitlines() if line.strip()]


def _count_column(line: str) -> int:
    match = re.search(r"\d+ tasks?\b", line)
    assert match is not None, line
    return match.start()


class TestProjectListLayout:
    def test_long_name_is_not_truncated(self) -> None:
        _create(LONG_NAME)
        assert any(LONG_NAME in line for line in _list_lines())

    def test_count_column_aligned_across_all_rows(self) -> None:
        _create("short")
        _create(LONG_NAME)
        rows = [line for line in _list_lines() if re.search(r"\d+ tasks?\b", line)]
        # short / 長い名前 / Inbox の3行
        assert len(rows) == 3
        assert len({_count_column(line) for line in rows}) == 1

    def test_active_project_is_marked(self) -> None:
        _create("first")
        _create("second")  # create でアクティブになる
        lines = _list_lines()
        second = next(line for line in lines if "second" in line)
        first = next(line for line in lines if "first" in line)
        assert "*" in second
        assert "*" not in first

    def test_inbox_row_is_listed_with_count(self) -> None:
        _create("only")
        inbox = next(line for line in _list_lines() if "Inbox" in line)
        assert "0 tasks" in inbox

"""利用者に見えるヘルプ文・案内文が、実在するコマンドを指していること(Issue #58, #60)。"""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.deps import get_use_case
from task_cli.cli.main import app
from task_cli.services.daily_service import DailyService

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "200")
    return tmp_path


def test_web_help_does_not_claim_read_only() -> None:
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "読み取り専用" not in result.output
    assert "127.0.0.1" in result.output


def test_overview_hints_point_at_existing_commands() -> None:
    DailyService().add_routine("朝のストレッチ")
    get_use_case().add_task("やること", project=None)

    result = runner.invoke(app, ["overview"])
    assert result.exit_code == 0

    hints = [line for line in result.output.splitlines() if "💡" in line]
    assert len(hints) == 2
    assert not any("done r<ID>" in h for h in hints)

    # 案内に出る `task-py <コマンド> <ID>` が、実在するコマンドとして解決できる
    commands = re.findall(r"task-py ((?:[a-z]+ )+?)<ID>", "\n".join(hints))
    assert ["daily done ", "start ", "done "] == commands
    for words in commands:
        result = runner.invoke(app, [*words.split(), "--help"])
        assert result.exit_code == 0, words

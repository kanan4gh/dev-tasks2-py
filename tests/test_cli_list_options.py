"""`list` の絞り込み・並べ替え(Issue #65)。PRD の機能4・7・8の要求。"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.deps import get_use_case
from task_cli.cli.main import app
from task_cli.models.task import Priority
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "160")
    return tmp_path


def seed() -> None:
    """Inbox に、優先度・期限・ステータスの違う4件を作る。"""
    uc = get_use_case()
    uc.add_task("low-late", priority=Priority.LOW, due_date="2030-12-31", project=None)  # 1
    uc.add_task("high-none", priority=Priority.HIGH, project=None)  # 2(期限なし)
    uc.add_task("medium-early", priority=Priority.MEDIUM, due_date="2030-01-01", project=None)  # 3
    uc.add_task("high-done", priority=Priority.HIGH, due_date="2030-06-01", project=None)  # 4
    uc.start_task(4, project=None)
    uc.complete_task(4, project=None)


def titles(args: list[str]) -> list[str]:
    result = runner.invoke(app, ["list", "--inbox", *args])
    assert result.exit_code == 0, result.output
    names = ["low-late", "high-none", "medium-early", "high-done"]
    found = [(result.output.index(n), n) for n in names if n in result.output]
    return [n for _, n in sorted(found)]


class TestStatusFilter:
    def test_default_hides_completed(self) -> None:
        seed()
        assert "high-done" not in titles([])

    def test_status_selects_only_that_status(self) -> None:
        seed()
        assert titles(["--status", "completed"]) == ["high-done"]

    def test_status_can_be_repeated(self) -> None:
        seed()
        assert sorted(titles(["--status", "open", "--status", "completed"])) == sorted(
            ["low-late", "high-none", "medium-early", "high-done"]
        )

    def test_status_and_all_status_cannot_be_combined(self) -> None:
        seed()
        result = runner.invoke(app, ["list", "--inbox", "--status", "open", "--all-status"])
        assert result.exit_code != 0
        assert "同時に指定できません" in result.output

    def test_unknown_status_is_rejected(self) -> None:
        result = runner.invoke(app, ["list", "--status", "nonsense"])
        assert result.exit_code != 0
        assert "nonsense" in result.output


class TestPriorityFilter:
    def test_priority_selects_only_that_priority(self) -> None:
        seed()
        assert titles(["--priority", "high"]) == ["high-none"]  # high-done は既定で出ない

    def test_priority_with_all_status(self) -> None:
        seed()
        assert sorted(titles(["--priority", "high", "--all-status"])) == ["high-done", "high-none"]


class TestSort:
    def test_default_is_by_id(self) -> None:
        seed()
        assert titles([]) == ["low-late", "high-none", "medium-early"]

    def test_sort_by_priority(self) -> None:
        seed()
        assert titles(["--sort", "priority"]) == ["high-none", "medium-early", "low-late"]

    def test_sort_by_due_date_puts_no_due_last(self) -> None:
        seed()
        assert titles(["--sort", "due_date"]) == ["medium-early", "low-late", "high-none"]

    def test_sort_by_created_at(self) -> None:
        seed()
        assert titles(["--sort", "created_at"]) == ["low-late", "high-none", "medium-early"]

    def test_unknown_sort_is_rejected(self) -> None:
        result = runner.invoke(app, ["list", "--sort", "nonsense"])
        assert result.exit_code != 0
        assert "nonsense" in result.output


class TestCombinedWithScope:
    def test_options_work_with_all_projects(self) -> None:
        seed()
        ProjectService(GlobalConfigStorage()).create_project("p")
        get_use_case().add_task("p-high", priority=Priority.HIGH, project="p")

        result = runner.invoke(app, ["list", "--all", "--priority", "high", "--sort", "priority"])

        assert result.exit_code == 0, result.output
        assert "p-high" in result.output and "high-none" in result.output
        assert "low-late" not in result.output and "medium-early" not in result.output

    def test_options_work_with_the_active_project(self) -> None:
        ProjectService(GlobalConfigStorage()).create_project("p")  # 作成するとアクティブになる
        uc = get_use_case()
        uc.add_task("a", priority=Priority.LOW)
        uc.add_task("b", priority=Priority.HIGH)

        result = runner.invoke(app, ["list", "--sort", "priority"])

        names = [line for line in result.output.splitlines() if " a" in line or " b" in line]
        assert len(names) == 2 and " b" in names[0]


def test_sort_choices_match_the_filter_the_service_accepts() -> None:
    """CLI の選択肢(SortKey)が、`TaskFilter.sort` が受ける値と食い違わない。"""
    from typing import get_args

    from task_cli.cli.commands.list import SortKey
    from task_cli.services.task_manager import TaskFilter

    accepted = set(get_args(TaskFilter.__dataclass_fields__["sort"].type))
    assert {k.value for k in SortKey} == accepted

from pathlib import Path

import pytest
import typer
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from task_cli.cli.main import app as _app
from task_cli.cli.shell import InteractiveShell, build_completer, get_prompt, parse_input
from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.storage.global_config_storage import GlobalConfigStorage


# --- parse_input ---

class TestParseInput:
    def test_splits_simple_args(self) -> None:
        assert parse_input("list") == ["list"]

    def test_splits_multiple_args(self) -> None:
        assert parse_input("start 1") == ["start", "1"]

    def test_preserves_space_in_double_quotes(self) -> None:
        assert parse_input('add "スペース 含む タイトル"') == ["add", "スペース 含む タイトル"]

    def test_preserves_space_in_single_quotes(self) -> None:
        assert parse_input("add 'hello world'") == ["add", "hello world"]

    def test_unclosed_double_quote_returns_none(self) -> None:
        assert parse_input('add "未閉じ') is None

    def test_unclosed_single_quote_returns_none(self) -> None:
        assert parse_input("add '未閉じ") is None

    def test_empty_string_returns_empty_list(self) -> None:
        assert parse_input("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert parse_input("   ") == []

    def test_strips_leading_trailing_spaces(self) -> None:
        assert parse_input("  list  ") == ["list"]


# --- get_prompt ---

class TestGetPrompt:
    def _make_service(self, tmp_path: Path, active: str | None) -> GlobalConfigService:
        storage = GlobalConfigStorage(tmp_path / "config.yaml")
        storage.save(GlobalConfig(active_project=active))
        return GlobalConfigService(storage)

    def test_shows_project_name(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path, "myapp")
        assert get_prompt(svc) == "task [myapp]> "

    def test_shows_inbox_when_no_project(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path, None)
        assert get_prompt(svc) == "task [inbox]> "


# --- 補完(Issue #36) ---



def _complete(text: str) -> list[str]:
    completer = build_completer(_app)
    return [c.text for c in completer.get_completions(Document(text), CompleteEvent())]


class TestCompleter:
    def test_completes_command_names(self) -> None:
        assert "list" in _complete("lis")
        assert "add" not in _complete("lis")

    def test_completes_group_subcommands(self) -> None:
        assert "create" in _complete("project cr")
        assert "create" in _complete("project ")

    def test_completes_option_names_of_the_command(self) -> None:
        got = _complete("list --")
        assert "--all" in got
        assert "--inbox" in got

    def test_completes_enum_values_after_option(self) -> None:
        assert set(_complete("add x --priority ")) == {"high", "medium", "low"}
        assert _complete("add x --priority h") == ["high"]

    def test_short_option_also_completes_values(self) -> None:
        assert set(_complete("add x -p ")) == {"high", "medium", "low"}

    def test_options_complete_again_after_a_value(self) -> None:
        got = _complete("add x --priority high --")
        assert "--due" in got
        assert "--description" in got

    def test_no_candidates_after_unknown_command(self) -> None:
        assert _complete("nosuchcommand ") == []
        assert _complete("nosuchcommand --") == []

    def test_no_completion_inside_or_right_after_a_quoted_word(self) -> None:
        # クォートを外した語で置き換えると入力行が壊れるので、何も出さない
        assert _complete('add "a b') == []
        assert _complete('add "lis"') == []

    def test_completes_after_a_quoted_word_and_space(self) -> None:
        assert "--priority" in _complete('add "my task" --pri')

    def test_empty_input_lists_commands(self) -> None:
        got = _complete("")
        assert "list" in got and "project" in got


# --- AppError の表示(Issue #68) ---

class TestRunCommandShowsAppErrorFully:
    def test_app_error_is_shown_with_cause_and_remedy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """コマンドが `AppError` を捕捉しそこねても、原因と対処が出る(メッセージだけにならない)。"""
        monkeypatch.setenv("HOME", str(tmp_path))
        fake = typer.Typer()

        @fake.command("boom")
        def boom() -> None:
            raise AppError("壊れました", cause="ファイルが読めません", remedy="直してください")

        @fake.command("other")
        def other() -> None: ...

        monkeypatch.setattr("task_cli.cli.main.app", fake)

        InteractiveShell()._run_command(["boom"])

        out = capsys.readouterr().out
        assert "[Error] 壊れました" in out
        assert "原因: ファイルが読めません" in out
        assert "対処: 直してください" in out

    def test_broken_config_does_not_crash_the_shell(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".task-py").mkdir()
        (tmp_path / ".task-py" / "config.yaml").write_text("not: [valid: yaml", encoding="utf-8")

        InteractiveShell()._run_command(["list"])

        out = capsys.readouterr().out
        assert "[Error]" in out and "原因" in out and "対処" in out
        assert "Traceback" not in out

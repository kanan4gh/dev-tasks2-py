from pathlib import Path

from task_cli.cli.shell import get_prompt, parse_input
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

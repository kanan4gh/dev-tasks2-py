import pytest
from typer.testing import CliRunner

from task_cli.cli import main as main_mod

runner = CliRunner()


class TestIsNewer:
    @pytest.mark.parametrize(
        ("latest", "current", "expected"),
        [
            ("0.13.0", "0.12.1", True),
            ("0.12.1", "0.12.1", False),
            ("0.12.0", "0.12.1", False),  # 開発版: ローカルのほうが新しい
            ("0.10.0", "0.9.0", True),  # 文字列比較だと逆になる
            ("0.9.0", "0.10.0", False),
            ("not-a-version", "0.12.1", False),
            ("0.13.0", "garbage", False),
        ],
    )
    def test_cases(self, latest: str, current: str, expected: bool) -> None:
        assert main_mod._is_newer(latest, current) is expected  # pyright: ignore[reportPrivateUsage]


class TestVersionOutput:
    def _run(self, monkeypatch: pytest.MonkeyPatch, latest: str | None, current: str) -> str:
        monkeypatch.setattr(main_mod, "pkg_version", lambda _name: current)
        monkeypatch.setattr(main_mod, "_fetch_latest_version", lambda: latest)
        result = runner.invoke(main_mod.app, ["--version"])
        assert result.exit_code == 0
        return result.output

    def test_prompts_update_when_release_is_newer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert "新しいバージョン 0.13.0" in self._run(monkeypatch, "0.13.0", "0.12.1")

    def test_silent_when_equal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert "新しいバージョン" not in self._run(monkeypatch, "0.12.1", "0.12.1")

    def test_silent_when_local_is_ahead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert "新しいバージョン" not in self._run(monkeypatch, "0.12.0", "0.12.1")

    def test_silent_when_fetch_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert "新しいバージョン" not in self._run(monkeypatch, None, "0.12.1")

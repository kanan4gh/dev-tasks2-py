from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from task_cli.cli.commands import migrate as migrate_mod
from task_cli.cli.commands import reset as reset_mod

runner = CliRunner()


def _app() -> typer.Typer:
    app = typer.Typer()
    app.command()(reset_mod.reset)
    return app


def _generations(home: Path) -> list[Path]:
    return sorted(p for p in home.iterdir() if p.name.startswith(".task-py.backup."))


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    py_dir = tmp_path / ".task-py"
    backup = tmp_path / ".task-py.backup"
    monkeypatch.setattr(reset_mod, "_PY_DIR", py_dir)
    monkeypatch.setattr(reset_mod, "_BACKUP_DIR", backup)
    monkeypatch.setattr(migrate_mod, "_PY_DIR", py_dir)
    monkeypatch.setattr(migrate_mod, "_BACKUP_DIR", backup)
    return tmp_path


def _write(home: Path, content: str) -> None:
    py_dir = home / ".task-py"
    py_dir.mkdir(exist_ok=True)
    (py_dir / "tasks.yaml").write_text(content, encoding="utf-8")


class TestResetKeepsPreviousBackups:
    def test_second_reset_does_not_destroy_first_backup(self, home: Path) -> None:
        _write(home, "first")
        assert runner.invoke(_app(), [], input="y\n").exit_code == 0
        _write(home, "second")
        assert runner.invoke(_app(), [], input="y\n").exit_code == 0

        contents = sorted((g / "tasks.yaml").read_text(encoding="utf-8") for g in _generations(home))
        assert contents == ["first", "second"]

    def test_dialog_names_backup_pattern_and_retention(self, home: Path) -> None:
        _write(home, "x")
        result = runner.invoke(_app(), [], input="n\n")
        assert ".task-py.backup.<日時>" in result.output
        assert "5" in result.output


class TestMigrateThenReset:
    def test_pre_migrate_backup_survives_later_reset(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ts_dir = home / ".task"
        ts_dir.mkdir()
        monkeypatch.setattr(migrate_mod, "_TS_DIR", ts_dir)
        migrate_app = typer.Typer()
        migrate_app.command()(migrate_mod.migrate)

        _write(home, "before-migrate")
        assert runner.invoke(migrate_app, ["--force"]).exit_code == 0
        _write(home, "after-migrate")
        assert runner.invoke(_app(), [], input="y\n").exit_code == 0

        contents = sorted((g / "tasks.yaml").read_text(encoding="utf-8") for g in _generations(home))
        assert contents == ["after-migrate", "before-migrate"]

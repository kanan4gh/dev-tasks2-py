"""壊れた保存ファイルを読んだときの扱い(Issue #59)。

トレースバックではなく、`AppError` の3要素(message / cause / remedy)で
対象ファイルと対処を示すことを確かめる。
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from typer.testing import CliRunner

from task_cli.cli.main import app
from task_cli.exceptions import AppError, StorageReadError
from task_cli.storage.daily_log_storage import DailyLogStorage
from task_cli.storage.file_storage import FileStorage
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_cli.storage.routine_storage import RoutineStorage
from task_cli.storage.timer_storage import TimerStorage
from task_web.server import create_app

BROKEN_YAML = "not: [valid: yaml"
# YAML としては妥当だが、モデルの検証に通らない(status が未知)
INVALID_TASKS = "- id: 1\n  title: x\n  status: no-such-status\n"
INVALID_ROUTINES = "- id: not-a-number\n  title: x\n"
INVALID_LOGS = "- date: 2026-01-01\n  completed: not-a-list\n"
INVALID_CONFIG = "last_project_id: not-a-number\n"

runner = CliRunner()


def _loaders(base: Path):
    """(読み込み関数, ファイル, 不正な値の内容) の一覧。"""
    return [
        (FileStorage(base / "tasks.yaml").load, base / "tasks.yaml", INVALID_TASKS),
        (RoutineStorage(base / "routines.yaml").load, base / "routines.yaml", INVALID_ROUTINES),
        (DailyLogStorage(base / "log.yaml").load_all, base / "log.yaml", INVALID_LOGS),
        (GlobalConfigStorage(base / "config.yaml").load, base / "config.yaml", INVALID_CONFIG),
    ]


@pytest.mark.parametrize("index", range(4))
class TestStorageReadError:
    def test_broken_yaml_raises_storage_read_error(self, tmp_path: Path, index: int) -> None:
        load, path, _ = _loaders(tmp_path)[index]
        path.write_text(BROKEN_YAML, encoding="utf-8")

        with pytest.raises(StorageReadError) as info:
            load()

        error = info.value
        assert isinstance(error, AppError)
        assert "読み込めません" in str(error)
        assert str(path) in error.cause
        assert "行" in error.cause  # YAML の行・列が原因に入る
        assert "手で直" in error.remedy

    def test_invalid_values_raise_storage_read_error(self, tmp_path: Path, index: int) -> None:
        load, path, content = _loaders(tmp_path)[index]
        path.write_text(content, encoding="utf-8")

        with pytest.raises(StorageReadError) as info:
            load()

        assert str(path) in info.value.cause

    def test_invalid_encoding_raises_storage_read_error(self, tmp_path: Path, index: int) -> None:
        load, path, _ = _loaders(tmp_path)[index]
        path.write_bytes(b"\xff\xfe\x00bad")

        with pytest.raises(StorageReadError):
            load()

    def test_remedy_mentions_bak_only_when_it_exists(self, tmp_path: Path, index: int) -> None:
        load, path, _ = _loaders(tmp_path)[index]
        path.write_text(BROKEN_YAML, encoding="utf-8")
        with pytest.raises(StorageReadError) as without_bak:
            load()
        assert ".bak" not in without_bak.value.remedy

        bak = Path(str(path) + ".bak")
        bak.write_text("[]", encoding="utf-8")
        with pytest.raises(StorageReadError) as with_bak:
            load()
        assert str(bak) in with_bak.value.remedy


class TestHealthyFilesUnchanged:
    def test_missing_files_load_as_empty(self, tmp_path: Path) -> None:
        assert FileStorage(tmp_path / "tasks.yaml").load() == []
        assert RoutineStorage(tmp_path / "routines.yaml").load() == []
        assert DailyLogStorage(tmp_path / "log.yaml").load_all() == []

    def test_empty_file_loads_as_empty(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.yaml").write_text("", encoding="utf-8")
        assert FileStorage(tmp_path / "tasks.yaml").load() == []


class TestTimerStaysForgiving:
    def test_broken_timer_file_means_not_running(self, tmp_path: Path) -> None:
        path = tmp_path / "timer.yaml"
        path.write_text(BROKEN_YAML, encoding="utf-8")
        assert TimerStorage(path).load().active is None

    def test_invalid_timer_values_mean_not_running(self, tmp_path: Path) -> None:
        path = tmp_path / "timer.yaml"
        path.write_text("active: not-a-timer\n", encoding="utf-8")
        assert TimerStorage(path).load().active is None


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "120")
    return tmp_path


class TestCliShowsThreeElements:
    @pytest.mark.parametrize("args", [["list"], ["overview"], ["inbox"]])
    def test_broken_config_is_reported_without_traceback(self, home: Path, args: list[str]) -> None:
        (home / ".task-py").mkdir()
        (home / ".task-py" / "config.yaml").write_text(BROKEN_YAML, encoding="utf-8")

        result = runner.invoke(app, args)

        assert result.exit_code == 1
        assert "[Error]" in result.output
        assert "原因:" in result.output
        assert "対処:" in result.output
        assert "Traceback" not in result.output
        assert isinstance(result.exception, SystemExit)

    def test_broken_tasks_file_is_reported_by_list(self, home: Path) -> None:
        inbox = home / ".task-py" / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "tasks.yaml").write_text(BROKEN_YAML, encoding="utf-8")

        result = runner.invoke(app, ["list", "--inbox"])

        assert result.exit_code == 1
        assert "tasks.yaml" in result.output
        assert isinstance(result.exception, SystemExit)


@pytest.fixture
def client(home: Path) -> Iterator[TestClient]:
    with TestClient(create_app(["127.0.0.1", "localhost", "testserver"])) as c:
        yield c


class TestWebReportsCause:
    def test_broken_config_returns_500_with_cause_and_remedy(self, home: Path, client: TestClient) -> None:
        (home / ".task-py").mkdir()
        (home / ".task-py" / "config.yaml").write_text(BROKEN_YAML, encoding="utf-8")

        response = client.get("/api/state")

        assert response.status_code == 500
        body = response.json()
        assert "config.yaml" in str(body)
        assert "手で直" in str(body)


class TestReadErrorDetails:
    def test_wrong_top_level_shape_is_named(self, tmp_path: Path) -> None:
        path = tmp_path / "tasks.yaml"
        path.write_text("a: 1\n", encoding="utf-8")
        with pytest.raises(StorageReadError) as info:
            FileStorage(path).load()
        assert "最上位" in info.value.cause

    def test_cause_points_at_record_number_and_counts_others(self, tmp_path: Path) -> None:
        path = tmp_path / "tasks.yaml"
        path.write_text(
            "- id: 1\n  title: ok\n- id: 2\n  title: x\n  status: bad\n- id: 3\n  title: y\n  status: bad\n",
            encoding="utf-8",
        )
        with pytest.raises(StorageReadError) as info:
            FileStorage(path).load()
        assert "2件目" in info.value.cause
        assert "ほかに 1 件" in info.value.cause

    def test_bak_remedy_warns_it_may_be_stale(self, tmp_path: Path) -> None:
        path = tmp_path / "tasks.yaml"
        path.write_text(BROKEN_YAML, encoding="utf-8")
        Path(str(path) + ".bak").write_text("[]", encoding="utf-8")
        with pytest.raises(StorageReadError) as info:
            FileStorage(path).load()
        assert "確認" in info.value.remedy


class TestMarkupInErrorIsNotInterpreted:
    def test_brackets_in_path_and_message_are_printed_literally(
        self, home: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from task_cli.cli.renderer import render_error

        render_error(AppError("m [/x]", "cause [/bold] [a]", "fix [b]"))
        out = capsys.readouterr().out
        assert "[/bold]" in out and "[a]" in out and "[b]" in out and "[/x]" in out


class TestEveryReadingCommandHandlesBrokenFiles:
    @pytest.mark.parametrize(
        "args",
        [["project", "list"], ["daily", "list"], ["daily", "stats"], ["list"], ["overview"], ["inbox"]],
    )
    def test_no_traceback(self, home: Path, args: list[str]) -> None:
        daily = home / ".task-py" / "daily"
        daily.mkdir(parents=True)
        for name in ("routines.yaml", "log.yaml"):
            (daily / name).write_text(BROKEN_YAML, encoding="utf-8")
        (home / ".task-py" / "config.yaml").write_text(BROKEN_YAML, encoding="utf-8")

        result = runner.invoke(app, args)

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "[Error]" in result.output

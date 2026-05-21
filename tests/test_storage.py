from datetime import datetime, timezone
from pathlib import Path

import pytest

from task_cli.models.task import GlobalConfig, Priority, ProjectEntry, Task, TaskStatus
from task_cli.storage.file_storage import FileStorage
from task_cli.storage.global_config_storage import GlobalConfigStorage


def make_task(id: int, title: str = "テスト", **kwargs) -> Task:
    return Task(id=id, title=title, **kwargs)


class TestFileStorage:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        storage = FileStorage(tmp_path / "tasks.yaml")
        assert storage.load() == []

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        storage = FileStorage(tmp_path / "tasks.yaml")
        tasks = [
            make_task(1, "タスク1"),
            make_task(2, "タスク2", status=TaskStatus.IN_PROGRESS, priority=Priority.HIGH),
        ]
        storage.save(tasks)
        loaded = storage.load()

        assert len(loaded) == 2
        assert loaded[0].id == 1
        assert loaded[0].title == "タスク1"
        assert loaded[1].status == TaskStatus.IN_PROGRESS
        assert loaded[1].priority == Priority.HIGH

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "projects" / "my-app" / "tasks.yaml"
        storage = FileStorage(nested)
        storage.save([make_task(1)])
        assert nested.exists()

    def test_save_empty_list(self, tmp_path: Path) -> None:
        storage = FileStorage(tmp_path / "tasks.yaml")
        storage.save([make_task(1)])
        storage.save([])
        assert storage.load() == []

    def test_save_preserves_datetime(self, tmp_path: Path) -> None:
        now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        task = Task(id=1, title="t", created_at=now, updated_at=now)
        storage = FileStorage(tmp_path / "tasks.yaml")
        storage.save([task])
        loaded = storage.load()
        assert loaded[0].created_at == now

    def test_save_preserves_due_date(self, tmp_path: Path) -> None:
        task = make_task(1, due_date="2026-12-31")
        storage = FileStorage(tmp_path / "tasks.yaml")
        storage.save([task])
        loaded = storage.load()
        assert loaded[0].due_date == "2026-12-31"

    def test_save_preserves_branch(self, tmp_path: Path) -> None:
        task = make_task(1, branch="feature/task-1-test")
        storage = FileStorage(tmp_path / "tasks.yaml")
        storage.save([task])
        loaded = storage.load()
        assert loaded[0].branch == "feature/task-1-test"

    def test_backup_created_during_save(self, tmp_path: Path) -> None:
        path = tmp_path / "tasks.yaml"
        storage = FileStorage(path)
        storage.save([make_task(1)])

        bak_path = Path(str(path) + ".bak")
        # バックアップは成功後に削除される
        assert not bak_path.exists()

    def test_backup_restored_on_write_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "tasks.yaml"
        storage = FileStorage(path)
        original = [make_task(1, "元のタスク")]
        storage.save(original)

        # 書き込み中にエラーが発生するよう yaml.safe_dump をモック
        import yaml
        def broken_dump(*args, **kwargs):
            raise OSError("disk full")
        monkeypatch.setattr(yaml, "safe_dump", broken_dump)

        with pytest.raises(OSError):
            storage.save([make_task(2, "新しいタスク")])

        # 元のデータが復元されている
        storage2 = FileStorage(path)
        loaded = storage2.load()
        assert len(loaded) == 1
        assert loaded[0].title == "元のタスク"


class TestGlobalConfigStorage:
    def test_load_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        storage = GlobalConfigStorage(tmp_path / "config.yaml")
        config = storage.load()
        assert config.active_project is None
        assert config.projects == []
        assert config.last_project_id == 0

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        storage = GlobalConfigStorage(tmp_path / "config.yaml")
        config = GlobalConfig(
            active_project="my-app",
            projects=[ProjectEntry(name="my-app", id=1)],
            last_project_id=1,
        )
        storage.save(config)
        loaded = storage.load()

        assert loaded.active_project == "my-app"
        assert len(loaded.projects) == 1
        assert loaded.projects[0].name == "my-app"
        assert loaded.last_project_id == 1

    def test_save_null_active_project(self, tmp_path: Path) -> None:
        storage = GlobalConfigStorage(tmp_path / "config.yaml")
        storage.save(GlobalConfig(active_project=None))
        loaded = storage.load()
        assert loaded.active_project is None

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "task" / "config.yaml"
        storage = GlobalConfigStorage(path)
        storage.save(GlobalConfig())
        assert path.exists()

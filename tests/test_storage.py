from datetime import datetime, timezone
from pathlib import Path

import pytest

from task_cli.models.task import GlobalConfig, Priority, ProjectEntry, Task, TaskStatus
from task_cli.models.time import WorkSession
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

    def test_completed_at_roundtrip(self, tmp_path: Path) -> None:
        storage = FileStorage(tmp_path / "tasks.yaml")
        completed_at = datetime(2026, 7, 1, 12, 34, tzinfo=timezone.utc)
        storage.save([make_task(1, status=TaskStatus.COMPLETED, completed_at=completed_at)])
        assert storage.load()[0].completed_at == completed_at

    def test_load_yaml_without_completed_at_key(self, tmp_path: Path) -> None:
        """completed_at キーを持たない既存 YAML を直接書いて読めること。"""
        path = tmp_path / "tasks.yaml"
        path.write_text(
            "- id: 1\n"
            "  title: 旧データ\n"
            "  description: ''\n"
            "  status: completed\n"
            "  priority: medium\n"
            "  branch: null\n"
            "  due_date: null\n"
            "  created_at: '2026-06-01T00:00:00+00:00'\n"
            "  updated_at: '2026-06-02T00:00:00+00:00'\n"
            "  scheduled_date: null\n",
            encoding="utf-8",
        )
        loaded = FileStorage(path).load()
        assert len(loaded) == 1
        assert loaded[0].completed_at is None

    def test_work_sessions_roundtrip(self, tmp_path: Path) -> None:
        """ネストしたリストが model_dump(mode="json") の往復で保たれること。"""
        storage = FileStorage(tmp_path / "tasks.yaml")
        started = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
        ended = datetime(2026, 7, 1, 9, 20, tzinfo=timezone.utc)
        storage.save([
            make_task(1, work_sessions=[
                WorkSession(started_at=started, ended_at=ended, seconds=1200),
                WorkSession(started_at=started, ended_at=ended, seconds=300, source="manual"),
            ])
        ])
        loaded = storage.load()[0]
        assert len(loaded.work_sessions) == 2
        assert loaded.work_sessions[0].started_at == started
        assert loaded.work_sessions[0].ended_at == ended
        assert loaded.work_sessions[0].source == "timer"
        assert loaded.work_sessions[1].source == "manual"
        assert loaded.total_worked_seconds == 1500

    def test_load_yaml_without_work_sessions_key(self, tmp_path: Path) -> None:
        path = tmp_path / "tasks.yaml"
        path.write_text(
            "- id: 1\n"
            "  title: 旧データ\n"
            "  status: open\n"
            "  priority: medium\n"
            "  created_at: '2026-06-01T00:00:00+00:00'\n"
            "  updated_at: '2026-06-02T00:00:00+00:00'\n",
            encoding="utf-8",
        )
        loaded = FileStorage(path).load()
        assert loaded[0].work_sessions == []

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


class TestWriteFailureLeavesDataIntact:
    """書き込み中に落ちても既存ファイルが 0 バイトにならないこと。

    5ストレージすべてが `write_atomic` を通ることの回帰テスト。従来は
    `open(path, "w")` が先にファイルを切り詰めていたため、ここで落ちると
    `.bak` を持たない4ストレージはデータを丸ごと失っていた。
    """

    @staticmethod
    def _cases(tmp_path: Path) -> list[tuple[str, object, object]]:
        from task_cli.models.daily import DailyLog, Routine
        from task_cli.models.time import TimerFile
        from task_cli.storage.daily_log_storage import DailyLogStorage
        from task_cli.storage.routine_storage import RoutineStorage
        from task_cli.storage.timer_storage import TimerStorage

        created = datetime(2026, 9, 6, tzinfo=timezone.utc)
        return [
            ("tasks.yaml", FileStorage(tmp_path / "tasks.yaml"), [make_task(1)]),
            ("config.yaml", GlobalConfigStorage(tmp_path / "config.yaml"), GlobalConfig()),
            (
                "routines.yaml",
                RoutineStorage(tmp_path / "routines.yaml"),
                [Routine(id=1, title="朝会", created_at=created)],
            ),
            ("log.yaml", DailyLogStorage(tmp_path / "log.yaml"), [DailyLog(date="2026-09-06")]),
            ("timer.yaml", TimerStorage(tmp_path / "timer.yaml"), TimerFile()),
        ]

    @staticmethod
    def _save(storage: object, payload: object) -> None:
        save_all = getattr(storage, "save_all", None)
        if save_all is not None:
            save_all(payload)
            return
        getattr(storage, "save")(payload)

    def test_original_content_survives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import yaml

        for name, storage, payload in self._cases(tmp_path):
            path = tmp_path / name
            self._save(storage, payload)
            before = path.read_bytes()
            assert before, f"{name}: 前提となる初回書き込みが空だった"

            def broken_dump(*args: object, **kwargs: object) -> None:
                raise OSError("disk full")

            monkeypatch.setattr(yaml, "safe_dump", broken_dump)
            with pytest.raises(OSError):
                self._save(storage, payload)
            monkeypatch.undo()

            assert path.read_bytes() == before, f"{name}: 書き込み失敗で内容が壊れた"
            leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
            assert leftovers == [], f"{name}: 一時ファイルが残った: {leftovers}"

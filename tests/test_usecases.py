from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig, Priority, TaskStatus
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.task_manager import TaskFilter, TaskManager
from task_cli.storage.file_storage import FileStorage
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_cli.usecases.task_crud_usecase import TaskCrudUseCase, resolve_storage_path


# --- helpers ---

def make_storage(tmp_path: Path, name: str = "tasks.yaml") -> FileStorage:
    return FileStorage(tmp_path / name)


def make_manager(tmp_path: Path) -> TaskManager:
    return TaskManager(make_storage(tmp_path))


def make_use_case(tmp_path: Path, active_project: str | None = None) -> TaskCrudUseCase:
    config_storage = GlobalConfigStorage(tmp_path / "config.yaml")
    config_storage.save(GlobalConfig(active_project=active_project))
    global_config_service = GlobalConfigService(config_storage)

    storages: dict[Path, FileStorage] = {}

    def storage_factory(path: Path) -> FileStorage:
        if path not in storages:
            # プロジェクト名とファイル名を組み合わせてユニークにする
            unique_name = f"{path.parent.name}_{path.name}"
            storages[path] = FileStorage(tmp_path / unique_name)
        return storages[path]

    return TaskCrudUseCase(global_config_service, storage_factory)


# --- TaskManager tests ---

class TestTaskManagerCreate:
    def test_create_assigns_id_starting_at_1(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        task = manager.create_task("最初のタスク")
        assert task.id == 1

    def test_create_increments_id(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク1")
        task2 = manager.create_task("タスク2")
        assert task2.id == 2

    def test_create_with_all_fields(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        task = manager.create_task(
            "タスク",
            description="詳細",
            priority=Priority.HIGH,
            due_date="2026-12-31",
        )
        assert task.description == "詳細"
        assert task.priority == Priority.HIGH
        assert task.due_date == "2026-12-31"
        assert task.status == TaskStatus.OPEN

    def test_create_persists_task(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("永続化テスト")
        # 別インスタンスで読み込んでも取得できる
        manager2 = make_manager(tmp_path)
        tasks = manager2.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "永続化テスト"


class TestTaskManagerGet:
    def test_get_existing_task(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("取得テスト")
        task = manager.get_task(1)
        assert task.title == "取得テスト"

    def test_get_nonexistent_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        with pytest.raises(AppError):
            manager.get_task(99)


class TestTaskManagerList:
    def test_list_all(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("A")
        manager.create_task("B")
        assert len(manager.list_tasks()) == 2

    def test_list_filter_by_status(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("open")
        t2 = manager.create_task("in_progress")
        manager.start_task(t2.id)

        result = manager.list_tasks(TaskFilter(status=TaskStatus.IN_PROGRESS))
        assert len(result) == 1
        assert result[0].title == "in_progress"

    def test_list_filter_by_multiple_status(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("open")
        t2 = manager.create_task("in_progress")
        manager.start_task(t2.id)
        t3 = manager.create_task("completed")
        manager.start_task(t3.id)
        manager.complete_task(t3.id)

        result = manager.list_tasks(
            TaskFilter(status=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS])
        )
        assert len(result) == 2

    def test_list_filter_by_priority(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("high", priority=Priority.HIGH)
        manager.create_task("medium")
        result = manager.list_tasks(TaskFilter(priority=Priority.HIGH))
        assert len(result) == 1
        assert result[0].title == "high"

    def test_list_sort_by_priority(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("low", priority=Priority.LOW)
        manager.create_task("high", priority=Priority.HIGH)
        manager.create_task("medium", priority=Priority.MEDIUM)
        result = manager.list_tasks(TaskFilter(sort="priority"))
        assert [t.priority for t in result] == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_list_sort_by_due_date_null_last(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("no-due")
        manager.create_task("later", due_date="2026-12-31")
        manager.create_task("earlier", due_date="2026-01-01")
        result = manager.list_tasks(TaskFilter(sort="due_date"))
        assert result[0].due_date == "2026-01-01"
        assert result[1].due_date == "2026-12-31"
        assert result[2].due_date is None


class TestTaskManagerStatusTransitions:
    def test_start_task(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        task = manager.start_task(1)
        assert task.status == TaskStatus.IN_PROGRESS

    def test_complete_task(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        task = manager.complete_task(1)
        assert task.status == TaskStatus.COMPLETED

    def test_archive_from_open(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        task = manager.archive_task(1)
        assert task.status == TaskStatus.ARCHIVED

    def test_archive_from_completed(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        manager.complete_task(1)
        task = manager.archive_task(1)
        assert task.status == TaskStatus.ARCHIVED

    def test_start_already_in_progress_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        with pytest.raises(AppError):
            manager.start_task(1)

    def test_complete_open_task_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        with pytest.raises(AppError):
            manager.complete_task(1)

    def test_archive_in_progress_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        with pytest.raises(AppError):
            manager.archive_task(1)


class TestTaskManagerDelete:
    def test_delete_existing(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("削除対象")
        manager.delete_task(1)
        assert manager.list_tasks() == []

    def test_delete_id_not_reused(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("A")
        manager.create_task("B")
        manager.delete_task(1)
        task = manager.create_task("C")
        assert task.id == 3  # ID=1 は再利用しない

    def test_delete_nonexistent_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        with pytest.raises(AppError):
            manager.delete_task(99)


class TestTaskManagerSearch:
    def test_search_by_title(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("ユーザー認証機能")
        manager.create_task("データエクスポート")
        result = manager.search_tasks("認証")
        assert len(result) == 1
        assert result[0].title == "ユーザー認証機能"

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("Fix Login Bug")
        result = manager.search_tasks("login")
        assert len(result) == 1

    def test_search_by_description(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク", description="JWT認証の実装")
        result = manager.search_tasks("JWT")
        assert len(result) == 1

    def test_search_no_match(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        result = manager.search_tasks("存在しないキーワード")
        assert result == []


# --- TaskCrudUseCase tests ---

class TestTaskCrudUseCase:
    def test_add_and_list(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        uc.add_task("タスク1")
        uc.add_task("タスク2")
        tasks = uc.list_tasks()
        assert len(tasks) == 2

    def test_add_get_flow(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        added = uc.add_task("取得テスト", priority=Priority.HIGH)
        fetched = uc.get_task(added.id)
        assert fetched.title == "取得テスト"
        assert fetched.priority == Priority.HIGH

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("ライフサイクルテスト")
        assert task.status == TaskStatus.OPEN

        task = uc.start_task(task.id)
        assert task.status == TaskStatus.IN_PROGRESS

        task = uc.complete_task(task.id)
        assert task.status == TaskStatus.COMPLETED

        task = uc.archive_task(task.id)
        assert task.status == TaskStatus.ARCHIVED

    def test_delete_task(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("削除テスト")
        uc.delete_task(task.id)
        assert uc.list_tasks() == []

    def test_search_tasks(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        uc.add_task("ユーザー認証")
        uc.add_task("DB設計")
        result = uc.search_tasks("認証")
        assert len(result) == 1


class TestMoveTask:
    def test_move_to_another_project(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path, active_project="src-proj")
        task = uc.add_task("移動タスク")
        moved = uc.move_task(task.id, "dst-proj")
        assert moved.title == "移動タスク"
        # 移動元からなくなっている
        assert uc.list_tasks() == []

    def test_move_to_inbox(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path, active_project="myapp")
        task = uc.add_task("Inboxへ移動")
        moved = uc.move_task(task.id, None)
        assert moved.title == "Inboxへ移動"
        assert uc.list_tasks() == []

    def test_move_nonexistent_id_raises(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        with pytest.raises(AppError):
            uc.move_task(999, "other-proj")


class TestResolveStoragePath:
    def test_with_active_project(self) -> None:
        path = resolve_storage_path("my-app")
        assert "projects/my-app/tasks.yaml" in str(path)

    def test_inbox_when_no_project(self) -> None:
        path = resolve_storage_path(None)
        assert "inbox/tasks.yaml" in str(path)

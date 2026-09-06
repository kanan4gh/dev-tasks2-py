from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig, Priority, ProjectEntry, TaskStatus
from task_cli.models.time import WorkSession
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


def make_session(seconds: int, source: str = "timer") -> WorkSession:
    started = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    return WorkSession(
        started_at=started,
        ended_at=started + timedelta(seconds=seconds),
        seconds=seconds,
        source="manual" if source == "manual" else "timer",
    )


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

    def test_complete_records_completed_at(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        task = manager.complete_task(1)
        assert task.completed_at is not None

    def test_completed_at_is_none_before_completion(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        assert manager.get_task(1).completed_at is None
        assert manager.start_task(1).completed_at is None

    def test_archive_from_completed_keeps_completed_at(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        completed_at = manager.complete_task(1).completed_at
        task = manager.archive_task(1)
        assert task.completed_at == completed_at

    def test_archive_from_open_leaves_completed_at_none(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        task = manager.archive_task(1)
        assert task.completed_at is None

    def test_editing_after_completion_keeps_completed_at(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        completed_at = manager.complete_task(1).completed_at
        task = manager.edit_fields(1, title="新しいタイトル")
        assert task.completed_at == completed_at
        assert task.updated_at != completed_at

    def test_leaving_completed_clears_completed_at(self, tmp_path: Path) -> None:
        """完了から出る遷移が追加されたときに備えた、絞り口そのものの検証。

        can_transition_to には現在 completed -> open の経路が無いため、
        _apply_status_change を直接呼んで規則だけを確かめる。
        """
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.start_task(1)
        manager.complete_task(1)
        completed = manager.get_task(1)
        task = manager._apply_status_change(completed, TaskStatus.OPEN)  # pyright: ignore[reportPrivateUsage]
        assert task.completed_at is None

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

    def test_start_with_future_scheduled_date_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.set_scheduled_date(1, "2099-01-01")
        with pytest.raises(AppError):
            manager.start_task(1)

    def test_start_with_past_scheduled_date_succeeds(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.set_scheduled_date(1, "2000-01-01")
        task = manager.start_task(1)
        assert task.status == TaskStatus.IN_PROGRESS

    def test_start_without_scheduled_date_succeeds(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        task = manager.start_task(1)
        assert task.status == TaskStatus.IN_PROGRESS


class TestTaskManagerWorkSessions:
    def test_append_adds_session(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        task = manager.append_work_session(1, make_session(1200))
        assert len(task.work_sessions) == 1
        assert task.total_worked_seconds == 1200

    def test_append_accumulates(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.append_work_session(1, make_session(1200))
        task = manager.append_work_session(1, make_session(600))
        assert len(task.work_sessions) == 2
        assert task.total_worked_seconds == 1800

    def test_append_does_not_touch_updated_at(self, tmp_path: Path) -> None:
        """作業時間の記録は内容の編集ではないので updated_at を動かしてはいけない。"""
        manager = make_manager(tmp_path)
        created = manager.create_task("タスク")
        task = manager.append_work_session(1, make_session(1200))
        assert task.updated_at == created.updated_at

    def test_append_persists(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        manager.create_task("タスク")
        manager.append_work_session(1, make_session(1200))
        assert make_manager(tmp_path).get_task(1).total_worked_seconds == 1200

    def test_append_to_missing_task_raises(self, tmp_path: Path) -> None:
        manager = make_manager(tmp_path)
        with pytest.raises(AppError):
            manager.append_work_session(99, make_session(60))

    def test_sessions_survive_move(self, tmp_path: Path) -> None:
        """move で ID が振り直されてもセッションが一緒に移ること。"""
        uc = make_use_case(tmp_path, active_project=None)
        uc.add_task("タスク")
        uc._get_manager().append_work_session(1, make_session(1200))  # pyright: ignore[reportPrivateUsage]
        moved = uc.move_task(1, "proj-a")
        assert moved.total_worked_seconds == 1200


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


def make_use_case_with_projects(
    tmp_path: Path, active_project: str | None, project_names: list[str]
) -> TaskCrudUseCase:
    config_storage = GlobalConfigStorage(tmp_path / "config.yaml")
    projects = [ProjectEntry(id=i + 1, name=name) for i, name in enumerate(project_names)]
    config_storage.save(GlobalConfig(active_project=active_project, projects=projects, last_project_id=len(projects)))
    global_config_service = GlobalConfigService(config_storage)
    storages: dict[Path, FileStorage] = {}

    def storage_factory(path: Path) -> FileStorage:
        if path not in storages:
            unique_name = f"{path.parent.name}_{path.name}"
            storages[path] = FileStorage(tmp_path / unique_name)
        return storages[path]

    return TaskCrudUseCase(global_config_service, storage_factory)


class TestListAllProjects:
    def test_returns_inbox_and_projects(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(tmp_path, active_project="proj-a", project_names=["proj-a"])
        uc.add_task("プロジェクトタスク")

        result = uc.list_all_projects()
        assert None in result
        assert "proj-a" in result
        assert len(result["proj-a"]) == 1

    def test_inbox_tasks_are_included(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(tmp_path, active_project=None, project_names=[])
        uc.add_task("Inboxタスク")

        result = uc.list_all_projects()
        assert None in result
        assert len(result[None]) == 1

    def test_filter_applied_to_all_projects(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(tmp_path, active_project="proj-a", project_names=["proj-a"])
        uc.add_task("オープンタスク")
        t2 = uc.add_task("完了タスク")
        uc.start_task(t2.id)
        uc.complete_task(t2.id)

        result = uc.list_all_projects(TaskFilter(status=[TaskStatus.OPEN]))
        assert len(result["proj-a"]) == 1
        assert result["proj-a"][0].title == "オープンタスク"


class TestListInboxTasks:
    def test_returns_only_inbox_tasks(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path, active_project=None)
        uc.add_task("Inboxタスク1")
        uc.add_task("Inboxタスク2")

        result = uc.list_inbox_tasks()
        assert len(result) == 2

    def test_filter_applied(self, tmp_path: Path) -> None:
        from task_cli.models.task import TaskStatus
        uc = make_use_case(tmp_path, active_project=None)
        uc.add_task("オープン")
        t2 = uc.add_task("完了")
        uc.start_task(t2.id)
        uc.complete_task(t2.id)

        result = uc.list_inbox_tasks(TaskFilter(status=[TaskStatus.OPEN]))
        assert len(result) == 1
        assert result[0].title == "オープン"


class TestEditTask:
    def test_update_title(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("元タイトル")
        updated = uc.edit_task(task.id, title="新タイトル")
        assert updated.title == "新タイトル"

    def test_update_description_and_priority(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("タスク")
        updated = uc.edit_task(task.id, description="詳細", priority=Priority.HIGH)
        assert updated.description == "詳細"
        assert updated.priority == Priority.HIGH

    def test_set_and_clear_due_date(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("タスク")
        updated = uc.edit_task(task.id, due_date="2026-12-31")
        assert updated.due_date == "2026-12-31"
        cleared = uc.edit_task(task.id, clear_due_date=True)
        assert cleared.due_date is None

    def test_set_and_clear_scheduled_date(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("タスク")
        updated = uc.edit_task(task.id, scheduled_date="2099-01-01")
        assert updated.scheduled_date == "2099-01-01"
        cleared = uc.edit_task(task.id, clear_scheduled_date=True)
        assert cleared.scheduled_date is None

    def test_nonexistent_id_raises(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        with pytest.raises(AppError):
            uc.edit_task(999, title="X")


class TestSetScheduledDate:
    def test_set_scheduled_date(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("タスク")
        updated = uc.set_scheduled_date(task.id, "2099-06-01")
        assert updated.scheduled_date == "2099-06-01"

    def test_clear_scheduled_date(self, tmp_path: Path) -> None:
        uc = make_use_case(tmp_path)
        task = uc.add_task("タスク")
        uc.set_scheduled_date(task.id, "2099-06-01")
        cleared = uc.set_scheduled_date(task.id, None)
        assert cleared.scheduled_date is None


class TestResolveStoragePath:
    def test_with_active_project(self) -> None:
        path = resolve_storage_path("my-app")
        assert "projects/my-app/tasks.yaml" in str(path)

    def test_inbox_when_no_project(self) -> None:
        path = resolve_storage_path(None)
        assert "inbox/tasks.yaml" in str(path)


class TestExplicitProjectTarget:
    """書き込み先をアクティブプロジェクトではなく呼び出し側が決められること。

    GUI は全プロジェクトを一画面に出す面なので、画面上のタスクと実際に
    書き換わるタスクが食い違ってはいけない。タスク ID はストレージ
    ローカルであり、別プロジェクトにも同じ ID が存在しうる。
    """

    def test_add_task_targets_the_named_project(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("Bのタスク", project="proj-b")

        assert [t.title for t in uc.list_tasks(project="proj-b")] == ["Bのタスク"]
        assert uc.list_tasks(project="proj-a") == []

    def test_add_task_targets_inbox_when_project_is_none(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a"]
        )
        uc.add_task("Inboxのタスク", project=None)

        assert [t.title for t in uc.list_inbox_tasks()] == ["Inboxのタスク"]
        assert uc.list_tasks(project="proj-a") == []

    def test_operations_do_not_touch_the_same_id_in_the_active_project(
        self, tmp_path: Path
    ) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("Aの1番")
        uc.add_task("Bの1番", project="proj-b")

        uc.start_task(1, project="proj-b")
        uc.complete_task(1, project="proj-b")

        assert uc.get_task(1, project="proj-a").status == TaskStatus.OPEN
        assert uc.get_task(1, project="proj-b").status == TaskStatus.COMPLETED

    def test_edit_and_delete_target_the_named_project(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("Aの1番")
        uc.add_task("Bの1番", project="proj-b")

        uc.edit_task(1, title="Bの1番（改）", project="proj-b")
        assert uc.get_task(1, project="proj-b").title == "Bの1番（改）"
        assert uc.get_task(1, project="proj-a").title == "Aの1番"

        uc.delete_task(1, project="proj-b")
        assert uc.list_tasks(project="proj-b") == []
        assert len(uc.list_tasks(project="proj-a")) == 1

    def test_search_and_schedule_target_the_named_project(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("Aの検索対象")
        uc.add_task("Bの検索対象", project="proj-b")

        found = uc.search_tasks("検索対象", project="proj-b")
        assert [t.title for t in found] == ["Bの検索対象"]

        uc.set_scheduled_date(1, "2026-12-31", project="proj-b")
        assert uc.get_task(1, project="proj-b").scheduled_date == "2026-12-31"
        assert uc.get_task(1, project="proj-a").scheduled_date is None

    def test_move_reads_from_the_named_source_project(self, tmp_path: Path) -> None:
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("Aの1番")
        uc.add_task("Bの1番", project="proj-b")

        moved = uc.move_task(1, None, project="proj-b")

        assert moved.title == "Bの1番"
        assert uc.list_tasks(project="proj-b") == []
        assert len(uc.list_tasks(project="proj-a")) == 1
        assert [t.title for t in uc.list_inbox_tasks()] == ["Bの1番"]

    def test_default_still_follows_the_active_project(self, tmp_path: Path) -> None:
        """既定値は現行の挙動のまま（CLI・MCP の無改修を担保する）。"""
        uc = make_use_case_with_projects(
            tmp_path, active_project="proj-a", project_names=["proj-a", "proj-b"]
        )
        uc.add_task("既定のタスク")

        assert [t.title for t in uc.list_tasks()] == ["既定のタスク"]
        assert uc.list_tasks(project="proj-b") == []


class TestMoveDoesNotCreateStrayDirectories:
    """存在しないタスクの move が空のプロジェクトディレクトリを残さないこと（段3 指摘6）。

    ロックファイルを置くために `ensure_directory()` が要るが、それを検証より
    前に無条件で行うと、失敗しただけで `config.yaml` に載らない見えない
    ディレクトリが残る。
    """

    def test_moving_a_missing_task_leaves_no_directory(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        config_storage = GlobalConfigStorage(tmp_path / "config.yaml")
        config_storage.save(GlobalConfig(active_project=None))
        uc = TaskCrudUseCase(
            GlobalConfigService(config_storage),
            lambda path: FileStorage(home / path.parent.name / path.name),
        )

        with pytest.raises(AppError):
            uc.move_task(999, "typo-project")

        assert not (home / "typo-project").exists()

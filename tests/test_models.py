from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from task_cli.models.task import GlobalConfig, Priority, ProjectEntry, Task, TaskStatus
from task_cli.models.time import WorkSession


class TestTaskStatus:
    def test_values(self) -> None:
        assert TaskStatus.OPEN == "open"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.ARCHIVED == "archived"


class TestPriority:
    def test_values(self) -> None:
        assert Priority.HIGH == "high"
        assert Priority.MEDIUM == "medium"
        assert Priority.LOW == "low"


class TestTask:
    def test_create_minimal(self) -> None:
        task = Task(id=1, title="テストタスク")
        assert task.id == 1
        assert task.title == "テストタスク"
        assert task.description == ""
        assert task.status == TaskStatus.OPEN
        assert task.priority == Priority.MEDIUM
        assert task.branch is None
        assert task.due_date is None
        assert task.completed_at is None

    def test_validate_legacy_dict_without_completed_at(self) -> None:
        """completed_at を持たない移行前の YAML をそのまま読めること。"""
        task = Task.model_validate({
            "id": 1,
            "title": "旧データ",
            "description": "",
            "status": "completed",
            "priority": "medium",
            "branch": None,
            "due_date": None,
            "created_at": "2026-06-01T00:00:00+00:00",
            "updated_at": "2026-06-02T00:00:00+00:00",
            "scheduled_date": None,
        })
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is None
        assert task.work_sessions == []

    def test_total_worked_seconds_defaults_to_zero(self) -> None:
        assert Task(id=1, title="タスク").total_worked_seconds == 0

    def test_total_worked_seconds_sums_sessions(self) -> None:
        started = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
        task = Task(
            id=1,
            title="タスク",
            work_sessions=[
                WorkSession(started_at=started, ended_at=started, seconds=1200),
                WorkSession(started_at=started, ended_at=started, seconds=600, source="manual"),
            ],
        )
        assert task.total_worked_seconds == 1800

    def test_total_worked_seconds_is_not_persisted(self) -> None:
        """計算値をシリアライズすると二重の真実になるため出さない。"""
        assert "total_worked_seconds" not in Task(id=1, title="タスク").model_dump()

    def test_create_full(self) -> None:
        now = datetime.now(timezone.utc)
        task = Task(
            id=2,
            title="フルタスク",
            description="詳細説明",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            branch="feature/task-2-full",
            due_date="2026-12-31",
            created_at=now,
            updated_at=now,
        )
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == Priority.HIGH
        assert task.due_date == "2026-12-31"

    def test_title_too_short(self) -> None:
        with pytest.raises(ValidationError):
            Task(id=1, title="")

    def test_title_too_long(self) -> None:
        with pytest.raises(ValidationError):
            Task(id=1, title="x" * 201)

    def test_title_max_length(self) -> None:
        task = Task(id=1, title="x" * 200)
        assert len(task.title) == 200

    def test_due_date_valid(self) -> None:
        task = Task(id=1, title="test", due_date="2026-03-31")
        assert task.due_date == "2026-03-31"

    def test_due_date_invalid(self) -> None:
        with pytest.raises(ValidationError):
            Task(id=1, title="test", due_date="31-03-2026")

    def test_due_date_invalid_format(self) -> None:
        with pytest.raises(ValidationError):
            Task(id=1, title="test", due_date="2026/03/31")


class TestTaskStatusTransition:
    def test_open_to_in_progress(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.OPEN)
        assert task.can_transition_to(TaskStatus.IN_PROGRESS) is True

    def test_open_to_archived(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.OPEN)
        assert task.can_transition_to(TaskStatus.ARCHIVED) is True

    def test_open_to_completed_not_allowed(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.OPEN)
        assert task.can_transition_to(TaskStatus.COMPLETED) is False

    def test_in_progress_to_completed(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.IN_PROGRESS)
        assert task.can_transition_to(TaskStatus.COMPLETED) is True

    def test_in_progress_to_archived_not_allowed(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.IN_PROGRESS)
        assert task.can_transition_to(TaskStatus.ARCHIVED) is False

    def test_completed_to_archived(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.COMPLETED)
        assert task.can_transition_to(TaskStatus.ARCHIVED) is True

    def test_completed_to_in_progress_not_allowed(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.COMPLETED)
        assert task.can_transition_to(TaskStatus.IN_PROGRESS) is False

    def test_archived_no_transitions(self) -> None:
        task = Task(id=1, title="t", status=TaskStatus.ARCHIVED)
        for status in TaskStatus:
            assert task.can_transition_to(status) is False


class TestGlobalConfig:
    def test_defaults(self) -> None:
        config = GlobalConfig()
        assert config.active_project is None
        assert config.projects == []
        assert config.last_project_id == 0

    def test_with_projects(self) -> None:
        config = GlobalConfig(
            active_project="my-app",
            projects=[ProjectEntry(name="my-app", id=1)],
            last_project_id=1,
        )
        assert config.active_project == "my-app"
        assert len(config.projects) == 1
        assert config.projects[0].name == "my-app"
        assert config.projects[0].id == 1


from task_cli.cli.commands.migrate import (
    _convert_config,
    _convert_logs,
    _convert_routines,
    _convert_tasks,
)
from task_cli.models.task import GlobalConfig, Priority, TaskStatus


class TestConvertConfig:
    def test_basic(self) -> None:
        raw = {
            "activeProject": "my-proj",
            "projects": [{"name": "my-proj", "id": 1}],
            "lastProjectId": 1,
        }
        config = _convert_config(raw)
        assert config.active_project == "my-proj"
        assert config.last_project_id == 1
        assert len(config.projects) == 1
        assert config.projects[0].name == "my-proj"

    def test_null_active_project(self) -> None:
        raw = {"activeProject": None, "projects": [], "lastProjectId": 0}
        config = _convert_config(raw)
        assert config.active_project is None

    def test_empty(self) -> None:
        config = _convert_config({})
        assert isinstance(config, GlobalConfig)
        assert config.active_project is None
        assert config.last_project_id == 0


class TestConvertTasks:
    def test_field_rename(self) -> None:
        raw = [
            {
                "id": 1,
                "title": "Test",
                "description": "desc",
                "status": "open",
                "priority": "high",
                "branch": None,
                "dueDate": "2026-07-01",
                "scheduledDate": "2026-06-15",
                "createdAt": "2026-06-01T00:00:00+00:00",
                "updatedAt": "2026-06-02T00:00:00+00:00",
            }
        ]
        tasks = _convert_tasks(raw)
        assert len(tasks) == 1
        t = tasks[0]
        assert t.id == 1
        assert t.due_date == "2026-07-01"
        assert t.scheduled_date == "2026-06-15"
        assert t.status == TaskStatus.OPEN
        assert t.priority == Priority.HIGH

    def test_null_optional_fields(self) -> None:
        raw = [
            {
                "id": 2,
                "title": "No dates",
                "description": "",
                "status": "in_progress",
                "priority": "medium",
                "branch": None,
                "dueDate": None,
                "scheduledDate": None,
                "createdAt": "2026-06-01T00:00:00+00:00",
                "updatedAt": "2026-06-01T00:00:00+00:00",
            }
        ]
        tasks = _convert_tasks(raw)
        assert tasks[0].due_date is None
        assert tasks[0].scheduled_date is None
        assert tasks[0].completed_at is None

    def test_completed_at_is_picked_up_when_present(self) -> None:
        raw = [
            {
                "id": 3,
                "title": "Done",
                "description": "",
                "status": "completed",
                "priority": "medium",
                "branch": None,
                "dueDate": None,
                "scheduledDate": None,
                "createdAt": "2026-06-01T00:00:00+00:00",
                "updatedAt": "2026-06-03T00:00:00+00:00",
                "completedAt": "2026-06-02T00:00:00+00:00",
            }
        ]
        tasks = _convert_tasks(raw)
        assert tasks[0].completed_at is not None
        assert tasks[0].completed_at.isoformat() == "2026-06-02T00:00:00+00:00"

    def test_empty_list(self) -> None:
        assert _convert_tasks([]) == []


class TestConvertRoutines:
    def test_field_rename(self) -> None:
        raw = [
            {
                "id": 1,
                "title": "Morning run",
                "paused": False,
                "createdAt": "2026-06-01T00:00:00+00:00",
            }
        ]
        routines = _convert_routines(raw)
        assert len(routines) == 1
        r = routines[0]
        assert r.id == 1
        assert r.title == "Morning run"
        assert r.paused is False

    def test_empty(self) -> None:
        assert _convert_routines([]) == []


class TestConvertLogs:
    def test_entries_dict_to_list(self) -> None:
        raw = [
            {
                "date": "2026-06-06",
                "entries": {"1": "done", "2": "pending"},
            }
        ]
        logs = _convert_logs(raw)
        assert len(logs) == 1
        log = logs[0]
        assert log.date == "2026-06-06"
        assert len(log.entries) == 2
        by_id = {e.routine_id: e for e in log.entries}
        assert by_id[1].status == "done"
        assert by_id[2].status == "pending"

    def test_entries_keys_are_int(self) -> None:
        raw = [{"date": "2026-06-07", "entries": {"10": "done"}}]
        logs = _convert_logs(raw)
        assert logs[0].entries[0].routine_id == 10
        assert isinstance(logs[0].entries[0].routine_id, int)

    def test_empty_entries(self) -> None:
        raw = [{"date": "2026-06-08", "entries": {}}]
        logs = _convert_logs(raw)
        assert logs[0].entries == []

    def test_empty_list(self) -> None:
        assert _convert_logs([]) == []

    def test_multiple_days(self) -> None:
        raw = [
            {"date": "2026-06-06", "entries": {"1": "done"}},
            {"date": "2026-06-07", "entries": {"1": "pending"}},
        ]
        logs = _convert_logs(raw)
        assert len(logs) == 2
        assert logs[0].date == "2026-06-06"
        assert logs[1].date == "2026-06-07"

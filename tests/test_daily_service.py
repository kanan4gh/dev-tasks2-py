from pathlib import Path
from unittest.mock import patch

import pytest

from task_cli.exceptions import AppError
from task_cli.services.daily_service import DailyService
from task_cli.storage.daily_log_storage import DailyLogStorage
from task_cli.storage.routine_storage import RoutineStorage


def make_service(tmp_path: Path, today: str = "2026-06-07") -> tuple[DailyService, str]:
    routine_storage = RoutineStorage(tmp_path / "routines.yaml")
    log_storage = DailyLogStorage(tmp_path / "log.yaml")
    svc = DailyService(routine_storage, log_storage)
    return svc, today


class TestAddRoutine:
    def test_add_routine_creates_entry(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            r = svc.add_routine("朝のストレッチ")
        assert r.id == 1
        assert r.title == "朝のストレッチ"

    def test_add_routine_increments_id(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            r1 = svc.add_routine("A")
            r2 = svc.add_routine("B")
        assert r1.id == 1
        assert r2.id == 2

    def test_add_routine_adds_to_today_log(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("朝ランニング")
            items = svc.list_today()
        assert len(items) == 1
        assert items[0][0].title == "朝ランニング"
        assert items[0][1] == "pending"


class TestListToday:
    def test_done_before_pending(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.add_routine("B")
            svc.mark_done(1)
            items = svc.list_today()
        statuses = [status for _, status in items]
        assert statuses[0] == "done"
        assert statuses[1] == "pending"

    def test_paused_is_excluded_by_default(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.add_routine("B")
            svc.pause(2)
            items = svc.list_today()
        assert len(items) == 1
        assert items[0][0].id == 1

    def test_paused_included_when_flag_set(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.add_routine("B")
            svc.pause(2)
            items = svc.list_today(include_paused=True)
        assert len(items) == 2
        # paused は末尾
        assert items[-1][0].id == 2


class TestMarkDone:
    def test_mark_done(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.mark_done(1)
            items = svc.list_today()
        assert items[0][1] == "done"

    def test_mark_done_nonexistent_raises(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            with pytest.raises(AppError):
                svc.mark_done(99)


class TestPauseResume:
    def test_pause(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.pause(1)
        routines = svc._routines.load()
        assert routines[0].paused is True

    def test_resume(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.pause(1)
            svc.resume(1)
        routines = svc._routines.load()
        assert routines[0].paused is False

    def test_resume_all(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.add_routine("B")
            svc.pause(1)
            svc.pause(2)
            count = svc.resume_all()
        assert count == 2
        for r in svc._routines.load():
            assert r.paused is False


class TestDelete:
    def test_delete_removes_routine_and_log_entries(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.delete(1)
            items = svc.list_today()
        assert items == []
        assert svc._routines.load() == []

    def test_delete_nonexistent_raises(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            with pytest.raises(AppError):
                svc.delete(99)


class TestStats:
    def test_stats_returns_daily_rates(self, tmp_path: Path) -> None:
        svc, _ = make_service(tmp_path)
        days = ["2026-06-01", "2026-06-02", "2026-06-03"]
        for day in days:
            with patch("task_cli.services.daily_service._today_str", return_value=day):
                svc.add_routine(f"routine-{day}")
                svc.mark_done(svc._routines.load()[-1].id)
        result = svc.stats()
        assert len(result) <= 7
        for entry in result:
            assert "date" in entry
            assert "rate" in entry

    def test_stats_no_tasks_gives_none_rate(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        result = svc.stats()
        assert result == []


class TestResetToday:
    def test_reset_marks_all_pending(self, tmp_path: Path) -> None:
        svc, today = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value=today):
            svc.add_routine("A")
            svc.add_routine("B")
            svc.mark_done(1)
            svc.reset_today()
            items = svc.list_today()
        statuses = [s for _, s in items]
        assert all(s == "pending" for s in statuses)


class TestEnsureTodayLog:
    def test_new_log_created_when_date_changes(self, tmp_path: Path) -> None:
        svc, _ = make_service(tmp_path)
        with patch("task_cli.services.daily_service._today_str", return_value="2026-06-06"):
            svc.add_routine("A")
        # 翌日に切り替わった場合、新しいログが作られる
        with patch("task_cli.services.daily_service._today_str", return_value="2026-06-07"):
            svc._ensure_today_log()
            log_today = svc._logs.load_today("2026-06-07")
        assert any(e.routine_id == 1 for e in log_today.entries)

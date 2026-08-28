from datetime import datetime, timezone

from task_cli.exceptions import AppError
from task_cli.models.daily import DailyLogEntry, Routine
from task_cli.storage.daily_log_storage import DailyLogStorage
from task_cli.storage.routine_storage import RoutineStorage


def _today_str() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


class DailyService:
    def __init__(
        self,
        routine_storage: RoutineStorage | None = None,
        log_storage: DailyLogStorage | None = None,
    ) -> None:
        self._routines = routine_storage or RoutineStorage()
        self._logs = log_storage or DailyLogStorage()

    def add_routine(self, title: str) -> Routine:
        routines = self._routines.load()
        next_id = max((r.id for r in routines), default=0) + 1
        routine = Routine(id=next_id, title=title, created_at=datetime.now(timezone.utc))
        routines.append(routine)
        self._routines.save(routines)
        self._ensure_today_log()
        return routine

    def list_today(self, include_paused: bool = False) -> list[tuple[Routine, str]]:
        self._ensure_today_log()
        today = _today_str()
        routines = {r.id: r for r in self._routines.load()}
        log = self._logs.load_today(today)
        entry_map = {e.routine_id: e.status for e in log.entries}

        result: list[tuple[Routine, str]] = []
        for routine in routines.values():
            if routine.paused and not include_paused:
                continue
            status = entry_map.get(routine.id, "pending")
            result.append((routine, status))

        def sort_key(item: tuple[Routine, str]) -> tuple[int, int, int]:
            routine, status = item
            # paused は末尾（1）、それ以外は先頭（0）
            paused_rank = 1 if routine.paused else 0
            # done は高達成（0）、pending は低達成（1）
            done_rank = 0 if status == "done" else 1
            return (paused_rank, done_rank, routine.id)

        result.sort(key=sort_key)
        return result

    def mark_done(self, id: int) -> None:
        self._ensure_today_log()
        today = _today_str()
        log = self._logs.load_today(today)
        for entry in log.entries:
            if entry.routine_id == id:
                entry.status = "done"
                self._logs.save(log)
                return
        raise AppError(
            "ルーティーンが見つかりません。",
            cause=f"ID {id} のルーティーンは今日のログに存在しません。",
            remedy="daily list で有効な ID を確認してください。",
        )

    def pause(self, id: int) -> None:
        self._update_paused(id, True)

    def resume(self, id: int) -> None:
        self._update_paused(id, False)

    def resume_all(self) -> int:
        routines = self._routines.load()
        count = sum(1 for r in routines if r.paused)
        for r in routines:
            r.paused = False
        self._routines.save(routines)
        return count

    def delete(self, id: int) -> None:
        routines = self._routines.load()
        if not any(r.id == id for r in routines):
            raise AppError(
                "ルーティーンが見つかりません。",
                cause=f"ID {id} のルーティーンは存在しません。",
                remedy="daily list で有効な ID を確認してください。",
            )
        routines = [r for r in routines if r.id != id]
        self._routines.save(routines)
        logs = self._logs.load_all()
        for log in logs:
            log.entries = [e for e in log.entries if e.routine_id != id]
        self._logs.save_all(logs)

    def stats(self) -> list[dict[str, object]]:
        logs = self._logs.load_all()
        logs.sort(key=lambda entry: entry.date, reverse=True)
        result = []
        for log in logs[:7]:
            active = [e for e in log.entries if True]
            done = sum(1 for e in active if e.status == "done")
            total = len(active)
            rate = done / total if total > 0 else None
            result.append({"date": log.date, "done": done, "total": total, "rate": rate})
        return result

    def reset_today(self) -> None:
        today = _today_str()
        log = self._logs.load_today(today)
        for entry in log.entries:
            entry.status = "pending"
        self._logs.save(log)

    def _ensure_today_log(self) -> None:
        today = _today_str()
        log = self._logs.load_today(today)
        routines = self._routines.load()
        existing_ids = {e.routine_id for e in log.entries}
        added = False
        for r in routines:
            if r.id not in existing_ids and not r.paused:
                log.entries.append(DailyLogEntry(routine_id=r.id))
                added = True
        if added or not self._logs.load_today(today).entries:
            self._logs.save(log)

    def _update_paused(self, id: int, paused: bool) -> None:
        routines = self._routines.load()
        for r in routines:
            if r.id == id:
                r.paused = paused
                self._routines.save(routines)
                return
        raise AppError(
            "ルーティーンが見つかりません。",
            cause=f"ID {id} のルーティーンは存在しません。",
            remedy="daily list で有効な ID を確認してください。",
        )

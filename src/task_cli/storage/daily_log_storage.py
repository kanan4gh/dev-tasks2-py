import os
from pathlib import Path

import yaml

from task_cli.models.daily import DailyLog

_DEFAULT_PATH = Path("~/.task-py/daily/log.yaml")
_MAX_DAYS = 30


class DailyLogStorage:
    def __init__(self, file_path: Path | None = None) -> None:
        self._path = (file_path or _DEFAULT_PATH).expanduser()

    def load_all(self) -> list[DailyLog]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return []
        return [DailyLog.model_validate(item) for item in data]

    def load_today(self, today: str) -> DailyLog:
        for log in self.load_all():
            if log.date == today:
                return log
        return DailyLog(date=today)

    def save(self, log: DailyLog) -> None:
        logs = self.load_all()
        logs = [entry for entry in logs if entry.date != log.date]
        logs.insert(0, log)
        # 日付降順にして直近30日だけ保持
        logs.sort(key=lambda entry: entry.date, reverse=True)
        logs = logs[:_MAX_DAYS]
        self._write(logs)

    def save_all(self, logs: list[DailyLog]) -> None:
        self._write(logs)

    def _write(self, logs: list[DailyLog]) -> None:
        self._ensure_directory()
        data = [entry.model_dump(mode="json") for entry in logs]
        with self._path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def _ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

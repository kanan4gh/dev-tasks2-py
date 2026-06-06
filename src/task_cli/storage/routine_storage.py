import os
from pathlib import Path

import yaml

from task_cli.models.daily import Routine

_DEFAULT_PATH = Path("~/.task-py/daily/routines.yaml")


class RoutineStorage:
    def __init__(self, file_path: Path | None = None) -> None:
        self._path = (file_path or _DEFAULT_PATH).expanduser()

    def load(self) -> list[Routine]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return []
        return [Routine.model_validate(item) for item in data]

    def save(self, routines: list[Routine]) -> None:
        self.ensure_directory()
        data = [r.model_dump(mode="json") for r in routines]
        with self._path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

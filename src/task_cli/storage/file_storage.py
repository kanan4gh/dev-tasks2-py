import os
import shutil
from pathlib import Path

import yaml

from task_cli.models.task import Task


class FileStorage:
    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path).expanduser()

    def load(self) -> list[Task]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return []
        return [Task.model_validate(item) for item in data]

    def save(self, tasks: list[Task]) -> None:
        self.ensure_directory()
        bak_path = Path(str(self._path) + ".bak")

        if self._path.exists():
            shutil.copy2(self._path, bak_path)

        try:
            data = [task.model_dump(mode="json") for task in tasks]
            with self._path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            if bak_path.exists():
                bak_path.unlink()
        except Exception:
            if bak_path.exists():
                shutil.move(str(bak_path), str(self._path))
            raise

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

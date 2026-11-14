import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

from task_cli.models.daily import Routine
from task_cli.storage.atomic import locked, write_atomic
from task_cli.storage.yaml_io import read_yaml, validated_list

_DEFAULT_PATH = Path("~/.task-py/daily/routines.yaml")


class RoutineStorage:
    def __init__(self, file_path: Path | None = None) -> None:
        self._path = (file_path or _DEFAULT_PATH).expanduser()

    @property
    def path(self) -> Path:
        return self._path

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """`load()` → 変更 → `save()` をひとまとまりの排他区間にする。

        `DailyService.add_routine()` が `max(id) + 1` で採番するため、排他
        しないと同時実行で同じ ID を配る（`ProjectService.create_project()`
        と同じ形）。
        """
        self.ensure_directory()
        with locked(self._path):
            yield

    def load(self) -> list[Routine]:
        if not self._path.exists():
            return []
        data = read_yaml(self._path, list)
        if not data:
            return []
        return validated_list(self._path, Routine, data)

    def save(self, routines: list[Routine]) -> None:
        with self.transaction():
            data = [r.model_dump(mode="json") for r in routines]
            write_atomic(
                self._path,
                lambda f: yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False),
            )

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

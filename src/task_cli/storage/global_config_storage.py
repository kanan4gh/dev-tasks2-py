import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

from task_cli.models.task import GlobalConfig
from task_cli.storage.atomic import locked, write_atomic

_TASK_DIR = Path("~/.task-py").expanduser()
_CONFIG_PATH = _TASK_DIR / "config.yaml"


class GlobalConfigStorage:
    def __init__(self, config_path: str | Path = _CONFIG_PATH) -> None:
        self._path = Path(config_path).expanduser()

    @property
    def path(self) -> Path:
        return self._path

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """`load()` → 変更 → `save()` をひとまとまりの排他区間にする。

        `ProjectService` は全ての変更メソッドがこの形をしている。特に
        `create_project()` の `last_project_id += 1` は、排他しないと同時実行で
        同じ ID を採番する。
        """
        self.ensure_directory()
        with locked(self._path):
            yield

    def load(self) -> GlobalConfig:
        if not self._path.exists():
            return GlobalConfig()
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return GlobalConfig()
        return GlobalConfig.model_validate(data)

    def save(self, config: GlobalConfig) -> None:
        with self.transaction():
            data = config.model_dump(mode="json")
            write_atomic(
                self._path,
                lambda f: yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False),
            )

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

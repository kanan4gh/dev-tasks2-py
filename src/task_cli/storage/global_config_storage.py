import os
from pathlib import Path

import yaml

from task_cli.models.task import GlobalConfig

_TASK_DIR = Path("~/.task-py").expanduser()
_CONFIG_PATH = _TASK_DIR / "config.yaml"


class GlobalConfigStorage:
    def __init__(self, config_path: str | Path = _CONFIG_PATH) -> None:
        self._path = Path(config_path).expanduser()

    def load(self) -> GlobalConfig:
        if not self._path.exists():
            return GlobalConfig()
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return GlobalConfig()
        return GlobalConfig.model_validate(data)

    def save(self, config: GlobalConfig) -> None:
        self.ensure_directory()
        data = config.model_dump(mode="json")
        with self._path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

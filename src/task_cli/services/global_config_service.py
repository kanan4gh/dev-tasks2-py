from pathlib import Path

from task_cli.models.task import GlobalConfig
from task_cli.storage.global_config_storage import GlobalConfigStorage


class GlobalConfigService:
    def __init__(self, storage: GlobalConfigStorage) -> None:
        self._storage = storage

    @property
    def config_path(self) -> Path:
        """設定ファイルの位置。

        Web GUI が「データが変わったか」を判定するために監視対象を組み立てる。
        `storage/` へ直接依存させないため、service 経由で取れるようにしている。
        """
        return self._storage.path

    def get_active_project(self) -> str | None:
        return self._storage.load().active_project

    def set_active_project(self, name: str | None) -> None:
        config = self._storage.load()
        config.active_project = name
        self._storage.save(config)

    def get_all(self) -> GlobalConfig:
        return self._storage.load()

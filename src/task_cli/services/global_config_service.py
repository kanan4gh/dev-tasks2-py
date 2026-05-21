from task_cli.models.task import GlobalConfig
from task_cli.storage.global_config_storage import GlobalConfigStorage


class GlobalConfigService:
    def __init__(self, storage: GlobalConfigStorage) -> None:
        self._storage = storage

    def get_active_project(self) -> str | None:
        return self._storage.load().active_project

    def set_active_project(self, name: str | None) -> None:
        config = self._storage.load()
        config.active_project = name
        self._storage.save(config)

    def get_all(self) -> GlobalConfig:
        return self._storage.load()

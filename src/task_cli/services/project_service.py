from pathlib import Path

from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig, ProjectEntry
from task_cli.storage.global_config_storage import GlobalConfigStorage


class ProjectService:
    def __init__(self, storage: GlobalConfigStorage) -> None:
        self._storage = storage

    def create_project(self, name: str) -> ProjectEntry:
        config = self._storage.load()
        if any(p.name == name for p in config.projects):
            raise AppError(
                "同名のプロジェクトが既に存在します。",
                cause=f"プロジェクト '{name}' は既に登録されています。",
                remedy="別の名前を指定してください。",
            )
        config.last_project_id += 1
        entry = ProjectEntry(name=name, id=config.last_project_id)
        config.projects.append(entry)
        config.active_project = name
        self._storage.save(config)
        return entry

    def list_projects(self) -> list[ProjectEntry]:
        return self._storage.load().projects

    def get_project(self, name: str) -> ProjectEntry:
        for p in self._storage.load().projects:
            if p.name == name:
                return p
        raise AppError(
            "プロジェクトが見つかりません。",
            cause=f"プロジェクト '{name}' は存在しません。",
            remedy="task-py project list で有効な名前を確認してください。",
        )

    def use_project(self, name: str) -> None:
        self.get_project(name)
        config = self._storage.load()
        config.active_project = name
        self._storage.save(config)

    def remove_project(self, name: str) -> None:
        self.get_project(name)
        config = self._storage.load()
        config.projects = [p for p in config.projects if p.name != name]
        if config.active_project == name:
            config.active_project = None
        self._storage.save(config)

    def rename_project(self, old: str, new: str) -> None:
        self.get_project(old)
        config = self._storage.load()
        if any(p.name == new for p in config.projects):
            raise AppError(
                "同名のプロジェクトが既に存在します。",
                cause=f"プロジェクト '{new}' は既に登録されています。",
                remedy="別の名前を指定してください。",
            )
        for p in config.projects:
            if p.name == old:
                p.name = new
        if config.active_project == old:
            config.active_project = new
        self._storage.save(config)
        old_dir = Path(f"~/.task-py/projects/{old}").expanduser()
        new_dir = Path(f"~/.task-py/projects/{new}").expanduser()
        if old_dir.exists():
            old_dir.rename(new_dir)

    def get_config(self) -> GlobalConfig:
        return self._storage.load()

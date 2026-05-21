from pathlib import Path
from typing import Callable

from task_cli.models.task import Priority, Task
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.task_manager import TaskFilter, TaskManager
from task_cli.storage.file_storage import FileStorage


def resolve_storage_path(active_project: str | None) -> Path:
    if active_project:
        return Path(f"~/.task-py/projects/{active_project}/tasks.yaml").expanduser()
    return Path("~/.task-py/inbox/tasks.yaml").expanduser()


class TaskCrudUseCase:
    def __init__(
        self,
        global_config_service: GlobalConfigService,
        storage_factory: Callable[[Path], FileStorage] | None = None,
    ) -> None:
        self._global_config_service = global_config_service
        self._storage_factory: Callable[[Path], FileStorage] = storage_factory or FileStorage

    def _get_manager(self) -> TaskManager:
        active = self._global_config_service.get_active_project()
        path = resolve_storage_path(active)
        return TaskManager(self._storage_factory(path))

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
    ) -> Task:
        return self._get_manager().create_task(title, description, priority, due_date)

    def list_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
        return self._get_manager().list_tasks(filter)

    def get_task(self, id: int) -> Task:
        return self._get_manager().get_task(id)

    def start_task(self, id: int) -> Task:
        return self._get_manager().start_task(id)

    def complete_task(self, id: int) -> Task:
        return self._get_manager().complete_task(id)

    def archive_task(self, id: int) -> Task:
        return self._get_manager().archive_task(id)

    def delete_task(self, id: int) -> None:
        self._get_manager().delete_task(id)

    def search_tasks(self, keyword: str) -> list[Task]:
        return self._get_manager().search_tasks(keyword)

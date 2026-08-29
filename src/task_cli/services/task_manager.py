from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from task_cli.exceptions import AppError
from task_cli.models.task import Priority, Task, TaskStatus
from task_cli.storage.file_storage import FileStorage

_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


@dataclass
class TaskFilter:
    status: TaskStatus | list[TaskStatus] | None = None
    priority: Priority | None = None
    sort: Literal["id", "priority", "due_date", "created_at"] = "id"


class TaskManager:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
    ) -> Task:
        tasks = self._storage.load()
        task = Task(
            id=self._next_id(tasks),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
        )
        tasks.append(task)
        self._storage.save(tasks)
        return task

    def list_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
        tasks = self._storage.load()
        if filter is None:
            return self._sort(tasks, "id")

        if filter.status is not None:
            statuses = filter.status if isinstance(filter.status, list) else [filter.status]
            tasks = [t for t in tasks if t.status in statuses]

        if filter.priority is not None:
            tasks = [t for t in tasks if t.priority == filter.priority]

        return self._sort(tasks, filter.sort)

    def get_task(self, id: int) -> Task:
        for task in self._storage.load():
            if task.id == id:
                return task
        raise AppError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def update_task(self, id: int, **kwargs: object) -> Task:
        tasks = self._storage.load()
        for i, task in enumerate(tasks):
            if task.id == id:
                updated = task.model_copy(
                    update={**kwargs, "updated_at": datetime.now(timezone.utc)}
                )
                tasks[i] = updated
                self._storage.save(tasks)
                return updated
        raise AppError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def delete_task(self, id: int) -> None:
        tasks = self._storage.load()
        for i, task in enumerate(tasks):
            if task.id == id:
                tasks.pop(i)
                self._storage.save(tasks)
                return
        raise AppError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def edit_fields(
        self,
        id: int,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: str | None = None,
        clear_due_date: bool = False,
        scheduled_date: str | None = None,
        clear_scheduled_date: bool = False,
    ) -> Task:
        updates: dict[str, object] = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if priority is not None:
            updates["priority"] = priority
        if clear_due_date:
            updates["due_date"] = None
        elif due_date is not None:
            updates["due_date"] = due_date
        if clear_scheduled_date:
            updates["scheduled_date"] = None
        elif scheduled_date is not None:
            updates["scheduled_date"] = scheduled_date
        return self.update_task(id, **updates)

    def set_scheduled_date(self, id: int, date: str | None) -> Task:
        return self.update_task(id, scheduled_date=date)

    def start_task(self, id: int) -> Task:
        task = self.get_task(id)
        if not task.can_transition_to(TaskStatus.IN_PROGRESS):
            raise AppError(
                "このタスクは開始できません。",
                cause=f"{task.status.value} のタスクは in_progress に変更できません。",
                remedy="タスクのステータスを確認してください。",
            )
        if task.scheduled_date is not None:
            today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
            if task.scheduled_date > today:
                raise AppError(
                    "このタスクはまだ解禁されていません。",
                    cause=f"scheduled_date ({task.scheduled_date}) が未来のため着手できません。",
                    remedy=f"解禁日 ({task.scheduled_date}) 以降に start を実行してください。",
                )
        return self.update_task(id, status=TaskStatus.IN_PROGRESS)

    def complete_task(self, id: int) -> Task:
        task = self.get_task(id)
        if not task.can_transition_to(TaskStatus.COMPLETED):
            raise AppError(
                "このタスクは完了できません。",
                cause=f"{task.status.value} のタスクは completed に変更できません。",
                remedy="task start <id> でタスクを開始してから完了してください。",
            )
        return self.update_task(id, status=TaskStatus.COMPLETED)

    def archive_task(self, id: int) -> Task:
        task = self.get_task(id)
        if not task.can_transition_to(TaskStatus.ARCHIVED):
            raise AppError(
                "このタスクはアーカイブできません。",
                cause=f"{task.status.value} のタスクは archived に変更できません。",
                remedy="in_progress のタスクは先に完了させてください。",
            )
        return self.update_task(id, status=TaskStatus.ARCHIVED)

    def search_tasks(self, keyword: str) -> list[Task]:
        kw = keyword.lower()
        return [
            t for t in self._storage.load()
            if kw in t.title.lower() or kw in t.description.lower()
        ]

    def next_id(self) -> int:
        return self._next_id(self._storage.load())

    def _next_id(self, tasks: list[Task]) -> int:
        return max((t.id for t in tasks), default=0) + 1

    def _sort(self, tasks: list[Task], sort: str) -> list[Task]:
        if sort == "priority":
            return sorted(tasks, key=lambda t: _PRIORITY_ORDER[t.priority])
        if sort == "due_date":
            return sorted(tasks, key=lambda t: (t.due_date is None, t.due_date or ""))
        if sort == "created_at":
            return sorted(tasks, key=lambda t: t.created_at)
        return sorted(tasks, key=lambda t: t.id)

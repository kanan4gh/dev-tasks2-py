from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import ValidationError

from task_cli.exceptions import AppError, NotFoundError, StateConflictError
from task_cli.models.task import Priority, Task, TaskStatus
from task_cli.models.time import WorkSession
from task_cli.storage.file_storage import FileStorage

_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


@dataclass
class TaskFilter:
    status: TaskStatus | list[TaskStatus] | None = None
    priority: Priority | None = None
    sort: Literal["id", "priority", "due_date", "created_at"] = "id"


class InvalidTaskData(AppError):
    """タスクの値が不正で保存できない。

    呼び出し側（CLI / MCP / Web）が「見つからない」と区別できるよう、
    `AppError` のサブクラスにしてある。Web 層はこれを 400 に写す
    （`NotFoundError` は 404、`StateConflictError` は 409。どれにも当たらない
    素の `AppError` は 500 になる）。
    """


_FIELD_LABELS = {
    "title": "タイトル",
    "due_date": "期限",
    "scheduled_date": "解禁日",
    "priority": "優先度",
    "status": "ステータス",
    "description": "説明",
}

_FIELD_REMEDIES = {
    "title": "1〜200文字で指定してください。",
    "due_date": "YYYY-MM-DD の形式で指定してください（例: 2026-12-31）。",
    "scheduled_date": "YYYY-MM-DD の形式で指定してください（例: 2026-12-31）。",
}


def _validated(task: Task) -> Task:
    """保存する直前に `Task` として検証し直す。

    **`model_copy(update=...)` は pydantic v2 では再バリデーションしない。**
    そのため編集経路（`update_task`）ではフィールドバリデータが一切効かず、
    `due_date: bogus` のような値がそのまま YAML に書き込まれていた。書き込まれた
    あとは `load()` の `Task.model_validate` が落ちるため、**そのプロジェクトの
    タスクが全部読めなくなる**（`list` も `show` も `add` も落ちる）。手で YAML を
    直す以外に復旧手段がない。

    保存**前**に弾くのが肝である。保存後に気づいても遅い。
    """
    try:
        return Task.model_validate(task.model_dump())
    except ValidationError as e:
        raise _invalid_task_data(e) from e


def _invalid_task_data(error: ValidationError) -> InvalidTaskData:
    """pydantic の英文ではなく、どの項目が何を期待しているかを日本語で出す。"""
    first = error.errors()[0]
    field = str(first["loc"][0]) if first["loc"] else ""
    label = _FIELD_LABELS.get(field, field or "入力値")
    given = first.get("input")
    return InvalidTaskData(
        f"{label}の値が正しくありません。",
        cause=f"{label}に {given!r} が指定されました。",
        remedy=_FIELD_REMEDIES.get(field, "入力した値を確認してください。"),
    )


class TaskManager:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
        scheduled_date: str | None = None,
    ) -> Task:
        with self._storage.transaction():
            tasks = self._storage.load()
            try:
                task = Task(
                    id=self._next_id(tasks),
                    title=title,
                    description=description,
                    priority=priority,
                    due_date=due_date,
                    scheduled_date=scheduled_date,
                )
            except ValidationError as e:
                # 生の ValidationError を入口まで通すと、CLI も MCP も
                # トレースバックを出してしまう。
                raise _invalid_task_data(e) from e
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
        raise NotFoundError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def update_task(self, id: int, **kwargs: object) -> Task:
        with self._storage.transaction():
            tasks = self._storage.load()
            for i, task in enumerate(tasks):
                if task.id == id:
                    updated = _validated(
                        task.model_copy(
                            update={**kwargs, "updated_at": datetime.now(timezone.utc)}
                        )
                    )
                    tasks[i] = updated
                    self._storage.save(tasks)
                    return updated
        raise NotFoundError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def append_work_session(self, id: int, session: WorkSession) -> Task:
        """作業セッションを追記する。

        `update_task` を使わないのは意図的である。作業時間の記録はタスク内容の
        編集ではないため、`updated_at` を動かしてはいけない（動かすと
        `completed_at` を追加した理由と同じ問題を新しく作ることになる）。
        """
        with self._storage.transaction():
            tasks = self._storage.load()
            for i, task in enumerate(tasks):
                if task.id == id:
                    updated = task.model_copy(
                        update={"work_sessions": [*task.work_sessions, session]}
                    )
                    tasks[i] = updated
                    self._storage.save(tasks)
                    return updated
        raise NotFoundError(
            "タスクが見つかりません。",
            cause=f"ID={id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )

    def delete_task(self, id: int) -> None:
        with self._storage.transaction():
            tasks = self._storage.load()
            for i, task in enumerate(tasks):
                if task.id == id:
                    tasks.pop(i)
                    self._storage.save(tasks)
                    return
        raise NotFoundError(
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
            raise StateConflictError(
                "このタスクは開始できません。",
                cause=f"{task.status.value} のタスクは in_progress に変更できません。",
                remedy="タスクのステータスを確認してください。",
            )
        if task.scheduled_date is not None:
            today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
            if task.scheduled_date > today:
                raise StateConflictError(
                    "このタスクはまだ解禁されていません。",
                    cause=f"scheduled_date ({task.scheduled_date}) が未来のため着手できません。",
                    remedy=f"解禁日 ({task.scheduled_date}) 以降に start を実行してください。",
                )
        return self._apply_status_change(task, TaskStatus.IN_PROGRESS)

    def complete_task(self, id: int) -> Task:
        task = self.get_task(id)
        if not task.can_transition_to(TaskStatus.COMPLETED):
            raise StateConflictError(
                "このタスクは完了できません。",
                cause=f"{task.status.value} のタスクは completed に変更できません。",
                remedy="task start <id> でタスクを開始してから完了してください。",
            )
        return self._apply_status_change(task, TaskStatus.COMPLETED)

    def archive_task(self, id: int) -> Task:
        task = self.get_task(id)
        if not task.can_transition_to(TaskStatus.ARCHIVED):
            raise StateConflictError(
                "このタスクはアーカイブできません。",
                cause=f"{task.status.value} のタスクは archived に変更できません。",
                remedy="in_progress のタスクは先に完了させてください。",
            )
        return self._apply_status_change(task, TaskStatus.ARCHIVED)

    def _apply_status_change(self, task: Task, new_status: TaskStatus) -> Task:
        """ステータス変更の唯一の絞り口。completed_at の出入りをここだけで決める。

        completed へ入るときに記録し、completed から出るときにクリアする。
        archived は「片付け」であって「完了の取り消し」ではないため、
        completed → archived では completed_at を保持する。
        """
        updates: dict[str, object] = {"status": new_status}
        was_completed = task.status is TaskStatus.COMPLETED
        now_completed = new_status is TaskStatus.COMPLETED

        if now_completed and not was_completed:
            updates["completed_at"] = datetime.now(timezone.utc)
        elif was_completed and new_status is not TaskStatus.ARCHIVED:
            updates["completed_at"] = None

        return self.update_task(task.id, **updates)

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

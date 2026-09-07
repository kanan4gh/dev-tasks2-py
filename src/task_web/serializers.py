"""pydantic モデルを JSON にする。

モデルにはエイリアス設定が無いため、フィールド名は Python の snake_case のまま
出る。日時は pydantic v2 の既定どおり ISO 8601 文字列になる。

ここが独立したモジュールになっているのは、**永続化されない派生値を足す**必要が
あるためである。`Task.total_worked_seconds` は `@property` なので
`model_dump()` には現れない。
"""

from typing import Any

from task_cli.models.daily import Routine
from task_cli.models.task import ProjectEntry, Task
from task_cli.models.time import TimerState


def task_summary(task: Task) -> dict[str, Any]:
    """一覧用。作業セッションの中身は落とす。

    セッションは1タスクにいくつでも溜まるため、一覧に含めると
    タスク数 × セッション数でペイロードが増える。合計と件数があれば一覧の
    用途には足りる。
    """
    data = task.model_dump(mode="json", exclude={"work_sessions", "description"})
    data["total_worked_seconds"] = task.total_worked_seconds
    data["work_session_count"] = len(task.work_sessions)
    data["has_description"] = bool(task.description)
    return data


def task_detail(task: Task) -> dict[str, Any]:
    """詳細用。作業セッションも含めて全部返す。"""
    data = task.model_dump(mode="json")
    data["total_worked_seconds"] = task.total_worked_seconds
    return data


def project_entry(entry: ProjectEntry) -> dict[str, Any]:
    return entry.model_dump(mode="json")


def timer_state(state: TimerState | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return state.model_dump(mode="json")


def routine(item: Routine, status: str) -> dict[str, Any]:
    data = item.model_dump(mode="json")
    data["status"] = status
    return data


def grouped_tasks(groups: dict[str | None, list[Task]]) -> dict[str, Any]:
    """`list_all_projects()` の戻り値を JSON にする。

    キーの `None`（Inbox）は JSON のオブジェクトキーにできないため、`inbox` と
    `projects` に分ける。`inbox` という**名前のプロジェクト**があっても
    `projects` 側に入るので衝突しない。
    """
    return {
        "inbox": [task_summary(t) for t in groups.get(None, [])],
        "projects": {
            name: [task_summary(t) for t in tasks]
            for name, tasks in groups.items()
            if name is not None
        },
    }

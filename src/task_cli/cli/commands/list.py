from enum import Enum

import typer

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_error, render_task_table
from task_cli.exceptions import AppError
from task_cli.models.task import Priority, TaskStatus
from task_cli.services.task_manager import TaskFilter


class SortKey(str, Enum):
    """`--sort` の選択肢。`TaskFilter.sort` が受ける値と同じ。"""

    ID = "id"
    PRIORITY = "priority"
    DUE_DATE = "due_date"
    CREATED_AT = "created_at"


def list_tasks(
    all_projects: bool = typer.Option(False, "--all", help="全プロジェクト + Inbox のタスクを表示"),
    inbox: bool = typer.Option(False, "--inbox", help="Inbox のタスクのみ表示"),
    all_status: bool = typer.Option(False, "--all-status", help="全ステータスのタスクを表示"),
    status: list[TaskStatus] = typer.Option(
        [], "--status", help="このステータスだけを表示（複数指定可。--all-status とは併用できない）"
    ),
    priority: Priority | None = typer.Option(None, "--priority", help="この優先度だけを表示"),
    sort: SortKey = typer.Option(SortKey.ID, "--sort", help="並べ替えの基準"),
) -> None:
    """タスク一覧を表示します。デフォルトは open と in_progress のみ。"""
    if status and all_status:
        raise typer.BadParameter("--status と --all-status は同時に指定できません。")
    try:
        svc = get_global_config_service()
        active = svc.get_active_project()
        config = svc.get_all()
        uc = get_use_case()

        # 既定は open + in_progress。--status はそのステータスだけ、--all-status は全ステータス
        statuses: list[TaskStatus] | None
        if status:
            statuses = status
        elif all_status:
            statuses = None
        else:
            statuses = [TaskStatus.OPEN, TaskStatus.IN_PROGRESS]
        filter = TaskFilter(status=statuses, priority=priority, sort=sort.value)

        if all_projects:
            tasks_by_project = uc.list_all_projects(filter)
            for project_name, tasks in tasks_by_project.items():
                render_task_table(tasks, project_name, config, is_active=(project_name == active))
        elif inbox:
            tasks = uc.list_inbox_tasks(filter)
            render_task_table(tasks, None, config)
        else:
            tasks = uc.list_tasks(filter)
            render_task_table(tasks, active, config)

    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

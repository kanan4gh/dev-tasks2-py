import typer

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_error, render_task_table
from task_cli.exceptions import AppError
from task_cli.models.task import TaskStatus
from task_cli.services.task_manager import TaskFilter


def list_tasks(
    all_projects: bool = typer.Option(False, "--all", help="全プロジェクト + Inbox のタスクを表示"),
    inbox: bool = typer.Option(False, "--inbox", help="Inbox のタスクのみ表示"),
    all_status: bool = typer.Option(False, "--all-status", help="全ステータスのタスクを表示"),
) -> None:
    """タスク一覧を表示します。デフォルトは open と in_progress のみ。"""
    try:
        svc = get_global_config_service()
        active = svc.get_active_project()
        config = svc.get_all()
        uc = get_use_case()

        filter = None if all_status else TaskFilter(status=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS])

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

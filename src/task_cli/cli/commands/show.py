import typer

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_error, render_task_detail
from task_cli.exceptions import AppError


def show(
    id: int = typer.Argument(..., help="タスクのID"),
) -> None:
    """タスクの詳細を表示します。"""
    try:
        svc = get_global_config_service()
        active = svc.get_active_project()
        config = svc.get_all()

        uc = get_use_case()
        task = uc.get_task(id)

        render_task_detail(task, active, config)
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

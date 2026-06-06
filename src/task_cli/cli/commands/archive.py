import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def archive(
    id: int = typer.Argument(..., help="タスクID"),
) -> None:
    """タスクをアーカイブします (archived に変更)。"""
    try:
        uc = get_use_case()
        task = uc.archive_task(id)
        render_success(f"タスク #{task.id} をアーカイブしました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

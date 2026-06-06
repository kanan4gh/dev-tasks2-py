import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def start(
    id: int = typer.Argument(..., help="タスクID"),
) -> None:
    """タスクを開始します (in_progress に変更)。"""
    try:
        uc = get_use_case()
        task = uc.start_task(id)
        render_success(f"タスク #{task.id} を開始しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

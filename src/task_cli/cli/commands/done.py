import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def done(
    id: int = typer.Argument(..., help="タスクID"),
) -> None:
    """タスクを完了します (completed に変更)。"""
    try:
        uc = get_use_case()
        task = uc.complete_task(id)
        render_success(f"タスク #{task.id} を完了しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

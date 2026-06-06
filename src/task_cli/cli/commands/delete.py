import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def delete(
    id: int = typer.Argument(..., help="タスクID"),
) -> None:
    """タスクを削除します。"""
    try:
        uc = get_use_case()
        task = uc.get_task(id)
        confirmed = typer.confirm(f"タスク #{task.id}「{task.title}」を削除しますか？")
        if not confirmed:
            typer.echo("削除をキャンセルしました")
            return
        uc.delete_task(id)
        render_success(f"タスク #{id} を削除しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

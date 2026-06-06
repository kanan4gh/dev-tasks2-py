import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def move(
    id: int = typer.Argument(..., help="タスクID"),
    project: str = typer.Argument(..., help="移動先プロジェクト名（'inbox' で Inbox に移動）"),
) -> None:
    """タスクを別のプロジェクト（または Inbox）に移動します。"""
    try:
        uc = get_use_case()
        target = None if project.lower() == "inbox" else project
        task = uc.move_task(id, target)
        dest = "Inbox" if target is None else f"'{target}'"
        render_success(f"タスク #{task.id} を {dest} に移動しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

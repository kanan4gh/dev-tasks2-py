import typer

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError
from task_cli.models.task import Priority


def add(
    title: str = typer.Argument(..., help="タスクのタイトル"),
    description: str = typer.Option("", "--description", "-d", help="詳細説明"),
    priority: Priority = typer.Option(Priority.MEDIUM, "--priority", "-p", help="優先度"),
    due_date: str = typer.Option("", "--due", help="期限 (YYYY-MM-DD)"),
) -> None:
    """タスクを作成します。"""
    try:
        uc = get_use_case()
        task = uc.add_task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date or None,
        )
        svc = get_global_config_service()
        active = svc.get_active_project()
        render_success(f"タスクを作成しました (ID: {task.id})")
        if active:
            typer.echo(f"プロジェクト: {active}")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

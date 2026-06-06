from typing import Optional

import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError
from task_cli.models.task import Priority


def edit(
    id: int = typer.Argument(..., help="タスクID"),
    title: Optional[str] = typer.Option(None, "-t", "--title", help="タイトルを変更"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="説明を変更"),
    priority: Optional[Priority] = typer.Option(None, "-p", "--priority", help="優先度を変更 (high/medium/low)"),
    due: Optional[str] = typer.Option(None, "--due", help="期限を設定 (YYYY-MM-DD)"),
    due_clear: bool = typer.Option(False, "--due-clear", help="期限を削除"),
    scheduled: Optional[str] = typer.Option(None, "--scheduled", help="解禁日を設定 (YYYY-MM-DD)"),
    scheduled_clear: bool = typer.Option(False, "--scheduled-clear", help="解禁日を削除"),
) -> None:
    """タスクを編集します。"""
    if not any([title, description, priority, due, due_clear, scheduled, scheduled_clear]):
        render_error(AppError(
            "変更するフィールドを指定してください。",
            cause="オプションが何も指定されていません。",
            remedy="-t/--title, -d/--description, -p/--priority, --due, --due-clear, --scheduled, --scheduled-clear のいずれかを指定してください。",
        ))
        raise typer.Exit(code=1)

    try:
        uc = get_use_case()
        task = uc.edit_task(
            id,
            title=title,
            description=description,
            priority=priority,
            due_date=due,
            clear_due_date=due_clear,
            scheduled_date=scheduled,
            clear_scheduled_date=scheduled_clear,
        )
        render_success(f"タスク ID {task.id} を更新しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

from typing import Optional

import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError


def schedule(
    id: int = typer.Argument(..., help="タスクID"),
    date: Optional[str] = typer.Argument(None, help="解禁日 (YYYY-MM-DD)"),
    clear: bool = typer.Option(False, "--clear", help="解禁日を削除"),
) -> None:
    """タスクの解禁日を設定・削除します。解禁日以降に start できます。"""
    if not date and not clear:
        render_error(AppError(
            "解禁日を指定してください。",
            cause="日付も --clear も指定されていません。",
            remedy="task-py schedule <id> <YYYY-MM-DD>  または  task-py schedule <id> --clear",
        ))
        raise typer.Exit(code=1)

    try:
        uc = get_use_case()
        if clear:
            task = uc.set_scheduled_date(id, None)
            render_success(f"タスク ID {task.id} の解禁日を削除しました")
        else:
            task = uc.set_scheduled_date(id, date)
            render_success(f"タスク ID {task.id} の解禁日を {date} に設定しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

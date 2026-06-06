import typer

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_error, render_task_table
from task_cli.exceptions import AppError


def search(
    keyword: str = typer.Argument(..., help="検索キーワード"),
) -> None:
    """タスクをキーワードで検索します（アクティブプロジェクトまたはInbox）。"""
    try:
        svc = get_global_config_service()
        active = svc.get_active_project()
        config = svc.get_all()
        uc = get_use_case()
        tasks = uc.search_tasks(keyword)
        render_task_table(tasks, active, config)
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

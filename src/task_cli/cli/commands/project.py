from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from task_cli.cli.deps import get_global_config_service
from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError
from task_cli.services.project_service import ProjectService
from task_cli.storage.file_storage import FileStorage
from task_cli.storage.global_config_storage import GlobalConfigStorage

project_app = typer.Typer(help="プロジェクトを管理します。")
console = Console()


def _get_project_service() -> ProjectService:
    return ProjectService(GlobalConfigStorage())


def _count_tasks(project_name: str) -> tuple[int, int]:
    path = Path(f"~/.task-py/projects/{project_name}/tasks.yaml").expanduser()
    if not path.exists():
        return 0, 0
    tasks = FileStorage(path).load()
    in_progress = sum(1 for t in tasks if t.status.value == "in_progress")
    return len(tasks), in_progress


@project_app.command("create")
def create(
    name: str = typer.Argument(..., help="プロジェクト名"),
) -> None:
    """プロジェクトを作成します。"""
    try:
        svc = _get_project_service()
        svc.create_project(name)
        render_success(f"プロジェクト '{name}' を作成しました（アクティブに設定済み）")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@project_app.command("list")
def list_projects() -> None:
    """プロジェクト一覧を表示します。"""
    svc = _get_project_service()
    config_svc = get_global_config_service()
    projects = svc.list_projects()
    active = config_svc.get_active_project()

    # 桁揃えは Table の列幅に任せる（名前の長さに制限がないため固定幅にしない）
    table = Table(box=None, padding=(0, 1), show_header=False)
    table.add_column(no_wrap=True)  # アクティブマーカー
    table.add_column(overflow="fold")  # 名前（省略せず、狭い端末では折り返す。project use に必要なため）
    table.add_column(no_wrap=True)  # タスク数

    for p in projects:
        total, in_prog = _count_tasks(p.name)
        is_active = p.name == active
        task_label = "task" if total == 1 else "tasks"
        table.add_row(
            Text("*", style="green bold") if is_active else Text(" "),
            Text(p.name, style="green bold" if is_active else ""),
            f"{total} {task_label} ({in_prog} in_progress)",
        )

    inbox_path = Path("~/.task-py/inbox/tasks.yaml").expanduser()
    inbox_total = len(FileStorage(inbox_path).load()) if inbox_path.exists() else 0
    inbox_label = "task" if inbox_total == 1 else "tasks"
    table.add_row(Text(" "), Text("[Inbox]", style="dim"), f"{inbox_total} {inbox_label}")
    console.print(table)


@project_app.command("use")
def use(
    name: str = typer.Argument(..., help="プロジェクト名"),
) -> None:
    """アクティブプロジェクトを切り替えます。"""
    try:
        svc = _get_project_service()
        svc.use_project(name)
        render_success(f"アクティブプロジェクトを '{name}' に切り替えました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@project_app.command("rename")
def rename(
    old: str = typer.Argument(..., help="変更前のプロジェクト名"),
    new: str = typer.Argument(..., help="変更後のプロジェクト名"),
) -> None:
    """プロジェクトをリネームします。"""
    try:
        svc = _get_project_service()
        svc.rename_project(old, new)
        render_success(f"プロジェクト '{old}' を '{new}' にリネームしました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@project_app.command("remove")
def remove(
    name: str = typer.Argument(..., help="プロジェクト名"),
) -> None:
    """プロジェクトを削除します。"""
    try:
        svc = _get_project_service()
        svc.get_project(name)
        confirmed = typer.confirm(f"プロジェクト '{name}' を削除しますか？")
        if not confirmed:
            typer.echo("削除をキャンセルしました")
            return
        svc.remove_project(name)
        render_success(f"プロジェクト '{name}' を削除しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

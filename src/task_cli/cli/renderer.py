from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import ParamSpec, TypeVar

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from task_cli.duration import format_duration
from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig, Priority, Task, TaskStatus

console = Console()

_STATUS_STYLES: dict[TaskStatus, str] = {
    TaskStatus.OPEN: "white",
    TaskStatus.IN_PROGRESS: "yellow",
    TaskStatus.COMPLETED: "green",
    TaskStatus.ARCHIVED: "dim",
}

_PRIORITY_STYLES: dict[Priority, str] = {
    Priority.HIGH: "red",
    Priority.MEDIUM: "yellow",
    Priority.LOW: "blue",
}


def _compound_id(task_id: int, active_project: str | None, config: GlobalConfig) -> str:
    if active_project is None:
        return f"0-{task_id}"
    for entry in config.projects:
        if entry.name == active_project:
            return f"{entry.id}-{task_id}"
    return str(task_id)


def _header(active_project: str | None) -> str:
    return f"[Project: {active_project}]" if active_project else "[Inbox]"


def render_task_table(
    tasks: list[Task],
    active_project: str | None,
    config: GlobalConfig,
    is_active: bool = False,
) -> None:
    header_style = "bold green" if is_active else "bold"
    console.print(f"[{header_style}]{_header(active_project)}[/{header_style}]")

    if not tasks:
        console.print("[dim]タスクがありません。[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("ID", justify="right", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Title")

    for task in tasks:
        cid = _compound_id(task.id, active_project, config)
        style = _STATUS_STYLES[task.status]
        title = task.title if len(task.title) <= 40 else task.title[:39] + "…"
        table.add_row(
            cid,
            Text(task.status.value, style=style),
            title,
        )

    console.print(table)


def _today() -> str:
    """`start` の判定（services/task_manager.py）と同じ「今日」の定義。ずらさないこと。"""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def render_task_detail(
    task: Task,
    active_project: str | None,
    config: GlobalConfig,
) -> None:
    cid = _compound_id(task.id, active_project, config)
    status_style = _STATUS_STYLES[task.status]
    priority_style = _PRIORITY_STYLES[task.priority]

    lines = [
        f"[bold]ID[/bold]       {cid}",
        f"[bold]Title[/bold]    {task.title}",
        f"[bold]Status[/bold]   [{status_style}]{task.status.value}[/{status_style}]",
        f"[bold]Priority[/bold] [{priority_style}]{task.priority.value}[/{priority_style}]",
    ]
    if task.description:
        lines.append(f"[bold]Desc[/bold]     {task.description}")
    if task.branch:
        lines.append(f"[bold]Branch[/bold]   {task.branch}")
    if task.due_date:
        lines.append(f"[bold]Due[/bold]      {task.due_date}")
    if task.scheduled_date:
        # 解禁日は `start` の可否を決める。未来なら、そのことも見せる
        note = "  [yellow]（まだ着手できません）[/yellow]" if task.scheduled_date > _today() else ""
        lines.append(f"[bold]Sched[/bold]    {task.scheduled_date}{note}")
    lines.append(f"[bold]Created[/bold]  {task.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"[bold]Updated[/bold]  {task.updated_at.strftime('%Y-%m-%d %H:%M')}")
    if task.completed_at is not None:
        lines.append(f"[bold]Done[/bold]     {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
    elif task.status is TaskStatus.COMPLETED:
        # 完了日時を持たない移行前のタスク。updated_at で代用すると嘘が定着するので出さない。
        lines.append("[bold]Done[/bold]     —（記録なし）")
    if task.work_sessions:
        total = format_duration(task.total_worked_seconds)
        lines.append(f"[bold]Worked[/bold]   {total}（{len(task.work_sessions)} セッション）")

    console.print(Panel("\n".join(lines), title=f"Task {cid}", expand=False))


def render_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def render_info(message: str) -> None:
    """エラーではないが成功でもない通知（「変更はありませんでした」等）。"""
    console.print(f"[dim]{message}[/dim]")


def render_error(error: AppError) -> None:
    # 原因にはファイルのパスや YAML パーサの文言が入り、`[` `]` を含みうる。
    # rich のマークアップとして解釈されると、文が欠けたり表示自体が落ちたりする。
    console.print(f"[red][Error] {escape(str(error))}[/red]")
    console.print(f"  原因: {escape(error.cause)}")
    console.print(f"  対処: {escape(error.remedy)}")


_P = ParamSpec("_P")
_R = TypeVar("_R")


def handle_app_errors(func: Callable[_P, _R]) -> Callable[_P, _R | None]:
    """コマンド本体で出た `AppError` を `render_error` で表示し、終了コード 1 で終える。

    保存ファイルを読むコマンドは、どれも壊れたファイルで `StorageReadError` を
    投げうる。コマンドごとに try/except を書くと書き忘れた分がトレースバックに
    なるので、これで包む。
    """

    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R | None:
        try:
            return func(*args, **kwargs)
        except AppError as e:
            render_error(e)
            raise typer.Exit(code=1)

    return wrapper

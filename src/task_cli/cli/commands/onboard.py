from rich.console import Console
from rich.rule import Rule

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.cli.renderer import render_task_table
from task_cli.models.task import TaskStatus
from task_cli.services.daily_service import DailyService
from task_cli.services.task_manager import TaskFilter

console = Console()


def onboard() -> None:
    """現在の状況を要約表示します。"""
    svc = get_global_config_service()
    active = svc.get_active_project()
    config = svc.get_all()
    uc = get_use_case()

    label = f"Project: {active}" if active else "Inbox"
    console.print(Rule(f"[bold]{label}[/bold]"))

    # daily pending
    daily_svc = DailyService()
    pending = [(r, s) for r, s in daily_svc.list_today() if s == "pending"]
    if pending:
        console.print("\n[bold]📋 今日のルーティーン[/bold]")
        for routine, _ in pending:
            console.print(f"  {routine.id}  {routine.title}")

    # 着手すべきタスク最大3件
    in_progress = uc.list_tasks(TaskFilter(status=[TaskStatus.IN_PROGRESS]))
    open_tasks = uc.list_tasks(TaskFilter(status=[TaskStatus.OPEN]))
    priority_tasks = (in_progress + open_tasks)[:3]
    if priority_tasks:
        console.print("\n[bold]🚀 今とりかかるべきタスク[/bold]")
        render_task_table(priority_tasks, active, config)

    # 全タスク一覧
    all_tasks = uc.list_tasks()
    console.print("\n[bold]📝 すべてのタスク[/bold]")
    render_task_table(all_tasks, active, config)

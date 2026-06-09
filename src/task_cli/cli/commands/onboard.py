from rich.console import Console
from rich.markup import escape
from rich.rule import Rule

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.models.task import TaskStatus
from task_cli.services.daily_service import DailyService
from task_cli.services.task_manager import TaskFilter

console = Console()


def overview() -> None:
    """現在の状況を要約表示します。"""
    svc = get_global_config_service()
    active = svc.get_active_project()
    uc = get_use_case()

    label = f"Project: {active}" if active else "Inbox"
    console.print(Rule(f"[bold]{label}[/bold]"))

    # ルーティーン（全件取得して pending のみ表示）
    daily_svc = DailyService()
    all_routines = daily_svc.list_today(include_paused=True)
    done_count = sum(1 for _, s in all_routines if s == "done")
    total_count = len(all_routines)
    pending_routines = [(r, s) for r, s in all_routines if s == "pending"]
    if total_count > 0:
        console.print(f"\n[bold]📅 今日の毎日やること ({done_count}/{total_count} 完了)[/bold]")
        for routine, _ in pending_routines:
            rid = escape(f"[r{routine.id}]")
            console.print(f"  ○ {rid} {escape(routine.title)}")
        console.print("  [dim]💡 done r<ID> で完了[/dim]")

    # 着手すべきタスク最大3件（アクティブプロジェクトから）
    in_progress = uc.list_tasks(TaskFilter(status=[TaskStatus.IN_PROGRESS]))
    open_tasks = uc.list_tasks(TaskFilter(status=[TaskStatus.OPEN]))
    priority_tasks = (in_progress + open_tasks)[:3]
    if priority_tasks:
        console.print("\n[bold]📌 今とりかかるべきタスク[/bold]")
        proj_label = f"Project: {active}" if active else "Inbox"
        for i, task in enumerate(priority_tasks, 1):
            status_tag = escape(f"[{task.status.value}]")
            task_id = f"{task.id}" if active else f"0-{task.id}"
            console.print(f"  {i}. {status_tag} {task_id}  {escape(task.title)}  ({proj_label})")
        console.print("  [dim]💡 start <ID> でタスクを開始、done <ID> で完了[/dim]")

    # 全プロジェクト横断・open + in_progress のみ
    active_filter = TaskFilter(status=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS])
    all_projects = uc.list_all_projects(active_filter)
    ordered = [(k, v) for k, v in all_projects.items() if k is not None and v]
    inbox_tasks = all_projects.get(None, [])

    if any(v for v in all_projects.values()):
        console.print("\n[bold]💼 全タスク (open + in_progress)[/bold]")
        for proj_name, tasks in ordered:
            in_prog_count = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
            console.print(f"  {escape(f'[Project: {proj_name}]')}  {len(tasks)} 件 (in_progress: {in_prog_count})")
            for task in tasks:
                console.print(f"    • {task.id}  {escape(f'[{task.status.value}]')}  {escape(task.title)}")
        if inbox_tasks:
            in_prog_count = sum(1 for t in inbox_tasks if t.status == TaskStatus.IN_PROGRESS)
            console.print(f"  {escape('[Inbox]')}  {len(inbox_tasks)} 件 (in_progress: {in_prog_count})")
            for task in inbox_tasks:
                console.print(f"    • 0-{task.id}  {escape(f'[{task.status.value}]')}  {escape(task.title)}")

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from task_cli.exceptions import AppError
from task_cli.models.daily import DailyLog, DailyLogEntry, Routine
from task_cli.models.task import GlobalConfig, Priority, ProjectEntry, Task, TaskStatus

_TS_DIR = Path("~/.task").expanduser()
_PY_DIR = Path("~/.task-py").expanduser()

console = Console()


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _convert_config(raw: dict[str, Any]) -> GlobalConfig:
    projects = [ProjectEntry(**p) for p in raw.get("projects", [])]
    return GlobalConfig(
        active_project=raw.get("activeProject"),
        projects=projects,
        last_project_id=raw.get("lastProjectId", 0),
    )


def _convert_tasks(raw: list[dict[str, Any]]) -> list[Task]:
    tasks = []
    for t in raw:
        tasks.append(Task(
            id=t["id"],
            title=t["title"],
            description=t.get("description", ""),
            status=TaskStatus(t["status"]),
            priority=Priority(t["priority"]),
            branch=t.get("branch"),
            due_date=t.get("dueDate"),
            scheduled_date=t.get("scheduledDate"),
            created_at=t["createdAt"],
            updated_at=t["updatedAt"],
        ))
    return tasks


def _convert_routines(raw: list[dict[str, Any]]) -> list[Routine]:
    return [
        Routine(
            id=r["id"],
            title=r["title"],
            paused=r.get("paused", False),
            created_at=r["createdAt"],
        )
        for r in raw
    ]


def _convert_logs(raw: list[dict[str, Any]]) -> list[DailyLog]:
    logs = []
    for log in raw:
        entries = [
            DailyLogEntry(routine_id=int(k), status=v)
            for k, v in log.get("entries", {}).items()
        ]
        logs.append(DailyLog(date=log["date"], entries=entries))
    return logs


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def _tasks_to_yaml_data(tasks: list[Task]) -> list[dict[str, Any]]:
    return [t.model_dump(mode="json") for t in tasks]


def _py_has_data() -> bool:
    return _PY_DIR.exists() and any(_PY_DIR.iterdir())


def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="変換内容をプレビューします（書き込みなし）"),
    force: bool = typer.Option(False, "--force", help="既存データを確認なしで上書きします"),
) -> None:
    """TypeScript 版（~/.task/）のデータを Python 版（~/.task-py/）に移行します。"""
    if not _TS_DIR.exists():
        from task_cli.cli.renderer import render_error
        render_error(AppError(
            "TypeScript 版のデータが見つかりません。",
            cause=f"{_TS_DIR} が存在しません。",
            remedy="dev-tasks2（TypeScript 版）をインストールしてタスクを作成してから実行してください。",
        ))
        raise typer.Exit(code=1)

    # 各ファイルを読み込む
    config_path = _TS_DIR / "config.json"
    config = _convert_config(_read_json(config_path)) if config_path.exists() else GlobalConfig()

    inbox_path = _TS_DIR / "inbox" / "tasks.json"
    inbox_tasks = _convert_tasks(_read_json(inbox_path)) if inbox_path.exists() else []

    project_tasks: dict[str, list[Task]] = {}
    projects_dir = _TS_DIR / "projects"
    if projects_dir.exists():
        for proj_dir in sorted(projects_dir.iterdir()):
            if proj_dir.is_dir():
                t_path = proj_dir / "tasks.json"
                project_tasks[proj_dir.name] = _convert_tasks(_read_json(t_path)) if t_path.exists() else []

    routines_path = _TS_DIR / "daily" / "routines.json"
    routines = _convert_routines(_read_json(routines_path)) if routines_path.exists() else []

    logs_path = _TS_DIR / "daily" / "log.json"
    logs = _convert_logs(_read_json(logs_path)) if logs_path.exists() else []

    total_tasks = len(inbox_tasks) + sum(len(v) for v in project_tasks.values())

    if dry_run:
        _print_preview(config, inbox_tasks, project_tasks, routines, logs, total_tasks)
        return

    # 既存データの上書き確認
    if _py_has_data() and not force:
        confirmed = typer.confirm(
            f"\n{_PY_DIR} に既存データがあります。上書きしますか？"
        )
        if not confirmed:
            console.print("[yellow]移行をキャンセルしました。[/yellow]")
            raise typer.Exit()

    # 書き込み
    _write_yaml(_PY_DIR / "config.yaml", config.model_dump(mode="json"))

    _write_yaml(_PY_DIR / "inbox" / "tasks.yaml", _tasks_to_yaml_data(inbox_tasks))

    for proj_name, tasks in project_tasks.items():
        _write_yaml(_PY_DIR / "projects" / proj_name / "tasks.yaml", _tasks_to_yaml_data(tasks))

    routines_data = [r.model_dump(mode="json") for r in routines]
    _write_yaml(_PY_DIR / "daily" / "routines.yaml", routines_data)

    logs_data = [l.model_dump(mode="json") for l in logs]
    _write_yaml(_PY_DIR / "daily" / "log.yaml", logs_data)

    _print_summary(config, inbox_tasks, project_tasks, routines, logs, total_tasks)


def _print_preview(
    config: GlobalConfig,
    inbox_tasks: list[Task],
    project_tasks: dict[str, list[Task]],
    routines: list[Routine],
    logs: list[DailyLog],
    total_tasks: int,
) -> None:
    console.print(Panel("[bold cyan]移行プレビュー（dry-run）[/bold cyan]\nファイルの書き込みは行いません。"))

    table = Table(title="変換対象", show_header=True, header_style="bold")
    table.add_column("ファイル")
    table.add_column("件数", justify="right")
    table.add_row("config", "1")
    table.add_row("inbox/tasks", str(len(inbox_tasks)))
    for proj, tasks in project_tasks.items():
        table.add_row(f"projects/{proj}/tasks", str(len(tasks)))
    table.add_row("daily/routines", str(len(routines)))
    table.add_row("daily/log（日数）", str(len(logs)))
    console.print(table)

    console.print(
        f"\n[green]合計: タスク {total_tasks} 件、ルーティン {len(routines)} 件、"
        f"ログ {len(logs)} 日分を移行します。[/green]"
    )
    console.print("[dim]実際に移行するには --dry-run を外して実行してください。[/dim]")


def _print_summary(
    config: GlobalConfig,
    inbox_tasks: list[Task],
    project_tasks: dict[str, list[Task]],
    routines: list[Routine],
    logs: list[DailyLog],
    total_tasks: int,
) -> None:
    console.print(Panel("[bold green]移行完了[/bold green]"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("ファイル")
    table.add_column("件数", justify="right")
    table.add_row("config", "1")
    table.add_row("inbox/tasks", str(len(inbox_tasks)))
    for proj, tasks in project_tasks.items():
        table.add_row(f"projects/{proj}/tasks", str(len(tasks)))
    table.add_row("daily/routines", str(len(routines)))
    table.add_row("daily/log（日数）", str(len(logs)))
    console.print(table)

    console.print(
        f"\n[green]タスク {total_tasks} 件、ルーティン {len(routines)} 件、"
        f"ログ {len(logs)} 日分を {_PY_DIR} に移行しました。[/green]"
    )
    active = config.active_project or "（未設定）"
    console.print(f"アクティブプロジェクト: [bold]{active}[/bold]")

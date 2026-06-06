from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from task_cli.cli.renderer import render_error, render_success
from task_cli.exceptions import AppError
from task_cli.services.daily_service import DailyService

daily_app = typer.Typer(help="デイリールーティーンを管理します。")
console = Console()


def _get_service() -> DailyService:
    return DailyService()


@daily_app.command("add")
def add(
    title: str = typer.Argument(..., help="ルーティーンのタイトル"),
) -> None:
    """デイリールーティーンを追加します。"""
    try:
        svc = _get_service()
        r = svc.add_routine(title)
        render_success(f"ルーティーン '{r.title}' を追加しました（ID: {r.id}）")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@daily_app.command("list")
def list_routines(
    all_status: bool = typer.Option(False, "--all", help="pause中も含めて表示"),
) -> None:
    """今日のルーティーン一覧を表示します。"""
    svc = _get_service()
    items = svc.list_today(include_paused=all_status)
    if not items:
        console.print("[dim]ルーティーンがありません。[/dim]")
        return
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Title")
    for routine, status in items:
        style = "green" if status == "done" else ("dim" if routine.paused else "white")
        paused_marker = " [paused]" if routine.paused else ""
        table.add_row(str(routine.id), status, f"{routine.title}{paused_marker}", style=style)
    console.print(table)


@daily_app.command("done")
def done(
    id: int = typer.Argument(..., help="ルーティーンID"),
) -> None:
    """ルーティーンを完了にします。"""
    try:
        svc = _get_service()
        svc.mark_done(id)
        render_success(f"ID {id} を完了にしました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@daily_app.command("pause")
def pause(
    id: int = typer.Argument(..., help="ルーティーンID"),
) -> None:
    """ルーティーンを一時停止します。"""
    try:
        svc = _get_service()
        svc.pause(id)
        render_success(f"ID {id} を一時停止しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@daily_app.command("resume")
def resume(
    id: Optional[int] = typer.Argument(None, help="ルーティーンID（省略で全再開）"),
    all_flag: bool = typer.Option(False, "--all", help="全ルーティーンを再開"),
) -> None:
    """ルーティーンの一時停止を解除します。"""
    try:
        svc = _get_service()
        if all_flag or id is None:
            count = svc.resume_all()
            render_success(f"{count} 件のルーティーンを再開しました")
        else:
            svc.resume(id)
            render_success(f"ID {id} を再開しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@daily_app.command("delete")
def delete(
    id: int = typer.Argument(..., help="ルーティーンID"),
) -> None:
    """ルーティーンを削除します。"""
    try:
        svc = _get_service()
        svc.delete(id)
        render_success(f"ID {id} を削除しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)


@daily_app.command("stats")
def stats() -> None:
    """直近7日の達成率を表示します。"""
    svc = _get_service()
    result = svc.stats()
    if not result:
        console.print("[dim]記録がありません。[/dim]")
        return
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("日付")
    table.add_column("完了", justify="right")
    table.add_column("合計", justify="right")
    table.add_column("達成率", justify="right")
    for entry in result:
        rate = entry["rate"]
        rate_str = f"{rate:.0%}" if rate is not None else "--"
        table.add_row(str(entry["date"]), str(entry["done"]), str(entry["total"]), rate_str)
    console.print(table)


@daily_app.command("reset")
def reset() -> None:
    """今日のルーティーンをすべてpendingに戻します。"""
    svc = _get_service()
    svc.reset_today()
    render_success("今日のルーティーンをリセットしました")

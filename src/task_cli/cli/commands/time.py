import time
from datetime import datetime
from typing import NoReturn, Optional

import typer
from rich.live import Live

from task_cli.cli.deps import get_time_tracking_use_case
from task_cli.cli.renderer import render_error, render_info, render_success
from task_cli.duration import format_clock, format_duration, parse_duration
from task_cli.exceptions import AppError
from task_cli.services.timer_service import TimerService
from task_cli.usecases.time_tracking_usecase import StopResult

# parse_duration は MCP からも使うため task_cli.duration へ移した。
# 既存の import 経路（task_cli.cli.commands.time.parse_duration）は維持する。
__all__ = ["time_app", "parse_duration"]

time_app = typer.Typer(help="タイマー機能を提供します。")


def _format_time(seconds: int) -> str:
    return format_clock(seconds)


def _fail(e: AppError) -> NoReturn:
    render_error(e)
    raise typer.Exit(code=1)


def _report_stop(result: StopResult) -> None:
    elapsed = format_duration(result.elapsed_seconds)
    if result.state.task_id is None:
        render_success(f"タイマーを終了しました（経過 {elapsed}）")
    elif result.session is None:
        render_info(
            f"タイマーを終了しましたが、タスク #{result.state.task_id} が"
            f"見つからないため記録できませんでした（経過 {elapsed}）"
        )
    else:
        render_success(
            f"タスク #{result.state.task_id} に "
            f"{format_duration(result.session.seconds)} を記録しました"
        )
    if result.overrun_seconds > 0:
        render_info(
            f"設定時間を {format_duration(result.overrun_seconds)} 超過した分は"
            f"記録に含めていません（必要なら task-py time log で追加してください）"
        )


@time_app.command("start")
def start(
    duration: Optional[str] = typer.Argument(
        None, help="時間（例: 20m, 1h, 30s）。省略するとストップウォッチになります"
    ),
    task: Optional[int] = typer.Option(None, "-t", "--task", help="作業時間を記録するタスクID"),
    detach: bool = typer.Option(
        False, "-d", "--detach", help="残り時間を表示せず、状態だけ記録して終了します"
    ),
    force: bool = typer.Option(False, "--force", help="実行中のタイマーを置き換えます"),
) -> None:
    """タイマーを開始します。"""
    try:
        seconds = parse_duration(duration) if duration is not None else None
        uc = get_time_tracking_use_case()
        started = uc.start_timer(duration_seconds=seconds, task_id=task, force=force)
    except AppError as e:
        _fail(e)

    if started.replaced is not None:
        _report_stop(started.replaced)
    state = started.state

    if task is None:
        render_info("💡 --task <id> を付けると作業時間がタスクに記録されます")

    if detach:
        render_success(f"タイマーを開始しました（{TimerService.describe(state)}）")
        render_info("task-py time status で確認し、task-py time stop で記録します")
        return

    try:
        with Live(refresh_per_second=1) as live:
            while True:
                # 残り時間は保存された started_at から都度計算する。
                # 変数でカウントダウンしないため、スリープや別プロセスとズレない。
                remaining = TimerService.remaining_seconds(state)
                if remaining is None:
                    live.update(f"⏱  経過 {_format_time(TimerService.elapsed_seconds(state))}")
                else:
                    if remaining <= 0:
                        break
                    live.update(f"⏱  残り {_format_time(remaining)}")
                time.sleep(1)
        typer.echo("⏱  完了！")
        print("\a", end="", flush=True)
    except KeyboardInterrupt:
        typer.echo("")

    # 自分が開始したタイマーだけを止める。別プロセスが stop / --force で
    # 張り替えていた場合に、他人のタイマーを取り違えて記録しないため。
    _finish(expected_started_at=state.started_at)


@time_app.command("status")
def status() -> None:
    """実行中のタイマーを表示します。"""
    state = get_time_tracking_use_case().status()
    if state is None:
        render_info("実行中のタイマーはありません")
        return
    render_success(TimerService.describe(state))
    if TimerService.is_expired(state):
        render_info("task-py time stop で作業時間を記録して終了してください")


@time_app.command("stop")
def stop() -> None:
    """タイマーを終了し、経過時間をタスクに記録します。"""
    _finish()


@time_app.command("cancel")
def cancel() -> None:
    """タイマーを破棄します（作業時間は記録しません）。"""
    try:
        state = get_time_tracking_use_case().cancel_timer()
    except AppError as e:
        _fail(e)
    render_success(f"タイマーを破棄しました（{TimerService.describe(state)}）")


@time_app.command("log")
def log(
    task_id: int = typer.Argument(..., help="タスクID"),
    duration: str = typer.Argument(..., help="作業時間（例: 25m, 1h）"),
) -> None:
    """作業時間を手動で記録します。"""
    try:
        seconds = parse_duration(duration)
        task = get_time_tracking_use_case().log_work(task_id, seconds)
    except AppError as e:
        _fail(e)
    render_success(
        f"タスク #{task.id} に {format_duration(seconds)} を記録しました"
        f"（合計 {format_duration(task.total_worked_seconds)}）"
    )


def _finish(expected_started_at: datetime | None = None) -> None:
    try:
        result = get_time_tracking_use_case().stop_timer(
            expected_started_at=expected_started_at
        )
    except AppError as e:
        _fail(e)
    _report_stop(result)

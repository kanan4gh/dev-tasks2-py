import re
import time

import typer
from rich.live import Live

from task_cli.exceptions import AppError

time_app = typer.Typer(help="タイマー機能を提供します。")


def parse_duration(s: str) -> int:
    """時間文字列を秒数に変換する。数値のみは分として扱う。"""
    s = s.strip()
    m = re.fullmatch(r"(\d+)(min|m|h|s)?", s)
    if not m:
        raise AppError(
            "不正な時間形式です。",
            cause=f"'{s}' は解釈できません。",
            remedy="例: 20m, 1h, 30s, 20（数値のみは分）",
        )
    value = int(m.group(1))
    unit = m.group(2) or "m"
    if unit in ("m", "min"):
        return value * 60
    if unit == "h":
        return value * 3600
    return value  # s


def _format_time(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@time_app.command("start")
def start(
    duration: str = typer.Argument(..., help="時間（例: 20m, 1h, 30s）"),
) -> None:
    """タイマーを開始します。"""
    try:
        remaining = parse_duration(duration)
    except AppError as e:
        from task_cli.cli.renderer import render_error
        render_error(e)
        raise typer.Exit(code=1)

    try:
        with Live(refresh_per_second=1) as live:
            while remaining > 0:
                live.update(f"⏱  残り {_format_time(remaining)}")
                time.sleep(1)
                remaining -= 1
        typer.echo("⏱  完了！")
        print("\a", end="", flush=True)
    except KeyboardInterrupt:
        typer.echo("\nキャンセルしました")

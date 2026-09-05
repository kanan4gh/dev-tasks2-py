"""時間の文字列表現のパースと整形。

CLI・MCP の両方から使うため、どの層にも属さない leaf モジュールとして
`exceptions.py` と同じくパッケージ直下に置く。
"""

import re

from task_cli.exceptions import AppError

_DURATION_RE = re.compile(r"(\d+)(min|m|h|s)?")


def parse_duration(s: str) -> int:
    """時間文字列を秒数に変換する。数値のみは分として扱う。"""
    s = s.strip()
    m = _DURATION_RE.fullmatch(s)
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


def format_clock(seconds: int) -> str:
    """タイマー表示用の時計形式に整形する（例: 05:30 / 01:05:30）。"""
    sign = "-" if seconds < 0 else ""
    h, rem = divmod(abs(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{sign}{h:02d}:{m:02d}:{s:02d}"
    return f"{sign}{m:02d}:{s:02d}"


def format_duration(seconds: int) -> str:
    """作業時間の要約用に整形する（例: 45s / 20m / 1h 20m）。"""
    if seconds < 60:
        return f"{seconds}s"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"

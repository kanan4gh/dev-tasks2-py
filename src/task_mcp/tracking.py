import json
import time
from collections import Counter
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

_LOG_PATH = Path("~/.task-py/mcp_calls.jsonl")

F = TypeVar("F", bound=Callable[..., Any])


def track(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        ok = True
        try:
            return fn(*args, **kwargs)
        except Exception:
            ok = False
            raise
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            _append_log(fn.__name__, elapsed_ms, ok)

    return wrapper  # type: ignore[return-value]


def _append_log(tool: str, elapsed_ms: int, ok: bool) -> None:
    try:
        path = _LOG_PATH.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tool": tool,
            "elapsed_ms": elapsed_ms,
            "ok": ok,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_stats(log_path: Path | None = None) -> str:
    path = (log_path or _LOG_PATH).expanduser()
    if not path.exists():
        return "ログがまだありません。"

    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not entries:
        return "ログがまだありません。"

    tool_counts: Counter[str] = Counter(e["tool"] for e in entries)
    error_counts: Counter[str] = Counter(
        e["tool"] for e in entries if not e.get("ok", True)
    )

    lines = [f"総呼び出し数: {len(entries)} 件\n", "ツール別呼び出し回数（多い順）:"]
    for tool, count in tool_counts.most_common():
        err = error_counts.get(tool, 0)
        err_str = f"  (エラー: {err})" if err else ""
        lines.append(f"  {tool}: {count}{err_str}")

    return "\n".join(lines)

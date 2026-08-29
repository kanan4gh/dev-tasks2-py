"""PostToolUseフック: 実装ファイル編集が続いてもtasklist.mdが更新されない場合、非強制リマインドを注入する。"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REMIND_THRESHOLD = 5
INCOMPLETE_PATTERN = re.compile(r"^\s*- \[ \] ", re.MULTILINE)
# 日付接頭辞を持つ作業ディレクトリのみが対象(example/ 等のサンプルを誤検出しない)
STEERING_DIR_PATTERN = re.compile(r"^\d{8}-")
STATE_FILE = Path(".claude") / "hooks" / "state" / "edit_count.json"

REMINDER = (
    f"実装ファイルの編集が{REMIND_THRESHOLD}回続いていますが、tasklist.md が更新されていません。"
    "完了したタスクがあれば .steering/ 配下の tasklist.md を [x] に更新してください。"
)


def has_active_steering_work(project_root: Path) -> bool:
    """最新ステアリングディレクトリのtasklist.mdに未完了タスクがあるか。"""
    steering = project_root / ".steering"
    if not steering.is_dir():
        return False
    dirs = sorted(
        (p for p in steering.iterdir() if p.is_dir() and STEERING_DIR_PATTERN.match(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )
    if not dirs:
        return False
    tasklist = dirs[0] / "tasklist.md"
    if not tasklist.is_file():
        return False
    return bool(INCOMPLETE_PATTERN.search(tasklist.read_text(encoding="utf-8")))


def load_count(state_path: Path) -> int:
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        count = data["count"]
        return count if isinstance(count, int) and count >= 0 else 0
    except Exception:
        return 0  # fail-open: 状態が読めなければ初期化して継続


def save_count(state_path: Path, count: int) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"count": count}), encoding="utf-8")


def check(event: dict[str, Any], project_root: Path) -> dict[str, Any] | None:
    """リマインドが必要なら additionalContext のJSONを、不要ならNoneを返す。"""
    file_path = event.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return None

    state_path = project_root / STATE_FILE

    if ".steering/" in str(Path(file_path).as_posix()) + "/":
        save_count(state_path, 0)
        return None

    if not has_active_steering_work(project_root):
        return None

    count = load_count(state_path) + 1
    if count < REMIND_THRESHOLD:
        save_count(state_path, count)
        return None

    save_count(state_path, 0)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER,
        }
    }


def main() -> None:
    try:
        event = json.load(sys.stdin)
        project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        result = check(event, project_root)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
    except Exception:
        pass  # fail-open: フックの不具合でユーザーの作業を止めない
    sys.exit(0)


if __name__ == "__main__":
    main()

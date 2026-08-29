"""tasklist.mdの作業状態を決定論的に遷移するCLI。"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Sequence

from steering_lint import (
    RETROSPECTIVE_HEADING,
    STEERING_DIR_PATTERN,
    find_incomplete_tasks,
    find_latest_tasklist,
    find_pause_record,
    find_retrospective_placeholders,
    has_retrospective_content,
    missing_pause_record_labels,
    parse_task_state,
)

STATE_SECTION_PATTERN = re.compile(
    r"^## 作業状態[ \t]*\n.*?(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
HISTORY_SECTION_PATTERN = re.compile(
    r"^(## 作業履歴[ \t]*\n)(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
TASKLIST_HEADING_PATTERN = re.compile(r"^# タスクリスト[ \t]*$", re.MULTILINE)


class TransitionError(ValueError):
    """状態遷移の前提を満たさない。"""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_tasklist(project_root: Path, steering: str | None) -> Path:
    """明示対象または最新の日付付きtasklistを返す。"""
    if steering is None:
        candidate = find_latest_tasklist(project_root)
        if candidate is None:
            raise TransitionError("対象のtasklist.mdがありません")
    else:
        requested = Path(steering)
        if requested.is_absolute():
            candidate = requested
        elif len(requested.parts) == 1:
            candidate = project_root / ".steering" / requested
        else:
            candidate = project_root / requested

    resolved = candidate.resolve()
    steering_root = (project_root / ".steering").resolve()
    if resolved.is_dir():
        resolved = resolved / "tasklist.md"
    if (
        resolved.parent.parent != steering_root
        or STEERING_DIR_PATTERN.match(resolved.parent.name) is None
        or not resolved.is_file()
    ):
        raise TransitionError("対象は.steering直下の日付付きtasklistに限ります")
    return resolved


def state_section(state: str, timestamp: str, harness: str) -> str:
    return (
        "## 作業状態\n\n"
        f"- **状態**: {state}\n"
        f"- **状態更新日時**: {timestamp}\n"
        f"- **使用ハーネス**: {harness}\n\n"
    )


def set_state(text: str, state: str, timestamp: str, harness: str) -> str:
    """既存状態セクションを置換し、旧形式には先頭見出し後へ追加する。"""
    replacement = state_section(state, timestamp, harness)
    if STATE_SECTION_PATTERN.search(text):
        return STATE_SECTION_PATTERN.sub(replacement, text, count=1)
    heading = TASKLIST_HEADING_PATTERN.search(text)
    if heading is None:
        raise TransitionError("tasklist.mdに「# タスクリスト」見出しがありません")
    return text[: heading.end()] + "\n\n" + replacement + text[heading.end() :].lstrip("\n")


def append_history(text: str, record: str) -> str:
    """作業履歴セクションへ記録を追記する。"""
    match = HISTORY_SECTION_PATTERN.search(text)
    if match is not None:
        body = match.group(2).strip()
        if body.startswith("_記録なし_"):
            body = body.removeprefix("_記録なし_").lstrip()
        if not body:
            new_body = record.rstrip()
        else:
            new_body = f"{body}\n\n{record.rstrip()}"
        replacement = f"{match.group(1)}\n{new_body}\n\n"
        return text[: match.start()] + replacement + text[match.end() :]

    state_match = STATE_SECTION_PATTERN.search(text)
    if state_match is None:
        raise TransitionError("作業状態セクションがありません")
    history = f"## 作業履歴\n\n{record.rstrip()}\n\n"
    return text[: state_match.end()] + history + text[state_match.end() :].lstrip("\n")


def pause_text(
    text: str,
    *,
    harness: str,
    completed_scope: str,
    uncommitted_changes: str,
    resume_at: str,
    reason: str,
    timestamp: str,
) -> str:
    """activeまたは未分類の旧tasklistをpausedへ遷移する。"""
    state = parse_task_state(text)
    incomplete = find_incomplete_tasks(text)
    if state.error is not None:
        raise TransitionError(state.error)
    if state.value not in {None, "active"}:
        raise TransitionError(f"{state.value}からpausedへは遷移できません")
    if state.value is None and not incomplete:
        raise TransitionError("完了済みの旧tasklistはpauseできません")
    if not incomplete:
        raise TransitionError("未完了タスクがないためpauseではなくcompleteを使用してください")
    values = {
        "使用ハーネス": harness,
        "完了済みの範囲": completed_scope,
        "未コミット変更": uncommitted_changes,
        "再開位置": resume_at,
        "中断理由": reason,
    }
    empty = [label for label, value in values.items() if not value.strip()]
    if empty:
        raise TransitionError(f"中断記録の必須値が空です: {', '.join(empty)}")

    updated = set_state(text, "paused", timestamp, harness)
    record = "\n".join(
        [
            f"### 中断記録: {timestamp}",
            "",
            f"- **使用ハーネス**: {harness}",
            f"- **完了済みの範囲**: {completed_scope}",
            f"- **未コミット変更**: {uncommitted_changes}",
            f"- **再開位置**: {resume_at}",
            f"- **中断理由**: {reason}",
        ]
    )
    return append_history(updated, record)


def resume_text(
    text: str,
    *,
    harness: str,
    resume_at: str,
    reason: str,
    timestamp: str,
) -> str:
    """pausedまたは検証失敗後のcompleteをactiveへ戻す。"""
    state = parse_task_state(text)
    if state.error is not None:
        raise TransitionError(state.error)
    if state.value not in {"paused", "complete"}:
        raise TransitionError(f"{state.value or '未宣言'}からactiveへは遷移できません")
    if not harness.strip() or not resume_at.strip() or not reason.strip():
        raise TransitionError("使用ハーネス、再開位置、再開理由は必須です")
    if state.value == "paused":
        record = (
            find_pause_record(text, state.updated_at)
            if state.updated_at is not None
            else None
        )
        if record is None:
            raise TransitionError("pausedに対応する中断記録がありません")
        missing = missing_pause_record_labels(record)
        if missing:
            raise TransitionError(
                f"pausedに対応する中断記録の必須項目がありません: {', '.join(missing)}"
            )

    updated = set_state(text, "active", timestamp, harness)
    record = "\n".join(
        [
            f"### 再開記録: {timestamp}",
            "",
            f"- **使用ハーネス**: {harness}",
            f"- **再開位置**: {resume_at}",
            f"- **再開理由**: {reason}",
        ]
    )
    return append_history(updated, record)


def complete_text(text: str, *, harness: str, timestamp: str) -> str:
    """active tasklistの完了前提を検証しcompleteへ遷移する。"""
    state = parse_task_state(text)
    if state.error is not None:
        raise TransitionError(state.error)
    if state.value != "active":
        raise TransitionError(f"{state.value or '未宣言'}からcompleteへは遷移できません")
    incomplete = find_incomplete_tasks(text)
    if incomplete:
        raise TransitionError(
            f"未完了タスクが{len(incomplete)}件あります(先頭: {incomplete[0]})"
        )
    if RETROSPECTIVE_HEADING not in text:
        raise TransitionError("「実装後の振り返り」セクションがありません")
    if not has_retrospective_content(text):
        raise TransitionError("「実装後の振り返り」が未記入です")
    placeholders = find_retrospective_placeholders(text)
    if placeholders:
        raise TransitionError(
            f"振り返りにプレースホルダがあります(先頭: {placeholders[0]})"
        )
    if not harness.strip():
        raise TransitionError("使用ハーネスは必須です")
    return set_state(text, "complete", timestamp, harness)


def write_transition(tasklist: Path, updated: str) -> None:
    """同一ディレクトリの一時ファイルから原子的に置換する。"""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=tasklist.parent,
            prefix=f".{tasklist.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(tasklist.stat().st_mode))
        os.replace(temporary, tasklist)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--steering", help="日付付きステアリング名またはtasklistへのパス")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pause = subparsers.add_parser("pause")
    pause.add_argument("--harness", required=True)
    pause.add_argument("--completed-scope", required=True)
    pause.add_argument("--uncommitted-changes", required=True)
    pause.add_argument("--resume-at", required=True)
    pause.add_argument("--reason", required=True)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--harness", required=True)
    resume.add_argument("--resume-at", required=True)
    resume.add_argument("--reason", required=True)

    complete = subparsers.add_parser("complete")
    complete.add_argument("--harness", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = args.project_root.resolve()
    try:
        tasklist = resolve_tasklist(project_root, args.steering)
        text = tasklist.read_text(encoding="utf-8")
        timestamp = now_iso()
        if args.command == "pause":
            updated = pause_text(
                text,
                harness=args.harness,
                completed_scope=args.completed_scope,
                uncommitted_changes=args.uncommitted_changes,
                resume_at=args.resume_at,
                reason=args.reason,
                timestamp=timestamp,
            )
        elif args.command == "resume":
            updated = resume_text(
                text,
                harness=args.harness,
                resume_at=args.resume_at,
                reason=args.reason,
                timestamp=timestamp,
            )
        else:
            updated = complete_text(text, harness=args.harness, timestamp=timestamp)
        write_transition(tasklist, updated)
    except (OSError, TransitionError) as exc:
        print(f"steering state: {exc}", file=sys.stderr)
        return 1
    print(f"steering state: {tasklist} -> {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

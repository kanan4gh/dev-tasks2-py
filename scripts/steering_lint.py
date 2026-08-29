"""ステアリング規律の状態対応lint CLI。

`.steering/[YYYYMMDD]-*/` を1回走査し、全ディレクトリへ通常規則を適用する。
`--require-complete` 指定時は、同じ走査の中で対象1件だけに完了規則G1を追加する。

- C1: 必須ファイル（軽量パスではdesign.mdを省略可）
- C2: requirements.mdのGitHub Issue URL
- C3: tasklist.mdの作業状態と未完了タスクの整合性
- C4: complete相当tasklistの振り返り
- C5: paused tasklistの中断記録
- G1: 完了検査対象がcomplete相当
"""

from __future__ import annotations

import argparse
from datetime import datetime
import re
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

STEERING_DIR_PATTERN = re.compile(r"^\d{8}-")
INCOMPLETE_PATTERN = re.compile(r"^\s*- \[ \] (.+)$", re.MULTILINE)
FENCE_PATTERN = re.compile(r"^[ \t]*(`{3,}|~{3,})")
ISSUE_URL_PATTERN = re.compile(r"github\.com/[^/\s]+/[^/\s]+/issues/\d+")
PLACEHOLDER_PATTERN = re.compile(r"\{[^{}\n]+\}")
LIGHTWEIGHT_PATTERN = re.compile(r"^- \*\*軽量パス\*\*: 適用[ \t]*$", re.MULTILINE)
STATE_PATTERN = re.compile(r"^- \*\*状態\*\*: (.+?)[ \t]*$", re.MULTILINE)
STATE_UPDATED_PATTERN = re.compile(
    r"^- \*\*状態更新日時\*\*: (.+?)[ \t]*$", re.MULTILINE
)
STATE_HARNESS_PATTERN = re.compile(
    r"^- \*\*使用ハーネス\*\*: (.+?)[ \t]*$", re.MULTILINE
)
STATE_SECTION_PATTERN = re.compile(
    r"^## 作業状態[ \t]*\n.*?(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
PAUSE_HEADING_PATTERN = re.compile(r"^### 中断記録: (.+?)[ \t]*$", re.MULTILINE)
SECTION_HEADING_PATTERN = re.compile(r"^#{2,3} ", re.MULTILINE)

VALID_STATES = frozenset({"active", "paused", "complete"})
PAUSE_REQUIRED_LABELS = (
    "使用ハーネス",
    "完了済みの範囲",
    "未コミット変更",
    "再開位置",
    "中断理由",
)
RETROSPECTIVE_HEADING = "## 実装後の振り返り"
REQUIRED_FILES = ("requirements.md", "design.md", "tasklist.md")

# ---------------------------------------------------------------------------
# 派生固有差分(dev-tasks2-py): 移行前ステアリングのgrandfather
#
# platform-harness v1.6.1 導入(GitHub issue #26)より前に作られたステアリングは、
# 旧SDD世代および project-ouroboros 軽量レーンの形式であり、現行の C1〜C5 を満たさない。
# これらは適応度計測(reports/fitness-report-dev-tasks2-py.md)の基礎データであり、
# lint を通すための事後改変は帰属と観測被覆率を壊すため行わない。
#
# 免除は下の限定列挙のみ。前方一致・ワイルドカードは使わない。
# 移行後に作られるステアリングは一切免除しない。
# platform-harness の release を同期する際は、この差分を温存すること。
# ---------------------------------------------------------------------------
LEGACY_PRE_MIGRATION = frozenset(
    {
        "20260402-dev-tasks2-py-setup",
        "20260521-change-storage-dir-express",
        "20260521-rename-command-task-py-express",
        "20260522-aws-devcontainer-starter",
        "20260606-implement-p0-remaining",
        "20260606-implement-remaining-commands",
        "20260606-implement-shell-command",
        "20260607-fix-shell-onboard-display",
        "20260607-implement-edit-schedule",
        "20260607-implement-migrate",
        "20260607-migrate-priority-keyerror-express",
        "20260607-ux-improvements-from-install-review",
        "20260608-implement-mcp-server",
        "20260609-restore-japanese-descriptions-express",
        "20260610-mcp-observability",
        "20260610-rename-onboard-to-overview-express",
        "20260617-mcp-overview-task-details-express",
        "20260706-harness-rollout-express",
    }
)
LATEST_TARGET = "latest"


class Violation(NamedTuple):
    directory: str
    check_id: str
    message: str


class TaskState(NamedTuple):
    value: str | None
    updated_at: str | None
    harness: str | None
    error: str | None


class TasklistContext(NamedTuple):
    """1回だけ読み込んだtasklistと解析結果。"""

    text: str
    incomplete: tuple[str, ...]
    state: TaskState
    effective: TaskState


def iter_steering_dirs(project_root: Path) -> list[Path]:
    """日付接頭辞を持つステアリングディレクトリを名前昇順で返す。"""
    steering = project_root / ".steering"
    if not steering.is_dir():
        return []
    return sorted(
        (p for p in steering.iterdir() if p.is_dir() and STEERING_DIR_PATTERN.match(p.name)),
        key=lambda p: p.name,
    )


def find_latest_tasklist(project_root: Path) -> Path | None:
    """最新の日付付きステアリングのtasklist.mdを返す。"""
    dirs = iter_steering_dirs(project_root)
    if not dirs:
        return None
    tasklist = dirs[-1] / "tasklist.md"
    return tasklist if tasklist.is_file() else None


def strip_code_fences(text: str) -> str:
    """Markdownフェンス付きコードブロック内を空行化する。"""
    lines = text.split("\n")
    stripped: list[str] = []
    open_marker: str | None = None
    for line in lines:
        match = FENCE_PATTERN.match(line)
        if open_marker is None:
            if match is None:
                stripped.append(line)
            else:
                open_marker = match.group(1)
                stripped.append("")
            continue
        if match is not None and _closes_fence(match, line, open_marker):
            open_marker = None
        stripped.append("")
    return "\n".join(stripped)


def _closes_fence(match: re.Match[str], line: str, open_marker: str) -> bool:
    marker = match.group(1)
    if marker[0] != open_marker[0] or len(marker) < len(open_marker):
        return False
    return not line[match.end() :].strip()


def find_incomplete_tasks(text: str) -> list[str]:
    """未完了タスクを出現順に返す。コードフェンスも安全側で検査対象にする。"""
    return INCOMPLETE_PATTERN.findall(text)


def has_lightweight_declaration(steering_dir: Path) -> bool:
    requirements = steering_dir / "requirements.md"
    if not requirements.is_file():
        return False
    return bool(
        LIGHTWEIGHT_PATTERN.search(strip_code_fences(requirements.read_text(encoding="utf-8")))
    )


def parse_task_state(text: str) -> TaskState:
    """tasklistの状態ブロックを解析する。旧形式はvalue=Noneで返す。"""
    visible = strip_code_fences(text)
    sections = list(STATE_SECTION_PATTERN.finditer(visible))
    if not sections:
        if STATE_PATTERN.search(visible):
            return TaskState(None, None, None, "状態宣言は「## 作業状態」内に置いてください")
        return TaskState(None, None, None, None)
    if len(sections) != 1:
        return TaskState(None, None, None, "作業状態セクションが複数あります")
    state_text = sections[0].group(0)
    values = STATE_PATTERN.findall(state_text)
    updated_values = STATE_UPDATED_PATTERN.findall(state_text)
    harness_values = STATE_HARNESS_PATTERN.findall(state_text)

    if not values:
        return TaskState(None, None, None, "作業状態セクションに状態宣言がありません")
    if len(values) != 1:
        return TaskState(None, None, None, "状態宣言が複数あります")

    value = values[0].strip()
    if value not in VALID_STATES:
        return TaskState(value, None, None, f"未知の状態です: {value}")
    if len(updated_values) != 1:
        return TaskState(value, None, None, "状態更新日時は1件必要です")
    if len(harness_values) != 1:
        return TaskState(value, None, None, "使用ハーネスは1件必要です")

    updated_at = updated_values[0].strip()
    harness = harness_values[0].strip()
    if not _is_timezone_aware_iso8601(updated_at):
        return TaskState(
            value,
            updated_at,
            harness,
            "状態更新日時はタイムゾーン付きISO 8601で記録してください",
        )
    if not harness:
        return TaskState(value, updated_at, harness, "使用ハーネスが空です")
    return TaskState(value, updated_at, harness, None)


def _is_timezone_aware_iso8601(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def effective_state(text: str) -> TaskState:
    """旧完了tasklistをcomplete相当として補完した状態を返す。"""
    state = parse_task_state(text)
    if state.value is None and state.error is None and not find_incomplete_tasks(text):
        return TaskState("complete", None, None, None)
    return state


def load_tasklist_context(steering_dir: Path) -> TasklistContext | None:
    """tasklistを1回読み、通常規則と完了規則で共有する解析結果を返す。"""
    tasklist = steering_dir / "tasklist.md"
    if not tasklist.is_file():
        return None
    text = tasklist.read_text(encoding="utf-8")
    incomplete = tuple(find_incomplete_tasks(text))
    state = parse_task_state(text)
    effective = state
    if state.value is None and state.error is None and not incomplete:
        effective = TaskState("complete", None, None, None)
    return TasklistContext(text, incomplete, state, effective)


def has_retrospective_content(text: str) -> bool:
    """振り返りに見出し以外の記入が1行以上あるかを返す。"""
    _, separator, retrospective = text.partition(RETROSPECTIVE_HEADING)
    if not separator:
        return False
    return any(
        stripped and not stripped.startswith("#") and stripped != "---"
        for line in retrospective.splitlines()
        if (stripped := line.strip())
    )


def check_required_files(steering_dir: Path) -> list[Violation]:
    missing = [name for name in REQUIRED_FILES if not (steering_dir / name).is_file()]
    if "design.md" in missing and has_lightweight_declaration(steering_dir):
        missing.remove("design.md")
    return [Violation(steering_dir.name, "C1", f"{name} がありません") for name in missing]


def check_issue_url(steering_dir: Path) -> list[Violation]:
    requirements = steering_dir / "requirements.md"
    if not requirements.is_file():
        return []
    if ISSUE_URL_PATTERN.search(requirements.read_text(encoding="utf-8")):
        return []
    return [Violation(steering_dir.name, "C2", "requirements.md にGitHub Issue URLがありません")]


def check_task_state(
    steering_dir: Path, context: TasklistContext | None = None
) -> list[Violation]:
    """C3: 状態と未完了タスクの整合性を1回評価する。"""
    context = context or load_tasklist_context(steering_dir)
    if context is None:
        return []
    incomplete = context.incomplete
    state = context.state

    if state.error is not None:
        return [Violation(steering_dir.name, "C3", state.error)]
    if state.value is None:
        if incomplete:
            return [
                Violation(
                    steering_dir.name,
                    "C3",
                    "未完了タスクがある旧形式tasklistには作業状態の宣言が必要です",
                )
            ]
        return []
    if state.value == "complete" and incomplete:
        return [
            Violation(
                steering_dir.name,
                "C3",
                f"状態がcompleteですが未完了タスクが{len(incomplete)}件あります"
                f"(先頭: {incomplete[0]})",
            )
        ]
    if state.value == "paused" and not incomplete:
        return [
            Violation(
                steering_dir.name,
                "C3",
                "状態がpausedですが未完了タスクがありません。completeへ遷移してください",
            )
        ]
    return []


def check_retrospective(
    steering_dir: Path, context: TasklistContext | None = None
) -> list[Violation]:
    """C4: complete相当tasklistの振り返りを検査する。"""
    context = context or load_tasklist_context(steering_dir)
    if context is None:
        return []
    text = context.text
    state = context.effective
    if state.error is not None or state.value != "complete" or context.incomplete:
        return []
    _, separator, retrospective = text.partition(RETROSPECTIVE_HEADING)
    if not separator:
        return [Violation(steering_dir.name, "C4", "「実装後の振り返り」セクションがありません")]
    if not has_retrospective_content(text):
        return [Violation(steering_dir.name, "C4", "「実装後の振り返り」が未記入です")]
    placeholders = PLACEHOLDER_PATTERN.findall(retrospective)
    if not placeholders:
        return []
    return [
        Violation(
            steering_dir.name,
            "C4",
            f"振り返りにプレースホルダが{len(placeholders)}件残っています"
            f"(先頭: {placeholders[0]})",
        )
    ]


def find_pause_record(text: str, updated_at: str) -> str | None:
    """状態更新日時に対応する最新の中断記録本文を返す。"""
    visible = strip_code_fences(text)
    latest: str | None = None
    for match in PAUSE_HEADING_PATTERN.finditer(visible):
        if match.group(1).strip() != updated_at:
            continue
        start = match.end()
        next_heading = SECTION_HEADING_PATTERN.search(visible, start)
        end = next_heading.start() if next_heading is not None else len(visible)
        latest = visible[start:end]
    return latest


def missing_pause_record_labels(record: str) -> list[str]:
    """中断記録の空でない必須ラベルのうち欠けているものを返す。"""
    return [
        label
        for label in PAUSE_REQUIRED_LABELS
        if not re.search(rf"^- \*\*{re.escape(label)}\*\*: \S", record, re.MULTILINE)
    ]


def check_pause_record(
    steering_dir: Path, context: TasklistContext | None = None
) -> list[Violation]:
    """C5: paused状態に対応する定型中断記録を検査する。"""
    context = context or load_tasklist_context(steering_dir)
    if context is None:
        return []
    text = context.text
    state = context.state
    if state.error is not None or state.value != "paused" or state.updated_at is None:
        return []
    record = find_pause_record(text, state.updated_at)
    if record is None:
        return [
            Violation(
                steering_dir.name,
                "C5",
                "pausedの状態更新日時に対応する中断記録がありません",
            )
        ]
    missing = missing_pause_record_labels(record)
    if not missing:
        return []
    return [
        Violation(
            steering_dir.name,
            "C5",
            f"中断記録の必須項目がありません: {', '.join(missing)}",
        )
    ]


def check_completion_target(
    steering_dir: Path, context: TasklistContext | None = None
) -> list[Violation]:
    """G1: 完了検査対象がcomplete相当であることだけを追加検査する。"""
    context = context or load_tasklist_context(steering_dir)
    if context is None:
        return []
    state = context.effective
    if state.error is not None or state.value == "complete":
        return []
    return [
        Violation(
            steering_dir.name,
            "G1",
            f"完了検査の対象ですが状態が{state.value or '未宣言'}です",
        )
    ]


def resolve_completion_target(project_root: Path, value: str) -> Path:
    """latestまたは日付付きディレクトリ名を完了対象へ解決する。"""
    dirs = iter_steering_dirs(project_root)
    if value == LATEST_TARGET:
        if not dirs:
            raise ValueError("完了検査対象のステアリングがありません")
        return dirs[-1]

    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    elif len(candidate.parts) == 1:
        resolved = (project_root / ".steering" / candidate).resolve()
    else:
        resolved = (project_root / candidate).resolve()
    steering_root = (project_root / ".steering").resolve()
    if resolved.parent != steering_root:
        raise ValueError("完了検査対象は.steering直下の日付付きディレクトリに限ります")
    if not STEERING_DIR_PATTERN.match(resolved.name) or not resolved.is_dir():
        raise ValueError(f"完了検査対象が見つかりません: {value}")
    return resolved


def lint(project_root: Path, completion_target: Path | None = None) -> list[Violation]:
    """通常規則を単一走査し、対象だけにG1を追加する。"""
    violations: list[Violation] = []
    normalized_target = completion_target.resolve() if completion_target is not None else None
    for steering_dir in iter_steering_dirs(project_root):
        is_target = normalized_target is not None and steering_dir.resolve() == normalized_target
        # 移行前ステアリングは通常規則から免除する。完了対象に明示指定された場合だけG1を課す。
        is_legacy = steering_dir.name in LEGACY_PRE_MIGRATION
        if is_legacy and not is_target:
            continue
        context = load_tasklist_context(steering_dir)
        if not is_legacy:
            violations.extend(check_required_files(steering_dir))
            violations.extend(check_issue_url(steering_dir))
            violations.extend(check_task_state(steering_dir, context))
            violations.extend(check_retrospective(steering_dir, context))
            violations.extend(check_pause_record(steering_dir, context))
        if is_target:
            violations.extend(check_completion_target(steering_dir, context))
    return violations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--require-complete",
        nargs="?",
        const=LATEST_TARGET,
        metavar="STEERING",
        help="最新または指定したステアリングを完了対象にする",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = args.project_root.resolve()
    completion_target: Path | None = None
    if args.require_complete is not None:
        try:
            completion_target = resolve_completion_target(project_root, args.require_complete)
        except ValueError as exc:
            print(f"steering lint: {exc}", file=sys.stderr)
            return 2
    violations = lint(project_root, completion_target)
    if not violations:
        return 0
    print(f"steering lint: {len(violations)}件の違反があります")
    for violation in violations:
        print(
            f"  [{violation.check_id}] .steering/{violation.directory}/: {violation.message}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

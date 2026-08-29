"""Nested worktree checkouts must stay out of the tools that walk the project.

`EnterWorktree` puts a full checkout under `.claude/worktrees/<name>/`. Tools that honour
`.gitignore` (ruff among them) would otherwise lint that checkout, so an unrelated worktree
would decide whether the parent repository's quality gate passes (see GitHub issue #41).

The contract is verified through `git check-ignore` rather than by matching strings in
`.gitignore`: git's ignore resolution is what those tools actually consume.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]

IGNORED_PATHS = (
    ".claude/worktrees/",
    ".claude/worktrees/feature+example/scripts/steering_lint.py",
    ".claude/worktrees/feature+example/tests/lint/test_metered_automation_lint.py",
    ".claude/worktrees/feature+example/.steering/20260101-example/tasklist.md",
)
# 過剰無視の検出用。`.claude/` 直下の管理対象は走査され続けなければならない
TRACKED_PATHS = (
    ".claude/commands/add-feature.md",
    ".claude/hooks/remind_tasklist_update.py",
    ".claude/README.md",
)


def is_ignored(relative_path: str) -> bool:
    """git のignore解決で無視対象かを返す(ファイルの実在は問わない)。

    `--no-index` は必須である。これが無いと追跡済みファイルは常に「無視されない」と
    判定され、`.claude/` 全体を無視するような過剰な除外を書いてもテストが通ってしまう。
    ルールそのものが一致するかを見るために index を参照させない。
    """
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "--", relative_path],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise AssertionError(
            f"git check-ignore failed for {relative_path}: {result.stderr.decode(errors='replace')}"
        )
    return result.returncode == 0


def test_nested_worktree_checkouts_are_ignored() -> None:
    for path in IGNORED_PATHS:
        assert is_ignored(path), f"{path} が無視対象になっていない"


def test_managed_claude_files_are_not_ignored() -> None:
    """除外が広がりすぎて `.claude/` 直下の管理対象まで隠していないこと。"""
    for path in TRACKED_PATHS:
        assert not is_ignored(path), f"{path} が誤って無視されている"

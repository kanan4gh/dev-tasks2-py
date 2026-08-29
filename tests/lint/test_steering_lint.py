"""steering_lint.pyの状態・通常/完了プロファイルを検証する。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

LINT_PATH = Path(__file__).parents[2] / "scripts" / "steering_lint.py"
ISSUE_URL = "https://github.com/example/repo/issues/1"
TIMESTAMP = "2026-07-28T10:00:00+09:00"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("steering_lint", LINT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lint_mod = load_module()

REQUIREMENTS = f"# 要求内容\n\n関連Issue: {ISSUE_URL}\n"
LIGHTWEIGHT_REQUIREMENTS = (
    f"# 要求内容\n\n- **関連Issue**: {ISSUE_URL}\n- **軽量パス**: 適用\n"
)
RETROSPECTIVE = """## 実装後の振り返り

### 実装完了日

2026-07-28

### 学んだこと

- 具体的な学び
"""


def tasklist(
    state: str | None,
    tasks: str,
    *,
    timestamp: str = TIMESTAMP,
    harness: str = "Codex",
    history: str = "",
    retrospective: str = RETROSPECTIVE,
) -> str:
    state_block = ""
    if state is not None:
        state_block = (
            "## 作業状態\n\n"
            f"- **状態**: {state}\n"
            f"- **状態更新日時**: {timestamp}\n"
            f"- **使用ハーネス**: {harness}\n\n"
        )
    history_block = f"## 作業履歴\n\n{history.strip()}\n\n" if history else ""
    return (
        f"# タスクリスト\n\n{state_block}{history_block}"
        f"## タスク\n\n{tasks.strip()}\n\n{retrospective}"
    )


def pause_record(timestamp: str = TIMESTAMP) -> str:
    return f"""### 中断記録: {timestamp}

- **使用ハーネス**: Codex
- **完了済みの範囲**: フック作成まで
- **未コミット変更**: なし
- **再開位置**: plan_agent.py
- **中断理由**: 今回の学習範囲を終了
"""


def make_steering(
    tmp_path: Path,
    dirname: str,
    *,
    requirements: str | None = REQUIREMENTS,
    design: str | None = "# 設計書\n",
    tasklist_text: str | None = None,
    write_tasklist: bool = True,
) -> Path:
    steering_dir = tmp_path / ".steering" / dirname
    steering_dir.mkdir(parents=True)
    if requirements is not None:
        (steering_dir / "requirements.md").write_text(requirements, encoding="utf-8")
    if design is not None:
        (steering_dir / "design.md").write_text(design, encoding="utf-8")
    if tasklist_text is None:
        tasklist_text = tasklist("complete", "- [x] done")
    if write_tasklist:
        (steering_dir / "tasklist.md").write_text(tasklist_text, encoding="utf-8")
    return steering_dir


def ids(violations: list) -> list[str]:
    return [violation.check_id for violation in violations]


def test_clean_complete_steering_has_no_violations(tmp_path: Path) -> None:
    make_steering(tmp_path, "20260728-complete")
    assert lint_mod.lint(tmp_path) == []


def test_non_dated_dirs_are_ignored(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "example",
        requirements="no issue",
        tasklist_text=tasklist("active", "- [ ] ignored"),
    )
    assert lint_mod.lint(tmp_path) == []


def test_c1_requires_three_files_for_normal_path(tmp_path: Path) -> None:
    make_steering(tmp_path, "20260728-missing", design=None, write_tasklist=False)
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C1", "C1"]
    assert "design.md" in violations[0].message
    assert "tasklist.md" in violations[1].message


def test_c1_lightweight_declaration_allows_missing_design(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-light",
        requirements=LIGHTWEIGHT_REQUIREMENTS,
        design=None,
    )
    assert lint_mod.lint(tmp_path) == []


@pytest.mark.parametrize(
    "non_declaration",
    [
        "```markdown\n- **軽量パス**: 適用\n```\n",
        "- **非軽量パス**: 適用\n",
        "例として軽量パス: 適用\n",
    ],
)
def test_c1_ignores_lightweight_like_text(
    tmp_path: Path, non_declaration: str
) -> None:
    requirements = f"# 要求内容\n\n関連Issue: {ISSUE_URL}\n{non_declaration}"
    make_steering(
        tmp_path,
        "20260728-not-lightweight",
        requirements=requirements,
        design=None,
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C1"]


def test_c2_requires_issue_url(tmp_path: Path) -> None:
    make_steering(tmp_path, "20260728-no-issue", requirements="# 要求内容\n")
    assert ids(lint_mod.lint(tmp_path)) == ["C2"]


def test_c3_active_with_incomplete_tasks_passes(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-active",
        tasklist_text=tasklist("active", "- [x] done\n- [ ] next"),
    )
    assert lint_mod.lint(tmp_path) == []


def test_c3_paused_with_incomplete_tasks_and_record_passes(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-paused",
        tasklist_text=tasklist(
            "paused",
            "- [x] done\n- [ ] next",
            history=pause_record(),
        ),
    )
    assert lint_mod.lint(tmp_path) == []


def test_c3_complete_with_incomplete_reports_once(tmp_path: Path) -> None:
    steering = make_steering(
        tmp_path,
        "20260728-invalid-complete",
        tasklist_text=tasklist("complete", "- [x] done\n- [ ] next"),
    )
    violations = lint_mod.lint(tmp_path, completion_target=steering)
    assert ids(violations) == ["C3"]
    assert "1件" in violations[0].message


def test_c3_paused_without_incomplete_requires_complete_transition(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-empty-paused",
        tasklist_text=tasklist("paused", "- [x] done", history=pause_record()),
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C3"]


def test_c3_legacy_complete_is_backward_compatible(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-legacy-complete",
        tasklist_text=tasklist(None, "- [x] done"),
    )
    assert lint_mod.lint(tmp_path) == []


def test_c3_legacy_incomplete_requires_state_classification(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-legacy-active",
        tasklist_text=tasklist(None, "- [x] done\n- [ ] next"),
    )
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C3"]
    assert "作業状態" in violations[0].message


@pytest.mark.parametrize(
    ("state_block", "message"),
    [
        (
            "## 作業状態\n\n"
            "- **状態**: unknown\n"
            f"- **状態更新日時**: {TIMESTAMP}\n"
            "- **使用ハーネス**: Codex\n",
            "未知の状態",
        ),
        (
            "## 作業状態\n\n"
            "- **状態**: active\n"
            "- **状態更新日時**: 2026-07-28\n"
            "- **使用ハーネス**: Codex\n",
            "タイムゾーン付きISO 8601",
        ),
    ],
)
def test_c3_rejects_invalid_state_metadata(
    tmp_path: Path, state_block: str, message: str
) -> None:
    text = f"# タスクリスト\n\n{state_block}\n- [ ] next\n\n{RETROSPECTIVE}"
    make_steering(tmp_path, "20260728-invalid-state", tasklist_text=text)
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C3"]
    assert message in violations[0].message


def test_c3_rejects_duplicate_state_sections(tmp_path: Path) -> None:
    duplicated = tasklist("active", "- [ ] next")
    duplicate_block = (
        "\n## 作業状態\n\n"
        "- **状態**: active\n"
        f"- **状態更新日時**: {TIMESTAMP}\n"
        "- **使用ハーネス**: Codex\n"
    )
    make_steering(
        tmp_path,
        "20260728-duplicate-state",
        tasklist_text=duplicated + duplicate_block,
    )
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C3"]
    assert "複数" in violations[0].message


def test_c4_complete_requires_retrospective(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-no-retro",
        tasklist_text=tasklist("complete", "- [x] done", retrospective=""),
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C4"]


def test_c4_complete_rejects_empty_retrospective(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-empty-retro",
        tasklist_text=tasklist(
            "complete",
            "- [x] done",
            retrospective="## 実装後の振り返り\n\n### 実装完了日\n",
        ),
    )
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C4"]
    assert "未記入" in violations[0].message


def test_c4_complete_rejects_retrospective_placeholder(tmp_path: Path) -> None:
    retrospective = "## 実装後の振り返り\n\n### 実装完了日\n\n{YYYY-MM-DD}\n"
    make_steering(
        tmp_path,
        "20260728-placeholder",
        tasklist_text=tasklist(
            "complete",
            "- [x] done",
            retrospective=retrospective,
        ),
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C4"]


def test_c4_is_deferred_for_active_state(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-active-placeholder",
        tasklist_text=tasklist(
            "active",
            "- [x] done\n- [ ] next",
            retrospective="## 実装後の振り返り\n\n{YYYY-MM-DD}\n",
        ),
    )
    assert lint_mod.lint(tmp_path) == []


def test_c5_paused_requires_matching_record(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-paused-no-record",
        tasklist_text=tasklist("paused", "- [ ] next"),
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C5"]


def test_c5_rejects_record_for_stale_timestamp(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-paused-stale",
        tasklist_text=tasklist(
            "paused",
            "- [ ] next",
            history=pause_record("2026-07-27T10:00:00+09:00"),
        ),
    )
    assert ids(lint_mod.lint(tmp_path)) == ["C5"]


def test_c5_reports_missing_record_fields(tmp_path: Path) -> None:
    history = f"""### 中断記録: {TIMESTAMP}

- **使用ハーネス**: Codex
"""
    make_steering(
        tmp_path,
        "20260728-paused-partial",
        tasklist_text=tasklist("paused", "- [ ] next", history=history),
    )
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C5"]
    assert "再開位置" in violations[0].message


def test_g1_active_target_reports_only_completion_policy(tmp_path: Path) -> None:
    target = make_steering(
        tmp_path,
        "20260728-active-target",
        tasklist_text=tasklist("active", "- [x] done\n- [ ] next"),
    )
    violations = lint_mod.lint(tmp_path, completion_target=target)
    assert ids(violations) == ["G1"]


def test_g1_paused_target_reports_only_completion_policy_when_record_valid(
    tmp_path: Path,
) -> None:
    target = make_steering(
        tmp_path,
        "20260728-paused-target",
        tasklist_text=tasklist(
            "paused",
            "- [x] done\n- [ ] next",
            history=pause_record(),
        ),
    )
    violations = lint_mod.lint(tmp_path, completion_target=target)
    assert ids(violations) == ["G1"]


def test_c5_uses_latest_pause_record_when_timestamps_match(tmp_path: Path) -> None:
    incomplete_latest = f"""### 中断記録: {TIMESTAMP}

- **使用ハーネス**: Codex
- **再開位置**: next
"""
    steering = make_steering(
        tmp_path,
        "20260728-latest-pause",
        tasklist_text=tasklist(
            "paused",
            "- [x] done\n- [ ] next",
            history=f"{pause_record()}\n{incomplete_latest}",
        ),
    )
    violations = lint_mod.lint(tmp_path)
    assert ids(violations) == ["C5"]
    assert violations[0].directory == steering.name


def test_completion_target_passes_with_historical_paused_steering(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260727-paused-history",
        tasklist_text=tasklist(
            "paused",
            "- [x] done\n- [ ] later",
            history=pause_record(),
        ),
    )
    target = make_steering(tmp_path, "20260728-complete-target")
    assert lint_mod.lint(tmp_path, completion_target=target) == []


def test_c3_is_called_once_per_directory_in_completion_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = make_steering(tmp_path, "20260728-target")
    calls: list[str] = []
    original = lint_mod.check_task_state

    def counted(steering_dir: Path, context: object | None = None) -> list:
        calls.append(steering_dir.name)
        return original(steering_dir, context)

    monkeypatch.setattr(lint_mod, "check_task_state", counted)
    assert lint_mod.lint(tmp_path, completion_target=target) == []
    assert calls == ["20260728-target"]


def test_lint_reads_each_tasklist_once_in_completion_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = make_steering(tmp_path, "20260728-single-read")
    tasklist_path = target / "tasklist.md"
    reads = 0
    original = Path.read_text

    def counted(
        path: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        nonlocal reads
        if path == tasklist_path:
            reads += 1
        return original(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", counted)
    assert lint_mod.lint(tmp_path, completion_target=target) == []
    assert reads == 1


def test_resolve_completion_target_uses_latest_dated_directory(tmp_path: Path) -> None:
    make_steering(tmp_path, "20260727-old")
    expected = make_steering(tmp_path, "20260728-new")
    make_steering(tmp_path, "example")
    assert lint_mod.resolve_completion_target(tmp_path, "latest") == expected


def run_cli(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_PATH), str(project_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_normal_and_completion_profiles(tmp_path: Path) -> None:
    make_steering(
        tmp_path,
        "20260728-active",
        tasklist_text=tasklist("active", "- [ ] next"),
    )
    assert run_cli(tmp_path).returncode == 0
    completion = run_cli(tmp_path, "--require-complete")
    assert completion.returncode == 1
    assert "[G1]" in completion.stdout
    assert "[C3]" not in completion.stdout


def test_cli_rejects_unknown_completion_target(tmp_path: Path) -> None:
    make_steering(tmp_path, "20260728-existing")
    result = run_cli(tmp_path, "--require-complete", "20260728-missing")
    assert result.returncode == 2
    assert "見つかりません" in result.stderr


def test_find_incomplete_tasks_includes_fenced_examples() -> None:
    assert lint_mod.find_incomplete_tasks("```\n- [ ] example\n```\n") == ["example"]

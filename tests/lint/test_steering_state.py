"""steering_state.pyの状態遷移と非変更保証を検証する。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "steering_state.py"
TIMESTAMP = "2026-07-28T10:00:00+09:00"
PAUSE_REQUIRED_LABELS = (
    "使用ハーネス",
    "完了済みの範囲",
    "未コミット変更",
    "再開位置",
    "中断理由",
)


def load_module() -> ModuleType:
    scripts = str(SCRIPT_PATH.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("steering_state", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


state_mod = load_module()

RETROSPECTIVE = """## 実装後の振り返り

### 実装完了日

2026-07-28

### 学んだこと

- 状態遷移を検証した
"""


def tasklist(state: str | None, tasks: str, *, retrospective: str = RETROSPECTIVE) -> str:
    state_block = ""
    if state is not None:
        state_block = (
            "## 作業状態\n\n"
            f"- **状態**: {state}\n"
            f"- **状態更新日時**: {TIMESTAMP}\n"
            "- **使用ハーネス**: Codex\n\n"
        )
    return (
        f"# タスクリスト\n\n{state_block}"
        "## 作業履歴\n\n_記録なし_\n\n"
        f"## タスク\n\n{tasks.strip()}\n\n{retrospective}"
    )


def pause(text: str, timestamp: str = TIMESTAMP) -> str:
    return state_mod.pause_text(
        text,
        harness="Codex",
        completed_scope="セットアップまで",
        uncommitted_changes="なし",
        resume_at="plan_agent.py",
        reason="今回の学習範囲を終了",
        timestamp=timestamp,
    )


def test_pause_adds_state_and_complete_record() -> None:
    updated = pause(tasklist("active", "- [x] done\n- [ ] next"))
    assert "- **状態**: paused" in updated
    assert f"### 中断記録: {TIMESTAMP}" in updated
    for label in PAUSE_REQUIRED_LABELS:
        assert f"- **{label}**:" in updated
    assert "_記録なし_" not in updated


def test_pause_migrates_legacy_incomplete_tasklist() -> None:
    updated = pause(tasklist(None, "- [x] done\n- [ ] next"))
    assert "- **状態**: paused" in updated
    assert "### 中断記録:" in updated


@pytest.mark.parametrize("state", ["paused", "complete"])
def test_pause_rejects_invalid_source_state(state: str) -> None:
    original = tasklist(state, "- [x] done\n- [ ] next")
    with pytest.raises(state_mod.TransitionError):
        pause(original)


def test_pause_rejects_tasklist_without_incomplete_tasks() -> None:
    with pytest.raises(state_mod.TransitionError):
        pause(tasklist("active", "- [x] done"))


def test_resume_paused_adds_record_and_returns_active() -> None:
    paused = pause(tasklist("active", "- [x] done\n- [ ] next"))
    updated = state_mod.resume_text(
        paused,
        harness="Codex",
        resume_at="plan_agent.py",
        reason="学習を再開",
        timestamp="2026-07-29T09:00:00+09:00",
    )
    assert "- **状態**: active" in updated
    assert "### 中断記録:" in updated
    assert "### 再開記録: 2026-07-29T09:00:00+09:00" in updated
    assert "- **再開理由**: 学習を再開" in updated


def test_resume_complete_reopens_after_gate_failure() -> None:
    updated = state_mod.resume_text(
        tasklist("complete", "- [x] done"),
        harness="Codex",
        resume_at="失敗したテストの修正",
        reason="最終品質ゲートが失敗",
        timestamp="2026-07-29T09:00:00+09:00",
    )
    assert "- **状態**: active" in updated
    assert "最終品質ゲートが失敗" in updated


def test_resume_rejects_active_state() -> None:
    with pytest.raises(state_mod.TransitionError):
        state_mod.resume_text(
            tasklist("active", "- [ ] next"),
            harness="Codex",
            resume_at="next",
            reason="再開",
            timestamp=TIMESTAMP,
        )


def test_resume_rejects_incomplete_pause_record() -> None:
    text = tasklist("paused", "- [x] done\n- [ ] next")
    partial_record = (
        f"### 中断記録: {TIMESTAMP}\n\n"
        "- **使用ハーネス**: Codex\n"
        "- **再開位置**: next\n"
    )
    text = text.replace("_記録なし_", partial_record)
    with pytest.raises(state_mod.TransitionError, match="必須項目"):
        state_mod.resume_text(
            text,
            harness="Codex",
            resume_at="next",
            reason="再開",
            timestamp=TIMESTAMP,
        )


def test_complete_changes_valid_active_tasklist() -> None:
    updated = state_mod.complete_text(
        tasklist("active", "- [x] done"),
        harness="Codex",
        timestamp=TIMESTAMP,
    )
    assert "- **状態**: complete" in updated


def test_complete_rejects_incomplete_task_without_modifying_source() -> None:
    original = tasklist("active", "- [x] done\n- [ ] next")
    with pytest.raises(state_mod.TransitionError):
        state_mod.complete_text(original, harness="Codex", timestamp=TIMESTAMP)
    assert "- **状態**: active" in original


def test_complete_rejects_retrospective_placeholder() -> None:
    text = tasklist(
        "active",
        "- [x] done",
        retrospective="## 実装後の振り返り\n\n{YYYY-MM-DD}\n",
    )
    with pytest.raises(state_mod.TransitionError):
        state_mod.complete_text(text, harness="Codex", timestamp=TIMESTAMP)


def test_complete_rejects_empty_retrospective() -> None:
    text = tasklist(
        "active",
        "- [x] done",
        retrospective="## 実装後の振り返り\n\n### 実装完了日\n",
    )
    with pytest.raises(state_mod.TransitionError, match="未記入"):
        state_mod.complete_text(text, harness="Codex", timestamp=TIMESTAMP)


def test_complete_rejects_duplicate_state_sections_without_modifying_source() -> None:
    original = tasklist("active", "- [x] done")
    duplicate = (
        "\n## 作業状態\n\n"
        "- **状態**: active\n"
        f"- **状態更新日時**: {TIMESTAMP}\n"
        "- **使用ハーネス**: Codex\n"
    )
    text = original + duplicate
    with pytest.raises(state_mod.TransitionError, match="複数"):
        state_mod.complete_text(text, harness="Codex", timestamp=TIMESTAMP)
    assert text == original + duplicate


def make_project(tmp_path: Path, dirname: str = "20260728-state") -> Path:
    steering = tmp_path / ".steering" / dirname
    steering.mkdir(parents=True)
    (steering / "tasklist.md").write_text(
        tasklist("active", "- [x] done\n- [ ] next"),
        encoding="utf-8",
    )
    return steering


def test_resolve_tasklist_uses_latest_dated_directory(tmp_path: Path) -> None:
    make_project(tmp_path, "20260727-old")
    expected = make_project(tmp_path, "20260728-new") / "tasklist.md"
    example = tmp_path / ".steering" / "example"
    example.mkdir()
    (example / "tasklist.md").write_text("ignored", encoding="utf-8")
    assert state_mod.resolve_tasklist(tmp_path, None) == expected


def test_resolve_tasklist_accepts_explicit_dated_directory(tmp_path: Path) -> None:
    expected = make_project(tmp_path, "20260728-explicit") / "tasklist.md"
    assert state_mod.resolve_tasklist(tmp_path, "20260728-explicit") == expected


def test_resolve_tasklist_rejects_explicit_non_dated_directory(tmp_path: Path) -> None:
    make_project(tmp_path, "example")
    with pytest.raises(state_mod.TransitionError):
        state_mod.resolve_tasklist(tmp_path, "example")


def test_resolve_tasklist_rejects_tasklist_outside_project_without_modifying_it(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = make_project(tmp_path / "outside")
    target = outside / "tasklist.md"
    original = target.read_text(encoding="utf-8")
    with pytest.raises(state_mod.TransitionError):
        state_mod.resolve_tasklist(project, str(target))
    assert target.read_text(encoding="utf-8") == original


def test_cli_rejects_latest_external_symlink_without_modifying_target(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    make_project(project, "20260728-inside")
    outside = make_project(tmp_path / "outside")
    target = outside / "tasklist.md"
    original = target.read_text(encoding="utf-8")
    (project / ".steering" / "99999999-external").symlink_to(
        outside,
        target_is_directory=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-root",
            str(project),
            "pause",
            "--harness",
            "Codex",
            "--completed-scope",
            "境界検査前",
            "--uncommitted-changes",
            "なし",
            "--resume-at",
            "境界検査",
            "--reason",
            "回帰テスト",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "対象は.steering直下の日付付きtasklistに限ります" in result.stderr
    assert target.read_text(encoding="utf-8") == original


def test_cli_error_does_not_modify_tasklist(tmp_path: Path) -> None:
    steering = make_project(tmp_path)
    target = steering / "tasklist.md"
    original = target.read_text(encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-root",
            str(tmp_path),
            "complete",
            "--harness",
            "Codex",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "未完了タスク" in result.stderr
    assert target.read_text(encoding="utf-8") == original


def test_write_transition_replace_failure_keeps_original_and_cleans_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "tasklist.md"
    target.write_text("original\n", encoding="utf-8")

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(state_mod.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        state_mod.write_transition(target, "updated\n")
    assert target.read_text(encoding="utf-8") == "original\n"
    assert list(tmp_path.glob(".tasklist.md.*")) == []

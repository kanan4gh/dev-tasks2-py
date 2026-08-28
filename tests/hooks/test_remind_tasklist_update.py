"""remind_tasklist_update.py(PostToolUseフック)のユニットテスト。"""

import importlib.util
import json
from pathlib import Path

HOOK_PATH = Path(__file__).parents[2] / ".claude" / "hooks" / "remind_tasklist_update.py"

spec = importlib.util.spec_from_file_location("remind_tasklist_update", HOOK_PATH)
assert spec is not None and spec.loader is not None
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def make_active_steering(tmp_path: Path) -> None:
    d = tmp_path / ".steering" / "20260709-foo"
    d.mkdir(parents=True)
    (d / "tasklist.md").write_text("- [ ] 未完了タスク\n", encoding="utf-8")


def edit_event(file_path: str) -> dict[str, object]:
    return {"tool_input": {"file_path": file_path}}


def state_path(tmp_path: Path) -> Path:
    return tmp_path / hook.STATE_FILE


def read_count(tmp_path: Path) -> int:
    return json.loads(state_path(tmp_path).read_text(encoding="utf-8"))["count"]


def test_check_counts_up_below_threshold(tmp_path: Path) -> None:
    make_active_steering(tmp_path)
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is None
    assert read_count(tmp_path) == 1


def test_check_steering_edit_resets_counter(tmp_path: Path) -> None:
    make_active_steering(tmp_path)
    hook.save_count(state_path(tmp_path), 3)
    result = hook.check(edit_event("/repo/.steering/20260709-foo/tasklist.md"), tmp_path)
    assert result is None
    assert read_count(tmp_path) == 0


def test_check_threshold_reached_reminds_and_resets(tmp_path: Path) -> None:
    make_active_steering(tmp_path)
    hook.save_count(state_path(tmp_path), hook.REMIND_THRESHOLD - 1)
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is not None
    assert "tasklist.md" in result["hookSpecificOutput"]["additionalContext"]
    assert read_count(tmp_path) == 0


def test_check_no_active_steering_does_not_count(tmp_path: Path) -> None:
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is None
    assert not state_path(tmp_path).exists()


def test_check_completed_steering_does_not_count(tmp_path: Path) -> None:
    d = tmp_path / ".steering" / "20260709-foo"
    d.mkdir(parents=True)
    (d / "tasklist.md").write_text("- [x] 完了済み\n", encoding="utf-8")
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is None
    assert not state_path(tmp_path).exists()


def test_check_non_dated_steering_dir_is_not_active(tmp_path: Path) -> None:
    # example/ 等のサンプルディレクトリはアクティブ作業とみなさない
    d = tmp_path / ".steering" / "example"
    d.mkdir(parents=True)
    (d / "tasklist.md").write_text("- [ ] サンプルタスク\n", encoding="utf-8")
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is None
    assert not state_path(tmp_path).exists()


def test_check_missing_file_path_returns_none(tmp_path: Path) -> None:
    make_active_steering(tmp_path)
    assert hook.check({"tool_input": {}}, tmp_path) is None
    assert hook.check({}, tmp_path) is None


def test_load_count_broken_state_returns_zero(tmp_path: Path) -> None:
    p = state_path(tmp_path)
    p.parent.mkdir(parents=True)
    p.write_text("not json", encoding="utf-8")
    assert hook.load_count(p) == 0


def test_load_count_negative_value_returns_zero(tmp_path: Path) -> None:
    p = state_path(tmp_path)
    p.parent.mkdir(parents=True)
    p.write_text('{"count": -2}', encoding="utf-8")
    assert hook.load_count(p) == 0


def test_check_recovers_after_broken_state(tmp_path: Path) -> None:
    make_active_steering(tmp_path)
    p = state_path(tmp_path)
    p.parent.mkdir(parents=True)
    p.write_text("{broken", encoding="utf-8")
    result = hook.check(edit_event("/repo/src/foo.py"), tmp_path)
    assert result is None
    assert read_count(tmp_path) == 1

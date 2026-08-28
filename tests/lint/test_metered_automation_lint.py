"""Tests for the metered automation policy lint."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

LINT_PATH = Path(__file__).parents[2] / "scripts" / "metered_automation_lint.py"


def load_lint_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("metered_automation_lint", LINT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lint = load_lint_module()


def policy_data(
    *, include_paths: list[str] | None = None, exclude_paths: list[str] | None = None
) -> dict[str, Any]:
    return {
        "version": 1,
        "signatures": [
            {"id": "short", "command": "claude", "arguments": ["-p"]},
            {"id": "codex", "command": "codex", "arguments": ["exec"]},
        ],
        "include_paths": include_paths or ["active"],
        "exclude_paths": exclude_paths or [".steering", "docs/ideas"],
        "extensions": [".md", ".py"],
    }


def write_policy(root: Path, data: dict[str, Any] | None = None) -> Path:
    path = root / "policy.json"
    path.write_text(json.dumps(data or policy_data()), encoding="utf-8")
    return path


def scan(root: Path, data: dict[str, Any] | None = None) -> list[Any]:
    policy = lint.load_policy(write_policy(root, data))
    return lint.scan_repository(root, policy)


def test_scan_detects_shell_string(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "run.md").write_text("`claude -p prompt`", encoding="utf-8")
    violations = scan(tmp_path)
    assert [(item.policy_id, item.line) for item in violations] == [("short", 1)]


def test_scan_detects_python_argument_array(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "run.py").write_text(
        "import subprocess\nsubprocess.run(['claude', '-p', 'prompt'])\n", encoding="utf-8"
    )
    assert any(item.policy_id == "short" for item in scan(tmp_path))


def test_scan_detects_multiline_array(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "run.py").write_text(
        "import subprocess\nsubprocess.run([\n    'codex',\n    'exec',\n    'prompt',\n])\n",
        encoding="utf-8",
    )
    assert any(item.policy_id == "codex" for item in scan(tmp_path))


def test_scan_detects_constant_string_concatenation(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "run.py").write_text(
        "import os\ncommand = 'claude' + ' -p prompt'\nos.system(command)\n", encoding="utf-8"
    )
    assert any(item.policy_id == "short" for item in scan(tmp_path))


def test_scan_allows_interactive_cli_descriptions(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "guide.md").write_text(
        "Use the Claude interactive CLI or run Codex interactively.", encoding="utf-8"
    )
    assert scan(tmp_path) == []


def test_scan_does_not_walk_steering_or_ideas_outside_includes(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "safe.md").write_text("interactive only", encoding="utf-8")
    steering = tmp_path / ".steering"
    steering.mkdir()
    (steering / "history.md").write_text("claude -p historical", encoding="utf-8")
    ideas = tmp_path / "docs" / "ideas"
    ideas.mkdir(parents=True)
    (ideas / "draft.md").write_text("codex exec historical", encoding="utf-8")
    assert scan(tmp_path) == []


def test_scan_honors_specific_excluded_fixture(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "fixture.py").write_text("claude -p", encoding="utf-8")
    data = policy_data(exclude_paths=["active/fixture.py", ".steering"])
    assert scan(tmp_path, data) == []


def test_scan_skips_nested_worktree_checkouts(tmp_path: Path) -> None:
    # 除外と過剰除外を1ケースで確認する(片方だけ通って安心しないため)。
    # 入れ子側は実際の誘因ファイルに合わせて .py に置き、Python解析経路も通す。
    commands = tmp_path / ".claude" / "commands"
    commands.mkdir(parents=True)
    (commands / "run.md").write_text("`claude -p prompt`", encoding="utf-8")
    nested = tmp_path / ".claude" / "worktrees" / "feature+x" / "tests" / "lint"
    nested.mkdir(parents=True)
    (nested / "fixture.py").write_text('run(["codex", "exec", "task"])', encoding="utf-8")

    data = policy_data(include_paths=[".claude"], exclude_paths=[".claude/worktrees"])
    violations = scan(tmp_path, data)

    assert [violation.path for violation in violations] == [Path(".claude/commands/run.md")]


def test_repository_policy_scans_active_surfaces_but_not_nested_worktrees() -> None:
    # メンバーシップではなく実際の走査結果で固定する。exclude_paths に `.claude/commands`
    # のような指示面を足すと、このテストが落ちる(過剰除外ガードは1階層しか審査しないため、
    # 複数階層のディレクトリ除外を機械的に捕捉できるのはこの経路だけ)。
    root = LINT_PATH.parents[1]
    policy = lint.load_policy(LINT_PATH.with_name("metered_automation_policy.json"))

    targets = {path.relative_to(root) for path in lint.iter_target_files(root, policy)}

    assert Path(".claude/commands/add-feature.md") in targets
    assert not [path for path in targets if path.parts[:2] == (".claude", "worktrees")]


def test_load_policy_rejects_overly_broad_exclude(tmp_path: Path) -> None:
    path = write_policy(tmp_path, policy_data(exclude_paths=["docs"]))
    with pytest.raises(lint.PolicyError, match="overly broad"):
        lint.load_policy(path)


def test_load_policy_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(lint.PolicyError, match="cannot read policy"):
        lint.load_policy(path)


def test_scan_fails_closed_for_python_syntax_error(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()
    (active / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    with pytest.raises(lint.PolicyError, match="cannot parse Python"):
        scan(tmp_path)


def test_scan_fails_closed_when_include_is_missing(tmp_path: Path) -> None:
    policy = lint.load_policy(write_policy(tmp_path))
    with pytest.raises(lint.PolicyError, match="include path does not exist"):
        lint.scan_repository(tmp_path, policy)


def test_scan_fails_closed_for_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = tmp_path / "active"
    active.mkdir()
    target = active / "guide.md"
    target.write_text("interactive only", encoding="utf-8")
    policy = lint.load_policy(write_policy(tmp_path))
    original_read_text = Path.read_text

    def fail_for_target(
        path: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if path == target:
            raise OSError("denied")
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_for_target)
    with pytest.raises(lint.PolicyError, match="cannot read active/guide.md"):
        lint.scan_repository(tmp_path, policy)


def test_main_returns_one_for_violation_and_zero_for_clean_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active = tmp_path / "active"
    active.mkdir()
    target = active / "guide.md"
    target.write_text("claude -p prompt", encoding="utf-8")
    policy_path = write_policy(tmp_path)
    assert lint.main(["--root", str(tmp_path), "--policy", str(policy_path)]) == 1
    assert "[short] active/guide.md:1" in capsys.readouterr().err
    target.write_text("interactive only", encoding="utf-8")
    assert lint.main(["--root", str(tmp_path), "--policy", str(policy_path)]) == 0
    assert "passed" in capsys.readouterr().out

"""全ハーネスでStopフックを廃止し、非強制リマインドだけを維持する契約。"""

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_claude_has_no_stop_hook_and_keeps_post_tool_use_reminder() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    assert "Stop" not in hooks
    assert "PostToolUse" in hooks
    commands = [
        hook["command"]
        for group in hooks["PostToolUse"]
        for hook in group["hooks"]
    ]
    assert any("remind_tasklist_update.py" in command for command in commands)


def test_codex_has_no_hook_registration_or_stop_script() -> None:
    assert not (ROOT / ".codex" / "hooks.json").exists()
    assert not (ROOT / ".codex" / "hooks" / "check_tasklist_complete.py").exists()


def test_kiro_cli_has_no_stop_hook_or_stop_script() -> None:
    config = json.loads((ROOT / ".kiro" / "agents" / "sdd.json").read_text(encoding="utf-8"))
    assert "hooks" not in config
    assert not (ROOT / ".kiro" / "hooks" / "check_tasklist_complete.py").exists()
    assert not (ROOT / ".kiro" / "hooks" / "state").exists()


def test_no_adapter_contains_stop_hook_implementation() -> None:
    for adapter in (".claude", ".codex", ".kiro"):
        assert not (ROOT / adapter / "hooks" / "check_tasklist_complete.py").exists()

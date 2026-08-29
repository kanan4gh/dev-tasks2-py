"""Kiroアダプタの構造と中立手順参照を検証する。"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
KIRO = ROOT / ".kiro"

SKILL_PROCEDURES = {
    "steering": "docs/procedures/steering.md",
    "add-feature": "docs/procedures/add-feature.md",
    "setup-project": "docs/procedures/setup-project.md",
    "review-docs": "docs/procedures/review-docs.md",
    "distill": "docs/procedures/distill.md",
}

AGENT_PROCEDURES = {
    "doc-reviewer.md": "docs/procedures/review-docs.md",
    "implementation-validator.md": "docs/procedures/validate-implementation.md",
}


def frontmatter(text: str) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None
    return match.group(1)


def field(metadata: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", metadata, re.MULTILINE)
    assert match is not None
    return match.group(1).strip()


def test_all_kiro_skills_have_valid_metadata_and_procedure_reference() -> None:
    for skill_name, procedure in SKILL_PROCEDURES.items():
        path = KIRO / "skills" / skill_name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        assert field(metadata, "name") == skill_name
        assert 0 < len(field(metadata, "description")) <= 1024
        assert procedure in text
        assert "Codexアダプタ" not in text


def test_steering_and_add_feature_cover_kiro_control_points() -> None:
    steering = (KIRO / "skills" / "steering" / "SKILL.md").read_text(encoding="utf-8")
    add_feature = (KIRO / "skills" / "add-feature" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "再開依頼" in steering
    assert "使用ハーネス欄" in steering
    assert "唯一の承認ゲート" in add_feature
    assert "implementation-validator.md" in add_feature


def test_ide_subagents_are_read_only_and_reference_neutral_procedures() -> None:
    for filename, procedure in AGENT_PROCEDURES.items():
        text = (KIRO / "agents" / filename).read_text(encoding="utf-8")
        metadata = frontmatter(text)
        assert field(metadata, "name") == filename.removesuffix(".md")
        assert field(metadata, "tools") == "[read]"
        assert procedure in text


def test_cli_sdd_agent_inherits_core_resources_and_configures_controls() -> None:
    config = json.loads((KIRO / "agents" / "sdd.json").read_text(encoding="utf-8"))
    assert config["name"] == "sdd"
    assert "resources" not in config
    assert config["tools"] == ["read", "write", "shell", "subagent"]
    assert config["allowedTools"] == ["read"]
    assert "hooks" not in config
    assert not (KIRO / "hooks" / "check_tasklist_complete.py").exists()


def test_readme_documents_ide_cli_trust_permissions_and_differences() -> None:
    readme = (KIRO / "README.md").read_text(encoding="utf-8")
    for expected in (
        "## Kiro IDE",
        "## Kiro CLI",
        "Kiro CLI 2.7.0以降",
        "chat.disableInheritingDefaultResources=false",
        "kiro-cli agent validate --path .kiro/agents/sdd.json",
        "kiro-cli --agent sdd",
        "## 実機受け入れ",
        "未完了の`active` fixture",
        "終了ブロックなく完了",
        "状態遷移CLIと通常／完了lint",
        "Stop登録がない",
        "trust",
        "write / shell",
        "## IDEとCLIの差分",
        "| Stopフック | なし | なし |",
    ):
        assert expected in readme


def test_readme_uses_replaceable_fixture_values() -> None:
    readme = (KIRO / "README.md").read_text(encoding="utf-8")
    acceptance = (ROOT / "docs" / "procedures" / "harness-acceptance.md").read_text(
        encoding="utf-8"
    )
    assert "requirements.mdへ検証用Issue URL" in acceptance
    assert "project-uroboros-neo" not in readme
    assert "2026-07-15の実機結果" not in readme

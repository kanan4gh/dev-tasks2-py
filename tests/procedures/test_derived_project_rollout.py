"""Structural contracts for the derived-project rollout procedure.

派生固有差分(dev-tasks2-py): 正典の同名ファイルにある「展開候補台帳」の検査6件は、
platform-harness 自身の `docs/derived-projects.md` を対象とするため取り込んでいない
(GitHub issue #26 の同期manifestで Exclude に分類)。手順書の契約検査だけを保持する。
platform-harness の release を同期する際は、この差分を温存すること。
"""

from pathlib import Path

ROOT = Path(__file__).parents[2]
PROCEDURE = ROOT / "docs" / "procedures" / "derived-project-rollout.md"


def procedure_text() -> str:
    return PROCEDURE.read_text(encoding="utf-8")


def outfit_manifest() -> dict[str, str]:
    section = procedure_text().split("### 初期manifest", maxsplit=1)[1].split(
        "### 移行順序", maxsplit=1
    )[0]
    lines = [line for line in section.splitlines() if line.startswith("|")]
    return {
        cells[0]: cells[1]
        for line in lines[2:]
        if len(cells := [cell.strip() for cell in line.strip("|").split("|")]) == 2
    }


def test_procedure_defines_unit_preflight_and_manifest() -> None:
    text = procedure_text()
    assert "1 platform-harness release × 1 GitHub remote × 1 feature branch × 1 PR" in text
    for value in (
        "対象remote",
        "default branch / OID",
        "dirty / ahead / behind",
        "同期元: platform-harness",
        "作業隔離",
    ):
        assert value in text
    for category in (
        "Preserve",
        "Replace from canonical",
        "Add from canonical",
        "Merge manually",
        "Exclude",
    ):
        assert category in text


def test_preflight_fixes_remote_freshness_and_concurrency_contracts() -> None:
    text = procedure_text()
    for contract in (
        "archive / template状態",
        "remote-tracking refをfetchした日時・方法とcommit OID",
        "active Issue / PR / branch",
        "同期元platform-harness release tagとcommit",
        "clean worktreeまたはclean clone",
    ):
        assert contract in text
    assert "G0で既存PRをマージする、破棄する、新移行へ引き継ぐ" in text
    assert "引継ぎを選んだ後のファイル単位の統合方法だけをG2" in text


def test_procedure_defines_bootstrap_authority_and_handoff() -> None:
    text = procedure_text()
    assert "旧Claude専用ハーネスの通常実行者はClaude Code" in text
    assert "ユーザーがG0とG1で承認した本展開手順" in text
    assert "bootstrap executor" in text
    assert "旧ハーネスを実行したことにしない" in text
    assert "Authority handoff" in text
    assert "新しい`AGENTS.md`と対象エージェント用アダプタ" in text


def test_procedure_protects_dirty_worktrees_and_target_history() -> None:
    text = procedure_text()
    assert "dirtyな既存checkoutを清掃・stash・上書きして移行を始めない" in text
    assert "clean worktreeまたはclean clone" in text
    assert "対象リポジトリ内に独立Issue・steering・feature branch" in text
    assert "プロダクト固有層、技術スタック固有層" in text


def test_outfit_pilot_defines_legacy_state_isolation_and_mapping() -> None:
    text = procedure_text()
    assert "UPDATED: 2026-05-27" in text
    assert "`AGENTS.md`、中立`docs/procedures/`、`.agents/`、`.codex/`、`.kiro/`" in text
    assert "feature/sync-platform-harness-v1-2-0" in text
    assert "/Users/akiraishihara/aiwork/operated/outfit-studio" in text
    assert "preflight・編集・同期対象から除外" in text
    assert "open PR #22" in text
    assert "状態は`on-hold`" in text
    assert "`.devcontainer/devcontainer-lock.json`" in text
    assert "既存テスト中のCodexサービスをCodex CLIアダプタと同じ概念として置換しない" in text
    isolation = text.split("### 隔離戦略", maxsplit=1)[1].split("### 初期manifest", maxsplit=1)[0]
    assert isolation.index("独立Issueを作成") < isolation.index("feature/sync-platform-harness")
    assert isolation.index("feature/sync-platform-harness") < isolation.index("Issue URLを含む")


def test_outfit_manifest_defines_concrete_non_overlapping_boundaries() -> None:
    text = procedure_text()
    for contract in (
        "`src/`、`tests/conftest.py`、`tests/integration/`、`tests/unit/`",
        "`docs/{architecture,development-guidelines,functional-design,glossary,product-requirements,repository-structure}.md`",
        "`CLAUDE.md`の「汎用層」「補足：この文書の運用方法」section",
        "`CLAUDE.md`の「プロジェクトメモリ」section",
        "`.claude/commands/{add-feature,review-docs,setup-project}.md`",
        "`.claude/skills/steering/`",
        "`AGENTS.md`、`docs/procedures/`",
        "`.claude/skills/`のうち`steering/`以外",
        "再生成可能な`.devcontainer/devcontainer-lock.json`",
        "各具体pathまたは明示した文書sectionをちょうど1分類",
    ):
        assert contract in text

    assert outfit_manifest() == {
        "Preserve": "`src/`、`tests/conftest.py`、`tests/integration/`、`tests/unit/`、"
        "`docs/{architecture,development-guidelines,functional-design,glossary,"
        "product-requirements,repository-structure}.md`、`CLAUDE.md`の"
        "「プロダクト固有層」「技術スタック固有層」section",
        "Replace from canonical": "`CLAUDE.md`の「汎用層」「補足：この文書の運用方法」section、"
        "`.claude/commands/{add-feature,review-docs,setup-project}.md`、"
        "`.claude/skills/steering/`と旧steering templates",
        "Add from canonical": "`AGENTS.md`、`docs/procedures/`とtemplates、`.agents/skills/`、"
        "`.codex/`、`.kiro/`、"
        "`scripts/{steering_lint,steering_state,metered_automation_lint,"
        "local_quality_gate}.py`、対応する`tests/{adapters,hooks,lint,procedures,"
        "scripts}/`のうち対象に存在しないpath",
        "Merge manually": "`CLAUDE.md`の「プロジェクトメモリ」section、"
        "`.claude/settings.json`、`.claude/README.md`、`.claude/agents/`、"
        "`.claude/skills/`のうち`steering/`以外、`.claude/hooks/*.py`、"
        "`docs/ideas/harness-engineering.md`、`.gitignore`、`pyproject.toml`、"
        "`uv.lock`、`.devcontainer/devcontainer.json`、"
        "`.devcontainer/postCreate.sh`、`.mcp.json.example`",
        "Exclude": "`.coverage`、`.playwright-mcp/`、`.claude/hooks/state/`、"
        "`**/__pycache__/`、"
        "再生成可能な`.devcontainer/devcontainer-lock.json`",
    }


def test_procedure_requires_local_and_interactive_validation_without_paid_automation() -> None:
    text = procedure_text()
    assert "local_quality_gate.py" in text
    assert "人がIDEまたは対話型CLI受け入れ" in text
    assert "GitHub Actions自動runと有料LLM headless mode起動が0件" in text
    assert "従量課金型headless mode" in text
    assert "`.kiro/hooks/state/`" not in outfit_manifest()["Add from canonical"]


def test_platform_issue_does_not_modify_derived_project() -> None:
    text = procedure_text()
    assert "outfit-studio本体を変更しない" in text
    assert "実展開はoutfit-studio側の独立Issue" in text

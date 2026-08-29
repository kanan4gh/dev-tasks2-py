"""Structural tests for optional, manually triggered GitHub Actions."""

from pathlib import Path
import re

ROOT = Path(__file__).parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "steering-lint.yml"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_only() -> None:
    text = workflow_text()
    assert re.search(r"(?m)^\s{2}workflow_dispatch:\s*$", text)
    assert not re.search(r"(?m)^\s{2}(pull_request|push|schedule):\s*$", text)


def test_workflow_calls_single_local_quality_gate_entrypoint() -> None:
    text = workflow_text()
    assert text.count("scripts/local_quality_gate.py") == 1
    assert "run: uv run pytest" not in text
    assert "run: uv run ruff" not in text
    assert "run: uv run basedpyright" not in text
    assert "run: python3 scripts/steering_lint.py" not in text


def test_workflow_warns_that_it_is_optional_and_manual() -> None:
    first_line = workflow_text().splitlines()[0].lower()
    assert "optional" in first_line
    assert "manual" in first_line


def test_pr_template_requires_local_and_interactive_evidence() -> None:
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    assert "scripts/local_quality_gate.py" in text
    assert "実行日時" in text
    assert "対話型実機受け入れ" in text
    assert "記録へのリンク" in text
    assert "GitHub Actionsを必須" in text

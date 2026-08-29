"""Structural contract tests for the distill procedure."""

from pathlib import Path

ROOT = Path(__file__).parents[2]
PROCEDURE = ROOT / "docs" / "procedures" / "distill.md"


def procedure_text() -> str:
    return PROCEDURE.read_text(encoding="utf-8")


def test_defines_planned_and_actual_two_stage_overlap_checks() -> None:
    text = procedure_text()
    assert "環流PR計画" in text
    assert "第1段: 予定変更ファイル集合の検査" in text
    assert "第2段: Git実変更ファイル集合の検査" in text
    assert "--set issue-a=AGENTS.md" in text
    assert "--base origin/main" in text
    assert "--ref issue-a=feature/a" in text


def test_requires_empty_intersections_and_three_resolution_methods() -> None:
    text = procedure_text()
    assert "activeなPR計画が2件以上ある場合、全PR組合せの積集合が空集合の場合だけ合格" in text
    assert "activeなfeature branchが2件以上ある場合、実集合も全PR組合せの積集合が空集合の場合だけ合格" in text
    assert "**統合**" in text
    assert "**再分割**" in text
    assert "**共通前提の先行正典化**" in text
    assert "スタックPRやマージ順固定" in text


def test_uses_stable_identifiers_and_real_pr_numbers() -> None:
    text = procedure_text()
    assert "安定識別子はIssue URLとbranch名" in text
    assert "まだ存在しないPR番号を予測" in text
    assert "実在するPR番号" in text
    assert "単独で検証・レビュー・ロールバック" in text
    assert "任意順でマージ可能" in text


def test_defines_canonical_sync_order_and_record() -> None:
    text = procedure_text()
    expected_order = [
        "派生プロジェクトの振り返り",
        "distillで環流候補へ分類",
        "platform-harnessでプロジェクト固有値を除去して中立化・実装",
        "platform-harnessのPRをマージしてrelease",
        "リリース済み正典を派生プロジェクトへ同期",
        "派生側でローカル品質ゲートと必要な対話型受け入れ",
    ]
    positions = [text.index(item, text.index("### 8.")) for item in expected_order]
    assert positions == sorted(positions)
    assert "release tagまたはcommit" in text
    assert "テンプレート化を兼ねる" in text
    assert "残したプロダクト固有層・技術スタック固有層・アダプタ差分" in text


def test_keeps_paid_or_remote_automation_out_of_required_path() -> None:
    text = procedure_text()
    boundary = text[text.index("### 7.") :]
    assert "GitHub Actionsの自動run、GitHub API、LLM headless modeを必須経路にしない" in boundary
    assert "ローカルGit" in boundary
    assert "対話型受け入れ: [IDE / 対話型CLI" in boundary


def test_requires_active_branch_inventory_even_for_one_plan() -> None:
    text = procedure_text()
    assert "未採用のbacklog Issueは比較対象へ含めない" in text
    assert "他のactiveな環流branchなし" in text
    assert "比較対象の棚卸しを省略したPASSにはしない" in text
    assert text.count("比較対象なし（PASSではない）") == 2
    assert "commit OID" in text
    assert "refの鮮度を確認できない場合" in text


def test_defines_canonical_path_rules_and_rename_handling() -> None:
    text = procedure_text()
    assert "リポジトリルート相対のPOSIX表記" in text
    assert "先頭`./`、絶対パス、親参照`..`" in text
    assert "文字大小を区別" in text
    assert "renameは旧パスと新パスの両方" in text


def test_defines_sync_record_location_and_template() -> None:
    text = procedure_text()
    assert "tasklist.md` の「受け入れ記録」" in text
    assert "- 同期元: platform-harness" in text
    assert "- 派生固有差分:" in text

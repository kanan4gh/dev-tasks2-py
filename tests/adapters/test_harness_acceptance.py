"""対話型受け入れ手順の状態・単一ゲート・無課金境界を検証する。"""

from pathlib import Path

ROOT = Path(__file__).parents[2]
PROCEDURE = ROOT / "docs" / "procedures" / "harness-acceptance.md"


def section(text: str, heading: str, next_heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.index(f"## {next_heading}", start)
    return text[start:end]


def assert_in_order(text: str, markers: tuple[str, ...]) -> None:
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)


def test_acceptance_connects_to_add_feature_with_single_candidate_gate() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    connection = section(text, "add-feature ステップ8-Bとの接続", "自動検証との境界")
    assert_in_order(
        connection,
        (
            "**候補ゲート**",
            "**候補コミット**",
            "**G3実施**",
            "**結果記録**",
            "**最終ゲート**",
            "**記録コミット**",
            "**push / PR作成**",
        ),
    )
    assert "候補ゲート**: ローカル品質ゲートを1回で全緑" in connection
    assert "受け入れ記録が製品ファイルを変更しない" in connection
    assert "状態を`active`へ戻し" in connection


def test_acceptance_replaces_stop_sentinel_with_active_read_only_fixture() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    preparation = section(text, "共通準備", "共通の状態・lint確認")
    assert "- **状態**: active" in preparation
    assert "- [ ] 応答終了を妨げない未完了タスク" in preparation
    assert "agentへfixtureを完了・更新させず" in preparation
    assert "Stop smoke sentinel" not in preparation
    assert "fixture内へ記録ファイルは作らない" in preparation
    assert "元リポジトリ側" in preparation


def test_acceptance_exercises_full_state_lifecycle_and_profiles() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    checks = section(text, "共通の状態・lint確認", "Claude Code")
    assert_in_order(
        checks,
        (
            "activeかつ未完了",
            "G1だけ",
            "steering_state.py pause",
            "pausedの通常lint",
            "steering_state.py resume",
            "steering_state.py complete",
            "steering_lint.py --require-complete",
        ),
    )


def test_each_harness_requires_read_only_response_to_finish_without_block() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    sections = (
        section(text, "Claude Code", "Codex"),
        section(text, "Codex", "Kiro IDE"),
        section(text, "Kiro IDE", "Kiro CLI"),
        section(text, "Kiro CLI", "判定"),
    )
    for harness in sections:
        assert "fixture tasklistを読" in harness
        assert "正常終了" in harness
    assert "Stop blockが登録されていない" in sections[0]
    assert "`.codex/hooks.json`がなく" in sections[1]
    assert "stop hookがなく" in sections[3]


def test_acceptance_forbids_metered_headless_modes() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    conditions = section(text, "実施条件", "add-feature ステップ8-Bとの接続")
    assert "従量課金型headless modeを使わない" in conditions
    assert "Claude Codeのprint mode" in conditions
    assert "Codexの非対話exec mode" in conditions


def test_acceptance_template_can_record_not_applicable_items() -> None:
    template = (
        ROOT / "docs" / "procedures" / "templates" / "harness-acceptance-record.md"
    ).read_text(encoding="utf-8")
    assert "合格 / 不合格 / 保留 / 対象外" in template
    assert "対象外: 実行面が対象能力を提供せず" in template
    assert "代替経路:" in template

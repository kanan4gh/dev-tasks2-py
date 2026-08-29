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
    conditions = section(text, "実施条件", "権限モードの中立化")
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


def test_acceptance_requires_default_permission_mode_before_launch() -> None:
    """宣言された承認境界が行使される状態を、実施条件として要求する。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    conditions = section(text, "実施条件", "権限モードの中立化")
    assert "権限モードが既定であり" in conditions
    assert "承認境界が実際に行使される状態" in conditions


def test_neutralization_covers_every_harness() -> None:
    """1ハーネスでも欠けると「そのハーネスは中立化不要」と読めてしまう。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    neutralization = section(text, "権限モードの中立化", "add-feature ステップ8-Bとの接続")
    for harness in ("Claude Code", "Codex", "Kiro"):
        assert harness in neutralization
    assert "--permission-mode manual" in neutralization
    assert "trust_level" in neutralization
    assert "allowedTools" in neutralization


def test_neutralization_records_capability_gap_with_substitute_gate() -> None:
    """中立化が原理的に不可能な項目は、代替ゲートか保留・対象外へ落とす。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    neutralization = section(text, "権限モードの中立化", "add-feature ステップ8-Bとの接続")
    assert "未信頼のまま実行する経路は存在しない" in neutralization
    assert "--sandbox read-only" in neutralization
    assert "未中立のまま観察した結果を合格として記録しない" in neutralization


def test_cleanup_blocks_trust_reuse_on_deterministic_paths() -> None:
    """害は蓄積ではなく決定論的pathの再利用にある。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    cleanup = section(text, "後片付け", "誤起動時")
    assert "信頼エントリを削除する" in cleanup
    assert "再現性のある受け入れ手順ほど壊れる" in cleanup
    assert "永続許可" in cleanup


def test_deterministic_path_recheck_belongs_to_the_pre_launch_section() -> None:
    """起動前の確認を後片付け節へ置くと、読者が到達した時点では手遅れになる。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    neutralization = section(text, "権限モードの中立化", "add-feature ステップ8-Bとの接続")
    cleanup = section(text, "後片付け", "誤起動時")
    assert "起動前に確認する" in neutralization
    # 後片付け節が起動前を「言及」するのは根拠として妥当。「指示」を置かないことが不変条件
    assert "起動前に確認する" not in cleanup
    assert "起動前に" not in cleanup


def test_acceptance_places_neutralization_before_observation_and_cleanup_after() -> None:
    """起動前に境界を作り、観察し、終了後に残さない、の時系列を固定する。"""
    text = PROCEDURE.read_text(encoding="utf-8")
    assert_in_order(
        text,
        (
            "## 実施条件",
            "## 権限モードの中立化",
            "## Claude Code",
            "## 判定",
            "## 後片付け",
            "## 誤起動時",
        ),
    )


def test_template_records_permission_mode_and_trust_state() -> None:
    """自由記述の「設定・承認ポリシー」では未記入が可視化されない。"""
    template = (
        ROOT / "docs" / "procedures" / "templates" / "harness-acceptance-record.md"
    ).read_text(encoding="utf-8")
    assert "| 権限モード |" in template
    assert "| プロジェクト信頼状態 |" in template
    assert "環境側の上書き（auto mode・プロジェクト信頼等）を中立化した" in template
    assert "前回の信頼が残っていないことを起動前に確認した" in template
    assert "付与した信頼エントリの削除" in template

"""Contracts for the lightweight-path criteria and how the path judgement is surfaced.

Criterion 3 decides whether a change may take the low-cost path, so its wording, its
record-only exception and the document list it points at must stay in sync across the
neutral procedure, the Claude adapter, the requirements template and the spec validator
(see GitHub issue #40).
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
AGENTS = ROOT / "AGENTS.md"
NEUTRAL = ROOT / "docs" / "procedures" / "add-feature.md"
CLAUDE_ADAPTER = ROOT / ".claude" / "commands" / "add-feature.md"
TEMPLATE = ROOT / "docs" / "procedures" / "templates" / "requirements.md"
VALIDATOR = ROOT / "docs" / "procedures" / "validate-implementation.md"

DOC_LIST_HEADING = "### 永続的ドキュメント一覧（`docs/`）"
LISTED_DOC_PATTERN = re.compile(r"^- \*\*([\w.-]+\.md)\*\*", re.MULTILINE)


def workflow_files() -> tuple[Path, Path]:
    """中立手順書とClaudeアダプタ。基準の契約は両方に同一で存在する必要がある。"""
    return (NEUTRAL, CLAUDE_ADAPTER)


def step_section(path: Path, number: str) -> str:
    """`## ステップ{number}:` 見出しから次の `## ` 見出し直前までを切り出す。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    heading = f"## ステップ{number}:"
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    assert len(starts) == 1, f"{path.name}: {heading} が1つだけ存在するはず"
    start = starts[0]
    for end in range(start + 1, len(lines)):
        if lines[end].startswith("## "):
            return "\n".join(lines[start:end])
    return "\n".join(lines[start:])


def listed_persistent_docs() -> set[str]:
    """AGENTS.md プロダクト固有層が列挙する永続ドキュメントのファイル名。"""
    text = AGENTS.read_text(encoding="utf-8")
    # 見出しの改名・移動で ValueError になると失敗理由が読めないため、先にガードする
    assert DOC_LIST_HEADING in text, f"AGENTS.md に {DOC_LIST_HEADING} が見つからない"
    start = text.index(DOC_LIST_HEADING)
    end_heading = "### 記憶層の運用"
    assert end_heading in text[start:], f"AGENTS.md に {end_heading} が見つからない"
    end = text.index(end_heading, start)
    return set(LISTED_DOC_PATTERN.findall(text[start:end]))


def actual_persistent_docs() -> set[str]:
    """`docs/` 直下に実在するMarkdownファイル名(サブディレクトリは対象外)。"""
    return {path.name for path in (ROOT / "docs").glob("*.md")}


def test_criterion3_names_the_documents_it_applies_to() -> None:
    plan = step_section(NEUTRAL, "4")
    assert "対象文書の更新が不要" in plan
    # 正典・アダプタ・テンプレートを取りこぼすと、方針の書き換えが基準3を素通りする
    assert "`AGENTS.md`(SDDプロセス正典)と、各ハーネスアダプタの規範記述" in plan
    assert "AGENTS.md プロダクト固有層が列挙する" in plan
    assert "`docs/procedures/templates/` の**テンプレート**" in plan


def test_criterion3_exempts_record_only_updates_with_a_stated_reason() -> None:
    plan = step_section(NEUTRAL, "4")
    assert "**記録例外**" in plan
    # 実体が文書の外にあることが例外の要。これが無いと「一覧への追加」だけで通る
    assert "変更の実体が対象文書の外にある" in plan
    # 追加だけでなく削除・値の更新も記録にとどまる更新である
    assert "一覧・台帳の項目の追加・削除・値の更新と、その理由の記述にとどまる" in plan
    # 根拠が無いと例外が拡大解釈される
    assert "その文書が「何を定めるか」自体は変わらず、設計判断が発生しない" in plan


def test_criterion3_exception_is_not_a_loophole() -> None:
    plan = step_section(NEUTRAL, "4")
    assert "**記録例外に該当しないもの**" in plan
    # 一覧が設計の実体である文書を、外形一致だけで例外に通さない
    assert "文書への記述**そのものが変更の実体**である場合" in plan
    assert "機能一覧へ機能を追加する" in plan
    assert "分類体系や適用範囲そのもの" in plan
    assert "方針・条件・手順そのもの" in plan
    assert "同一の変更に混在する" in plan


def test_criterion3_requires_recording_when_the_exception_is_used() -> None:
    plan = step_section(NEUTRAL, "4")
    # 同じステップ4のG3判定にも「判定結果を requirements.md に記録する」があるため、
    # 汎用語で判定すると空振りする。基準3側にしか無い文字列で固定する
    assert "記録例外を適用した場合は、判定結果(**変更の実体がどこにあるか**" in plan


def test_path_judgement_is_presented_for_both_paths() -> None:
    for path in workflow_files():
        approval = step_section(path, "4.5")
        assert "選択したパスにかかわらず" in approval
        # 通常パス側の理由提示が抜けると、基準の問題がユーザーから見えない
        assert "どの基準を満たさなかったか" in approval
        assert "暗黙に軽量化しない" in approval


def test_path_judgement_does_not_add_an_approval_gate() -> None:
    for path in workflow_files():
        approval = step_section(path, "4.5")
        assert "新たな承認ゲートは設けない" in approval
        assert "計画の構成要素" in approval


def test_escalation_triggers_on_policy_change_not_on_any_docs_edit() -> None:
    for path in workflow_files():
        step5 = step_section(path, "5")
        assert "対象文書が定める方針の変更が必要と判明した" in step5
        assert "記録にとどまる更新では昇格しない" in step5
        # 「docs更新が必要」という無限定の昇格条件が残っていないこと
        assert "docs更新が必要と判明した" not in step5


def test_completion_condition_covers_the_judgement_for_both_paths() -> None:
    """完了条件が片側条件のまま残ると、改訂の主旨と正面から矛盾する。"""
    for path in workflow_files():
        text = path.read_text(encoding="utf-8")
        condition = text[text.index("## 完了条件") :]
        assert "選択したパスにかかわらず提示済み" in condition
        assert "軽量パス適用時はその判定も" not in condition


def test_procedures_require_recording_the_judgement_for_both_paths() -> None:
    """記録を指示する側が軽量パス片側のままだと、通常パスでは判定が残らない。"""
    for path in workflow_files():
        plan = step_section(path, "4")
        assert "**どちらのパスでも**" in plan

    steering = (ROOT / "docs" / "procedures" / "steering.md").read_text(encoding="utf-8")
    assert "**通常パス・軽量パスのどちらでも**基準4項目それぞれの判定結果を記録する" in steering

    agents = AGENTS.read_text(encoding="utf-8")
    assert "通常パス・軽量パスのどちらでも `requirements.md` の「パス判定」セクションに記録" in agents


def test_template_records_the_judgement_for_both_paths() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**" in text
    # 「非適用ならセクションごと削除」という旧運用が復活したら落とす
    assert "非適用の場合はこのセクションを削除する" not in text
    assert "の手順書とテンプレート)の更新が不要" in text
    assert "**記録例外**" in text
    assert "変更の実体が対象文書の外にあり" in text
    assert "**判定理由**" in text
    # steering lint の LIGHTWEIGHT_PATTERN が依存する行形式を壊さない
    assert "- **軽量パス**: {適用 / 非適用}" in text
    assert "`- **軽量パス**: 適用` の形で行を完結させ" in text


def test_validator_applies_the_same_criterion_including_the_exception() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    # 表記は正典(add-feature ステップ4)と揃える
    assert "**対象文書の更新が不要**" in text
    assert "基準3の判定にあたっては記録例外を考慮する" in text
    assert "変更の実体が対象文書の外にあり" in text
    assert "項目の追加・削除・値の更新と理由の記述にとどまる" in text
    # 抜け穴側も validator が検出できること
    assert "文書への記述そのものが変更の実体" in text
    assert "分類体系や適用範囲そのもの" in text
    assert "方針・条件・手順そのもの" in text
    assert "通常パスへ昇格すべき乖離" in text
    # 旧・無限定の基準列挙が残っていないこと
    assert "`docs/` 更新不要" not in text


def test_agents_document_list_matches_the_docs_directory() -> None:
    """一覧と実態が食い違うと基準3の判定対象が不定になる。双方向で固定する。"""
    listed = listed_persistent_docs()
    actual = actual_persistent_docs()

    assert listed, "AGENTS.md の永続ドキュメント一覧が読み取れていない"
    assert listed - actual == set(), f"一覧にあるが docs/ に無い: {sorted(listed - actual)}"
    assert actual - listed == set(), f"docs/ にあるが一覧に無い: {sorted(actual - listed)}"


def test_agents_states_the_list_drives_the_path_judgement() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "軽量パス基準3" in text
    assert "一覧と実態が食い違うとパス判定が不定になる" in text

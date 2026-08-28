"""派生固有差分(dev-tasks2-py): 移行前ステアリングのgrandfatherの契約。

platform-harness v1.6.1 の同期(GitHub issue #26)で導入した免除は、
移行前に存在したステアリングだけを対象とし、以後のステアリングには一切効かない。
この境界が崩れると、新しい作業がlintを素通りする。
"""

from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import steering_lint  # noqa: E402


def test_grandfather_list_is_a_closed_enumeration() -> None:
    """前方一致やワイルドカードではなく、名前の限定列挙であること。"""
    assert isinstance(steering_lint.LEGACY_PRE_MIGRATION, frozenset)
    assert len(steering_lint.LEGACY_PRE_MIGRATION) == 18
    for name in steering_lint.LEGACY_PRE_MIGRATION:
        assert "*" not in name and "?" not in name


def test_grandfathered_dirs_all_exist() -> None:
    """実在しない名前が残っていると、免除の意図が読めなくなる。"""
    for name in steering_lint.LEGACY_PRE_MIGRATION:
        assert (ROOT / ".steering" / name).is_dir(), f"存在しないステアリング: {name}"


def test_grandfather_covers_only_pre_migration_dirs() -> None:
    """同期用ステアリング以降のものを免除に含めない。"""
    assert "20260829-sync-platform-harness-v1-6-1" not in steering_lint.LEGACY_PRE_MIGRATION
    for name in steering_lint.LEGACY_PRE_MIGRATION:
        assert name < "20260829", f"移行以降のステアリングが免除されている: {name}"


def test_new_steering_is_not_exempt(tmp_path: Path) -> None:
    """免除外のディレクトリは、必須ファイル欠落がそのまま違反になる。"""
    (tmp_path / ".steering" / "20261231-brand-new").mkdir(parents=True)
    violations = steering_lint.lint(tmp_path)
    assert {v.check_id for v in violations} == {"C1"}
    assert all(v.directory == "20261231-brand-new" for v in violations)


def test_repository_steering_passes_lint() -> None:
    """リポジトリ全体が通常規則を満たすこと(免除適用後)。"""
    assert steering_lint.lint(ROOT) == []

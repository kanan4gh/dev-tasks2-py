from datetime import datetime
from pathlib import Path

import pytest

from task_cli.backup import backup_label, create_backup


def _src(tmp_path: Path, content: str = "data") -> Path:
    src = tmp_path / ".task-py"
    src.mkdir(exist_ok=True)
    (src / "tasks.yaml").write_text(content, encoding="utf-8")
    return src


def _generations(tmp_path: Path) -> list[str]:
    return sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".task-py.backup."))


class TestCreateBackup:
    def test_copies_into_timestamped_sibling(self, tmp_path: Path) -> None:
        src = _src(tmp_path, "v1")
        root = tmp_path / ".task-py.backup"
        dest = create_backup(src, root, now=datetime(2026, 11, 13, 9, 0, 0))
        assert dest == tmp_path / ".task-py.backup.20261113-090000"
        assert (dest / "tasks.yaml").read_text(encoding="utf-8") == "v1"

    def test_previous_generation_survives_next_backup(self, tmp_path: Path) -> None:
        src = _src(tmp_path, "first")
        root = tmp_path / ".task-py.backup"
        first = create_backup(src, root, now=datetime(2026, 11, 13, 9, 0, 0))
        (src / "tasks.yaml").write_text("second", encoding="utf-8")
        second = create_backup(src, root, now=datetime(2026, 11, 13, 9, 0, 5))
        assert (first / "tasks.yaml").read_text(encoding="utf-8") == "first"
        assert (second / "tasks.yaml").read_text(encoding="utf-8") == "second"

    def test_same_second_does_not_overwrite(self, tmp_path: Path) -> None:
        src = _src(tmp_path, "a")
        root = tmp_path / ".task-py.backup"
        now = datetime(2026, 11, 13, 9, 0, 0)
        first = create_backup(src, root, now=now)
        (src / "tasks.yaml").write_text("b", encoding="utf-8")
        second = create_backup(src, root, now=now)
        assert first != second
        assert (first / "tasks.yaml").read_text(encoding="utf-8") == "a"
        assert (second / "tasks.yaml").read_text(encoding="utf-8") == "b"

    def test_prunes_only_oldest_beyond_keep(self, tmp_path: Path) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        for sec in range(5):
            create_backup(src, root, keep=3, now=datetime(2026, 11, 13, 9, 0, sec))
        assert _generations(tmp_path) == [
            ".task-py.backup.20261113-090002",
            ".task-py.backup.20261113-090003",
            ".task-py.backup.20261113-090004",
        ]

    def test_suffixed_generations_order_numerically(self, tmp_path: Path) -> None:
        # 同一秒に 12 回: 接尾辞 -10 が -2 より古いと誤判定されないこと
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        now = datetime(2026, 11, 13, 9, 0, 0)
        created = [create_backup(src, root, keep=100, now=now) for _ in range(12)]
        create_backup(src, root, keep=12, now=datetime(2026, 11, 13, 9, 0, 1))
        # 最古(最初に作った1つ)だけが消える
        assert not created[0].exists()
        assert all(p.exists() for p in created[1:])

    def test_failed_copy_keeps_existing_generations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        for sec in range(3):
            create_backup(src, root, keep=3, now=datetime(2026, 11, 13, 9, 0, sec))
        before = _generations(tmp_path)

        def boom(*_a: object, **_k: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("task_cli.backup.shutil.copytree", boom)
        with pytest.raises(OSError):
            create_backup(src, root, keep=3, now=datetime(2026, 11, 13, 9, 0, 9))
        assert _generations(tmp_path) == before

    def test_failed_copy_removes_partial_destination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"

        def partial(s: Path, d: Path, *a: object, **k: object) -> None:
            Path(d).mkdir()
            raise OSError("half done")

        monkeypatch.setattr("task_cli.backup.shutil.copytree", partial)
        with pytest.raises(OSError):
            create_backup(src, root, now=datetime(2026, 11, 13, 9, 0, 0))
        assert _generations(tmp_path) == []

    def test_legacy_unsuffixed_backup_is_untouched_and_not_counted(self, tmp_path: Path) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        root.mkdir()
        (root / "old.txt").write_text("legacy", encoding="utf-8")
        for sec in range(3):
            create_backup(src, root, keep=2, now=datetime(2026, 11, 13, 9, 0, sec))
        assert (root / "old.txt").read_text(encoding="utf-8") == "legacy"
        assert len(_generations(tmp_path)) == 2

    def test_unrelated_siblings_are_never_pruned(self, tmp_path: Path) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        other = tmp_path / ".task-py.backup.notes"
        other.mkdir()
        for sec in range(3):
            create_backup(src, root, keep=1, now=datetime(2026, 11, 13, 9, 0, sec))
        assert other.exists()


class TestRetentionSafety:
    def test_new_backup_survives_when_clock_went_backwards(self, tmp_path: Path) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        for sec in range(3):
            create_backup(src, root, keep=3, now=datetime(2026, 11, 13, 9, 0, sec))
        # 時計が巻き戻り、新しい退避の名前が既存より古くなる
        dest = create_backup(src, root, keep=3, now=datetime(2026, 11, 13, 8, 0, 0))
        assert dest.exists()

    @pytest.mark.parametrize("keep", [0, -1])
    def test_rejects_keep_below_one(self, tmp_path: Path, keep: int) -> None:
        src = _src(tmp_path)
        with pytest.raises(ValueError):
            create_backup(src, tmp_path / ".task-py.backup", keep=keep)
        assert _generations(tmp_path) == []

    def test_failed_copy_does_not_remove_concurrent_backup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = _src(tmp_path)
        root = tmp_path / ".task-py.backup"
        rival = tmp_path / ".task-py.backup.20261113-090000"

        def collide(_s: Path, d: Path, *_a: object, **_k: object) -> None:
            Path(d).mkdir(exist_ok=True)  # 競合相手が先に作ったことを再現
            raise FileExistsError(str(d))

        monkeypatch.setattr("task_cli.backup.shutil.copytree", collide)
        with pytest.raises(FileExistsError):
            create_backup(src, root, now=datetime(2026, 11, 13, 9, 0, 0))
        assert rival.exists()


class TestBackupLabel:
    def test_mentions_pattern_and_keep(self, tmp_path: Path) -> None:
        label = backup_label(tmp_path / ".task-py.backup", keep=5)
        assert ".task-py.backup.<日時>" in label
        assert "5" in label

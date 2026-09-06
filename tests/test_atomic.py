import os
import threading
from pathlib import Path
from typing import TextIO

import pytest

from task_cli.storage import atomic


class TestWriteAtomic:
    def test_writes_content(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        atomic.write_atomic(path, lambda f: f.write("hello\n"))
        assert path.read_text(encoding="utf-8") == "hello\n"

    def test_leaves_no_temporary_file_on_success(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        atomic.write_atomic(path, lambda f: f.write("hello\n"))
        assert [p.name for p in tmp_path.iterdir()] == ["data.yaml"]

    def test_target_is_untouched_until_replace(self, tmp_path: Path) -> None:
        """書いている最中の内容は本体に現れない（読み手は完全な内容だけを見る）。"""
        path = tmp_path / "data.yaml"
        path.write_text("original\n", encoding="utf-8")

        observed: list[str] = []

        def dump(f: TextIO) -> None:
            f.write("new content\n")
            f.flush()
            observed.append(path.read_text(encoding="utf-8"))

        atomic.write_atomic(path, dump)

        assert observed == ["original\n"]
        assert path.read_text(encoding="utf-8") == "new content\n"

    def test_existing_file_survives_dump_failure(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        path.write_text("original\n", encoding="utf-8")

        def broken(f: TextIO) -> None:
            f.write("partial")
            raise OSError("disk full")

        with pytest.raises(OSError):
            atomic.write_atomic(path, broken)

        assert path.read_text(encoding="utf-8") == "original\n"
        assert [p.name for p in tmp_path.iterdir()] == ["data.yaml"]

    def test_no_file_is_created_when_dump_fails_for_new_path(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"

        def broken(f: TextIO) -> None:
            raise OSError("disk full")

        with pytest.raises(OSError):
            atomic.write_atomic(path, broken)

        assert not path.exists()
        assert list(tmp_path.iterdir()) == []

    def test_preserves_permissions_of_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        path.write_text("original\n", encoding="utf-8")
        os.chmod(path, 0o644)

        atomic.write_atomic(path, lambda f: f.write("new\n"))

        assert path.stat().st_mode & 0o777 == 0o644


class TestLocked:
    def test_is_reentrant_within_the_same_thread(self, tmp_path: Path) -> None:
        """同一プロセス内の再入で自己デッドロックしない（move_task が通る経路）。"""
        path = tmp_path / "data.yaml"
        with atomic.locked(path):
            with atomic.locked(path):
                pass

    def test_acquires_multiple_paths_in_sorted_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """取得順を一意にすることで、逆向きの同時取得でもデッドロックしない。"""
        a = tmp_path / "a.yaml"
        b = tmp_path / "b.yaml"
        opened: list[str] = []
        real_open = os.open

        def spy(path: object, flags: int, *args: object, **kwargs: object) -> int:
            if isinstance(path, str) and path.endswith(".lock"):
                opened.append(Path(path).name)
            return real_open(path, flags, *args, **kwargs)  # pyright: ignore[reportArgumentType]

        monkeypatch.setattr(os, "open", spy)

        with atomic.locked(b, a):
            pass
        forward = list(opened)
        opened.clear()
        with atomic.locked(a, b):
            pass

        assert forward == opened == ["a.yaml.lock", "b.yaml.lock"]

    def test_excludes_another_thread(self, tmp_path: Path) -> None:
        """再入の許可はスレッドごと。別スレッドは実際に待たされる。"""
        path = tmp_path / "data.yaml"
        acquired = threading.Event()
        release = threading.Event()
        order: list[str] = []

        def holder() -> None:
            with atomic.locked(path):
                order.append("holder-in")
                acquired.set()
                release.wait(timeout=5)
                order.append("holder-out")

        def waiter() -> None:
            with atomic.locked(path):
                order.append("waiter-in")

        t1 = threading.Thread(target=holder)
        t1.start()
        assert acquired.wait(timeout=5)

        t2 = threading.Thread(target=waiter)
        t2.start()
        t2.join(timeout=0.3)
        assert t2.is_alive(), "別スレッドがロックを取得できてしまった"

        release.set()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert order == ["holder-in", "holder-out", "waiter-in"]

    def test_releases_the_lock_when_the_body_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        with pytest.raises(RuntimeError):
            with atomic.locked(path):
                raise RuntimeError("boom")

        assert atomic._held_paths() == set()

    def test_degrades_to_no_op_without_fcntl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """fcntl の無いプラットフォームでは例外にならず素通しする。"""
        monkeypatch.setattr(atomic, "_flock", None)
        path = tmp_path / "data.yaml"

        with atomic.locked(path):
            pass

        assert not (tmp_path / "data.yaml.lock").exists()

"""ファイル書き込みの不可分性と、read-modify-write の排他を提供する。

`~/.task-py/` 配下の YAML は CLI・MCP サーバー・ローカル Web GUI という別々の
プロセスから更新される。それぞれが `load()` → 書き換え → `save()` を行うため、
次の2つが要る。

1. **書きかけのファイルを他のプロセスに見せない**（`write_atomic`）
   一時ファイルへ書いてから `os.replace()` で差し替える。読み手が観測するのは
   常に「置き換え前の完全な内容」か「置き換え後の完全な内容」のどちらかになる。

2. **更新を直列化する**（`locked`）
   `save()` だけを守ってもロストアップデートは防げない。ロックは `load()` から
   `save()` までの全体を覆う必要があり、その境界はサービス層が決める。
"""

import os
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

# fcntl は POSIX 専用。無い環境（Windows）ではロックなしに縮退する。現行の
# 実装にロックは存在しないため、縮退しても強度は後退しない。未検証の
# msvcrt 実装を持ち込むほうが害が大きい。
_flock: Callable[[int, int], object] | None
_LOCK_EX: int
try:
    import fcntl as _fcntl

    _flock = _fcntl.flock
    _LOCK_EX = _fcntl.LOCK_EX
except ImportError:  # pragma: no cover - POSIX 以外
    _flock = None
    _LOCK_EX = 0


def write_atomic(path: Path, dump: Callable[[TextIO], object]) -> None:
    """`path` を不可分に書き換える。

    `dump` は開かれたテキストファイルオブジェクトを受け取り、内容を書き出す
    （戻り値は無視するので `f.write(...)` をそのまま返す形でよい）。
    例外を投げた場合、`path` は一切変更されない（一時ファイルの段階で失敗する
    ため）。呼び出し側は親ディレクトリの存在を保証しておくこと。

    一時ファイルは**同じディレクトリ**に作る。`os.replace()` が不可分なのは
    同一ファイルシステム内だけで、`/tmp` を経由するとその保証が消える。
    """
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            dump(f)
            f.flush()
            # fsync を省くと「置き換えは成功したのに中身が空」という状態が
            # クラッシュ時に残りうる。メタデータの更新だけが先に永続化される
            # ことがあるため。
            os.fsync(f.fileno())
        _apply_mode(path, tmp_path)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    _fsync_directory(path.parent)


def _fsync_directory(directory: Path) -> None:
    """ディレクトリエントリの更新を永続化する。

    ファイルの中身を fsync しても、`os.replace()` が書き換えるのは親ディレクトリの
    エントリであって、そちらが永続化されていなければ電源断で置き換え前の inode を
    指したままになりうる。ディレクトリへの fsync を許さない環境もあるため、
    失敗は握りつぶす（そこでは元々この保証が得られない）。
    """
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:  # pragma: no cover - ディレクトリを開けない環境
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover - ディレクトリの fsync を許さない環境
        pass
    finally:
        os.close(fd)


def _apply_mode(target: Path, tmp_path: Path) -> None:
    """置き換え後のパーミッションを決める。

    既存ファイルを置き換える場合は元のパーミッションを引き継ぐ。新規作成の
    場合は `mkstemp` 由来の 600 のままとする（従来の `open(path, "w")` は
    umask 依存で通常 644 だった）。umask を読むには一度 `os.umask()` で
    書き換えて戻す必要があり、スレッドを持つローカル Web サーバーでは競合する。
    600 は 644 より狭く、親ディレクトリが 700 である以上、単一利用者の運用に
    影響しない。
    """
    if target.exists():
        os.chmod(tmp_path, target.stat().st_mode & 0o777)


_held = threading.local()


def _held_paths() -> set[str]:
    paths: set[str] | None = getattr(_held, "paths", None)
    if paths is None:
        paths = set()
        _held.paths = paths
    return paths


def _normalize(path: Path) -> str:
    return str(Path(path).expanduser().resolve())


@contextmanager
def locked(*paths: Path) -> Iterator[None]:
    """`paths` に対する排他ロックを取得する。

    ロックの対象は本体ではなく `<path>.lock` である。`write_atomic()` が
    `os.replace()` で inode を入れ替えるため、本体を直接 flock するとロックが
    別のファイルに付いてしまう。

    **同一プロセス内では再入できる。** `move_task` は移動元と移動先を跨いだ
    トランザクションを開き、その内側で `delete_task` → `save()` が同じパスの
    ロックを取りに行く。`flock` は同一プロセスでも別の fd なら待つため、
    再入を許さないと自己デッドロックする。

    **複数パスは正規化してソート順に取得する。** A→B と B→A の move を同時に
    走らせても取得順が一致するため、デッドロックしない。

    親ディレクトリは呼び出し側が用意しておくこと（`ensure_directory()`）。
    """
    if _flock is None:
        yield
        return

    held = _held_paths()
    targets = sorted({_normalize(p) for p in paths} - held)
    if not targets:
        yield
        return

    fds: list[int] = []
    try:
        for target in targets:
            fd = os.open(target + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
            fds.append(fd)
            _flock(fd, _LOCK_EX)
            held.add(target)
        yield
    finally:
        for target in targets:
            held.discard(target)
        for fd in fds:
            os.close(fd)

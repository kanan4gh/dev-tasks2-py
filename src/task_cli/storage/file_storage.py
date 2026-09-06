import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

from task_cli.models.task import Task
from task_cli.storage.atomic import locked, write_atomic


class FileStorage:
    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path).expanduser()

    @property
    def path(self) -> Path:
        return self._path

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """`load()` → 変更 → `save()` をひとまとまりの排他区間にする。

        `save()` だけを守ってもロストアップデートは防げない。2つのプロセスが
        同じ時点の内容を読み、あとから保存したほうが「自分が読んだ時点の一覧
        全体」を書き戻すため、もう一方の変更が丸ごと消えるからである。

        再入可能なので、この区間の内側で `save()` が同じロックを取っても
        待たされない。
        """
        self.ensure_directory()
        with locked(self._path):
            yield

    def load(self) -> list[Task]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return []
        return [Task.model_validate(item) for item in data]

    def save(self, tasks: list[Task]) -> None:
        with self.transaction():
            self._save_locked(tasks)

    def _save_locked(self, tasks: list[Task]) -> None:
        bak_path = Path(str(self._path) + ".bak")

        if self._path.exists():
            shutil.copy2(self._path, bak_path)

        try:
            data = [task.model_dump(mode="json") for task in tasks]
            write_atomic(
                self._path,
                lambda f: yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False),
            )
            if bak_path.exists():
                bak_path.unlink()
        # `write_atomic` は失敗しても本体に触れないため、この復元は実質的に
        # 何もしない（同じ内容を上書きするだけ）。それでも残すのは、`.bak` の
        # 意味論（書き込み前に作り、成功したら消す）を利用者から見て変えない
        # ためである。
        except Exception:
            if bak_path.exists():
                shutil.move(str(bak_path), str(self._path))
            raise

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

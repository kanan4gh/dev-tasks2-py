import os
from pathlib import Path

import yaml

from task_cli.models.time import TimerFile

_DEFAULT_PATH = Path("~/.task-py/timer.yaml")


class TimerStorage:
    """実行中タイマーの永続化。

    プロジェクト配下ではなく `~/.task-py/` 直下に置く。「今どのタイマーが
    動いているか」はプロジェクトを跨いだ唯一の答えであってほしいためで、
    プロジェクト配下だと読み手が全プロジェクトを走査する羽目になる。

    `FileStorage` と違って `.bak` を作らない。タイマーは揮発的な状態であり、
    失っても「動いていない」に落ちるだけでタスクのデータは壊れない。
    """

    def __init__(self, file_path: Path | None = None) -> None:
        self._path = (file_path or _DEFAULT_PATH).expanduser()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> TimerFile:
        if not self._path.exists():
            return TimerFile()
        try:
            with self._path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            # 壊れた状態ファイルは「動いていない」として扱う。ここで落とすと
            # 無関係なコマンドまで巻き添えで死ぬ。
            return TimerFile()
        if not data:
            return TimerFile()
        try:
            return TimerFile.model_validate(data)
        except ValueError:
            return TimerFile()

    def save(self, timer_file: TimerFile) -> None:
        self.ensure_directory()
        data = timer_file.model_dump(mode="json")
        with self._path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def ensure_directory(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)

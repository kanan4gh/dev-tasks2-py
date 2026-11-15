from pathlib import Path

from task_cli.exceptions import (
    AppError,
    InvalidProjectName,
    NotFoundError,
    StateConflictError,
)
from task_cli.models.task import GlobalConfig, ProjectEntry
from task_cli.storage.global_config_storage import GlobalConfigStorage


MAX_PROJECT_NAME_LENGTH = 64


def validate_project_name(name: str) -> None:
    """作成・改名の新しい名前を検査する。

    名前は `~/.task-py/projects/{name}/` のパスにそのまま使われる。`../x` や
    `a/b` を許すと、プロジェクトの外を指すディレクトリを作れてしまう。
    """
    problem: str | None = None
    if not name:
        problem = "名前が空です。"
    elif name != name.strip():
        problem = "名前の前後に空白があります。"
    elif len(name) > MAX_PROJECT_NAME_LENGTH:
        problem = f"名前が{MAX_PROJECT_NAME_LENGTH}文字を超えています。"
    elif any(ord(c) < 0x20 or ord(c) == 0x7F for c in name):
        problem = "名前に制御文字が含まれています。"
    elif "/" in name or "\\" in name:
        problem = "名前に / または \\ が含まれています。"
    elif name.startswith("."):
        problem = "名前が . で始まっています。"
    if problem is not None:
        raise InvalidProjectName(
            "プロジェクト名が不正です。",
            cause=problem,
            remedy=(
                f"{MAX_PROJECT_NAME_LENGTH}文字以内で、前後に空白がなく、/ \\ 制御文字を含まず、"
                ". で始まらない名前を指定してください。"
            ),
        )


class ProjectService:
    def __init__(self, storage: GlobalConfigStorage) -> None:
        self._storage = storage

    def create_project(self, name: str) -> ProjectEntry:
        validate_project_name(name)
        # 採番（last_project_id += 1）を含むため、load から save までを排他区間に
        # 入れないと同時実行で同じ ID を配ってしまう。
        with self._storage.transaction():
            config = self._storage.load()
            if any(p.name == name for p in config.projects):
                raise StateConflictError(
                    "同名のプロジェクトが既に存在します。",
                    cause=f"プロジェクト '{name}' は既に登録されています。",
                    remedy="別の名前を指定してください。",
                )
            config.last_project_id += 1
            entry = ProjectEntry(name=name, id=config.last_project_id)
            config.projects.append(entry)
            config.active_project = name
            self._storage.save(config)
        return entry

    def list_projects(self) -> list[ProjectEntry]:
        return self._storage.load().projects

    def get_project(self, name: str) -> ProjectEntry:
        for p in self._storage.load().projects:
            if p.name == name:
                return p
        raise NotFoundError(
            "プロジェクトが見つかりません。",
            cause=f"プロジェクト '{name}' は存在しません。",
            remedy="task-py project list で有効な名前を確認してください。",
        )

    def use_project(self, name: str) -> None:
        with self._storage.transaction():
            self.get_project(name)
            config = self._storage.load()
            config.active_project = name
            self._storage.save(config)

    def remove_project(self, name: str) -> None:
        with self._storage.transaction():
            self.get_project(name)
            config = self._storage.load()
            config.projects = [p for p in config.projects if p.name != name]
            if config.active_project == name:
                config.active_project = None
            self._storage.save(config)

    def rename_project(self, old: str, new: str) -> None:
        """プロジェクトを改名する。

        **ディレクトリの移動を先に行い、設定の更新を後にする。** 逆順にすると、
        ディレクトリの移動に失敗したときに「設定は new・データは old のまま」と
        いう戻せない食い違いが残る。実際に起こりうる: `remove_project()` は
        ディレクトリを消さないので、削除済みプロジェクトのディレクトリが残って
        いると `rename` の移動先が既に存在し、`Directory not empty` で失敗する。

        排他区間にディレクトリ移動まで含めるのは、他プロセスが中間状態の設定を
        観測しないようにするためである（ただし移動対象の `tasks.yaml` 自体の
        ロックは取らない。design.md の「意図的に残す窓」を参照）。
        """
        validate_project_name(new)
        with self._storage.transaction():
            self.get_project(old)
            config = self._storage.load()
            if any(p.name == new for p in config.projects):
                raise StateConflictError(
                    "同名のプロジェクトが既に存在します。",
                    cause=f"プロジェクト '{new}' は既に登録されています。",
                    remedy="別の名前を指定してください。",
                )

            old_dir = Path(f"~/.task-py/projects/{old}").expanduser()
            new_dir = Path(f"~/.task-py/projects/{new}").expanduser()
            if new_dir.exists():
                raise StateConflictError(
                    "リネーム先のデータディレクトリが既に存在します。",
                    cause=f"{new_dir} が残っています。"
                    "以前に削除したプロジェクトのデータである可能性があります。",
                    remedy="中身を確認し、退避または削除してから再実行してください。",
                )
            moved = False
            if old_dir.exists():
                try:
                    old_dir.rename(new_dir)
                except OSError as e:
                    raise AppError(
                        "プロジェクトのデータディレクトリを移動できませんでした。",
                        cause=str(e),
                        remedy=f"{old_dir} の権限と空き容量を確認してください。",
                    ) from e
                moved = True

            for p in config.projects:
                if p.name == old:
                    p.name = new
            if config.active_project == old:
                config.active_project = new
            try:
                self._storage.save(config)
            except Exception:
                # 設定を保存できなかったらディレクトリを元に戻す。戻さないと
                # 「設定は old・データは new」の食い違いが残る。
                if moved:
                    new_dir.rename(old_dir)
                raise

    def get_config(self) -> GlobalConfig:
        return self._storage.load()

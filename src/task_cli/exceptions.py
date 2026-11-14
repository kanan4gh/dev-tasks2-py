class AppError(Exception):
    def __init__(self, message: str, cause: str, remedy: str) -> None:
        super().__init__(message)
        self.cause = cause
        self.remedy = remedy


class NotFoundError(AppError):
    """対象（タスク・プロジェクト）が存在しない。"""


class StateConflictError(AppError):
    """いまの状態ではその操作ができない（開始できない・完了できない等）。

    「見つからない」とは別物である。Web ではこれを 404 にすると、経路や
    タスクが無いことと区別できなくなる。サブクラスなので、CLI と MCP は
    従来どおり `except AppError` で扱える。
    """


class StorageReadError(AppError):
    """保存先ファイルを読み込めない（YAML が壊れている・値が不正）。

    保存前の検証エラー（`InvalidTaskData`）とは別物で、こちらは読み込み側の失敗。
    Web では 500 のまま、原因と対処を返す。
    """

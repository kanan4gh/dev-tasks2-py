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

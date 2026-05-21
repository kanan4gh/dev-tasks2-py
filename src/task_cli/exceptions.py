class AppError(Exception):
    def __init__(self, message: str, cause: str, remedy: str) -> None:
        super().__init__(message)
        self.cause = cause
        self.remedy = remedy

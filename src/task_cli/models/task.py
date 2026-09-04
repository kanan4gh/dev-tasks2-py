from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from task_cli.models.time import WorkSession


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Task(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: TaskStatus = TaskStatus.OPEN
    priority: Priority = Priority.MEDIUM
    branch: str | None = None
    due_date: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # 完了した時刻。updated_at は編集のたびに更新されるため完了日の根拠にできない。
    # 値を持たない既存タスクは None のままにし、updated_at からの推測で埋めない。
    completed_at: datetime | None = None

    scheduled_date: str | None = None

    # 実際に作業した区間の履歴。タスク ID はストレージローカルで move のたびに
    # 振り直されるため、外部ファイルではなくタスク自身に持たせて追随させる。
    work_sessions: list[WorkSession] = Field(default_factory=list)

    @property
    def total_worked_seconds(self) -> int:
        """作業セッションの合計秒数。計算値であり永続化しない。"""
        return sum(s.seconds for s in self.work_sessions)

    @field_validator("due_date", "scheduled_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format, got: {v}")
        return v

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Return True if the status transition is valid."""
        allowed: dict[TaskStatus, set[TaskStatus]] = {
            TaskStatus.OPEN: {TaskStatus.IN_PROGRESS, TaskStatus.ARCHIVED},
            TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED},
            TaskStatus.COMPLETED: {TaskStatus.ARCHIVED},
            TaskStatus.ARCHIVED: set(),
        }
        return new_status in allowed[self.status]


class ProjectEntry(BaseModel):
    name: str
    id: int


class GlobalConfig(BaseModel):
    active_project: str | None = None
    projects: list[ProjectEntry] = Field(default_factory=list)
    last_project_id: int = 0

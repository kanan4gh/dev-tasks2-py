from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"due_date must be YYYY-MM-DD format, got: {v}")
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

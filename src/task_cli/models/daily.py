from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Routine(BaseModel):
    id: int
    title: str
    paused: bool = False
    created_at: datetime


class DailyLogEntry(BaseModel):
    routine_id: int
    status: Literal["pending", "done"] = "pending"


class DailyLog(BaseModel):
    date: str  # "YYYY-MM-DD"
    entries: list[DailyLogEntry] = []

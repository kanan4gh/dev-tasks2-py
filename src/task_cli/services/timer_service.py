from datetime import datetime, timezone

from task_cli.duration import format_clock
from task_cli.exceptions import AppError
from task_cli.models.time import TimerFile, TimerKind, TimerState
from task_cli.storage.timer_storage import TimerStorage


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


class TimerService:
    """実行中タイマーの状態遷移と時刻計算。

    経過・残り時間は保存された `started_at` から都度導出する。カウントダウンを
    変数で持たないため、別プロセスから読んでも・書いたプロセスが落ちても・
    端末がスリープしても同じ値になる。

    プロセスの生死はタイマーの有効性の判定に使わない。PID は再利用されるうえ、
    別ホストからは検証できないためである（`TimerState.pid` は表示用）。
    """

    def __init__(self, storage: TimerStorage | None = None) -> None:
        self._storage = storage or TimerStorage()

    def get_active(self) -> TimerState | None:
        return self._storage.load().active

    def start(self, state: TimerState, force: bool = False) -> TimerState:
        current = self.get_active()
        if current is not None and not force:
            raise AppError(
                "既にタイマーが実行中です。",
                cause=self.describe(current),
                remedy=(
                    "task-py time stop で作業時間を記録して終了するか、"
                    "task-py time cancel で破棄してください。"
                    "置き換える場合は --force を付けてください。"
                ),
            )
        self._storage.save(TimerFile(active=state))
        return state

    def clear(self) -> TimerState | None:
        """実行中タイマーを解除し、解除したものを返す。"""
        current = self.get_active()
        self._storage.save(TimerFile(active=None))
        return current

    @staticmethod
    def elapsed_seconds(state: TimerState, now: datetime | None = None) -> int:
        return int((_now(now) - state.started_at).total_seconds())

    @staticmethod
    def remaining_seconds(state: TimerState, now: datetime | None = None) -> int | None:
        """カウントダウンの残り秒数。時間切れなら負値。ストップウォッチは None。"""
        if state.duration_seconds is None:
            return None
        return state.duration_seconds - TimerService.elapsed_seconds(state, now)

    @staticmethod
    def is_expired(state: TimerState, now: datetime | None = None) -> bool:
        remaining = TimerService.remaining_seconds(state, now)
        return remaining is not None and remaining <= 0

    @staticmethod
    def describe(state: TimerState, now: datetime | None = None) -> str:
        """人が読める1行の要約。エラーの cause と CLI 表示で共有する。"""
        target = f"タスク #{state.task_id}" if state.task_id is not None else "タスク未指定"
        if state.task_title:
            target += f"「{state.task_title}」"
        remaining = TimerService.remaining_seconds(state, now)
        if state.kind is TimerKind.STOPWATCH or remaining is None:
            elapsed = format_clock(TimerService.elapsed_seconds(state, now))
            return f"{target} / ストップウォッチ 経過 {elapsed}"
        if remaining <= 0:
            return f"{target} / 時間切れ（超過 {format_clock(-remaining)}）"
        return f"{target} / 残り {format_clock(remaining)}"

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from task_cli.exceptions import AppError
from task_cli.models.task import Task
from task_cli.models.time import TimerKind, TimerState, WorkSession
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.task_manager import TaskManager
from task_cli.services.timer_service import TimerService
from task_cli.storage.file_storage import FileStorage
from task_cli.usecases.project_target import ACTIVE_PROJECT, ProjectTarget, ActiveProject
from task_cli.usecases.task_crud_usecase import resolve_storage_path


@dataclass(frozen=True)
class StopResult:
    """タイマー停止の結果。

    `session` は記録できた場合のみ入る（タスク未指定・記録先タスクが消えた場合は None）。
    `elapsed_seconds` は記録の可否によらず、実際に経過した秒数。
    `overrun_seconds` はカウントダウンの宣言時間を超えた分で、実績には含めていない秒数。
    """

    state: TimerState
    elapsed_seconds: int
    overrun_seconds: int
    session: WorkSession | None


@dataclass(frozen=True)
class StartResult:
    """タイマー開始の結果。

    `replaced` は `--force` で置き換えられた前のタイマーの停止結果（あれば）。
    """

    state: TimerState
    replaced: StopResult | None = None


class TimeTrackingUseCase:
    """タイマーとタスクストレージの調整役。

    `TaskCrudUseCase` と同じく、アクティブプロジェクトからストレージパスを
    解決し `storage_factory` を差し替え可能にする。
    """

    def __init__(
        self,
        global_config_service: GlobalConfigService,
        timer_service: TimerService | None = None,
        storage_factory: Callable[[Path], FileStorage] | None = None,
    ) -> None:
        self._global_config_service = global_config_service
        self._timer_service = timer_service or TimerService()
        self._storage_factory: Callable[[Path], FileStorage] = storage_factory or FileStorage

    # --- 内部ヘルパ ---

    def _manager_for(self, project: str | None) -> TaskManager:
        return TaskManager(self._storage_factory(resolve_storage_path(project)))

    def _active_project(self) -> str | None:
        return self._global_config_service.get_active_project()

    def _resolve(self, project: ProjectTarget) -> str | None:
        if isinstance(project, ActiveProject):
            return self._active_project()
        return project

    # --- タイマー操作 ---

    def start_timer(
        self,
        duration_seconds: int | None = None,
        task_id: int | None = None,
        force: bool = False,
        now: datetime | None = None,
        project: ProjectTarget = ACTIVE_PROJECT,
    ) -> StartResult:
        """タイマーを開始する。`duration_seconds` が None ならストップウォッチ。

        `force` で実行中タイマーを置き換える場合、置き換えられる側は**破棄せず
        記録して**から差し替える。ユーザーから見て `stop` してから `start` した
        のと同じ結果になり、実測した作業時間が黙って消えない。

        `project` を明示できるのは、対象タスクが属するプロジェクトを
        `state.project` に焼き付ける必要があるためである。ここでアクティブ
        プロジェクトを使うと、別プロジェクトのタスクに対してタイマーを張った
        ときに、停止時の作業セッションが無関係なプロジェクトへ記録される。
        """
        target_project = self._resolve(project)
        task_title: str | None = None
        if task_id is not None:
            # 存在しないタスクにタイマーを紐づけると、停止時に行き場がなくなる。
            # 置き換えより先に検証して、失敗時に実行中タイマーを巻き添えにしない。
            task_title = self._manager_for(target_project).get_task(task_id).title

        replaced: StopResult | None = None
        if force and self._timer_service.get_active() is not None:
            replaced = self.stop_timer(now=now)

        state = TimerState(
            kind=TimerKind.COUNTDOWN if duration_seconds is not None else TimerKind.STOPWATCH,
            project=target_project,
            task_id=task_id,
            task_title=task_title,
            duration_seconds=duration_seconds,
            started_at=now or datetime.now(timezone.utc),
            pid=os.getpid(),
        )
        return StartResult(state=self._timer_service.start(state), replaced=replaced)

    def status(self) -> TimerState | None:
        return self._timer_service.get_active()

    def stop_timer(
        self,
        now: datetime | None = None,
        expected_started_at: datetime | None = None,
    ) -> StopResult:
        """タイマーを止め、経過分を作業セッションとして記録する。

        記録先は **タイマー開始時のプロジェクト**（`state.project`）で解決する。
        実行中に `project use` で切り替えられている可能性があるため、
        現在のアクティブプロジェクトを使ってはいけない。

        `expected_started_at` を渡すと、実行中タイマーがそれと一致する場合だけ
        停止する。フォアグラウンド表示から呼ぶときに使い、別プロセスが張り直した
        タイマーを取り違えて止めてしまうのを防ぐ。
        """
        # 読み取りから解除までをひとつの排他区間に入れる。分けると、2つの
        # プロセスの stop が同じ TimerState を読んで両方が作業セッションを
        # 追記し、同じ時間が二重に計上される。
        with self._timer_service.transaction():
            return self._stop_locked(now, expected_started_at)

    def _stop_locked(
        self, now: datetime | None, expected_started_at: datetime | None
    ) -> StopResult:
        state = self._require_active()
        if expected_started_at is not None and state.started_at != expected_started_at:
            raise AppError(
                "タイマーが別のものに置き換わっています。",
                cause=f"実行中: {TimerService.describe(state, now)}",
                remedy="task-py time status で確認してください。",
            )

        ended_at = now or datetime.now(timezone.utc)
        elapsed = max(0, TimerService.elapsed_seconds(state, ended_at))
        # カウントダウンは宣言した時間が作業の枠なので、それを超えた分は実績にしない。
        # 25分のタイマーを掛けたまま一晩放置した結果が「10時間の作業」になると、
        # この機能の目的（正確な実績）そのものが壊れる。超過分は呼び出し側へ返し、
        # 本当に働いていたなら time log で足してもらう。
        recorded = min(elapsed, state.duration_seconds) if state.duration_seconds else elapsed
        overrun = elapsed - recorded

        if state.task_id is None:
            self._timer_service.clear()
            return StopResult(state, elapsed, overrun, None)

        session = WorkSession(
            started_at=state.started_at,
            ended_at=ended_at,
            seconds=recorded,
            source="timer",
        )
        try:
            self._manager_for(state.project).append_work_session(state.task_id, session)
        except AppError:
            # 実行中に対象タスクが消えた場合。記録先が無いのでタイマーだけ解除し、
            # 記録できなかったことを呼び出し側へ伝える。
            self._timer_service.clear()
            return StopResult(state, elapsed, overrun, None)

        # 記録が成功してから解除する。先に解除すると、保存が失敗（ディスク不足・
        # 権限等）したときに実測した作業時間を取り戻せなくなる。
        self._timer_service.clear()
        return StopResult(state, elapsed, overrun, session)

    def cancel_timer(self) -> TimerState:
        """タイマーを破棄する。作業セッションは記録しない。"""
        with self._timer_service.transaction():
            state = self._require_active()
            self._timer_service.clear()
        return state

    def clear_timer_for_task(
        self,
        project: str | None,
        task_id: int,
        record: bool = True,
        now: datetime | None = None,
    ) -> WorkSession | None:
        """指定タスクのタイマーが実行中なら解除する。

        タスクの完了・アーカイブ・削除で呼ぶ。対象でなければ何もしない。
        `record` が False のときはセッションを記録せずに解除する（削除時は
        記録先ごと消えるため）。
        """
        with self._timer_service.transaction():
            if not self._is_active_for(project, task_id):
                return None
            if not record:
                self._timer_service.clear()
                return None
            return self.stop_timer(now=now).session

    def retarget_timer_for_task(
        self,
        from_project: str | None,
        from_task_id: int,
        to_project: str | None,
        to_task_id: int,
    ) -> bool:
        """実行中タイマーの向き先を、移動後のタスクへ付け替える。

        `move` はタスクを移動先で採番し直すため、付け替えないとタイマーが
        存在しない ID を指したままになる。放置すると停止時に記録が黙って落ち、
        さらに移動元で ID が再利用されると**別のタスクに記録される**。
        """
        with self._timer_service.transaction():
            return self._retarget_locked(from_project, from_task_id, to_project, to_task_id)

    def _retarget_locked(
        self,
        from_project: str | None,
        from_task_id: int,
        to_project: str | None,
        to_task_id: int,
    ) -> bool:
        if not self._is_active_for(from_project, from_task_id):
            return False
        state = self._require_active()
        title: str | None = None
        try:
            title = self._manager_for(to_project).get_task(to_task_id).title
        except AppError:
            title = state.task_title
        self._timer_service.start(
            state.model_copy(
                update={"project": to_project, "task_id": to_task_id, "task_title": title}
            ),
            force=True,
        )
        return True

    def _is_active_for(self, project: str | None, task_id: int) -> bool:
        state = self._timer_service.get_active()
        return state is not None and state.task_id == task_id and state.project == project

    # --- 手動記録 ---

    def log_work(
        self,
        task_id: int,
        seconds: int,
        now: datetime | None = None,
        project: ProjectTarget = ACTIVE_PROJECT,
    ) -> Task:
        """作業時間を手動で記録する。"""
        if seconds <= 0:
            raise AppError(
                "記録する作業時間は1秒以上である必要があります。",
                cause=f"{seconds} 秒が指定されました。",
                remedy="例: task-py time log 1 25m",
            )
        ended_at = now or datetime.now(timezone.utc)
        session = WorkSession(
            started_at=ended_at - timedelta(seconds=seconds),
            ended_at=ended_at,
            seconds=seconds,
            source="manual",
        )
        return self._manager_for(self._resolve(project)).append_work_session(task_id, session)

    def _require_active(self) -> TimerState:
        state = self._timer_service.get_active()
        if state is None:
            raise AppError(
                "実行中のタイマーがありません。",
                cause="~/.task-py/timer.yaml に実行中タイマーの記録がありません。",
                remedy="task-py time start <duration> でタイマーを開始してください。",
            )
        return state

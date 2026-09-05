import unittest.mock as mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig, ProjectEntry
from task_cli.models.time import TimerKind
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.task_manager import TaskManager
from task_cli.services.timer_service import TimerService
from task_cli.storage.file_storage import FileStorage
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_cli.storage.timer_storage import TimerStorage
from task_cli.usecases.task_crud_usecase import TaskCrudUseCase
from task_cli.usecases.time_tracking_usecase import TimeTrackingUseCase

START = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)


class Env:
    """タイムトラッキングとタスク CRUD が同じストレージ群を共有する環境。"""

    def __init__(self, tmp_path: Path, active_project: str | None, projects: list[str]) -> None:
        config_storage = GlobalConfigStorage(tmp_path / "config.yaml")
        entries = [ProjectEntry(id=i + 1, name=n) for i, n in enumerate(projects)]
        config_storage.save(
            GlobalConfig(
                active_project=active_project,
                projects=entries,
                last_project_id=len(entries),
            )
        )
        self.config_storage = config_storage
        self.config_service = GlobalConfigService(config_storage)
        self._storages: dict[Path, FileStorage] = {}
        self._tmp_path = tmp_path
        self.timer_service = TimerService(TimerStorage(tmp_path / "timer.yaml"))

        self.time_uc = TimeTrackingUseCase(
            self.config_service, self.timer_service, self._factory
        )
        self.task_uc = TaskCrudUseCase(
            self.config_service, self._factory, time_tracking=self.time_uc
        )

    def _factory(self, path: Path) -> FileStorage:
        if path not in self._storages:
            unique = f"{path.parent.name}_{path.name}"
            self._storages[path] = FileStorage(self._tmp_path / unique)
        return self._storages[path]

    def use_project(self, name: str | None) -> None:
        config = self.config_storage.load()
        self.config_storage.save(config.model_copy(update={"active_project": name}))

    def manager_for(self, project: str | None) -> TaskManager:
        from task_cli.usecases.task_crud_usecase import resolve_storage_path

        return TaskManager(self._factory(resolve_storage_path(project)))


def make_env(tmp_path: Path, active_project: str | None = "proj-a",
             projects: list[str] | None = None) -> Env:
    return Env(tmp_path, active_project, projects if projects is not None else ["proj-a", "proj-b"])


class TestStartTimer:
    def test_start_without_task(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        state = env.time_uc.start_timer(duration_seconds=1200, now=START).state
        assert state.task_id is None
        assert state.kind is TimerKind.COUNTDOWN
        assert state.duration_seconds == 1200

    def test_start_with_task_records_title_and_project(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        state = env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START).state
        assert state.task_id == 1
        assert state.task_title == "実装する"
        assert state.project == "proj-a"

    def test_start_without_duration_is_stopwatch(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        state = env.time_uc.start_timer(now=START).state
        assert state.kind is TimerKind.STOPWATCH
        assert state.duration_seconds is None

    def test_start_with_unknown_task_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        with pytest.raises(AppError):
            env.time_uc.start_timer(duration_seconds=60, task_id=999, now=START)

    def test_failed_start_leaves_no_timer(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        with pytest.raises(AppError):
            env.time_uc.start_timer(duration_seconds=60, task_id=999, now=START)
        assert env.time_uc.status() is None

    def test_second_start_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.time_uc.start_timer(duration_seconds=60, now=START)
        with pytest.raises(AppError):
            env.time_uc.start_timer(duration_seconds=60, now=START)

    def test_force_replaces(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START)
        state = env.time_uc.start_timer(duration_seconds=60, task_id=2, force=True, now=START).state
        assert state.task_id == 2

    def test_force_records_the_replaced_timer(self, tmp_path: Path) -> None:
        """置き換えで実測した作業時間を黙って捨てない。

        エラーの remedy が stop / cancel と並べて --force を案内している以上、
        --force だけ記録されないのは利用者から見て一貫しない。
        """
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        env.time_uc.start_timer(duration_seconds=3600, task_id=1, now=START)

        started = env.time_uc.start_timer(
            duration_seconds=600, task_id=2, force=True, now=START + timedelta(seconds=2400)
        )

        assert started.replaced is not None
        assert started.replaced.session is not None
        assert env.task_uc.get_task(1).total_worked_seconds == 2400

    def test_force_without_running_timer_reports_no_replacement(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        started = env.time_uc.start_timer(duration_seconds=60, force=True, now=START)
        assert started.replaced is None

    def test_unknown_task_does_not_disturb_the_running_timer(self, tmp_path: Path) -> None:
        """--force でも、開始に失敗したら実行中タイマーを巻き添えにしない。"""
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.time_uc.start_timer(duration_seconds=3600, task_id=1, now=START)

        with pytest.raises(AppError):
            env.time_uc.start_timer(duration_seconds=60, task_id=999, force=True, now=START)

        active = env.time_uc.status()
        assert active is not None
        assert active.task_id == 1


class TestStopTimer:
    def test_stop_records_session(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        result = env.time_uc.stop_timer(now=START + timedelta(seconds=1200))

        assert result.elapsed_seconds == 1200
        assert result.session is not None
        assert result.session.source == "timer"
        assert env.task_uc.get_task(1).total_worked_seconds == 1200

    def test_stop_clears_active_timer(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START)
        env.time_uc.stop_timer(now=START + timedelta(seconds=60))
        assert env.time_uc.status() is None

    def test_stop_without_task_records_nothing(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.time_uc.start_timer(duration_seconds=60, now=START)
        result = env.time_uc.stop_timer(now=START + timedelta(seconds=60))
        assert result.session is None
        assert result.elapsed_seconds == 60

    def test_stop_records_into_the_project_the_timer_started_in(self, tmp_path: Path) -> None:
        """タイマー実行中にプロジェクトを切り替えても、記録先はぶれない。

        現在のアクティブプロジェクトでパス解決すると別プロジェクトに書き込むため、
        この作業で最も間違えやすい箇所として回帰テストを置く。
        """
        env = make_env(tmp_path, active_project="proj-a")
        env.task_uc.add_task("proj-a のタスク")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        env.use_project("proj-b")
        env.task_uc.add_task("proj-b の別タスク")  # proj-b にも ID 1 のタスクができる

        env.time_uc.stop_timer(now=START + timedelta(seconds=1200))

        assert env.manager_for("proj-a").get_task(1).total_worked_seconds == 1200
        assert env.manager_for("proj-b").get_task(1).total_worked_seconds == 0

    def test_stop_after_target_task_deleted(self, tmp_path: Path) -> None:
        """記録先が消えていてもタイマーは解除され、例外にはしない。

        タスクは（usecase のタイマー後始末を通らない）storage 経由で消し、
        タイマーだけが残った状態を作る。
        """
        env = make_env(tmp_path)
        env.task_uc.add_task("消えるタスク")
        env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START)
        env.manager_for("proj-a").delete_task(1)

        result = env.time_uc.stop_timer(now=START + timedelta(seconds=60))
        assert result.session is None
        assert result.elapsed_seconds == 60
        assert env.time_uc.status() is None

    def test_countdown_overrun_is_not_recorded(self, tmp_path: Path) -> None:
        """25分のタイマーを一晩放置しても、10時間の作業として記録しない。

        カウントダウンは宣言した時間が作業の枠なので、超過分は実績に含めず
        `overrun_seconds` で呼び出し側へ伝える。
        """
        env = make_env(tmp_path)
        env.task_uc.add_task("放置されるタスク")
        env.time_uc.start_timer(duration_seconds=1500, task_id=1, now=START)

        result = env.time_uc.stop_timer(now=START + timedelta(hours=10))

        assert result.elapsed_seconds == 36000
        assert result.overrun_seconds == 36000 - 1500
        assert result.session is not None
        assert result.session.seconds == 1500
        assert env.task_uc.get_task(1).total_worked_seconds == 1500

    def test_countdown_stopped_early_records_actual_elapsed(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("早めに止める")
        env.time_uc.start_timer(duration_seconds=1500, task_id=1, now=START)

        result = env.time_uc.stop_timer(now=START + timedelta(seconds=600))

        assert result.overrun_seconds == 0
        assert env.task_uc.get_task(1).total_worked_seconds == 600

    def test_stopwatch_is_not_capped(self, tmp_path: Path) -> None:
        """ストップウォッチには宣言した枠がないので、経過をそのまま記録する。"""
        env = make_env(tmp_path)
        env.task_uc.add_task("計り続ける")
        env.time_uc.start_timer(task_id=1, now=START)

        result = env.time_uc.stop_timer(now=START + timedelta(hours=3))

        assert result.overrun_seconds == 0
        assert env.task_uc.get_task(1).total_worked_seconds == 10800

    def test_stop_refuses_when_timer_was_replaced(self, tmp_path: Path) -> None:
        """フォアグラウンド表示が、張り替えられた別のタイマーを止めないこと。"""
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        mine = env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START).state
        env.time_uc.start_timer(
            duration_seconds=600, task_id=2, force=True, now=START + timedelta(seconds=30)
        )

        with pytest.raises(AppError):
            env.time_uc.stop_timer(
                now=START + timedelta(seconds=60), expected_started_at=mine.started_at
            )

        active = env.time_uc.status()
        assert active is not None
        assert active.task_id == 2

    def test_stop_proceeds_when_timer_matches(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        mine = env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START).state
        result = env.time_uc.stop_timer(
            now=START + timedelta(seconds=60), expected_started_at=mine.started_at
        )
        assert result.session is not None

    def test_timer_survives_a_failed_save(self, tmp_path: Path) -> None:
        """保存に失敗したら、実測した作業時間を失わないようタイマーを残す。"""
        env = make_env(tmp_path)
        env.task_uc.add_task("保存に失敗する")
        env.time_uc.start_timer(duration_seconds=600, task_id=1, now=START)

        storage = env.manager_for("proj-a")

        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("disk full")

        with mock.patch.object(type(storage._storage), "save", boom):  # pyright: ignore[reportPrivateUsage]
            with pytest.raises(OSError):
                env.time_uc.stop_timer(now=START + timedelta(seconds=600))

        assert env.time_uc.status() is not None

    def test_stop_without_timer_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        with pytest.raises(AppError):
            env.time_uc.stop_timer(now=START)

    def test_stop_does_not_touch_updated_at(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        created = env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=60, task_id=1, now=START)
        env.time_uc.stop_timer(now=START + timedelta(seconds=60))
        assert env.task_uc.get_task(1).updated_at == created.updated_at


class TestCancelTimer:
    def test_cancel_records_nothing(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        env.time_uc.cancel_timer()
        assert env.time_uc.status() is None
        assert env.task_uc.get_task(1).total_worked_seconds == 0

    def test_cancel_without_timer_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        with pytest.raises(AppError):
            env.time_uc.cancel_timer()


class TestLogWork:
    def test_log_records_manual_session(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        task = env.time_uc.log_work(1, 1500, now=START)
        assert task.total_worked_seconds == 1500
        assert task.work_sessions[0].source == "manual"
        assert task.work_sessions[0].started_at == START - timedelta(seconds=1500)

    def test_log_accumulates(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.log_work(1, 1500, now=START)
        task = env.time_uc.log_work(1, 600, now=START)
        assert task.total_worked_seconds == 2100

    def test_log_zero_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        with pytest.raises(AppError):
            env.time_uc.log_work(1, 0, now=START)

    def test_log_unknown_task_raises(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        with pytest.raises(AppError):
            env.time_uc.log_work(999, 60, now=START)


class TestClearTimerForTask:
    def test_records_when_task_matches(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        session = env.time_uc.clear_timer_for_task(
            "proj-a", 1, now=START + timedelta(seconds=600)
        )
        assert session is not None
        assert session.seconds == 600
        assert env.time_uc.status() is None

    def test_does_nothing_for_other_task(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        assert env.time_uc.clear_timer_for_task("proj-a", 2, now=START) is None
        assert env.time_uc.status() is not None

    def test_does_nothing_for_same_id_in_another_project(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("proj-a のタスク")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        assert env.time_uc.clear_timer_for_task("proj-b", 1, now=START) is None
        assert env.time_uc.status() is not None

    def test_clears_without_recording(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)
        session = env.time_uc.clear_timer_for_task("proj-a", 1, record=False, now=START)
        assert session is None
        assert env.time_uc.status() is None


class TestTaskLifecycleReleasesTimer:
    """タスクを終える／消すときに実行中タイマーを孤児にしないこと。"""

    def test_complete_records_and_clears(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("実装する")
        env.task_uc.start_task(1)
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        task = env.task_uc.complete_task(1)

        assert env.time_uc.status() is None
        assert task.total_worked_seconds > 0
        assert task.completed_at is not None

    def test_archive_records_and_clears(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("アーカイブする")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        task = env.task_uc.archive_task(1)

        assert env.time_uc.status() is None
        assert task.total_worked_seconds > 0

    def test_delete_clears_without_recording(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("消すタスク")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        env.task_uc.delete_task(1)

        assert env.time_uc.status() is None

    def test_other_tasks_timer_is_left_alone(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        env.time_uc.start_timer(duration_seconds=1200, task_id=2, now=START)

        env.task_uc.delete_task(1)

        active = env.time_uc.status()
        assert active is not None
        assert active.task_id == 2

    def test_failed_completion_leaves_the_timer_running(self, tmp_path: Path) -> None:
        """完了できない状態（open）なら、タイマーを巻き添えで止めない。

        利用者にはエラーしか見えないため、裏でタイマーが止まって作業時間が
        確定していると気づけない。遷移可否を先に確かめてから畳む。
        """
        env = make_env(tmp_path)
        env.task_uc.add_task("open のまま")
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        with pytest.raises(AppError):
            env.task_uc.complete_task(1)

        active = env.time_uc.status()
        assert active is not None
        assert active.task_id == 1
        task = env.task_uc.get_task(1)
        assert task.completed_at is None
        assert task.total_worked_seconds == 0

    def test_failed_archive_leaves_the_timer_running(self, tmp_path: Path) -> None:
        env = make_env(tmp_path)
        env.task_uc.add_task("in_progress のまま")
        env.task_uc.start_task(1)  # in_progress は archive できない
        env.time_uc.start_timer(duration_seconds=1200, task_id=1, now=START)

        with pytest.raises(AppError):
            env.task_uc.archive_task(1)

        assert env.time_uc.status() is not None
        assert env.task_uc.get_task(1).total_worked_seconds == 0


class TestMoveRetargetsTimer:
    """`move` はタスクを採番し直すので、タイマーの向き先も付け替える。"""

    def test_timer_follows_the_moved_task(self, tmp_path: Path) -> None:
        env = make_env(tmp_path, active_project="proj-a")
        env.task_uc.add_task("移動するタスク")
        env.time_uc.start_timer(duration_seconds=3600, task_id=1, now=START)

        moved = env.task_uc.move_task(1, "proj-b")

        active = env.time_uc.status()
        assert active is not None
        assert active.project == "proj-b"
        assert active.task_id == moved.id
        # 経過時間は引き継がれる（開始時刻を張り替えない）
        assert active.started_at == START

    def test_work_is_recorded_onto_the_moved_task(self, tmp_path: Path) -> None:
        env = make_env(tmp_path, active_project="proj-a")
        env.task_uc.add_task("移動するタスク")
        env.time_uc.start_timer(duration_seconds=3600, task_id=1, now=START)

        moved = env.task_uc.move_task(1, "proj-b")
        result = env.time_uc.stop_timer(now=START + timedelta(seconds=1200))

        assert result.session is not None
        assert env.manager_for("proj-b").get_task(moved.id).total_worked_seconds == 1200

    def test_reused_id_in_the_source_project_is_not_credited(self, tmp_path: Path) -> None:
        """移動元で ID が再利用されても、別タスクに記録されないこと。

        `_next_id` は max(id)+1 なので、移動したタスクが最大 ID だった場合に
        新しいタスクが同じ ID を取り戻す。付け替えを怠るとそこへ記録される。
        """
        env = make_env(tmp_path, active_project="proj-a")
        env.task_uc.add_task("移動するタスク")
        env.time_uc.start_timer(duration_seconds=3600, task_id=1, now=START)

        env.task_uc.move_task(1, "proj-b")
        reused = env.task_uc.add_task("移動元の新しいタスク")  # ID 1 を取り戻す
        assert reused.id == 1

        env.time_uc.stop_timer(now=START + timedelta(seconds=1200))

        assert env.manager_for("proj-a").get_task(1).total_worked_seconds == 0

    def test_other_tasks_timer_is_left_alone_on_move(self, tmp_path: Path) -> None:
        env = make_env(tmp_path, active_project="proj-a")
        env.task_uc.add_task("A")
        env.task_uc.add_task("B")
        env.time_uc.start_timer(duration_seconds=3600, task_id=2, now=START)

        env.task_uc.move_task(1, "proj-b")

        active = env.time_uc.status()
        assert active is not None
        assert active.project == "proj-a"
        assert active.task_id == 2

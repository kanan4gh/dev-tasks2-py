from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.models.time import TimerFile, TimerKind, TimerState
from task_cli.services.timer_service import TimerService
from task_cli.storage.timer_storage import TimerStorage

START = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)


def make_service(tmp_path: Path) -> TimerService:
    return TimerService(TimerStorage(tmp_path / "timer.yaml"))


def countdown(seconds: int = 1200, task_id: int | None = 1, project: str | None = None) -> TimerState:
    return TimerState(
        kind=TimerKind.COUNTDOWN,
        project=project,
        task_id=task_id,
        task_title="テストタスク",
        duration_seconds=seconds,
        started_at=START,
    )


def stopwatch(task_id: int | None = 1) -> TimerState:
    return TimerState(kind=TimerKind.STOPWATCH, task_id=task_id, started_at=START)


class TestTimerStorage:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        assert TimerStorage(tmp_path / "timer.yaml").load().active is None

    def test_roundtrip(self, tmp_path: Path) -> None:
        storage = TimerStorage(tmp_path / "timer.yaml")
        storage.save(TimerFile(active=countdown()))
        loaded = storage.load().active
        assert loaded is not None
        assert loaded.task_id == 1
        assert loaded.duration_seconds == 1200
        assert loaded.started_at == START

    def test_broken_yaml_is_treated_as_no_timer(self, tmp_path: Path) -> None:
        """壊れた状態ファイルで無関係なコマンドまで巻き添えにしない。"""
        path = tmp_path / "timer.yaml"
        path.write_text("active: [これは: 不正な, 構造\n", encoding="utf-8")
        assert TimerStorage(path).load().active is None

    def test_schema_mismatch_is_treated_as_no_timer(self, tmp_path: Path) -> None:
        path = tmp_path / "timer.yaml"
        path.write_text("active:\n  task_id: 1\n", encoding="utf-8")  # started_at 欠落
        assert TimerStorage(path).load().active is None


class TestTimerServiceCalculations:
    def test_elapsed_seconds(self) -> None:
        assert TimerService.elapsed_seconds(countdown(), START + timedelta(seconds=300)) == 300

    def test_remaining_seconds(self) -> None:
        assert TimerService.remaining_seconds(countdown(1200), START + timedelta(seconds=300)) == 900

    def test_remaining_goes_negative_when_expired(self) -> None:
        """時間切れを負値で表す。プロセスが落ちていても超過分が分かる。"""
        assert TimerService.remaining_seconds(countdown(60), START + timedelta(seconds=90)) == -30

    def test_stopwatch_has_no_remaining(self) -> None:
        assert TimerService.remaining_seconds(stopwatch(), START + timedelta(seconds=90)) is None

    def test_is_expired(self) -> None:
        assert TimerService.is_expired(countdown(60), START + timedelta(seconds=61)) is True
        assert TimerService.is_expired(countdown(60), START + timedelta(seconds=59)) is False

    def test_stopwatch_is_never_expired(self) -> None:
        assert TimerService.is_expired(stopwatch(), START + timedelta(days=1)) is False

    def test_describe_countdown(self) -> None:
        text = TimerService.describe(countdown(1200), START + timedelta(seconds=300))
        assert "タスク #1" in text
        assert "残り 15:00" in text

    def test_describe_expired(self) -> None:
        text = TimerService.describe(countdown(60), START + timedelta(seconds=90))
        assert "時間切れ" in text

    def test_describe_stopwatch(self) -> None:
        text = TimerService.describe(stopwatch(), START + timedelta(seconds=90))
        assert "経過 01:30" in text

    def test_describe_without_task(self) -> None:
        text = TimerService.describe(countdown(task_id=None), START)
        assert "タスク未指定" in text


class TestTimerServiceLifecycle:
    def test_get_active_is_none_initially(self, tmp_path: Path) -> None:
        assert make_service(tmp_path).get_active() is None

    def test_start_persists_state(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        service.start(countdown())
        active = service.get_active()
        assert active is not None
        assert active.task_id == 1

    def test_start_twice_raises(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        service.start(countdown())
        with pytest.raises(AppError) as excinfo:
            service.start(countdown(task_id=2))
        assert "--force" in excinfo.value.remedy

    def test_force_replaces_running_timer(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        service.start(countdown(task_id=1))
        service.start(countdown(task_id=2), force=True)
        active = service.get_active()
        assert active is not None
        assert active.task_id == 2

    def test_clear_returns_and_removes(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        service.start(countdown())
        cleared = service.clear()
        assert cleared is not None
        assert cleared.task_id == 1
        assert service.get_active() is None

    def test_clear_without_timer_returns_none(self, tmp_path: Path) -> None:
        assert make_service(tmp_path).clear() is None

    def test_state_is_visible_from_a_separate_instance(self, tmp_path: Path) -> None:
        """別プロセス相当の検証。

        GUI（別プロセス）が同じ YAML を読めば同じタイマーが見える、というのが
        この作業の土台要件そのものである。
        """
        path = tmp_path / "timer.yaml"
        TimerService(TimerStorage(path)).start(countdown())

        reader = TimerService(TimerStorage(path))
        active = reader.get_active()
        assert active is not None
        assert active.started_at == START
        # 同じ started_at から同じ式で導出するので、残り時間も一致する
        now = START + timedelta(seconds=300)
        assert TimerService.remaining_seconds(active, now) == 900

    def test_state_survives_a_lost_process(self, tmp_path: Path) -> None:
        """プロセスが落ちても状態は残り、超過分もそのまま読める。"""
        path = tmp_path / "timer.yaml"
        TimerService(TimerStorage(path)).start(countdown(60))
        active = TimerService(TimerStorage(path)).get_active()
        assert active is not None
        assert TimerService.is_expired(active, START + timedelta(seconds=120)) is True

import inspect

import pytest

from task_cli.cli.commands.time import parse_duration
from task_cli.exceptions import AppError


def test_parse_minutes_short() -> None:
    assert parse_duration("20m") == 1200


def test_parse_minutes_long() -> None:
    assert parse_duration("20min") == 1200


def test_parse_hours() -> None:
    assert parse_duration("1h") == 3600


def test_parse_seconds() -> None:
    assert parse_duration("30s") == 30


def test_parse_numeric_only_is_minutes() -> None:
    assert parse_duration("20") == 1200


def test_parse_invalid_raises() -> None:
    with pytest.raises(AppError):
        parse_duration("abc")


def test_parse_invalid_unit_raises() -> None:
    with pytest.raises(AppError):
        parse_duration("10x")


# --- コマンド表面の非破壊 ---

def _params(command_name: str) -> dict[str, object]:
    from task_cli.cli.commands.time import time_app

    info = next(c for c in time_app.registered_commands if c.name == command_name)
    assert info.callback is not None
    return dict(inspect.signature(info.callback).parameters)


def test_time_subcommands_registered() -> None:
    from task_cli.cli.commands.time import time_app

    names = {c.name for c in time_app.registered_commands}
    assert {"start", "status", "stop", "cancel", "log"} <= names


def test_start_duration_stays_positional() -> None:
    """`task-py time start 20m` の呼び出し方を壊さないこと。"""
    import typer.models

    params = _params("start")
    duration = params["duration"]
    assert isinstance(duration, inspect.Parameter)
    assert isinstance(duration.default, typer.models.ArgumentInfo)


def test_start_task_option_is_optional() -> None:
    """--task を付けなくても従来どおり動くこと。"""
    params = _params("start")
    task = params["task"]
    assert isinstance(task, inspect.Parameter)
    assert task.default.default is None  # type: ignore[union-attr]

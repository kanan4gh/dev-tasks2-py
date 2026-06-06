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

import pytest

from task_cli.duration import format_clock, format_duration, parse_duration
from task_cli.exceptions import AppError


class TestParseDuration:
    def test_units(self) -> None:
        assert parse_duration("20m") == 1200
        assert parse_duration("20min") == 1200
        assert parse_duration("1h") == 3600
        assert parse_duration("30s") == 30

    def test_numeric_only_is_minutes(self) -> None:
        assert parse_duration("20") == 1200

    def test_invalid_raises(self) -> None:
        with pytest.raises(AppError):
            parse_duration("abc")


class TestFormatClock:
    def test_under_an_hour(self) -> None:
        assert format_clock(90) == "01:30"

    def test_over_an_hour(self) -> None:
        assert format_clock(3690) == "01:01:30"

    def test_zero(self) -> None:
        assert format_clock(0) == "00:00"

    def test_negative_is_signed(self) -> None:
        """カウントダウンが時間切れを過ぎた状態を表す。"""
        assert format_clock(-90) == "-01:30"


class TestFormatDuration:
    def test_seconds(self) -> None:
        assert format_duration(45) == "45s"

    def test_minutes(self) -> None:
        assert format_duration(1200) == "20m"

    def test_hours_and_minutes(self) -> None:
        assert format_duration(4800) == "1h 20m"

    def test_whole_hours(self) -> None:
        assert format_duration(7200) == "2h"

    def test_zero(self) -> None:
        assert format_duration(0) == "0s"

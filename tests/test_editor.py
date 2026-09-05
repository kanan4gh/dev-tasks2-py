import unittest.mock as mock

import click
import pytest

from task_cli.cli.commands.edit import _description_after_edit, _is_interactive
from task_cli.cli.editor import open_editor
from task_cli.exceptions import AppError


class TestOpenEditor:
    def test_returns_edited_text(self) -> None:
        with mock.patch("click.edit", return_value="編集後の本文"):
            assert open_editor("編集前") == "編集後の本文"

    def test_returns_none_when_cancelled(self) -> None:
        """click.edit は保存せずに閉じると None を返す。"""
        with mock.patch("click.edit", return_value=None):
            assert open_editor("編集前") is None

    def test_decodes_bytes(self) -> None:
        with mock.patch("click.edit", return_value="バイト列".encode("utf-8")):
            assert open_editor("編集前") == "バイト列"

    def test_decodes_bytearray(self) -> None:
        with mock.patch("click.edit", return_value=bytearray("配列".encode("utf-8"))):
            assert open_editor("編集前") == "配列"

    def test_strips_trailing_newlines(self) -> None:
        """エディタが付ける末尾改行を正規化しないと毎回差分が出る。"""
        with mock.patch("click.edit", return_value="本文\n\n"):
            assert open_editor("本文") == "本文"

    def test_keeps_internal_newlines(self) -> None:
        with mock.patch("click.edit", return_value="1行目\n2行目\n"):
            assert open_editor("") == "1行目\n2行目"

    def test_keeps_leading_whitespace(self) -> None:
        with mock.patch("click.edit", return_value="  字下げ\n"):
            assert open_editor("") == "  字下げ"

    def test_click_exception_becomes_app_error(self) -> None:
        """click.edit の起動失敗は ClickException で飛ぶ。

        UsageError だけを拾うと取りこぼし、click 自身のエラーパネルが出て
        原因と対処が表示されなくなる。
        """
        with mock.patch("click.edit", side_effect=click.ClickException("Editing failed")):
            with pytest.raises(AppError) as excinfo:
                open_editor("編集前")
        assert "EDITOR" in excinfo.value.remedy
        assert "Editing failed" in excinfo.value.cause

    def test_usage_error_becomes_app_error(self) -> None:
        with mock.patch("click.edit", side_effect=click.UsageError("editor not found")):
            with pytest.raises(AppError) as excinfo:
                open_editor("編集前")
        assert "EDITOR" in excinfo.value.remedy

    def test_os_error_becomes_app_error(self) -> None:
        with mock.patch("click.edit", side_effect=OSError("no such file")):
            with pytest.raises(AppError):
                open_editor("編集前")

    def test_passes_initial_text_and_extension(self) -> None:
        with mock.patch("click.edit", return_value="x") as edit_mock:
            open_editor("初期値", extension=".txt")
        edit_mock.assert_called_once_with(text="初期値", extension=".txt")


class TestDescriptionAfterEdit:
    def test_edited_text_is_applied(self) -> None:
        assert _description_after_edit("新しい説明", "元の説明") == "新しい説明"

    def test_cancel_applies_nothing(self) -> None:
        assert _description_after_edit(None, "元の説明") is None

    def test_reverting_to_the_original_applies_nothing(self) -> None:
        """`-d` の値を初期値として渡していても、戻したのなら適用しない。

        `-d "new"` でエディタを開き、中で元の内容に戻したのは
        「やっぱり変えない」という意思なので `"new"` を通してはいけない。
        """
        assert _description_after_edit("元の説明", "元の説明") is None

    def test_clearing_the_description_is_applied(self) -> None:
        assert _description_after_edit("", "元の説明") == ""

    def test_clearing_an_already_empty_description_applies_nothing(self) -> None:
        assert _description_after_edit("", "") is None


class TestIsInteractive:
    def test_true_when_both_streams_are_tty(self) -> None:
        with mock.patch("sys.stdin.isatty", return_value=True), \
             mock.patch("sys.stdout.isatty", return_value=True):
            assert _is_interactive() is True

    def test_false_when_stdin_is_not_tty(self) -> None:
        """パイプ入力でエディタを開くと戻ってこられないため、起動してはいけない。"""
        with mock.patch("sys.stdin.isatty", return_value=False), \
             mock.patch("sys.stdout.isatty", return_value=True):
            assert _is_interactive() is False

    def test_false_when_stdout_is_not_tty(self) -> None:
        with mock.patch("sys.stdin.isatty", return_value=True), \
             mock.patch("sys.stdout.isatty", return_value=False):
            assert _is_interactive() is False

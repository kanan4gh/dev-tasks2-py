"""$EDITOR 連携。

`click.edit()` の扱いにくさ（戻り値が `str | bytes | bytearray | None`、
末尾改行がエディタ依存、失敗が click の例外で飛ぶ）をこの1ファイルに閉じ込める。
click は typer の推移的依存として既にインストールされているため、新規依存はない。

エディタの解決は click に委ねる（`VISUAL` → `EDITOR` の順に環境変数を見る）。
click は起動時に値を `shlex.split` してから `subprocess.Popen` に渡すので、
`EDITOR="code --wait"` のような引数付きの指定がそのまま通る。
"""

import click

from task_cli.exceptions import AppError

_REMEDY = (
    '環境変数 EDITOR を設定してください。例: export EDITOR="code --wait"'
    "（VS Code の場合は --wait が必須です）"
)


def open_editor(initial: str, extension: str = ".md") -> str | None:
    """エディタを開いて編集後の本文を返す。キャンセル・無変更なら None を返す。"""
    try:
        edited = click.edit(text=initial, extension=extension)
    except click.ClickException as e:
        # click は起動失敗を ClickException で投げる（UsageError はその一部でしかない）。
        # 拾い損ねると click 自身のエラーパネルが出て、原因と対処が表示されない。
        raise AppError(
            "エディタを起動できませんでした。",
            cause=e.format_message(),
            remedy=_REMEDY,
        ) from e
    except OSError as e:
        raise AppError(
            "エディタの起動に失敗しました。",
            cause=str(e),
            remedy=_REMEDY,
        ) from e

    if edited is None:
        return None
    if isinstance(edited, (bytes, bytearray)):
        edited = edited.decode("utf-8")
    # エディタは末尾に改行を足すことが多い。正規化しないと毎回差分が出る。
    return edited.rstrip("\n")

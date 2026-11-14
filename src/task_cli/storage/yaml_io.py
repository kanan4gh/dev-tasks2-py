"""保存ファイルの読み込みで、壊れたファイルを `StorageReadError` にする補助。

読み込みで出る例外(YAML の構文エラー・文字コード不正・モデルの検証エラー)を
そのまま通すと、CLI ではトレースバック、Web では素の 500、MCP ではツールの失敗に
なり、どのファイルをどう直せばよいかが示されない。ここで `AppError` に包むことで、
3つの入口が同じ message / cause / remedy を出せる。

タイマーは対象外である(`TimerStorage` は壊れた状態ファイルを「動いていない」
として扱う。失ってもデータは壊れないため)。
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from task_cli.exceptions import StorageReadError

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

_MESSAGE = "保存先ファイルを読み込めません"
_SHAPE = {list: "リスト（- で始まる項目の並び）", dict: "キーと値の組"}


def _remedy(path: Path) -> str:
    bak = Path(str(path) + ".bak")
    if bak.exists():
        return f"ファイルを手で直してください。{bak} が残っています（書き込み途中で止まったときの退避。古い内容の可能性があるので、中身を確認してから戻してください）"
    return "ファイルを手で直してください（YAML の書式を確認する）。直せない場合は、ファイルを移動して作り直します"


def read_yaml(path: Path, expect: type) -> Any:
    """`path` を YAML として読む。壊れていれば `StorageReadError`。

    `expect` は最上位の型（タスク等は `list`、設定は `dict`）。空のファイル
    （`None` や空）は検査せずそのまま返す。違う形なら、モデルの検証に進む前に
    「最上位の形が違う」と示す。
    """
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f"行{mark.line + 1}・列{mark.column + 1}: " if mark is not None else ""
        problem = getattr(e, "problem", None) or "YAML として読めません"
        raise StorageReadError(_MESSAGE, f"{path}: {where}{problem}", _remedy(path)) from e
    except UnicodeDecodeError as e:
        raise StorageReadError(
            _MESSAGE, f"{path}: UTF-8 として読めません（行・列は不明: {e.reason}）", _remedy(path)
        ) from e
    else:
        if data and not isinstance(data, expect):
            raise StorageReadError(
                _MESSAGE,
                f"{path}: 最上位が {_SHAPE[expect]} ではありません（{type(data).__name__}）",
                _remedy(path),
            )
        return data


def _describe(error: ValidationError) -> str:
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"]) or "(全体)"
    return f"{field}: {first['msg']}"


def validated(path: Path, build: Callable[[], T]) -> T:
    """`build()`(モデルの検証を行う関数)の検証エラーを `StorageReadError` にする。"""
    try:
        return build()
    except ValidationError as e:
        raise StorageReadError(_MESSAGE, f"{path}: 値が不正です（{_describe(e)}）", _remedy(path)) from e


def validated_list(path: Path, model: type[M], items: list[Any]) -> list[M]:
    """`items` の各項目を `model` で検証する。不正な項目が複数あれば、最初の項目と件数を示す。"""
    result: list[M] = []
    bad: list[tuple[int, ValidationError]] = []
    for index, item in enumerate(items):
        try:
            result.append(model.model_validate(item))
        except ValidationError as e:
            bad.append((index, e))
    if bad:
        index, error = bad[0]
        more = f"。ほかに {len(bad) - 1} 件" if len(bad) > 1 else ""
        raise StorageReadError(
            _MESSAGE,
            f"{path}: 値が不正です（{index + 1}件目の {_describe(error)}{more}）",
            _remedy(path),
        ) from error
    return result

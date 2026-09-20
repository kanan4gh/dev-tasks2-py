"""画面が見ていた版と、いま保存されている版を照合する。

GUI はタスクを画面に出したまま放置される。その間に CLI や MCP サーバーが同じ
タスクを変えているかもしれない。**黙って上書きしない**ために、画面が持っていた
版を送らせて保存の直前に照合する。

版には `Task.updated_at` をそのまま使う。`serializers` が一覧・詳細の両方で
返しているので、画面は追加の取得なしに送れる。

**`append_work_session` は `updated_at` を動かさない**（#38 で意図して決めた）。
おかげで、タイマーを止めて作業セッションが足されても 409 にならない。編集と
競合していないものを競合と呼ばずに済んでいる。
"""

from starlette.datastructures import Headers

from task_cli.exceptions import AppError
from task_cli.models.task import Task

IF_MATCH = "if-match"


class PreconditionRequired(AppError):
    """`If-Match` が無い。"""


class Conflict(AppError):
    """`If-Match` が現在の版と食い違う。"""

    def __init__(self, message: str, cause: str, remedy: str, current: Task) -> None:
        super().__init__(message, cause, remedy)
        self.current = current


def required_version(headers: Headers) -> str:
    """`If-Match` から期待する版を取り出す。無ければ 428 相当。

    **「省略したら上書き」にしない。** 黙って危険側に倒れる既定値を作ると、
    クライアントを書く側が気づかないまま競合検出を失う。
    """
    value = headers.get(IF_MATCH)
    if not value or value.strip() == "*":
        raise PreconditionRequired(
            "更新するには、いま表示している内容の版が必要です。",
            cause="If-Match ヘッダが指定されていません。",
            remedy="タスクを取得し直してから操作してください。",
        )
    return _unquote(value)


def ensure_matches(current: Task, expected: str) -> None:
    """現在の版と照合する。食い違えば 409 相当（現在の内容を添える）。"""
    actual = version_of(current)
    if actual == expected:
        return
    raise Conflict(
        "このタスクは別の場所で変更されています。",
        cause="画面に表示していた内容は最新ではありません。",
        remedy="最新の内容を確認してから操作し直してください。",
        current=current,
    )


def version_of(task: Task) -> str:
    """タスクの版。

    **クライアントが受け取ったのと同じ文字列**を作る必要がある。`serializers` は
    `model_dump(mode="json")` を使っており、pydantic は UTC を `Z` で書く。
    一方 `datetime.isoformat()` は `+00:00` を書く。ここを揃えないと
    **毎回かならず 409 になる**（画面からは「何をしても保存できない」）。

    同じ結果を2通りの方法で作らないよう、ここも pydantic に出させる。
    """
    return str(task.model_dump(mode="json")["updated_at"])


def _unquote(value: str) -> str:
    """`If-Match` は ETag の形で来ることがあるので、包みを外す。

    `"v"`（強い検証子）と `W/"v"`（弱い検証子）の両方を受ける。弱い検証子の
    `W/` を外さないと、プロキシが付け替えただけで**毎回かならず 409** になる。
    `*`（何でも良い）は「版を確認しない」の意味になり、競合検出を無効にして
    しまうので受け付けない（428 と同じ扱い）。
    """
    stripped = value.strip()
    if stripped.startswith(("W/", "w/")):
        stripped = stripped[2:]
    if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
        return stripped[1:-1]
    return stripped

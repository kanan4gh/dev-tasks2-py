"""書き込みリクエストが、このサーバ自身の画面から来たことを確かめる。

**`Host` の検証（`server.py`）では CSRF は防げない。** あれは DNS リバインディング
対策であり、攻撃者のページから

    fetch("http://127.0.0.1:8765/api/inbox/tasks", {method: "POST", ...})

を投げられた場合、`Host` はこちらの正しい値になる。別の検査が要る。

**考え方**: 攻撃者は利用者のブラウザ越しにしか来られない。そしてブラウザは、
ページ側から偽装できない形で出自を伝えてくる。だから「ブラウザが送ってくる
出自が同一オリジンでない」ものを弾けばよい。ヘッダが1つも無い場合（curl や
テスト）は通す — それは攻撃経路ではないからである。

トークン方式は採らない。サーバが状態を持たないという原則を崩さずに済み、
単一利用者のローカル面にはこれで足りる。
"""

from urllib.parse import urlsplit

from starlette.requests import Request

from task_cli.exceptions import AppError

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
JSON_CONTENT_TYPE = "application/json"


class Forbidden(AppError):
    """出自の検査に落ちた。"""


class UnsupportedMedia(AppError):
    """`Content-Type` が JSON でない。"""


def verify(request: Request, allowed_hosts: list[str]) -> None:
    """書き込みなら出自を検査する。読み取りは素通し。"""
    if request.method not in WRITE_METHODS:
        return

    _require_json(request)
    _require_same_origin(request)
    _require_known_origin(request, allowed_hosts)


def _require_json(request: Request) -> None:
    """`Content-Type: application/json` を必須にする。

    これ自体が第一の防御になる。クロスオリジンで JSON を送ると、ブラウザは
    本番のリクエストの前に**プリフライト**（`OPTIONS`）を投げる。こちらは
    `OPTIONS` を登録していないので 405 になり、本番のリクエストは飛ばない。

    逆にフォーム形式や `text/plain` を受け付けると、それらは「単純リクエスト」
    としてプリフライトなしで届いてしまう。
    """
    content_type = request.headers.get("content-type", "")
    if content_type.split(";")[0].strip().lower() != JSON_CONTENT_TYPE:
        raise UnsupportedMedia(
            "この形式のリクエストは受け付けません。",
            cause=f"Content-Type が {content_type or '未指定'} でした。",
            remedy=f"Content-Type: {JSON_CONTENT_TYPE} を付けてください。",
        )


def _require_same_origin(request: Request) -> None:
    """`Sec-Fetch-Site` があれば `same-origin` だけを通す。

    現行のブラウザは必ず送り、**ページ側の JavaScript からは偽装できない**。
    送ってこない相手（古いブラウザ・curl）は下の `Origin` 検査に任せる。
    """
    site = request.headers.get("sec-fetch-site")
    if site is None or site == "same-origin":
        return
    raise Forbidden(
        "別のサイトからの書き込みは受け付けません。",
        cause=f"Sec-Fetch-Site が {site} でした。",
        remedy="task-py web が開いた画面から操作してください。",
    )


def _require_known_origin(request: Request, allowed_hosts: list[str]) -> None:
    """`Origin` があればホストが許可リスト内であることを求める。

    `Sec-Fetch-Site` を送らないブラウザ向けの保険。ポートは見ない。別ポートに
    居るのは自分自身か、同じ機械の別のローカルサーバであり、後者は
    そもそもファイルを直接読めるので防御の対象にならない。
    """
    origin = request.headers.get("origin")
    if origin is None:
        return
    host = urlsplit(origin).hostname
    if host in allowed_hosts:
        return
    raise Forbidden(
        "別のサイトからの書き込みは受け付けません。",
        cause=f"Origin が {origin} でした。",
        remedy="task-py web が開いた画面から操作してください。",
    )

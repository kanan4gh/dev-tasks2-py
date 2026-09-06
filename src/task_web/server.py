"""Starlette アプリの組み立てと uvicorn の起動。

組み立て（`create_app`）と起動（`run`）を分けてあるのは、テストが uvicorn を
上げずに `TestClient` でアプリを直接叩けるようにするためである。
"""

import errno
import os
import socket
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from task_cli.exceptions import AppError
from task_web.api import api_routes

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

STATIC_DIR = Path(__file__).parent / "static"

# `Host` ヘッダの許可リスト。127.0.0.1 に待ち受けるだけでは DNS リバインディングを
# 防げない（利用者が開いた別のサイトが、自分のドメインを 127.0.0.1 に解決させれば
# このサーバに到達できる）。starlette の実装は `host.split(":")[0]` なので
# ポート番号は自動的に落ちる。
#
# IPv6 は対象外。`[::1]:8765` は上記の split で `[` になり照合に失敗するが、
# 待ち受けを IPv4 の 127.0.0.1 に限っているため到達しない。
#
# 当初はここに `testserver`（`TestClient` の既定 base_url）も入れていたが、
# **本番の許可リストにテスト専用の名前を残すのは防御を弱める**。`testserver` を
# 127.0.0.1 に解決する経路（内部 DNS・検索ドメイン・hosts）があれば、その名前で
# 到達できてしまう。`create_app()` が許可リストを引数で受けるので、テスト側が
# 明示的に渡せばよい。
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


class _RevalidatingStaticFiles(StaticFiles):
    """毎回 ETag で検証させる静的配信。

    `Cache-Control` を付けないと、ブラウザは経験則でキャッシュを使い回し、
    **利用者が task-py を更新しても古い画面のままになる**（実際に開発中、
    JavaScript を直してもブラウザが古い版を実行し続けた）。`no-cache` は
    「使うな」ではなく「使う前に必ず確かめろ」であり、変更が無ければ 304 で
    済む。相手はローカルサーバなので検証の往復は無視できる。
    """

    def file_response(
        self,
        full_path: "str | os.PathLike[str]",
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["cache-control"] = "no-cache"
        return response


def create_app(allowed_hosts: list[str] | None = None) -> Starlette:
    """読み取り専用の Starlette アプリを組み立てる。

    ルーティングには `GET` しか登録しない。「書き込まないよう気をつける」ので
    はなく、書き込みメソッドが 405 になることを機構で担保する。
    """
    routes = [
        *api_routes(),
        # 静的配信は最後にマウントする。先頭に置くと `/api/*` を飲み込む。
        Mount("/", app=_RevalidatingStaticFiles(directory=STATIC_DIR, html=True), name="static"),
    ]
    middleware = [
        Middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts if allowed_hosts is not None else ALLOWED_HOSTS,
        )
    ]
    return Starlette(routes=routes, middleware=middleware)


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """uvicorn でサーバを起動する。ポートが埋まっていれば `AppError`。

    待ち受けるアドレス自体を許可リストへ足す。足さないと、`127.0.0.1` 以外に
    bind したときにサーバは起動するのに全リクエストが 400 で弾かれる、という
    「起動しているのに何も見えない」状態になる。
    """
    _ensure_port_available(host, port)
    uvicorn.run(
        create_app(allowed_hosts=_allowed_hosts_for(host)),
        host=host,
        port=port,
        log_level="warning",
    )


def _allowed_hosts_for(host: str) -> list[str]:
    if host in ALLOWED_HOSTS:
        return list(ALLOWED_HOSTS)
    return [*ALLOWED_HOSTS, host]


def _ensure_port_available(host: str, port: int) -> None:
    """待ち受けられるかを先に確かめる。

    uvicorn に任せると `SystemExit` とスタックトレースになり、利用者には何が
    起きたのか分からない。空きポートを自動で探す方式は採らない。ブックマークした
    URL が黙って変わるほうが困るためである。
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((host, port))
    except OSError as e:
        if isinstance(e, socket.gaierror) or e.errno in (errno.EADDRINUSE, errno.EACCES):
            # gaierror も拾うのは、IPv4 で解決できないアドレス（`::1` 等）を
            # 渡されたときに生の例外を出さないため。
            raise AppError(
                "指定されたアドレスとポートで待ち受けられません。",
                cause=f"{host}:{port} は使用中か、IPv4 のアドレスとして解決できません。",
                remedy="task-py web --port <別の番号> で空いているポートを指定してください。",
            ) from e
        raise
    finally:
        probe.close()

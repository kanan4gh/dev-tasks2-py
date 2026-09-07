import threading
import webbrowser

import typer

from task_cli.cli.renderer import render_error, render_info
from task_cli.exceptions import AppError


def web(
    port: int = typer.Option(8765, "--port", "-p", help="待ち受けるポート"),
    no_open: bool = typer.Option(False, "--no-open", help="ブラウザを自動で開かない"),
) -> None:
    """ローカル Web GUI を起動します（読み取り専用）。

    待ち受けは 127.0.0.1 に固定する。`--host` を用意しないのは、外部から届く
    アドレスに bind できてしまうと、認証も CSRF 対策も持たないこの面が
    ネットワークへ露出するためである（`docs` のスコープ外に「リモートからの
    アクセス」を明記している）。
    """
    host = "127.0.0.1"
    # 起動そのものが重いので、import はコマンドが呼ばれてから行う。
    # これがモジュール先頭にあると、`task-py add` のような無関係なコマンドまで
    # starlette と uvicorn の読み込みを待たされる。
    from task_web.server import run

    url = f"http://{host}:{port}/"
    try:
        if not no_open:
            _open_browser_soon(url)
        render_info(f"ローカル Web GUI を起動します: {url}")
        render_info("停止するには Ctrl+C を押してください。")
        run(host=host, port=port)
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        render_info("停止しました。")


def _open_browser_soon(url: str) -> None:
    """サーバが待ち受け始めた頃にブラウザを開く。

    `run()` は戻ってこないので、その前に開くと接続拒否になることがある。
    タイマーで少し遅らせ、デーモンスレッドにして終了を妨げないようにする。
    """
    timer = threading.Timer(0.5, webbrowser.open, args=(url,))
    timer.daemon = True
    timer.start()

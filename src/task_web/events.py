"""他プロセスの変更をブラウザへ伝える SSE。

送るのは「変わった」という事実とリビジョン値だけである。差分は作らない
（`watcher.py` の説明を参照）。クライアントは通知を受けて、いま表示している
ものを取り直す。
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from sse_starlette import EventSourceResponse
from starlette.requests import Request

from task_cli.cli.deps import get_global_config_service
from task_web.watcher import revision

POLL_INTERVAL_SECONDS = 1.0


async def events_endpoint(request: Request) -> EventSourceResponse:
    return EventSourceResponse(_revision_stream(request))


async def _revision_stream(request: Request) -> AsyncIterator[dict[str, Any]]:
    """リビジョンが変わったときだけ送る。

    接続直後に一度だけ現在値を送るのは、切断と再接続の間に起きた変更を
    取りこぼさないためである（`EventSource` はネットワークが切れると自動で
    再接続する）。
    """
    config_service = get_global_config_service()
    last = revision(config_service)
    yield {"event": "revision", "data": last}

    try:
        while not await request.is_disconnected():
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            current = revision(config_service)
            if current != last:
                last = current
                yield {"event": "revision", "data": current}
    except asyncio.CancelledError:
        # クライアントが閉じただけなので、握りつぶして静かに終わる。
        return

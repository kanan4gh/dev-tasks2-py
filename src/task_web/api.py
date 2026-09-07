"""読み取り専用の JSON エンドポイント。

HTTP のパスとクエリを `usecases` の引数へ変換し、戻り値を JSON にするだけの層で
ある。ドメインの判断はここに置かない。

**Inbox と名前付きプロジェクトはパスで分ける**（`/api/inbox/tasks` と
`/api/projects/{name}/tasks`）。クエリ1つで両方を表そうとすると `None`（Inbox）と
「未指定」を URL 上で区別できず、`project=inbox` のような予約語方式にすると
`inbox` という名前のプロジェクトを作れなくなる。

**`project` は常に明示して usecase を呼ぶ。** 既定値の `ACTIVE_PROJECT` は
使わない。GUI は全プロジェクトを同時に扱う面であり、`~/.task-py/config.yaml` の
アクティブプロジェクトというプロセス外の共有状態に依存すると、CLI が
`project use` した瞬間に画面と実際の対象がずれる。
"""

import functools
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Route

from task_cli.cli.deps import (
    get_global_config_service,
    get_time_tracking_use_case,
    get_use_case,
)
from task_cli.exceptions import AppError
from task_cli.models.task import Priority, TaskStatus
from task_cli.services.daily_service import DailyService
from task_cli.services.task_manager import TaskFilter
from task_web import serializers
from task_web.events import events_endpoint
from task_web.watcher import revision

_SORT_KEYS = ("id", "priority", "due_date", "created_at")


def api_routes() -> list[BaseRoute]:
    """読み取りだけを登録する。

    書き込みメソッドは登録しないので 405 になる。「書き込まないよう気をつける」
    のではなく、ルーティングで機構的に担保する。
    """
    return [
        Route("/api/state", state, methods=["GET"]),
        Route("/api/overview", overview, methods=["GET"]),
        Route("/api/tasks", all_tasks, methods=["GET"]),
        Route("/api/search", search, methods=["GET"]),
        Route("/api/events", events_endpoint, methods=["GET"]),
        Route("/api/inbox/tasks", inbox_tasks, methods=["GET"]),
        Route("/api/inbox/tasks/{task_id:int}", inbox_task_detail, methods=["GET"]),
        Route("/api/projects/{name}/tasks", project_tasks, methods=["GET"]),
        Route("/api/projects/{name}/tasks/{task_id:int}", project_task_detail, methods=["GET"]),
    ]


# --- エラー変換 -------------------------------------------------------------


class BadRequest(AppError):
    """クエリの値が不正。`AppError` と同じ形で原因と対処を持つ。"""


def _error_response(error: AppError, status: int) -> JSONResponse:
    """`AppError` をそのまま JSON にする。

    CLI が表示するのと同じ message / cause / remedy を返す。同じ原因に対して
    2つの説明を作らないためである。
    """
    # `AppError` は message を属性で持たず `Exception` の引数として持つ。
    # `renderer.render_error` が `f"{error}"` で取り出しているのと同じ方法に揃える。
    return JSONResponse(
        {"error": {"message": str(error), "cause": error.cause, "remedy": error.remedy}},
        status_code=status,
    )


def _handle(fn: Any) -> Any:
    """`AppError` を HTTP に写す。

    ラッパを **同期関数のまま**にしておくのが重要である。`async def` にすると
    Starlette が「非同期エンドポイント」と判定してイベントループ上で直接実行し、
    YAML の読み込みや `flock` の待ちがループを塞ぐ。塞がれている間は他の
    リクエストも開いている SSE も止まる。同期のままなら Starlette が
    スレッドプールへ逃がしてくれる。
    """

    @functools.wraps(fn)
    def wrapper(request: Request) -> JSONResponse:
        try:
            return fn(request)
        except BadRequest as e:
            return _error_response(e, 400)
        except AppError as e:
            return _error_response(e, 404)

    return wrapper


# --- クエリの解釈 -----------------------------------------------------------


def _task_filter(request: Request) -> TaskFilter | None:
    """`?status=&priority=&sort=` を `TaskFilter` にする。

    `status` は繰り返し指定できる（`?status=open&status=in_progress`）。
    未知の値は握りつぶさず 400 にする。黙って全件を返すと、利用者は絞り込みが
    効いていないことに気づけない。
    """
    params = request.query_params
    statuses: list[TaskStatus] = []
    for raw in params.getlist("status"):
        try:
            statuses.append(TaskStatus(raw))
        except ValueError as e:
            raise BadRequest(
                "status の値が不正です。",
                cause=f"'{raw}' は有効なステータスではありません。",
                remedy=f"次のいずれかを指定してください: {', '.join(s.value for s in TaskStatus)}",
            ) from e

    priority: Priority | None = None
    raw_priority = params.get("priority")
    if raw_priority is not None:
        try:
            priority = Priority(raw_priority)
        except ValueError as e:
            raise BadRequest(
                "priority の値が不正です。",
                cause=f"'{raw_priority}' は有効な優先度ではありません。",
                remedy=f"次のいずれかを指定してください: {', '.join(p.value for p in Priority)}",
            ) from e

    sort = params.get("sort", "id")
    if sort not in _SORT_KEYS:
        raise BadRequest(
            "sort の値が不正です。",
            cause=f"'{sort}' は有効な並び順ではありません。",
            remedy=f"次のいずれかを指定してください: {', '.join(_SORT_KEYS)}",
        )

    if not statuses and priority is None and sort == "id":
        return None
    return TaskFilter(
        status=statuses or None,
        priority=priority,
        sort=sort,  # pyright: ignore[reportArgumentType]
    )


# --- エンドポイント ---------------------------------------------------------


@_handle
def state(request: Request) -> JSONResponse:
    """画面の骨組みに要る情報。

    `active_project` は**表示のためだけ**に返す。API はこれを操作対象の決定には
    使わない。
    """
    config_service = get_global_config_service()
    config = config_service.get_all()
    return JSONResponse(
        {
            "active_project": config.active_project,
            "projects": [serializers.project_entry(p) for p in config.projects],
            "revision": revision(config_service),
        }
    )


@_handle
def overview(request: Request) -> JSONResponse:
    """`task-py overview` 相当。"""
    uc = get_use_case()
    config_service = get_global_config_service()
    active = config_service.get_active_project()
    active_filter = TaskFilter(status=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS])

    daily = DailyService()
    # ensure=False は必須。既定の list_today() は「今日のログ」を書き足すため、
    # 読み取り専用のはずの画面を開くたびに daily/log.yaml へ書き込んでしまう
    # （ルーティーンが1件も無いときは毎回書き込む）。
    routines = daily.list_today(include_paused=True, ensure=False)

    return JSONResponse(
        {
            "active_project": active,
            "routines": [serializers.routine(r, status) for r, status in routines],
            "daily_stats": daily.stats(),
            "timer": serializers.timer_state(get_time_tracking_use_case().status()),
            "tasks": serializers.grouped_tasks(uc.list_all_projects(active_filter)),
        }
    )


@_handle
def all_tasks(request: Request) -> JSONResponse:
    """`task-py list --all` 相当。Inbox と全プロジェクトをまとめて返す。"""
    groups = get_use_case().list_all_projects(_task_filter(request))
    return JSONResponse(serializers.grouped_tasks(groups))


@_handle
def inbox_tasks(request: Request) -> JSONResponse:
    tasks = get_use_case().list_tasks(_task_filter(request), project=None)
    return JSONResponse({"project": None, "tasks": [serializers.task_summary(t) for t in tasks]})


@_handle
def project_tasks(request: Request) -> JSONResponse:
    name = _require_project(request)
    tasks = get_use_case().list_tasks(_task_filter(request), project=name)
    return JSONResponse({"project": name, "tasks": [serializers.task_summary(t) for t in tasks]})


@_handle
def inbox_task_detail(request: Request) -> JSONResponse:
    task = get_use_case().get_task(request.path_params["task_id"], project=None)
    return JSONResponse({"project": None, "task": serializers.task_detail(task)})


@_handle
def project_task_detail(request: Request) -> JSONResponse:
    name = _require_project(request)
    task = get_use_case().get_task(request.path_params["task_id"], project=name)
    return JSONResponse({"project": name, "task": serializers.task_detail(task)})


@_handle
def search(request: Request) -> JSONResponse:
    """`task-py search` を全プロジェクト横断に広げたもの。"""
    keyword = request.query_params.get("q", "").strip()
    if not keyword:
        raise BadRequest(
            "検索語が指定されていません。",
            cause="クエリ q が空です。",
            remedy="?q=<検索語> を付けてください。",
        )
    groups = get_use_case().search_all_projects(keyword)
    payload = serializers.grouped_tasks(groups)
    payload["query"] = keyword
    return JSONResponse(payload)


def _require_project(request: Request) -> str:
    """パスのプロジェクト名が実在することを確かめる。

    実在確認をしないと、存在しないプロジェクトが「タスク0件」として 200 で
    返ってしまい、打ち間違いに気づけない。
    """
    name: str = request.path_params["name"]
    for entry in get_global_config_service().get_all().projects:
        if entry.name == name:
            return name
    raise AppError(
        "プロジェクトが見つかりません。",
        cause=f"プロジェクト '{name}' は存在しません。",
        remedy="task-py project list で有効な名前を確認してください。",
    )

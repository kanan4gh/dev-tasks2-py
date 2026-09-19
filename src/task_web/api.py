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
import json
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route

from task_cli.cli.deps import (
    get_global_config_service,
    get_time_tracking_use_case,
    get_use_case,
)
from task_cli.exceptions import AppError
from task_cli.models.task import Priority, Task, TaskStatus
from task_cli.services.daily_service import DailyService
from task_cli.services.task_manager import InvalidTaskData, TaskFilter
from task_web import csrf, serializers, versions
from task_web.events import events_endpoint
from task_web.watcher import revision

_SORT_KEYS = ("id", "priority", "due_date", "created_at")


def api_routes(allowed_hosts: list[str] | None = None) -> list[BaseRoute]:
    """読み取りと書き込みのエンドポイントを登録する。

    登録しないメソッドは 405 になる。`OPTIONS` を登録しないのは意図的で、
    クロスオリジンの JSON 書き込みに必要なプリフライトが通らなくなる
    （`csrf.py` の第一の防御）。
    """
    hosts = allowed_hosts if allowed_hosts is not None else []
    write = _writer(hosts)

    task_paths = ("/api/inbox/tasks", "/api/projects/{name}/tasks")
    routes: list[BaseRoute] = [
        Route("/api/state", state, methods=["GET"]),
        Route("/api/overview", overview, methods=["GET"]),
        Route("/api/tasks", all_tasks, methods=["GET"]),
        Route("/api/search", search, methods=["GET"]),
        Route("/api/events", events_endpoint, methods=["GET"]),
    ]
    for base in task_paths:
        routes += [
            Route(base, _listing_for(base), methods=["GET"]),
            Route(base, write(create_task), methods=["POST"]),
            Route(f"{base}/{{task_id:int}}", _detail_for(base), methods=["GET"]),
            Route(f"{base}/{{task_id:int}}", write(edit_task), methods=["PATCH"]),
            Route(f"{base}/{{task_id:int}}", write(delete_task), methods=["DELETE"]),
            Route(f"{base}/{{task_id:int}}/start", write(start_task), methods=["POST"]),
            Route(f"{base}/{{task_id:int}}/done", write(complete_task), methods=["POST"]),
            Route(f"{base}/{{task_id:int}}/archive", write(archive_task), methods=["POST"]),
            Route(f"{base}/{{task_id:int}}/move", write(move_task), methods=["POST"]),
        ]
    return routes


def _listing_for(base: str) -> Any:
    return inbox_tasks if base.startswith("/api/inbox") else project_tasks


def _detail_for(base: str) -> Any:
    return inbox_task_detail if base.startswith("/api/inbox") else project_task_detail


def _target_project(request: Request) -> str | None:
    """パスが指す保存先。Inbox は `None`。

    書き込みでも読み取りと同じく**常に明示**する。グローバルのアクティブ
    プロジェクトは使わない。
    """
    if "name" not in request.path_params:
        return None
    return _require_project(request)


# --- エラー変換 -------------------------------------------------------------


class BadRequest(AppError):
    """クエリ・本文の値が不正。`AppError` と同じ形で原因と対処を持つ。"""


class NotFound(AppError):
    """対象が存在しない。"""


# 例外のクラスから HTTP の状態コードを引く。読み取りだけだったときは
# 「BadRequest→400 / その他→404」の2分岐で足りたが、書き込みでは
# 「見つからない」「値が不正」「出自が不正」「版が古い」が混ざる。
_STATUS_BY_ERROR: tuple[tuple[type[AppError], int], ...] = (
    (BadRequest, 400),
    (InvalidTaskData, 400),
    (csrf.Forbidden, 403),
    (NotFound, 404),
    (versions.Conflict, 409),
    (csrf.UnsupportedMedia, 415),
    (versions.PreconditionRequired, 428),
)


def _status_for(error: AppError) -> int:
    for kind, status in _STATUS_BY_ERROR:
        if isinstance(error, kind):
            return status
    # ドメイン層が投げる素の AppError は「見つからない」か「その状態では
    # できない」。前者に寄せる（読み取り面からの挙動を変えない）。
    return 404


def _error_response(error: AppError, status: int) -> JSONResponse:
    """`AppError` をそのまま JSON にする。

    CLI が表示するのと同じ message / cause / remedy を返す。同じ原因に対して
    2つの説明を作らないためである。
    """
    # `AppError` は message を属性で持たず `Exception` の引数として持つ。
    # `renderer.render_error` が `f"{error}"` で取り出しているのと同じ方法に揃える。
    body: dict[str, Any] = {
        "error": {"message": str(error), "cause": error.cause, "remedy": error.remedy}
    }
    if isinstance(error, versions.Conflict):
        # 409 のときは現在の内容を添える。画面が最新を出し直せるようにするため、
        # 「取り直してください」とだけ言って終わらせない。
        body["current"] = serializers.task_detail(error.current)
    return JSONResponse(body, status_code=status)


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
        except AppError as e:
            return _error_response(e, _status_for(e))

    return wrapper


def _writer(allowed_hosts: list[str]) -> Any:
    """書き込みエンドポイントのラッパを作る。

    本文を読むには `await` が要るので `async def` にせざるを得ない。しかし
    ドメインの処理をそのままループ上で走らせると、YAML の読み込みと `flock` の
    待ちが他のリクエストと開いている SSE を止める（読み取り面で一度踏んだ）。
    **本文の読み取りだけをループ上で行い、残りはスレッドプールへ逃がす。**
    """

    def decorate(fn: Any) -> Any:
        @functools.wraps(fn)
        async def wrapper(request: Request) -> Response:
            try:
                csrf.verify(request, allowed_hosts)
                payload = await _json_body(request)
            except AppError as e:
                return _error_response(e, _status_for(e))
            return await run_in_threadpool(_run_write, fn, request, payload)

        return wrapper

    return decorate


def _run_write(fn: Any, request: Request, payload: dict[str, Any]) -> Response:
    try:
        return fn(request, payload)
    except AppError as e:
        return _error_response(e, _status_for(e))


async def _json_body(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError as e:
        raise BadRequest(
            "リクエストの本文を解釈できませんでした。",
            cause="JSON として読めない内容が送られました。",
            remedy="正しい JSON を送ってください。",
        ) from e
    if not isinstance(parsed, dict):
        raise BadRequest(
            "リクエストの本文の形式が違います。",
            cause=f"{type(parsed).__name__} が送られました。",
            remedy="オブジェクト形式の JSON を送ってください。",
        )
    return parsed


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


# --- 書き込み ---------------------------------------------------------------
#
# いずれも `_writer()` が CSRF 検査と本文の読み取りを済ませてから、スレッド
# プール上で呼ぶ。第2引数は解釈済みの JSON（本文が空なら空の辞書）。
#
# 既存タスクを変える操作は `If-Match` を必須にする。省略を「上書きしてよい」と
# 解釈しない — 黙って危険側に倒れる既定値を作らないため。


def create_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    """`task-py add` 相当。新規なので版の照合は無い。"""
    project = _target_project(request)
    task = get_use_case().add_task(
        title=_require_str(payload, "title"),
        description=_optional_str(payload, "description") or "",
        priority=_priority(payload),
        due_date=_optional_str(payload, "due_date"),
        project=project,
    )
    return _task_response(project, task, status=201)


def edit_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    """`task-py edit` + `schedule` 相当。送られたフィールドだけを変える。"""
    project = _target_project(request)
    task_id = request.path_params["task_id"]
    uc = get_use_case()
    _check_version(request, uc.get_task(task_id, project=project))

    updated = uc.edit_task(
        task_id,
        title=_optional_str(payload, "title"),
        description=_optional_str(payload, "description"),
        priority=_priority(payload) if "priority" in payload else None,
        due_date=_optional_str(payload, "due_date"),
        clear_due_date=_is_cleared(payload, "due_date"),
        scheduled_date=_optional_str(payload, "scheduled_date"),
        clear_scheduled_date=_is_cleared(payload, "scheduled_date"),
        project=project,
    )
    return _task_response(project, updated)


def start_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return _transition(request, "start")


def complete_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return _transition(request, "done")


def archive_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return _transition(request, "archive")


def _transition(request: Request, action: str) -> JSONResponse:
    project = _target_project(request)
    task_id = request.path_params["task_id"]
    uc = get_use_case()
    _check_version(request, uc.get_task(task_id, project=project))

    if action == "start":
        task = uc.start_task(task_id, project=project)
    elif action == "done":
        task = uc.complete_task(task_id, project=project)
    else:
        task = uc.archive_task(task_id, project=project)
    return _task_response(project, task)


def delete_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    project = _target_project(request)
    task_id = request.path_params["task_id"]
    uc = get_use_case()
    _check_version(request, uc.get_task(task_id, project=project))

    uc.delete_task(task_id, project=project)
    return JSONResponse({"deleted": {"project": project, "id": task_id}})


def move_task(request: Request, payload: dict[str, Any]) -> JSONResponse:
    """`task-py move` 相当。

    移動先の実在は usecase 側が検証する（検証が無いと、成功を報告しながら
    `config.yaml` に載らないディレクトリへタスクを置き去りにしていた）。
    """
    project = _target_project(request)
    task_id = request.path_params["task_id"]
    uc = get_use_case()
    _check_version(request, uc.get_task(task_id, project=project))

    if "project" not in payload:
        raise BadRequest(
            "移動先が指定されていません。",
            cause="本文に project が含まれていません。",
            remedy='移動先のプロジェクト名、または Inbox なら null を指定してください。',
        )
    target = payload["project"]
    if target is not None and not isinstance(target, str):
        raise BadRequest(
            "移動先の指定が正しくありません。",
            cause=f"project に {type(target).__name__} が指定されました。",
            remedy='文字列、または Inbox なら null を指定してください。',
        )

    moved = uc.move_task(task_id, target, project=project)
    return _task_response(target, moved)


# --- 書き込みの補助 ---------------------------------------------------------


def _check_version(request: Request, current: Task) -> None:
    versions.ensure_matches(current, versions.required_version(request.headers))


def _task_response(project: str | None, task: Task, status: int = 200) -> JSONResponse:
    """更新後の内容をそのまま返す。

    画面が楽観的更新をせずに済むようにするため。画面とファイルが食い違う
    状態を作らない。
    """
    return JSONResponse(
        {"project": project, "task": serializers.task_detail(task)}, status_code=status
    )


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BadRequest(
            f"{key} が指定されていません。",
            cause=f"本文の {key} が空か、文字列ではありません。",
            remedy=f"{key} に文字列を指定してください。",
        )
    return value


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    """送られてこなかった、または null のときは None（＝変更しない）。"""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BadRequest(
            f"{key} の値が正しくありません。",
            cause=f"{key} に {type(value).__name__} が指定されました。",
            remedy=f"{key} には文字列を指定してください。",
        )
    return value


def _is_cleared(payload: dict[str, Any], key: str) -> bool:
    """`null` を明示的に送ってきたら「消す」。

    「キーが無い＝変更しない」「null＝消す」を区別する。区別しないと、
    一度設定した期限を画面から消せなくなる。
    """
    return key in payload and payload[key] is None


def _priority(payload: dict[str, Any]) -> Priority:
    raw = payload.get("priority")
    if raw is None:
        return Priority.MEDIUM
    try:
        return Priority(raw)
    except ValueError as e:
        raise BadRequest(
            "priority の値が不正です。",
            cause=f"'{raw}' は有効な優先度ではありません。",
            remedy=f"次のいずれかを指定してください: {', '.join(p.value for p in Priority)}",
        ) from e

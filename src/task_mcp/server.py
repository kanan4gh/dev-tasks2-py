from mcp.server.fastmcp import FastMCP

from task_cli.cli.deps import get_global_config_service, get_use_case
from task_cli.exceptions import AppError
from task_cli.models.task import Priority, TaskStatus
from task_cli.services.daily_service import DailyService
from task_cli.services.project_service import ProjectService
from task_cli.services.task_manager import TaskFilter
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_mcp.tracking import read_stats, track

mcp = FastMCP("task-py")


def _fmt_error(e: AppError) -> str:
    return f"エラー: {e.args[0]}\n原因: {e.cause}\n対処: {e.remedy}"


def _fmt_task(task: object) -> str:
    from task_cli.models.task import Task
    t = task  # type: ignore[assignment]
    assert isinstance(t, Task)
    lines = [
        f"ID: {t.id}",
        f"タイトル: {t.title}",
        f"ステータス: {t.status.value}",
        f"優先度: {t.priority.value}",
    ]
    if t.description:
        lines.append(f"説明: {t.description}")
    if t.due_date:
        lines.append(f"期限: {t.due_date}")
    if t.scheduled_date:
        lines.append(f"解禁日: {t.scheduled_date}")
    return "\n".join(lines)


# ─── タスク管理ツール ────────────────────────────────────────────────


@mcp.tool()
@track
def list_tasks(status: str | None = None) -> str:
    """アクティブプロジェクト（または Inbox）のタスク一覧を返す。
    status に "open" / "in_progress" / "completed" / "archived" を指定して絞り込み可能。
    省略時は全件返す。"""
    uc = get_use_case()
    try:
        f: TaskFilter | None = None
        if status:
            f = TaskFilter(status=[TaskStatus(status)])
        tasks = uc.list_tasks(f)
        if not tasks:
            return "タスクはありません。"
        return "\n---\n".join(_fmt_task(t) for t in tasks)
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def add_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str | None = None,
) -> str:
    """タスクを作成する。priority は "high" / "medium" / "low"。due_date は YYYY-MM-DD 形式。"""
    uc = get_use_case()
    try:
        task = uc.add_task(title, description, Priority(priority), due_date)
        return f"タスクを作成しました。\n{_fmt_task(task)}"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def show_task(id: int) -> str:
    """指定 ID のタスク詳細を返す。"""
    uc = get_use_case()
    try:
        return _fmt_task(uc.get_task(id))
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def start_task(id: int) -> str:
    """タスクのステータスを in_progress に変更する。"""
    uc = get_use_case()
    try:
        task = uc.start_task(id)
        return f"タスク #{id} '{task.title}' を開始しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def complete_task(id: int) -> str:
    """タスクのステータスを completed に変更する。"""
    uc = get_use_case()
    try:
        task = uc.complete_task(id)
        return f"タスク #{id} '{task.title}' を完了しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def delete_task(id: int) -> str:
    """タスクを削除する。確認プロンプトはない。"""
    uc = get_use_case()
    try:
        task = uc.get_task(id)
        title = task.title
        uc.delete_task(id)
        return f"タスク #{id} '{title}' を削除しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def archive_task(id: int) -> str:
    """タスクのステータスを archived に変更する。"""
    uc = get_use_case()
    try:
        task = uc.archive_task(id)
        return f"タスク #{id} '{task.title}' をアーカイブしました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def edit_task(
    id: int,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
    clear_due_date: bool = False,
    scheduled_date: str | None = None,
    clear_scheduled_date: bool = False,
) -> str:
    """タスクの属性を編集する。省略したフィールドは変更しない。
    期限を削除するには clear_due_date=true、解禁日を削除するには clear_scheduled_date=true を指定。"""
    uc = get_use_case()
    try:
        p = Priority(priority) if priority else None
        task = uc.edit_task(
            id,
            title=title,
            description=description,
            priority=p,
            due_date=due_date,
            clear_due_date=clear_due_date,
            scheduled_date=scheduled_date,
            clear_scheduled_date=clear_scheduled_date,
        )
        return f"タスク #{id} を更新しました。\n{_fmt_task(task)}"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def move_task(id: int, target_project: str | None = None) -> str:
    """タスクを別のプロジェクトに移動する。target_project を省略すると Inbox に移動する。"""
    uc = get_use_case()
    try:
        task = uc.move_task(id, target_project)
        dest = f"プロジェクト '{target_project}'" if target_project else "Inbox"
        return f"タスク #{id} '{task.title}' を {dest} に移動しました（新 ID: {task.id}）。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def search_tasks(keyword: str) -> str:
    """タイトル・説明をキーワードで検索する（大文字小文字を区別しない部分一致）。"""
    uc = get_use_case()
    try:
        tasks = uc.search_tasks(keyword)
        if not tasks:
            return f"'{keyword}' にマッチするタスクはありません。"
        return "\n---\n".join(_fmt_task(t) for t in tasks)
    except AppError as e:
        return _fmt_error(e)


# ─── プロジェクト管理ツール ──────────────────────────────────────────


@mcp.tool()
@track
def get_active_project() -> str:
    """現在のアクティブプロジェクト名を返す。Inbox モードの場合は 'Inbox' を返す。"""
    svc = get_global_config_service()
    active = svc.get_active_project()
    return active if active else "Inbox"


@mcp.tool()
@track
def list_projects() -> str:
    """プロジェクト一覧を返す。アクティブプロジェクトには * を付ける。"""
    svc = get_global_config_service()
    storage = GlobalConfigStorage()
    ps = ProjectService(storage)
    active = svc.get_active_project()
    projects = ps.list_projects()
    if not projects:
        return "プロジェクトはありません。"
    lines = []
    for p in projects:
        marker = "* " if p.name == active else "  "
        lines.append(f"{marker}{p.name}")
    return "\n".join(lines)


@mcp.tool()
@track
def create_project(name: str) -> str:
    """プロジェクトを作成し、アクティブプロジェクトに切り替える。"""
    storage = GlobalConfigStorage()
    ps = ProjectService(storage)
    try:
        entry = ps.create_project(name)
        return f"プロジェクト '{entry.name}' を作成し、アクティブプロジェクトに設定しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def use_project(name: str | None = None) -> str:
    """アクティブプロジェクトを切り替える。name を省略すると Inbox モードに切り替える。"""
    svc = get_global_config_service()
    if name is None:
        svc.set_active_project(None)
        return "Inbox モードに切り替えました。"
    storage = GlobalConfigStorage()
    ps = ProjectService(storage)
    try:
        ps.use_project(name)
        return f"アクティブプロジェクトを '{name}' に切り替えました。"
    except AppError as e:
        return _fmt_error(e)


# ─── onboard ────────────────────────────────────────────────────────


@mcp.tool()
@track
def get_overview() -> str:
    """現在の状況概観を返す。アクティブプロジェクト・今日のルーティーン・着手すべきタスク・全タスクサマリーを含む。"""
    svc = get_global_config_service()
    active = svc.get_active_project()
    uc = get_use_case()
    daily_svc = DailyService()

    lines: list[str] = []
    label = f"Project: {active}" if active else "Inbox"
    lines.append(f"=== {label} ===")

    # ルーティーン
    all_routines = daily_svc.list_today(include_paused=False)
    done_count = sum(1 for _, s in all_routines if s == "done")
    total_count = len(all_routines)
    if total_count > 0:
        pending = [(r, s) for r, s in all_routines if s == "pending"]
        lines.append(f"\n【今日のルーティーン】 {done_count}/{total_count} 完了")
        for r, _ in pending:
            lines.append(f"  ○ [r{r.id}] {r.title}")
        if not pending:
            lines.append("  ✓ すべて完了！")

    # 着手すべきタスク上位3件
    in_progress = uc.list_tasks(TaskFilter(status=[TaskStatus.IN_PROGRESS]))
    open_tasks = uc.list_tasks(TaskFilter(status=[TaskStatus.OPEN]))
    priority_tasks = (in_progress + open_tasks)[:3]
    if priority_tasks:
        lines.append("\n【今とりかかるべきタスク】")
        for i, t in enumerate(priority_tasks, 1):
            lines.append(f"  {i}. [{t.status.value}] #{t.id} {t.title}")

    # 全プロジェクト横断サマリー
    active_filter = TaskFilter(status=[TaskStatus.OPEN, TaskStatus.IN_PROGRESS])
    all_projects = uc.list_all_projects(active_filter)
    ordered_projects = [(k, v) for k, v in all_projects.items() if k is not None and v]
    inbox_tasks = all_projects.get(None, [])
    has_tasks = any(v for v in all_projects.values())
    if has_tasks:
        lines.append("\n【全タスクサマリー (open + in_progress)】")
        for proj_name, tasks in ordered_projects:
            in_prog = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
            lines.append(f"  [Project: {proj_name}] {len(tasks)} 件 (in_progress: {in_prog})")
            for t in tasks:
                lines.append(f"    • {t.id}  [{t.status.value}]  {t.title}")
        if inbox_tasks:
            in_prog = sum(1 for t in inbox_tasks if t.status == TaskStatus.IN_PROGRESS)
            lines.append(f"  [Inbox] {len(inbox_tasks)} 件 (in_progress: {in_prog})")
            for t in inbox_tasks:
                lines.append(f"    • 0-{t.id}  [{t.status.value}]  {t.title}")

    return "\n".join(lines)


# ─── ルーティーン管理ツール ──────────────────────────────────────────


@mcp.tool()
@track
def list_routines(include_paused: bool = False) -> str:
    """今日のルーティーン一覧を返す。include_paused=true で一時停止中も含める。"""
    svc = DailyService()
    items = svc.list_today(include_paused=include_paused)
    if not items:
        return "ルーティーンはありません。"
    lines = []
    for r, status in items:
        mark = "✓" if status == "done" else "○"
        paused = " [停止中]" if r.paused else ""
        lines.append(f"{mark} [r{r.id}] {r.title}{paused}")
    return "\n".join(lines)


@mcp.tool()
@track
def add_routine(title: str) -> str:
    """ルーティーンを登録する。"""
    svc = DailyService()
    routine = svc.add_routine(title)
    return f"ルーティーン [r{routine.id}] '{routine.title}' を登録しました。"


@mcp.tool()
@track
def complete_routine(id: int) -> str:
    """指定 ID のルーティーンを今日の分として済にする。"""
    svc = DailyService()
    try:
        svc.mark_done(id)
        return f"ルーティーン [r{id}] を済にしました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def pause_routine(id: int) -> str:
    """ルーティーンを一時停止する（list から非表示になる）。"""
    svc = DailyService()
    try:
        svc.pause(id)
        return f"ルーティーン [r{id}] を一時停止しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def resume_routine(id: int) -> str:
    """一時停止中のルーティーンを再開する。"""
    svc = DailyService()
    try:
        svc.resume(id)
        return f"ルーティーン [r{id}] を再開しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def delete_routine(id: int) -> str:
    """ルーティーンを削除する。実績ログも削除される。"""
    svc = DailyService()
    try:
        svc.delete(id)
        return f"ルーティーン [r{id}] を削除しました。"
    except AppError as e:
        return _fmt_error(e)


@mcp.tool()
@track
def get_daily_stats() -> str:
    """直近7日のルーティーン日別達成率を返す。"""
    svc = DailyService()
    stats = svc.stats()
    if not stats:
        return "統計データがありません。"
    lines = ["日付         完了  合計  達成率"]
    for s in stats:
        rate = f"{s['rate']:.0%}" if s["rate"] is not None else "  -  "
        lines.append(f"{s['date']}  {s['done']:>4}  {s['total']:>4}  {rate:>5}")
    return "\n".join(lines)


# ─── Observability ──────────────────────────────────────────────────


@mcp.tool()
@track
def get_mcp_stats() -> str:
    """MCPツールの呼び出し統計を返す。どのツールが何回呼ばれたかを確認できる。"""
    return read_stats()

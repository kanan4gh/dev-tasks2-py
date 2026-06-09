import asyncio
from pathlib import Path

import pytest

from task_mcp.server import mcp


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


# ─── ツール一覧・スキーマテスト ───────────────────────────────────────

EXPECTED_TOOLS = {
    # タスク管理
    "list_tasks", "add_task", "show_task", "start_task", "complete_task",
    "delete_task", "archive_task", "edit_task", "move_task", "search_tasks",
    # プロジェクト管理
    "get_active_project", "list_projects", "create_project", "use_project",
    # overview
    "get_overview",
    # ルーティーン管理
    "list_routines", "add_routine", "complete_routine", "pause_routine",
    "resume_routine", "delete_routine", "get_daily_stats",
    # observability
    "get_mcp_stats",
}


def test_all_tools_registered() -> None:
    tools = run(mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names, f"未登録のツール: {EXPECTED_TOOLS - names}"


def test_tool_descriptions_present() -> None:
    """全ツールに description が設定されていること（Claude が使い方を判断するために必須）。"""
    tools = run(mcp.list_tools())
    for tool in tools:
        if tool.name in EXPECTED_TOOLS:
            assert tool.description, f"ツール '{tool.name}' に description がありません"


def test_add_task_schema() -> None:
    tools = run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "add_task")
    schema = tool.inputSchema
    assert "title" in schema.get("required", []), "add_task: title が required でありません"


def test_edit_task_schema() -> None:
    tools = run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "edit_task")
    schema = tool.inputSchema
    assert "id" in schema.get("required", []), "edit_task: id が required でありません"
    props = schema.get("properties", {})
    optional_fields = ["title", "description", "priority", "due_date", "scheduled_date"]
    for f in optional_fields:
        assert f in props, f"edit_task: '{f}' が properties にありません"


def test_list_tasks_status_optional() -> None:
    tools = run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "list_tasks")
    schema = tool.inputSchema
    required = schema.get("required", [])
    assert "status" not in required, "list_tasks: status が required になっています（optional であるべき）"


# ─── ツール呼び出しテスト（MCP プロトコル経由）──────────────────────


@pytest.fixture
def tmp_task_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """~/.task-py/ を tmp_path に差し替える。"""
    task_dir = tmp_path / ".task-py"
    task_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    return task_dir


def _text(result: object) -> str:
    """call_tool の戻り値から text を取り出す。"""
    contents, _ = result  # type: ignore[misc]
    return contents[0].text  # type: ignore[union-attr]


def test_list_tasks_returns_string(tmp_task_env: Path) -> None:
    result = run(mcp.call_tool("list_tasks", {}))
    text = _text(result)
    assert isinstance(text, str)


def test_add_task_creates_task(tmp_task_env: Path) -> None:
    result = run(mcp.call_tool("add_task", {"title": "MCPテスト"}))
    text = _text(result)
    assert "MCPテスト" in text
    assert "作成しました" in text


def test_get_overview_returns_overview(tmp_task_env: Path) -> None:
    result = run(mcp.call_tool("get_overview", {}))
    text = _text(result)
    assert isinstance(text, str)
    assert len(text) > 0


# ─── エラーハンドリングテスト ────────────────────────────────────────


def test_show_task_error_returns_string_not_exception(tmp_task_env: Path) -> None:
    """存在しない ID → AppError → isError にならず文字列が返る。"""
    result = run(mcp.call_tool("show_task", {"id": 99999}))
    contents, _ = result  # type: ignore[misc]
    from mcp.types import TextContent
    first = contents[0]  # type: ignore[index]
    assert isinstance(first, TextContent), f"TextContent が返るべきですが {type(first)} でした"
    assert "エラー" in first.text
    assert first.type == "text"


def test_start_task_error_returns_string_not_exception(tmp_task_env: Path) -> None:
    """存在しない ID に start_task → エラー文字列が返る。"""
    result = run(mcp.call_tool("start_task", {"id": 99999}))
    text = _text(result)
    assert "エラー" in text


# ─── 外部試験（stdio プロセス起動）──────────────────────────────────────


def test_stdio_process_initialize(tmp_task_env: Path) -> None:
    """実プロセスとして起動し、JSON-RPC initialize が成功することを確認。"""
    import json
    import subprocess
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-m", "task_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def send(msg: dict) -> None:  # type: ignore[type-arg]
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def recv() -> dict:  # type: ignore[type-arg]
        assert proc.stdout is not None
        line = proc.stdout.readline()
        return json.loads(line)  # type: ignore[no-any-return]

    try:
        send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1"},
            },
        })
        resp = recv()
        assert resp.get("id") == 1, f"id が一致しません: {resp}"
        assert "result" in resp, f"result がありません: {resp}"
        assert "serverInfo" in resp["result"], f"serverInfo がありません: {resp['result']}"

        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = recv()
        assert tools_resp.get("id") == 2
        tools = {t["name"] for t in tools_resp["result"]["tools"]}
        assert "list_tasks" in tools
        assert "get_overview" in tools
        assert len(tools) >= 23, f"ツール数が少ない: {len(tools)}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


# ─── tracking テスト ─────────────────────────────────────────────────


def test_track_writes_log(tmp_task_env: Path) -> None:
    """@track デコレータが JSONL ログを書き込むことを確認。"""
    import json
    from task_mcp.tracking import _LOG_PATH, track

    log_path = tmp_task_env / "mcp_calls.jsonl"

    @track
    def dummy_tool() -> str:
        return "ok"

    import unittest.mock as mock
    with mock.patch.object(_LOG_PATH.__class__, "expanduser", return_value=log_path):
        from task_mcp import tracking
        orig = tracking._LOG_PATH
        tracking._LOG_PATH = log_path  # type: ignore[assignment]
        try:
            dummy_tool()
        finally:
            tracking._LOG_PATH = orig

    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "dummy_tool"
    assert entry["ok"] is True
    assert "elapsed_ms" in entry
    assert "ts" in entry


def test_read_stats_no_log(tmp_path: Path) -> None:
    """ログファイルが存在しない場合のフォールバック確認。"""
    from task_mcp.tracking import read_stats
    result = read_stats(tmp_path / "nonexistent.jsonl")
    assert "ログがまだありません" in result


def test_read_stats_returns_summary(tmp_path: Path) -> None:
    """read_stats() が正しい集計文字列を返すことを確認。"""
    import json
    from task_mcp.tracking import read_stats

    log_path = tmp_path / "mcp_calls.jsonl"
    entries = [
        {"ts": "2026-06-10T00:00:00+00:00", "tool": "list_tasks", "elapsed_ms": 10, "ok": True},
        {"ts": "2026-06-10T00:01:00+00:00", "tool": "list_tasks", "elapsed_ms": 8, "ok": True},
        {"ts": "2026-06-10T00:02:00+00:00", "tool": "add_task", "elapsed_ms": 5, "ok": True},
    ]
    log_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    result = read_stats(log_path)
    assert "総呼び出し数: 3 件" in result
    assert "list_tasks: 2" in result
    assert "add_task: 1" in result


def test_get_mcp_stats_tool(tmp_task_env: Path) -> None:
    """get_mcp_stats ツールの呼び出しテスト。"""
    result = run(mcp.call_tool("get_mcp_stats", {}))
    text = _text(result)
    assert isinstance(text, str)
    assert len(text) > 0

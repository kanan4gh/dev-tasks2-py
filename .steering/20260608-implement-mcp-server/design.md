# 設計書

## アーキテクチャ概要

既存の Clean Architecture に MCP サーバーを新しいインターフェースとして追加する。CLI と MCP の両方がサービス層を直接 import する。

```
既存:  サービス層 ← CLI レイヤー (src/task_cli/cli/)
今後:  サービス層 ← CLI レイヤー (src/task_cli/cli/)
                 ← MCP サーバー  (src/task_mcp/)     ← Claude
```

MCP サーバーは `task_cli.usecases`, `task_cli.services` を直接 import して呼び出す。HTTP サーバーも CLI subprocess も経由しない。

## コンポーネント設計

### 1. `src/task_mcp/__main__.py`

**責務**: `python -m task_mcp` および `task-mcp` コマンドのエントリーポイント

```python
from task_mcp.server import mcp

def main() -> None:
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
```

### 2. `src/task_mcp/server.py`

**責務**: MCP ツールの定義と、サービス層への委譲

**実装の要点**:
- `mcp = FastMCP("task-py")` でサーバーインスタンスを作成
- 各ツールは `@mcp.tool()` デコレータで定義
- サービスインスタンスは関数内でその都度生成（`get_use_case()`, `DailyService()`, `ProjectService()` を呼ぶ）
- `AppError` は `try/except` で捕捉し、エラー文字列として返す
- 返り値はすべて `str`（JSON 文字列または人間可読テキスト）

**ツール分類と委譲先**:

| ツール | 委譲先 |
|--------|--------|
| `list_tasks`, `add_task`, `show_task`, `start_task`, `complete_task`, `delete_task`, `archive_task`, `edit_task`, `move_task`, `search_tasks` | `TaskCrudUseCase` |
| `list_projects`, `create_project`, `use_project`, `get_active_project` | `ProjectService` / `GlobalConfigService` |
| `onboard` | `TaskCrudUseCase` + `DailyService` + `GlobalConfigService` を組み合わせ |
| `list_routines`, `add_routine`, `complete_routine`, `pause_routine`, `resume_routine`, `delete_routine`, `get_daily_stats` | `DailyService` |

## ツール仕様

### タスク管理ツール

```python
@mcp.tool()
def list_tasks(
    status: str | None = None,  # "open" | "in_progress" | "completed" | "archived" | None（全件）
) -> str: ...

@mcp.tool()
def add_task(
    title: str,
    description: str = "",
    priority: str = "medium",  # "high" | "medium" | "low"
    due_date: str | None = None,  # "YYYY-MM-DD"
) -> str: ...

@mcp.tool()
def show_task(id: int) -> str: ...

@mcp.tool()
def start_task(id: int) -> str: ...

@mcp.tool()
def complete_task(id: int) -> str: ...

@mcp.tool()
def delete_task(id: int) -> str: ...

@mcp.tool()
def archive_task(id: int) -> str: ...

@mcp.tool()
def edit_task(
    id: int,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
    clear_due_date: bool = False,
    scheduled_date: str | None = None,
    clear_scheduled_date: bool = False,
) -> str: ...

@mcp.tool()
def move_task(
    id: int,
    target_project: str | None = None,  # None = Inbox
) -> str: ...

@mcp.tool()
def search_tasks(keyword: str) -> str: ...
```

### プロジェクト管理ツール

```python
@mcp.tool()
def get_active_project() -> str: ...  # プロジェクト名または "Inbox"

@mcp.tool()
def list_projects() -> str: ...

@mcp.tool()
def create_project(name: str) -> str: ...

@mcp.tool()
def use_project(name: str | None = None) -> str: ...  # None = Inbox モードに切り替え
```

### onboard ツール

```python
@mcp.tool()
def onboard() -> str: ...
# 返す情報:
# - アクティブプロジェクト名
# - 今日のルーティーン（pending/done 件数）
# - 着手すべきタスク上位3件（in_progress → open の順）
# - 全プロジェクト横断のタスク数サマリー
```

### ルーティーン管理ツール

```python
@mcp.tool()
def list_routines(include_paused: bool = False) -> str: ...

@mcp.tool()
def add_routine(title: str) -> str: ...

@mcp.tool()
def complete_routine(id: int) -> str: ...

@mcp.tool()
def pause_routine(id: int) -> str: ...

@mcp.tool()
def resume_routine(id: int) -> str: ...

@mcp.tool()
def delete_routine(id: int) -> str: ...

@mcp.tool()
def get_daily_stats() -> str: ...
```

## データフロー

### 典型的なツール呼び出し

```
Claude
  → MCP クライアント (stdio)
  → task_mcp/server.py の @mcp.tool() 関数
  → TaskCrudUseCase / DailyService / ProjectService
  → TaskManager / DailyService
  → FileStorage / RoutineStorage / DailyLogStorage
  → ~/.task-py/ (YAML ファイル)
  → 結果を str で返す
  → Claude
```

### エラーハンドリング

```python
try:
    result = uc.start_task(id)
    return f"タスク #{id} '{result.title}' を開始しました。"
except AppError as e:
    return f"エラー: {e.message}\n原因: {e.cause}\n対処: {e.remedy}"
```

- `AppError` を捕捉して人間可読のテキストとして返す
- MCP ツールはエラー時も `str` を返す（例外を raise しない）
- Claude がエラー内容を読んでユーザーに伝える

## 依存ライブラリ

`pyproject.toml` の `dependencies` に追加:

```toml
"mcp[cli]"
```

- `mcp[cli]` — MCP Python SDK（`FastMCP` クラスと `mcp dev` コマンドを含む）

## ディレクトリ構造

```
src/
├── task_cli/         (既存・変更なし)
└── task_mcp/         (新規)
    ├── __init__.py
    ├── __main__.py   # python -m task_mcp のエントリーポイント
    └── server.py     # ツール定義
```

`pyproject.toml` の `[tool.hatch.build.targets.wheel]` に `task_mcp` を追加:
```toml
packages = ["src/task_cli", "src/task_mcp"]
```

## Claude への登録設定

`pyproject.toml` の `[project.scripts]` に `task-mcp` エントリーポイントを追加:

```toml
task-mcp = "task_mcp.__main__:main"
```

これにより `uv tool install` または `uvx` で使用可能になる。

**C: uv tool install（推奨）**
```bash
uv tool install git+https://github.com/kanan4gh/dev-tasks2-py.git
```
登録設定:
```json
{ "mcpServers": { "task-py": { "command": "task-mcp" } } }
```

**A: uvx（インストール不要）**
```json
{ "mcpServers": { "task-py": { "command": "uvx", "args": ["--from", "git+https://github.com/kanan4gh/dev-tasks2-py.git", "task-mcp"] } } }
```

README に設定手順を記載する。

## テスト戦略

### ユニットテスト

MCP サーバー自体の単体テストは、サービス層のロジックはすでにテスト済みのため、**最小限**とする。

`tests/test_mcp_server.py`:
- `list_tasks` がタスクリストを文字列で返すことを確認
- `add_task` がタスクを作成し結果文字列を返すことを確認
- `AppError` 発生時にエラー文字列を返すことを確認（例外を raise しない）
- `onboard` が全情報を含む文字列を返すことを確認

### 手動動作確認

```bash
# 直接起動確認
uv run python -m task_mcp
```

### 外部試験（subprocess JSON-RPC）

`tests/test_mcp_server.py::test_stdio_process_initialize`:
- `python -m task_mcp` をサブプロセスとして起動
- stdin に JSON-RPC `initialize` メッセージを送信
- stdout のレスポンスを検証（`serverInfo` の存在、`tools/list` でツール22件以上）

## 実装の順序

1. `mcp[cli]` を `pyproject.toml` に追加 → `uv sync`
2. `src/task_mcp/__init__.py` と `__main__.py` を作成
3. `src/task_mcp/server.py` にツールを実装（タスク管理 → プロジェクト管理 → onboard → ルーティーン管理の順）
4. `pyproject.toml` の `packages` に `task_mcp` を追加
5. `tests/test_mcp_server.py` を作成
6. 品質チェック（pytest + pyright）
7. README に登録設定を追記

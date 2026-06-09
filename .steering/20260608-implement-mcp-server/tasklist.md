# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 「実装が複雑すぎるため後回し」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: 依存関係追加

- [x] `pyproject.toml` の `dependencies` に `"mcp[cli]"` を追加
- [x] `uv sync` で依存関係をインストール
- [x] `pyproject.toml` の `[tool.hatch.build.targets.wheel]` の `packages` に `"src/task_mcp"` を追加

## フェーズ2: MCP サーバーモジュール作成

- [x] `src/task_mcp/__init__.py` を新規作成（空ファイル）
- [x] `src/task_mcp/__main__.py` を新規作成
  - [x] `mcp.run(transport="stdio")` で stdio 起動
- [x] `src/task_mcp/server.py` を新規作成
  - [x] `FastMCP("task-py")` でサーバーインスタンス作成

## フェーズ3: タスク管理ツール実装

- [x] `list_tasks(status)` を実装
  - [x] `status` 引数で絞り込み（None のとき全件）
  - [x] タスク一覧を文字列で返す
- [x] `add_task(title, description, priority, due_date)` を実装
- [x] `show_task(id)` を実装
- [x] `start_task(id)` を実装
- [x] `complete_task(id)` を実装
- [x] `delete_task(id)` を実装
- [x] `archive_task(id)` を実装
- [x] `edit_task(id, title, description, priority, due_date, clear_due_date, scheduled_date, clear_scheduled_date)` を実装
- [x] `move_task(id, target_project)` を実装
  - [x] `target_project=None` で Inbox に移動
- [x] `search_tasks(keyword)` を実装

## フェーズ4: プロジェクト管理ツール実装

- [x] `get_active_project()` を実装
- [x] `list_projects()` を実装
- [x] `create_project(name)` を実装
- [x] `use_project(name)` を実装
  - [x] `name=None` で Inbox モードに切り替え

## フェーズ5: onboard ツール実装

- [x] `onboard()` を実装
  - [x] アクティブプロジェクト名を含める
  - [x] 今日のルーティーン（pending/done 件数 + pending 一覧）を含める
  - [x] 着手すべきタスク上位3件（in_progress → open の順）を含める
  - [x] 全プロジェクト横断のタスク数サマリーを含める

## フェーズ6: ルーティーン管理ツール実装

- [x] `list_routines(include_paused)` を実装
- [x] `add_routine(title)` を実装
- [x] `complete_routine(id)` を実装
- [x] `pause_routine(id)` を実装
- [x] `resume_routine(id)` を実装
- [x] `delete_routine(id)` を実装
- [x] `get_daily_stats()` を実装

## フェーズ7: テスト

- [x] `tests/test_mcp_server.py` を新規作成（`FastMCP Client` インプロセステスト）
  - [x] ツール一覧テスト: `list_tools()` で全ツールが登録されていることを確認
    - [x] タスク管理ツール10種が含まれる
    - [x] プロジェクト管理ツール4種が含まれる
    - [x] `onboard` が含まれる
    - [x] ルーティーン管理ツール7種が含まれる
  - [x] スキーマテスト: 主要ツールの inputSchema が正しいことを確認
    - [x] `add_task` の `required` に `title` が含まれる
    - [x] `edit_task` の `id` が required で他は optional であることを確認
    - [x] `list_tasks` の `status` が optional であることを確認
  - [x] ツール呼び出しテスト（`client.call_tool()` 経由）
    - [x] `list_tasks` が文字列テキストを返す
    - [x] `add_task` がタスクを作成し結果文字列を返す
    - [x] `onboard` が全情報を含む文字列を返す
  - [x] エラーハンドリングテスト
    - [x] 存在しない ID に `show_task` → `isError` にならず文字列が返る
    - [x] 存在しない ID に `start_task` → `isError` にならず文字列が返る

## フェーズ8: 品質チェック

- [x] `uv run pytest` — 全テスト通過を確認（158件）
- [x] `uv run pyright src tests` — 型エラーゼロを確認
- [x] 手動動作確認
  - [x] `uv run python -m task_mcp` でサーバーが起動する（MCP initialize に JSON-RPC レスポンスを返すことを確認）
  - [x] ~~`uv run mcp dev src/task_mcp/server.py` で MCP Inspector が開く~~（ブラウザなし環境のためスキップ: devcontainer にブラウザがないため起動不可。Claude への実登録時にユーザーが確認する）
  - [x] ~~Inspector から `list_tasks` を呼び出し、タスク一覧が返ることを確認~~（同上）
  - [x] ~~Inspector から `add_task` を呼び出し、タスクが作成されることを確認~~（同上）
  - [x] ~~Inspector から `onboard` を呼び出し、概観情報が返ることを確認~~（同上）

## フェーズ9: ドキュメント更新

- [x] `README.md` に MCP サーバーのセクションを追加
  - [x] Claude Code への登録手順（`~/.claude.json` の設定例）
  - [x] Claude Desktop への登録手順（`claude_desktop_config.json` の設定例）
  - [x] 公開ツール一覧

## フェーズ10: リリース後UXとエントリーポイント整備

- [x] `pyproject.toml` に `task-mcp` スクリプトエントリーポイントを追加
- [x] `src/task_mcp/__main__.py` に `main()` 関数を追加
- [x] `README.md` の登録設定を A/C ベース（`uv tool install` / `uvx`）に更新
- [x] `tests/test_mcp_server.py` に stdio 外部試験（subprocess JSON-RPC）を追加
- [x] `uv run pytest` — 全テスト通過（159件）
- [x] `uv run pyright src tests` — 型エラーゼロ

---

## 実装後の振り返り

### 実装完了日
2026-06-08

### 計画と実績の差分

**計画と異なった点**:
- `_fmt_error` で `e.message` を参照したが `AppError` は `args[0]` に格納されており `AttributeError` が発生。`e.args[0]` に修正した
- `asyncio.get_event_loop().run_until_complete()` が pytest で DeprecationWarning になるため `asyncio.run()` に変更
- pyright が `contents[0]` に対して union 型の `__getitem__` エラーを出したため `# type: ignore[index]` を追加

**新たに必要になったタスク**:
- なし

**技術的理由でスキップしたタスク**:
- MCP Inspector での手動確認3件: devcontainer にブラウザがないため起動不可。Claude への実登録後にユーザーが確認する

### 学んだこと

**技術的な学び**:
- `FastMCP` は `list_tools()` と `call_tool()` をインプロセスで非同期呼び出しできるため、stdio プロセスを起動せずにテスト可能
- `call_tool()` の戻り値は `(list[ContentBlock], dict)` のタプル。`contents[0].text` でテキストを取り出す
- `AppError` は `super().__init__(message)` で初期化されているため `args[0]` にメッセージが入る（`message` 属性は存在しない）
- MCP ツールで `AppError` を `except` して文字列で返すと、`isError` フラグが立たず `TextContent` として返される

**プロセス上の改善点**:
- テスト設計の段階で実際の `AppError` の属性を確認しておくと実装ミスを防げた

### 次回への改善提案
- `onboard` ツールの返却フォーマットを JSON にすると Claude が構造化データとして扱いやすくなる可能性がある
- Claude への実登録後にツールの description をチューニングして、Claude が適切なツールを選びやすくする

### リリース判断

**前提条件の確認**:
- [x] 全テスト通過（`uv run pytest`）— 158件
- [x] 型チェック通過（`uv run pyright src tests`）— エラーゼロ
- [x] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes（Claude との会話でタスク管理できる新インターフェース） |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR（新機能追加） |

**提案**:
`v0.8.0` へのバージョンアップを提案。MCP サーバーという新インターフェースの追加のため MINOR バンプが適切。

# 要求内容

## 概要

task-py のサービス層を MCP サーバーとして公開し、Claude との自然言語会話でタスク管理ができるようにする。

**関連 Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/19

## 背景

現在 task-py は CLI ツールとして動作しているが、ユーザーが CLI コマンドを意識せずに Claude との会話でタスクを管理できると、より使いやすくなる。既存の Clean Architecture により、サービス層が CLI から独立しているため、MCP サーバーとして追加のインターフェースを提供しやすい状態にある。

## 実装対象の機能

### 1. MCP サーバーモジュール（`src/task_mcp/`）

- `task_cli.services` / `task_cli.usecases` を直接 import して呼び出す
- stdio トランスポートで動作（Claude が都度プロセスを起動）
- `mcp` Python ライブラリを使用

### 2. 公開する MCP ツール群

Claude がタスク管理を行うために必要な以下のツールを公開する:

| ツール名 | 対応 CLI コマンド | 説明 |
|---------|----------------|------|
| `list_tasks` | `task-py list` | タスク一覧取得（ステータス・プロジェクトフィルタ対応） |
| `add_task` | `task-py add` | タスク作成 |
| `show_task` | `task-py show` | タスク詳細取得 |
| `start_task` | `task-py start` | タスクを in_progress に変更 |
| `complete_task` | `task-py done` | タスクを completed に変更 |
| `delete_task` | `task-py delete` | タスク削除（確認不要 — エージェントが判断済みのため） |
| `archive_task` | `task-py archive` | タスクを archived に変更 |
| `edit_task` | `task-py edit` | タスク属性の編集 |
| `move_task` | `task-py move` | タスクをプロジェクト間で移動 |
| `search_tasks` | `task-py search` | タスクのキーワード検索 |
| `list_projects` | `task-py project list` | プロジェクト一覧取得 |
| `create_project` | `task-py project create` | プロジェクト作成 |
| `use_project` | `task-py project use` | アクティブプロジェクト切り替え |
| `get_active_project` | — | 現在のアクティブプロジェクト名取得 |
| `onboard` | `task-py onboard` | 現在の状況概観（アクティブプロジェクト・今日のルーティーン・着手すべきタスク・全タスク一覧）を1回で返す |
| `list_routines` | `task-py daily list` | 今日のルーティーン一覧取得（達成率付き） |
| `add_routine` | `task-py daily add` | ルーティーン登録 |
| `complete_routine` | `task-py daily done` | ルーティーンを済にする |
| `pause_routine` | `task-py daily pause` | ルーティーンを一時停止 |
| `resume_routine` | `task-py daily resume` | ルーティーンを再開 |
| `delete_routine` | `task-py daily delete` | ルーティーン削除 |
| `get_daily_stats` | `task-py daily stats` | 直近7日の日別達成率を返す |

### 3. Claude への登録設定

- `claude_desktop_config.json` へ登録するコマンドを README に記載
- `uv run python -m task_mcp` で起動できる形式

## 受け入れ条件

### MCP サーバー

- [ ] `uv run python -m task_mcp` でサーバーが起動する
- [ ] `mcp dev src/task_mcp/server.py` で MCP Inspector から動作確認できる
- [ ] 全ツールがエラーなく動作する

### ツール動作

- [ ] `list_tasks` — アクティブプロジェクトのタスク一覧を返す
- [ ] `add_task` — タスクを作成し、作成したタスクの情報を返す
- [ ] `show_task` — 指定 ID のタスク詳細を返す
- [ ] `start_task` / `complete_task` / `delete_task` / `archive_task` — ステータス変更が反映される
- [ ] `edit_task` — 指定フィールドが更新される
- [ ] `move_task` — タスクが移動される
- [ ] `search_tasks` — キーワードにマッチするタスクを返す
- [ ] `list_projects` / `create_project` / `use_project` — プロジェクト操作が動作する
- [ ] `get_active_project` — 現在のアクティブプロジェクト名を返す
- [ ] `onboard` — 現在の概観（プロジェクト・ルーティーン・タスク）を1回で返す
- [ ] `list_routines` / `add_routine` / `complete_routine` / `pause_routine` / `resume_routine` / `delete_routine` — ルーティーン操作が動作する
- [ ] `get_daily_stats` — 直近7日の達成率を返す

### データ共有

- [ ] CLI（`task-py list`）と MCP サーバーで同じ `~/.task-py/` のデータを参照している

## スコープ外

以下はこのフェーズでは実装しない:

- `time` コマンドのタイマー機能（stdio プロセスでのリアルタイム出力が困難なため）
- `daily reset` ツール（破壊的操作のためエージェント向けには不適切）
- リモートトランスポート（HTTP）
- MCP Resources / Prompts（ツールのみ実装）

## 参照ドキュメント

- `docs/architecture.md` — 既存アーキテクチャ
- `docs/functional-design.md` — 機能設計書（サービス層仕様）
- GitHub Issue #19 — 設計方針の議論

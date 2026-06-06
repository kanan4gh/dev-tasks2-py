# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 「実装が複雑すぎるため後回し」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: プロジェクト管理サービス

- [x] `src/task_cli/services/project_service.py` を新規作成
  - [x] `ProjectService.create_project(name)` — GlobalConfig に追加、last_project_id をインクリメント、重複名は AppError
  - [x] `ProjectService.list_projects()` — ProjectEntry[] を返す
  - [x] `ProjectService.get_project(name)` — 存在しない場合 AppError
  - [x] `ProjectService.use_project(name)` — active_project を切り替え
  - [x] `ProjectService.remove_project(name)` — エントリ削除、アクティブだった場合は None にリセット

- [x] `tests/test_project_service.py` を新規作成
  - [x] `create_project` 正常系（重複なし）
  - [x] `create_project` 異常系（重複名）
  - [x] `list_projects` 正常系
  - [x] `get_project` 正常系
  - [x] `get_project` 異常系（存在しない名前）
  - [x] `use_project` 正常系
  - [x] `use_project` 異常系（存在しない名前）
  - [x] `remove_project` 正常系（非アクティブ）
  - [x] `remove_project` 正常系（アクティブプロジェクトを削除 → active_project が None になる）
  - [x] `remove_project` 異常系（存在しない名前）

## フェーズ2: move_task ユースケース

- [x] `src/task_cli/usecases/task_crud_usecase.py` に `move_task` を追加
  - [x] 移動元からタスク取得
  - [x] 移動先ストレージで next_id() を取得
  - [x] タスクを新 ID でコピーして移動先に追加
  - [x] 移動元からタスクを削除

- [x] `tests/test_usecases.py` に `move_task` テストを追加
  - [x] プロジェクト → プロジェクト移動の正常系
  - [x] プロジェクト → inbox 移動（target_project=None）の正常系
  - [x] 存在しない ID の異常系

## フェーズ3: ステータス操作 CLI コマンド

- [x] `src/task_cli/cli/commands/start.py` を新規作成
  - [x] `task-py start <id>` → `uc.start_task(id)` → 成功メッセージ
- [x] `src/task_cli/cli/commands/done.py` を新規作成
  - [x] `task-py done <id>` → `uc.complete_task(id)` → 成功メッセージ
- [x] `src/task_cli/cli/commands/delete.py` を新規作成
  - [x] `task-py delete <id>` → タスク取得してタイトル表示 → `typer.confirm()` → `uc.delete_task(id)`
- [x] `src/task_cli/cli/commands/archive.py` を新規作成
  - [x] `task-py archive <id>` → `uc.archive_task(id)` → 成功メッセージ

## フェーズ4: プロジェクト管理 CLI コマンド

- [x] `src/task_cli/cli/commands/project.py` を新規作成（typer サブアプリ）
  - [x] `project create <name>` — ProjectService.create_project → 成功メッセージ
  - [x] `project list` — ProjectService.list_projects + 各プロジェクトのタスク数を読んで表示
  - [x] `project use <name>` — ProjectService.use_project → 成功メッセージ
  - [x] `project remove <name>` — タイトル表示 → `typer.confirm()` → ProjectService.remove_project

## フェーズ5: move・inbox CLI コマンド

- [x] `src/task_cli/cli/commands/move.py` を新規作成
  - [x] `task-py move <id> <project>` → `uc.move_task(id, target)` → 成功メッセージ
  - [x] `project` 引数が `"inbox"` の場合は `target_project=None` を渡す
- [x] `src/task_cli/cli/commands/inbox.py` を新規作成
  - [x] `task-py inbox` → `global_config_service.set_active_project(None)` → 成功メッセージ

## フェーズ6: main.py にコマンド登録

- [x] `src/task_cli/cli/main.py` を更新
  - [x] `start`, `done`, `delete`, `archive` を登録
  - [x] `project` サブアプリを登録（`app.add_typer(project_app, name="project")`）
  - [x] `move`, `inbox` を登録

## フェーズ7: 品質チェック

- [x] `uv run pytest` — 全テスト通過を確認（81件）
- [x] `uv run pyright src tests` — 型エラーゼロを確認
- [x] 動作確認（手動）
  - [x] `uv run task-py project create myproject` が動く
  - [x] `uv run task-py project list` が動く
  - [x] `uv run task-py project use myproject` が動く
  - [x] `uv run task-py add "テスト"` → `uv run task-py start 1` → `uv run task-py done 1` が動く
  - [x] `uv run task-py delete <id>` が動く（確認プロンプト付き）
  - [x] `uv run task-py move <id> inbox` が動く
  - [x] `uv run task-py inbox` が動く

## フェーズ8: ドキュメント更新

- [x] `README.md` にコマンド一覧を追記

---

## 実装後の振り返り

### 実装完了日
2026-06-06

### 計画と実績の差分

**計画と異なった点**:
- `move_task` のテストで storage_factory が複数プロジェクトを同一ファイルにマップする問題が発生。factory のキーをフルパス、ファイルを `{parent}_{name}` のユニーク名に変更して解決

**新たに必要になったタスク**:
- テストヘルパー `make_use_case` の storage_factory を複数プロジェクト対応に修正

### 学んだこと

**技術的な学び**:
- typer の `add_typer()` でサブコマンドグループを作れる（`project create/list/use/remove`）
- テスト用 storage_factory でパス衝突に注意が必要

**プロセス上の改善点**:
- フェーズごとに pytest を走らせることで問題を早期発見できた

### 次回への改善提案
- `project list` の表示で rich の Table を使うとより整列が綺麗になる

### リリース判断

**前提条件の確認**:
- [x] 全テスト通過（`uv run pytest`）— 81件
- [x] 型チェック通過（`uv run pyright src tests`）— エラーゼロ
- [x] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes（MVP 相当のコマンドが揃った） |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR（新機能追加） |

**提案**:
`v0.2.0` へのバージョンアップを提案。全コマンドが揃い実用可能な状態になったため MINOR バージョンアップが適切。

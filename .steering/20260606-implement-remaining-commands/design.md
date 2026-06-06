# 設計書

## アーキテクチャ概要

既存の Clean Architecture 4 層構造をそのまま踏襲する。

```
CLI レイヤー（cli/commands/）
    ↓
ユースケース層（usecases/task_crud_usecase.py）
    ↓
サービスレイヤー（services/task_manager.py, global_config_service.py）
    ↓
ストレージレイヤー（storage/file_storage.py, global_config_storage.py）
```

## コンポーネント設計

### 1. ステータス操作コマンド（cli/commands/）

**責務**: ID を受け取り、usecase の対応メソッドを呼ぶ

**実装の要点**:
- `start.py`, `done.py`, `delete.py`, `archive.py` を新規作成
- `delete` のみ確認プロンプト（`typer.confirm()`）を追加
- パターンは `add.py` に従う: `get_use_case()` → usecase 呼び出し → `render_success/render_error`

### 2. プロジェクト管理サービス（services/project_service.py）

**責務**: GlobalConfig のプロジェクト一覧の CRUD

```python
class ProjectService:
    def create_project(self, name: str) -> ProjectEntry
    def list_projects(self) -> list[ProjectEntry]
    def use_project(self, name: str) -> None
    def remove_project(self, name: str) -> None
    def get_project(self, name: str) -> ProjectEntry  # 存在チェック用
```

**実装の要点**:
- 重複名・存在しない名前は `AppError` で返す
- `create_project` は GlobalConfig.last_project_id をインクリメントして ID を採番
- `remove_project` でアクティブプロジェクトを削除した場合は `active_project` を `None` にリセット

### 3. タスク移動ユースケース（usecases/task_crud_usecase.py に追加）

**責務**: 移動元からタスクを取得し、移動先に追加、移動元から削除

```python
def move_task(self, id: int, target_project: str | None) -> Task:
    # target_project=None → Inbox
```

**実装の要点**:
- 移動先の `FileStorage` を別途作成してタスクを保存
- ID は移動先で `next_id()` を振り直す（移動先のIDと衝突しないため）
- 移動元から削除

### 4. プロジェクト管理コマンド（cli/commands/project.py）

**責務**: `task-py project` サブコマンド群

**実装の要点**:
- typer サブアプリ（`project_app = typer.Typer()`）を作成
- `project list` では `~/.task-py/projects/<name>/tasks.yaml` を読んでタスク数を表示
- `project list` の表示フォーマット（functional-design.md 参照）:
  ```
  * my-app     5 tasks (2 in_progress)   ← アクティブプロジェクト
    personal   3 tasks (0 in_progress)
  ─────────────────────────────────────
    [Inbox]    1 task
  ```

### 5. move・inbox コマンド（cli/commands/）

- `move.py`: `<id>` と `<project>` を受け取り `uc.move_task()` を呼ぶ
- `inbox.py`: `global_config_service.set_active_project(None)` を呼ぶ

## データフロー

### move <id> <project>
```
1. アクティブプロジェクトのストレージからタスク取得
2. 移動先ストレージで next_id() を取得
3. タスクを新 ID でコピー
4. 移動先ストレージに追加
5. 移動元ストレージから削除
6. 成功メッセージ表示
```

### project remove <name>
```
1. プロジェクトの存在確認
2. 確認プロンプト
3. GlobalConfig.projects からエントリ削除
4. アクティブプロジェクトだった場合は active_project = None
5. ~/ task-py/projects/<name>/ ディレクトリは削除しない（データ保護）
```

## エラーハンドリング戦略

既存の `AppError(message, cause, remedy)` を使用する。

| ケース | メッセージ例 |
|--------|-------------|
| 存在しないプロジェクト | `プロジェクトが見つかりません。` |
| 重複プロジェクト名 | `同名のプロジェクトが既に存在します。` |
| 不正ステータス遷移 | 既存の TaskManager のエラーを流用 |

## テスト戦略

### ユニットテスト
- `tests/test_project_service.py` — create/list/use/remove の正常系・異常系
- `tests/test_usecases.py` に move_task のテストを追加

### 動作確認（手動）
- `uv run task-py project create myproject`
- `uv run task-py project list`
- `uv run task-py start 1` / `done 1` / `delete 1` / `archive 1`
- `uv run task-py move 1 myproject`
- `uv run task-py inbox`

## 依存ライブラリ

新規追加なし。

## ディレクトリ構造

```
src/task_cli/
├── cli/
│   ├── commands/
│   │   ├── add.py        (既存)
│   │   ├── archive.py    (新規)
│   │   ├── delete.py     (新規)
│   │   ├── done.py       (新規)
│   │   ├── inbox.py      (新規)
│   │   ├── list.py       (既存)
│   │   ├── move.py       (新規)
│   │   ├── project.py    (新規)
│   │   ├── show.py       (既存)
│   │   └── start.py      (新規)
│   └── main.py           (更新: 新コマンドを登録)
├── services/
│   ├── global_config_service.py  (既存)
│   ├── project_service.py        (新規)
│   └── task_manager.py           (既存)
└── usecases/
    └── task_crud_usecase.py      (更新: move_task 追加)
tests/
├── test_project_service.py   (新規)
└── test_usecases.py          (更新: move_task テスト追加)
```

## 実装の順序

1. `project_service.py` — プロジェクト管理サービス
2. `test_project_service.py` — サービスのテスト
3. `task_crud_usecase.py` に `move_task` 追加
4. `test_usecases.py` に move_task テスト追加
5. CLIコマンド: `start.py`, `done.py`, `delete.py`, `archive.py`
6. CLIコマンド: `project.py`（サブアプリ）
7. CLIコマンド: `move.py`, `inbox.py`
8. `main.py` に全コマンドを登録
9. 品質チェック（pytest + pyright）
10. README 更新

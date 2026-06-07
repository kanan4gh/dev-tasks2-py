# 設計書

## アーキテクチャ概要

既存の Clean Architecture に乗せず、**単体の変換スクリプト**として実装する。
migrate は一度きりの操作であり、ストレージ層・ユースケース層を経由する必要がない。
Python 標準ライブラリの `json` で TypeScript 版 JSON を読み、
既存の Pydantic モデルを使って Python 版 YAML に書き出す。

```
~/.task/ (TypeScript JSON, camelCase)
  ├── config.json
  ├── inbox/tasks.json
  ├── projects/*/tasks.json
  └── daily/
      ├── routines.json
      └── log.json
          │
          ▼  task-py migrate
          │
~/.task-py/ (Python YAML, snake_case)
  ├── config.yaml
  ├── inbox/tasks.yaml
  ├── projects/*/tasks.yaml
  └── daily/
      ├── routines.yaml
      └── log.yaml
```

## フィールド変換仕様

### config.json → config.yaml

| TypeScript（camelCase）  | Python（snake_case）  |
|--------------------------|----------------------|
| `activeProject`          | `active_project`     |
| `lastProjectId`          | `last_project_id`    |
| `projects[].name`        | `projects[].name`    |
| `projects[].id`          | `projects[].id`      |

### tasks.json → tasks.yaml（inbox・projects 共通）

| TypeScript（camelCase）  | Python（snake_case）  |
|--------------------------|----------------------|
| `dueDate`                | `due_date`           |
| `scheduledDate`          | `scheduled_date`     |
| `createdAt`              | `created_at`         |
| `updatedAt`              | `updated_at`         |
| その他フィールド           | そのまま              |

### routines.json → routines.yaml

| TypeScript（camelCase）  | Python（snake_case）  |
|--------------------------|----------------------|
| `createdAt`              | `created_at`         |
| その他フィールド           | そのまま              |

### log.json → log.yaml（DailyLog entries の形式変換）

TypeScript:
```json
{"date": "2026-06-06", "entries": {"1": "done", "2": "pending"}}
```

Python:
```yaml
date: '2026-06-06'
entries:
  - routine_id: 1
    status: done
  - routine_id: 2
    status: pending
```

変換: `entries` の各 `{key: status}` → `{routine_id: int(key), status: status}`

## コンポーネント設計

### `src/task_cli/cli/commands/migrate.py`

**責務**:
- TypeScript 版データを読み込んで Python 版データに変換・書き込む
- `--dry-run` モードでプレビュー表示のみ実行
- 既存データが存在する場合は上書き確認
- 結果サマリーを rich で表示

**実装の要点**:
- `json` モジュールで TS JSON を読む（pydantic を通さず生 dict 操作）
- 変換後は既存の Pydantic モデル（Task, GlobalConfig, Routine, DailyLog 等）を使って
  YAML 書き込み（storage 層を直接呼ぶ）
- `--dry-run` では rich の Panel/Table でプレビュー表示、ファイル書き込みなし
- 既存データ上書きは `--force` フラグまたは対話的確認（typer.confirm）

**関数構成**:
```python
def migrate(dry_run: bool, force: bool) -> None:
    # メインエントリポイント

def _read_ts_config(ts_dir: Path) -> dict
def _convert_config(raw: dict) -> GlobalConfig
def _read_ts_tasks(path: Path) -> list[dict]
def _convert_tasks(raw_tasks: list[dict]) -> list[Task]
def _read_ts_routines(path: Path) -> list[dict]
def _convert_routines(raw: list[dict]) -> list[Routine]
def _read_ts_logs(path: Path) -> list[dict]
def _convert_logs(raw: list[dict]) -> list[DailyLog]
def _print_preview(...)  # dry-run 時の表示
def _print_summary(...)  # 実行後サマリー
```

## データフロー

### 通常実行（`task-py migrate`）

```
1. ~/.task/ の存在確認
2. ~/.task-py/ の既存データ確認 → 存在する場合は上書き確認
3. config.json を読み込み、GlobalConfig に変換して config.yaml に保存
4. inbox/tasks.json を読み込み、list[Task] に変換して tasks.yaml に保存
5. projects/ を走査し、各プロジェクトの tasks.json を変換
6. daily/routines.json を変換して routines.yaml に保存
7. daily/log.json を変換して log.yaml に保存
8. サマリーを表示（変換したファイル数・タスク数・ルーティン数・ログ日数）
```

### `--dry-run`

```
1. ~/.task/ の存在確認
2. 各ファイルを読み込み、変換内容を rich テーブルで表示
3. ファイルの書き込みは一切行わない
4. 「X件のタスク、Y件のルーティン、Zログを移行します」と表示
```

## エラーハンドリング戦略

- `~/.task/` が存在しない → AppError でユーザーフレンドリーなメッセージ
- TS データのパースエラー → ファイル名を明示してスキップ or 中断
- TS のフィールドが想定と異なる（旧フォーマット等）→ デフォルト値でフォールバック

## テスト戦略

### ユニットテスト（`tests/test_migrate.py`）

- `_convert_config`: camelCase → snake_case の変換
- `_convert_tasks`: フィールド変換、全フィールドが正しく変換される
- `_convert_routines`: `createdAt` → `created_at`
- `_convert_logs`: `entries` の dict → list 変換
- エラーケース: `~/.task/` が存在しない場合

## 依存ライブラリ

新規追加なし（`json`, `pathlib` は標準ライブラリ）

## ディレクトリ構造

```
src/task_cli/cli/commands/
  migrate.py          ← 新規
docs/
  migration-from-ts.md ← 新規
tests/
  test_migrate.py      ← 新規
```

## 実装の順序

1. `migrate.py` コマンド本体を実装（dry-run 含む）
2. `main.py` に `migrate` コマンドを登録
3. テスト `test_migrate.py` を作成
4. `docs/migration-from-ts.md` を作成
5. 品質チェック（pytest / pyright）

## セキュリティ考慮事項

- `~/.task/` と `~/.task-py/` はいずれも `chmod 700` で保護（既存の storage 層が担保）
- `json.load` はパスインジェクションを行わない（固定パスのみ）

## パフォーマンス考慮事項

- 移行は一度きりの操作であり、パフォーマンス要件なし
- タスク数が数百件程度であれば即時完了する想定

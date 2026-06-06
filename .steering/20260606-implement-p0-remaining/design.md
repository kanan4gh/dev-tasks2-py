# 設計書

## アーキテクチャ概要

既存の Clean Architecture 4 層構造を踏襲しつつ、daily 機能用の新レイヤーを追加。

```
CLI レイヤー
  ├── commands/list.py          (更新: --all / --inbox オプション)
  ├── commands/project.py       (更新: rename サブコマンド追加)
  ├── commands/search.py        (新規)
  ├── commands/onboard.py       (新規)
  ├── commands/daily.py         (新規: サブアプリ)
  └── commands/time.py          (新規)
サービスレイヤー
  ├── project_service.py        (更新: rename_project 追加)
  └── daily_service.py          (新規)
ストレージレイヤー
  ├── routine_storage.py        (新規)
  └── daily_log_storage.py      (新規)
モデル層
  └── daily.py                  (新規: Routine, DailyLog)
```

---

## A: list --all / --inbox

### 設計

`TaskCrudUseCase` に以下を追加:

```python
def list_all_projects(self, filter: TaskFilter | None = None) -> dict[str, list[Task]]:
    # GlobalConfig.projects + inbox のタスクを {プロジェクト名: [Task]} で返す
    # inbox のキーは None

def list_inbox_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
    # inbox のタスクのみ返す
```

### 表示

`--all` は `render_task_table` をプロジェクトごとに繰り返し呼ぶ。
アクティブプロジェクトのヘッダーは `[bold green]` で強調。

---

## B: project rename

### 設計

`ProjectService` に追加:

```python
def rename_project(self, old: str, new: str) -> None:
    # 1. old の存在確認
    # 2. new が重複していないか確認
    # 3. GlobalConfig.projects の name を更新
    # 4. active_project が old なら new に更新
    # 5. ディレクトリをリネーム（存在する場合のみ）
```

ディレクトリリネームは `Path.rename()` を使用。存在しない場合はスキップ（データがなくてもエラーにしない）。

---

## C: search

CLIコマンドのみ追加。`uc.search_tasks(keyword)` を呼んで `render_task_table` で表示。
検索対象はアクティブプロジェクト（またはInbox）。

---

## D: onboard

### 表示構成

```
═══════════════════════════════
  [Project: myapp]  （または [Inbox]）
═══════════════════════════════

📋 今日のルーティーン  （daily 実装後に有効）
  - 未実装のため省略

🚀 今とりかかるべきタスク
  1-1  in_progress  ユーザー認証実装
  1-2  open         DB設計

📝 すべてのタスク
  （list コマンドと同じテーブル、全ステータス）
```

daily が実装済みの場合は pending なルーティーンを表示する。

---

## E: daily

### データモデル（`models/daily.py`）

```python
class Routine(BaseModel):
    id: int
    title: str
    paused: bool = False
    created_at: datetime

class DailyLogEntry(BaseModel):
    routine_id: int
    status: Literal["pending", "done"] = "pending"

class DailyLog(BaseModel):
    date: str           # "YYYY-MM-DD"
    entries: list[DailyLogEntry] = []
```

### ストレージ

| クラス | ファイル |
|--------|---------|
| `RoutineStorage` | `~/.task-py/daily/routines.yaml` |
| `DailyLogStorage` | `~/.task-py/daily/log.yaml`（直近30日分） |

### DailyService の主要メソッド

```python
class DailyService:
    def add_routine(self, title: str) -> Routine
    def list_today(self, include_paused: bool = False) -> list[tuple[Routine, str]]
        # (Routine, status) のリスト。達成率高い順、paused は末尾
    def mark_done(self, id: int) -> None
    def pause(self, id: int) -> None
    def resume(self, id: int) -> None
    def resume_all(self) -> int   # 再開した件数を返す
    def delete(self, id: int) -> None
    def stats(self) -> list[dict]  # 直近7日の日別達成率
    def reset_today(self) -> None
    def _ensure_today_log(self) -> None  # 日付が変わったら新しいログを自動作成
```

### 達成率の計算

```
達成率 = done数 / (done数 + pending数)  ※ paused は除外
```

`daily list` の表示順: 達成率が高いルーティーンを上位に表示。同率は id 順。paused は末尾。

### `daily stats` の表示例

```
日付         月   火   水   木   金   土   日
──────────────────────────────────────────
2026-05-31  100%  75%  50%  --   --   --   --
...
```

`--` は当日にルーティーンが0件だった日。

---

## F: time start

### duration パース

```python
def parse_duration(s: str) -> int:  # 秒数を返す
    # "20min" / "20m" → 1200
    # "1h"            → 3600
    # "30s"           → 30
    # "20"            → 1200（数値のみは分）
```

### 表示（rich Live）

```python
from rich.live import Live

with Live(refresh_per_second=1) as live:
    while remaining > 0:
        live.update(f"⏱  残り {format_time(remaining)}")
        time.sleep(1)
        remaining -= 1
print("\a")  # ターミナルベル
```

Ctrl+C は `KeyboardInterrupt` をキャッチして「キャンセルしました」を表示。

---

## テスト戦略

### ユニットテスト追加対象

| ファイル | 内容 |
|---------|------|
| `tests/test_project_service.py` | `rename_project` の正常系・異常系 |
| `tests/test_usecases.py` | `list_all_projects` / `list_inbox_tasks` |
| `tests/test_daily_service.py` | DailyService の全メソッド |
| `tests/test_time.py` | `parse_duration` のパース |

---

## ディレクトリ構造（追加・変更分）

```
src/task_cli/
├── cli/
│   ├── commands/
│   │   ├── daily.py        (新規)
│   │   ├── onboard.py      (新規)
│   │   ├── search.py       (新規)
│   │   ├── time.py         (新規)
│   │   ├── list.py         (更新)
│   │   └── project.py      (更新)
│   └── main.py             (更新)
├── models/
│   └── daily.py            (新規)
├── services/
│   ├── daily_service.py    (新規)
│   └── project_service.py  (更新)
├── storage/
│   ├── routine_storage.py  (新規)
│   └── daily_log_storage.py (新規)
└── usecases/
    └── task_crud_usecase.py (更新)
tests/
├── test_daily_service.py   (新規)
└── test_time.py            (新規)
docs/ideas/
└── future-roadmap.md       (新規: G〜I を記録)
```

## 実装の順序

1. **A**: `list --all` / `--inbox`（usecase 拡張 + CLI）
2. **B**: `project rename`（service + CLI）
3. **C**: `search` CLI
4. **E-model**: daily モデル・ストレージ・サービス + テスト
5. **E-cli**: daily CLI コマンド群
6. **D**: `onboard`（daily が使えるので daily pending も表示）
7. **F**: `time start`（duration パース + rich Live）
8. 品質チェック・README 更新

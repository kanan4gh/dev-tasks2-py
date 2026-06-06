# 設計書

## アーキテクチャ概要

既存の Clean Architecture 4 層構造を踏襲。モデル層の変更が起点となり、上位層に伝播する。

```
CLI レイヤー
  ├── commands/edit.py      (新規)
  └── commands/schedule.py  (新規)
ユースケース層
  └── task_crud_usecase.py  (更新: edit_task / set_scheduled_date 追加)
サービス層
  └── task_manager.py       (更新: update_task / set_scheduled_date / start_task 変更)
モデル層
  └── models/task.py        (更新: scheduled_date フィールド追加)
```

---

## モデル設計

### `Task` モデルへの追加

```python
scheduled_date: str | None = None
```

`due_date` と同じ YYYY-MM-DD バリデータを適用。

---

## TaskManager の変更

### `update_task(id, data)` — 新規追加

```python
def update_task(
    self,
    id: int,
    title: str | None = None,
    description: str | None = None,
    priority: Priority | None = None,
    due_date: str | None = None,   # None = 変更なし、空文字 "" = 削除
    scheduled_date: str | None = None,  # 同上
) -> Task:
```

- `None` = 変更しない（フィールドをそのまま保持）
- 削除したい場合は専用フラグ（`clear_due_date: bool`、`clear_scheduled_date: bool`）で制御

> **設計判断**: Python の `None` は「値なし」と「変更なし」が区別できないため、`clear_*` フラグを使う。

### `set_scheduled_date(id, date | None)` — 新規追加

```python
def set_scheduled_date(self, id: int, date: str | None) -> Task:
```

`None` を渡すと解禁日を削除。

### `start_task` の変更

既存の遷移チェック後、以下を追加:

```python
if task.scheduled_date is not None:
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    if task.scheduled_date > today:
        raise AppError(
            "このタスクはまだ解禁されていません。",
            cause=f"scheduled_date ({task.scheduled_date}) が未来のため着手できません。",
            remedy=f"解禁日 ({task.scheduled_date}) 以降に start を実行してください。",
        )
```

---

## TaskCrudUseCase の変更

```python
def edit_task(
    self,
    id: int,
    title: str | None = None,
    description: str | None = None,
    priority: Priority | None = None,
    due_date: str | None = None,
    clear_due_date: bool = False,
    scheduled_date: str | None = None,
    clear_scheduled_date: bool = False,
) -> Task:
    return self._get_manager().update_task(
        id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        clear_due_date=clear_due_date,
        scheduled_date=scheduled_date,
        clear_scheduled_date=clear_scheduled_date,
    )

def set_scheduled_date(self, id: int, date: str | None) -> Task:
    return self._get_manager().set_scheduled_date(id, date)
```

---

## CLI 設計

### `edit.py`

```python
@app.command("edit")
def edit(
    id: int,
    title: Optional[str] = Option(None, "-t", "--title"),
    description: Optional[str] = Option(None, "-d", "--description"),
    priority: Optional[Priority] = Option(None, "-p", "--priority"),
    due: Optional[str] = Option(None, "--due"),
    due_clear: bool = Option(False, "--due-clear"),
    scheduled: Optional[str] = Option(None, "--scheduled"),
    scheduled_clear: bool = Option(False, "--scheduled-clear"),
)
```

オプションが1つも指定されていない場合は AppError。

### `schedule.py`

```python
@app.command("schedule")
def schedule(
    id: int,
    date: Optional[str] = Argument(None),
    clear: bool = Option(False, "--clear"),
)
```

`date` も `--clear` も指定がない場合は AppError。

---

## テスト戦略

| ファイル | 内容 |
|---------|------|
| `tests/test_usecases.py` | `edit_task` / `set_scheduled_date` の正常系・異常系 |
| 既存テスト | `start_task` の解禁日チェック（`TestTaskManagerStatusTransitions` に追加） |

---

## ディレクトリ構造（変更分）

```
src/task_cli/
├── cli/
│   ├── commands/
│   │   ├── edit.py        (新規)
│   │   └── schedule.py    (新規)
│   └── main.py            (更新)
├── models/
│   └── task.py            (更新: scheduled_date 追加)
├── services/
│   └── task_manager.py    (更新: update_task / set_scheduled_date / start_task)
└── usecases/
    └── task_crud_usecase.py (更新)
```

## 実装の順序

1. `Task` モデルに `scheduled_date` 追加
2. `TaskManager` に `update_task` / `set_scheduled_date` 追加、`start_task` 変更
3. `TaskCrudUseCase` に `edit_task` / `set_scheduled_date` 追加
4. テスト追加
5. CLI `edit.py` / `schedule.py` 作成・main.py に登録
6. README 更新

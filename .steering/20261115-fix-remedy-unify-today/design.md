# 設計書

## 方針

挙動を変えずに、(1) 対処文の文言を直し、(2) 重複した式を1つの関数にまとめる。どちらも再発防止の検査を足す。

## コンポーネント設計

### 1. `src/task_cli/clock.py`(新規)

- `today_str() -> str`: `datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")`。ローカルタイムゾーンの「今日」。解禁日(`scheduled_date`)の判定・表示とルーティーンの日付がこれを使う
- `task_manager.py` は `from task_cli.clock import today_str` で使う。`daily_service.py` は `from task_cli.clock import today_str as _today_str` とし、既存テストの `patch("task_cli.services.daily_service._today_str")` を壊さない。`renderer.py` の `_today()` は削除して `today_str` を使う

### 2. 対処文

- `task_manager.py`: `task list で…`(4か所)→ `task-py list で…`、`task start <id> で…`(1か所)→ `task-py start <id> で…`
- 文書: `functional-design.md` のエラー表の例、`architecture.md` の性能表(`task list`)、`development-guidelines.md` のサンプルコード

## テスト戦略

- `tests/test_user_facing_commands.py`(新規): `src/` の全 `.py` を AST で読み、docstring でない文字列定数に `task <コマンド>`(`task-py` ではない形)が無いこと。コマンド語の一覧は typer の登録から取る(手書きの一覧にしない)
- `tests/test_clock.py`(新規): `today_str()` の形式(`YYYY-MM-DD`)と、ローカル日付との一致。式の重複検査: `.astimezone().strftime(` が `src/` で `clock.py` にしか無いこと
- 既存の `show` と `start` の一致テスト(`test_cli_show_scheduled.py`)と `daily_service` のテストが通ること

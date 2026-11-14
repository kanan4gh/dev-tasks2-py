# 設計書

## 方針

`TaskFilter`(status / priority / sort)は既にあり、Web の一覧 API が使っている。CLI はそれを渡していないだけなので、オプションを足して `TaskFilter` に流す。表示は共有の `render_task_table` に列を足す。

## コンポーネント設計

### 1. `cli/commands/list.py`
- `--status`: `list[TaskStatus] | None`(typer の Enum リスト)。`--all-status` と併用すれば `typer.BadParameter`
- `--priority`: `Priority | None`、`--sort`: CLI 用の Enum `SortKey`(`id` / `priority` / `due_date` / `created_at`)。typer が選択肢(`click.Choice`)にするので、シェルの補完(#36)にも載る
- フィルタの組み立て: status = 指定があればそれ、無ければ(`--all-status` なら `None`、そうでなければ `[OPEN, IN_PROGRESS]`)。priority・sort はそのまま `TaskFilter` へ。`--all` / `--inbox` / 既定の3経路すべてに同じフィルタを渡す(既存の分岐を変えない)

### 2. `cli/renderer.py`
- `render_task_table`: 列を ID・Status・Priority・Title・Due に。Priority は既存の `_PRIORITY_STYLES` で着色。Due は `task.due_date or "-"`
- 期限切れの判定: `task.due_date is not None and task.due_date < today_str() and task.status in (OPEN, IN_PROGRESS)` → `[red]`。`today_str()` は `task_cli/clock.py`(#67)で、解禁日と同じ「今日」の定義
- `search` も `render_task_table` を使うので同じ列になる

## テスト戦略

- `tests/test_cli_list_options.py`(新規): 絞り込み(status 単一・複数・priority)、並べ替え(priority・due_date で期限なしが末尾・created_at)、`--status` と `--all-status` の併用エラー、`--all`・`--inbox` との併用
- `tests/test_cli_list_columns.py`(新規): Priority・Due 列の表示、期限切れの赤(rich の出力に色を残して検査)と、完了済み・今日・未来の期限が赤でないこと、`search` の列
- 既存テストへの影響(表の列を前提にした検査)を確認する

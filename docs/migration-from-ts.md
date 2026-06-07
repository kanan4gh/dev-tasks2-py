# TypeScript 版から Python 版への移行ガイド

## 前提条件

- TypeScript 版（dev-tasks2）が使用中で、`~/.task/` にデータが存在する
- Python 版（dev-tasks2-py）がインストール済み（`uv tool install` または `uv run task-py` で起動可能）

## データ構造の差異

| 項目           | TypeScript 版（dev-tasks2）        | Python 版（dev-tasks2-py）          |
|----------------|-----------------------------------|-------------------------------------|
| データディレクトリ | `~/.task/`                       | `~/.task-py/`                       |
| ファイル形式    | JSON                              | YAML                                |
| フィールド名    | camelCase（例: `dueDate`）        | snake_case（例: `due_date`）        |
| DailyLog形式   | `{id: "done"}` の辞書型           | `[{routine_id, status}]` のリスト型 |

### フィールド変換一覧

**タスク**

| TypeScript 版   | Python 版        |
|-----------------|-----------------|
| `dueDate`       | `due_date`      |
| `scheduledDate` | `scheduled_date`|
| `createdAt`     | `created_at`    |
| `updatedAt`     | `updated_at`    |

**設定ファイル**

| TypeScript 版     | Python 版          |
|-------------------|--------------------|
| `activeProject`   | `active_project`   |
| `lastProjectId`   | `last_project_id`  |

**ルーティン**

| TypeScript 版 | Python 版    |
|---------------|-------------|
| `createdAt`   | `created_at` |

## 移行手順

### ステップ 1: 事前確認（dry-run）

実際に書き込みを行わず、移行内容をプレビューします。

```bash
task-py migrate --dry-run
```

出力例:
```
╭──────────────────────────────────╮
│ 移行プレビュー（dry-run）         │
│ ファイルの書き込みは行いません。    │
╰──────────────────────────────────╯
         変換対象
┌──────────────────────┬──────┐
│ ファイル              │ 件数 │
├──────────────────────┼──────┤
│ config               │    1 │
│ inbox/tasks          │    5 │
│ projects/work/tasks  │   12 │
│ daily/routines       │    3 │
│ daily/log（日数）     │   30 │
└──────────────────────┴──────┘

合計: タスク 17 件、ルーティン 3 件、ログ 30 日分を移行します。
実際に移行するには --dry-run を外して実行してください。
```

### ステップ 2: 移行を実行

```bash
task-py migrate
```

`~/.task-py/` にすでにデータがある場合は、上書きするかどうかを確認します。

```
~/.task-py に既存データがあります。上書きしますか？ [y/N]:
```

確認なしで上書きしたい場合は `--force` を使用します：

```bash
task-py migrate --force
```

### ステップ 3: 移行結果を確認

```bash
task-py onboard      # 全体の状況を確認
task-py list         # タスク一覧を確認
task-py daily list   # ルーティン一覧を確認
```

## トラブルシューティング

### `TypeError: Vault directory not found` のようなエラーが出る

`~/.task/` が存在しない場合です。TypeScript 版で一度タスクを作成してからお試しください。

### タスクの日時がずれて見える

Python 版はタイムゾーン付きの ISO 8601 形式（例: `2026-06-06T10:00:00+00:00`）を保存します。表示上はシステムのタイムゾーンに変換されるため、正常な動作です。

### 移行後も TypeScript 版を使い続けたい

`~/.task/`（TypeScript 版）と `~/.task-py/`（Python 版）は完全に独立しています。移行後も TypeScript 版のデータは削除されないため、並行して使用できます。

Python 版に完全に切り替えたら、TypeScript 版の削除は手動で行ってください。

```bash
rm -rf ~/.task   # TypeScript 版データを削除（慎重に！）
```

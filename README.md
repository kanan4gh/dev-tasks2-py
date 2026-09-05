# dev-tasks2-py

タスク管理 CLI ツール。TypeScript 版 [dev-tasks2](https://github.com/kanan4gh/dev-tasks2) の Python/uv 再実装。

## インストール

[uv](https://docs.astral.sh/uv/) が必要です。

```bash
uv tool install git+https://github.com/kanan4gh/dev-tasks2-py
```

このコマンドはどのフォルダでも実行できます。グローバルにインストールされるため、カレントディレクトリは関係ありません。

インストール後は `task-py` コマンドが使えます。

## 使い方

### タスクの作成

```bash
task-py add "ユーザー認証機能の実装"
task-py add "バグ修正" --description "ログイン画面のバリデーションエラー" --priority high
task-py add "リリース作業" --due 2026-12-31
```

### タスク一覧

```bash
task-py list               # open と in_progress のみ表示
task-py list --all-status  # 全ステータスを表示
task-py list --all         # 全プロジェクト + Inbox のタスクを表示
task-py list --inbox       # Inbox のタスクのみ表示
```

表示例:

```
[Inbox]
  ID  Status  Title
 0-1  open    ユーザー認証機能の実装
 0-2  open    バグ修正
```

### タスク詳細

```bash
task-py show 1
```

### タスクの編集

```bash
task-py edit 1                       # $EDITOR で説明を編集（対話端末のみ）
task-py edit 1 -e                    # 他のオプションと併用してエディタを開く
task-py edit 1 --title "新しいタイトル"
task-py edit 1 -d "説明文" -p high
task-py edit 1 --due 2026-12-31
task-py edit 1 --due-clear           # 期限を削除
task-py edit 1 --scheduled 2026-07-01  # 解禁日を設定（それ以降に start できる）
task-py edit 1 --scheduled-clear       # 解禁日を削除
```

オプションを付けずに実行すると `$EDITOR` が開き、改行を含む長い説明を書けます。VS Code を使う場合は `--wait` が必須です。

```bash
export EDITOR="code --wait"
```

`VISUAL` → `EDITOR` の順に参照します。保存せずに閉じた場合・内容を元に戻した場合はどちらも「変更なし」として終了します。非対話環境（CI・パイプ）ではエディタを開かず、従来どおりオプションの指定を求めるエラーになります。

### 解禁日の設定

```bash
task-py schedule 1 2026-07-01  # 解禁日を設定
task-py schedule 1 --clear     # 解禁日を削除
```

解禁日が設定されたタスクは、その日付以降にならないと `start` できません。

### ステータス操作

```bash
task-py start 1    # in_progress に変更
task-py done 1     # completed に変更
task-py archive 1  # archived に変更
task-py delete 1   # 削除（確認プロンプトあり）
```

### タスク検索

```bash
task-py search "キーワード"  # アクティブプロジェクト内をキーワード検索
```

### プロジェクト管理

```bash
task-py project create myapp        # プロジェクトを作成（自動でアクティブに）
task-py project list                # プロジェクト一覧（タスク数付き）
task-py project use myapp           # アクティブプロジェクトを切り替え
task-py project rename myapp newapp # プロジェクトをリネーム
task-py project remove myapp        # プロジェクトを削除（確認プロンプトあり）
```

### タスク移動・Inbox

```bash
task-py move 1 other-project  # タスクを別プロジェクトへ移動
task-py move 1 inbox          # タスクを Inbox へ移動
task-py inbox                 # Inbox モードに切り替え
```

### デイリールーティーン

```bash
task-py daily add "朝のストレッチ"  # ルーティーンを追加
task-py daily list                  # 今日の一覧（done/pending）
task-py daily done 1                # ID 1 を完了にする
task-py daily pause 1               # 一時停止
task-py daily resume 1              # 再開（--all で全再開）
task-py daily delete 1              # 削除
task-py daily stats                 # 直近7日の達成率
task-py daily reset                 # 今日をすべて pending に戻す
```

### オンボーディング

```bash
task-py onboard  # アクティブプロジェクト・ルーティーン・優先タスクを要約表示
```

### タイマーと作業時間

```bash
task-py time start 25m            # 25分タイマー（完了時にベル通知）
task-py time start 1h             # 1時間タイマー
task-py time start 25m --task 1   # タスク1に作業時間を記録する
task-py time start --task 1       # 時間を省略するとストップウォッチ
task-py time start 25m --detach   # 残り時間を表示せず、状態だけ記録して抜ける

task-py time status               # 実行中タイマーの残り時間
task-py time stop                 # 終了して作業時間を記録
task-py time cancel               # 破棄（記録しない）
task-py time log 1 25m            # 作業時間を手動で記録
```

タイマーの状態は `~/.task-py/timer.yaml` に保存され、**別のシェルや MCP サーバーからも同じ状態が見えます**。残り時間は開始時刻から都度計算するので、シェルを閉じても・端末がスリープしても狂いません。実行中タイマーは同時に1本で、二重に開始しようとするとエラーになります（`--force` で置き換え可能。置き換えられた側の作業時間は記録されます）。

`--task` を付けたタイマーを `stop` すると、経過分がそのタスクの作業時間として記録されます。カウントダウンの場合、記録は設定時間が上限です（掛けっぱなしにした時間を作業時間にしないため）。合計は `task-py show <id>` で確認できます。

### インタラクティブシェル

```bash
task-py shell
```

起動するとプレフィックスなしでコマンドを連続実行できます。

```
task-py インタラクティブシェル（exit / quit で終了）
task [inbox]> list
task [inbox]> project use myapp
task [myapp]> add "新しいタスク"
task [myapp]> exit
```

- Tab キーでサブコマンドを補完
- プロンプトにアクティブプロジェクトをリアルタイム表示
- `exit` / `quit` または Ctrl+D で終了

## データ保存先

タスクデータはホームディレクトリの `~/.task-py/` に YAML 形式で保存されます。

```
~/.task-py/
├── config.yaml                    # グローバル設定
├── inbox/
│   └── tasks.yaml                 # Inbox タスク
├── projects/
│   └── <name>/
│       └── tasks.yaml             # プロジェクト別タスク
├── daily/
│   ├── routines.yaml              # ルーティーン定義
│   └── log.yaml                   # 日別達成ログ（直近30日）
└── timer.yaml                     # 実行中タイマー（プロセス間で共有）
```

作業時間の実績は独立したファイルではなく、各タスクの `work_sessions` として `tasks.yaml` に保存されます（`task-py move` でタスクを移動しても一緒に移ります）。

## アンインストール

ツール本体を削除するには:

```bash
uv tool uninstall dev-tasks2-py
```

タスクデータも合わせて削除する場合:

```bash
rm -rf ~/.task-py/
```

## MCP サーバー（Claude との連携）

task-py は MCP サーバーとして動作し、Claude との会話でタスクを自然言語管理できます。

### インストール

```bash
uv tool install git+https://github.com/kanan4gh/dev-tasks2-py.git
```

### Claude Code / Claude Desktop への登録

インストール後、`~/.claude.json`（Claude Code）または `~/Library/Application Support/Claude/claude_desktop_config.json`（Claude Desktop / Mac）に以下を追加してください:

```json
{
  "mcpServers": {
    "task-py": {
      "command": "task-mcp"
    }
  }
}
```

> **uvx で都度実行する場合（インストール不要）**:
> ```json
> {
>   "mcpServers": {
>     "task-py": {
>       "command": "uvx",
>       "args": ["--from", "git+https://github.com/kanan4gh/dev-tasks2-py.git", "task-mcp"]
>     }
>   }
> }
> ```

### 公開ツール一覧

| ツール | 説明 |
|--------|------|
| `list_tasks` | タスク一覧取得（ステータス絞り込み対応） |
| `add_task` | タスク作成 |
| `show_task` | タスク詳細取得 |
| `start_task` | タスクを in_progress に変更 |
| `complete_task` | タスクを completed に変更 |
| `delete_task` | タスク削除 |
| `archive_task` | タスクを archived に変更 |
| `edit_task` | タスク属性の編集 |
| `move_task` | タスクをプロジェクト間で移動 |
| `search_tasks` | キーワード検索 |
| `get_active_project` | 現在のアクティブプロジェクト取得 |
| `list_projects` | プロジェクト一覧取得 |
| `create_project` | プロジェクト作成 |
| `use_project` | アクティブプロジェクト切り替え |
| `get_overview` | 現在の状況概観（プロジェクト・ルーティーン・タスク） |
| `list_routines` | 今日のルーティーン一覧 |
| `add_routine` | ルーティーン登録 |
| `complete_routine` | ルーティーンを済にする |
| `pause_routine` | ルーティーンを一時停止 |
| `resume_routine` | ルーティーンを再開 |
| `delete_routine` | ルーティーン削除 |
| `get_daily_stats` | 直近7日の達成率 |
| `start_timer` | タイマー開始（常にバックグラウンド） |
| `get_timer_status` | 実行中タイマーの状態取得 |
| `stop_timer` | タイマー終了と作業時間の記録 |
| `cancel_timer` | タイマー破棄（記録しない） |
| `log_work_time` | 作業時間の手動記録 |
| `get_mcp_stats` | ツール別呼び出し回数の統計 |

CLI（`task-py`）と MCP サーバーは同じ `~/.task-py/` のデータを共有します。

## 開発者向け

```bash
git clone https://github.com/kanan4gh/dev-tasks2-py
cd dev-tasks2-py
uv sync
uv run task-py --help  # 開発環境での実行

uv run pytest          # テスト
uv run pyright src     # 型チェック
```

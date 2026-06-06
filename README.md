# dev-tasks2-py

タスク管理 CLI ツール。TypeScript 版 [dev-tasks2](https://github.com/kanan4gh/dev-tasks2) の Python/uv 再実装。

## インストール

[uv](https://docs.astral.sh/uv/) が必要です。

```bash
uv tool install git+https://github.com/kanan4gh/dev-tasks2-py
```

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
task-py edit 1 --title "新しいタイトル"
task-py edit 1 -d "説明文" -p high
task-py edit 1 --due 2026-12-31
task-py edit 1 --due-clear           # 期限を削除
task-py edit 1 --scheduled 2026-07-01  # 解禁日を設定（それ以降に start できる）
task-py edit 1 --scheduled-clear       # 解禁日を削除
```

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

### タイマー

```bash
task-py time start 25m  # 25分タイマー（完了時にベル通知）
task-py time start 1h   # 1時間タイマー
task-py time start 30s  # 30秒タイマー
```

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
└── daily/
    ├── routines.yaml              # ルーティーン定義
    └── log.yaml                   # 日別達成ログ（直近30日）
```

## 開発者向け

```bash
git clone https://github.com/kanan4gh/dev-tasks2-py
cd dev-tasks2-py
uv sync
uv run task-py --help  # 開発環境での実行

uv run pytest          # テスト
uv run pyright src     # 型チェック
```

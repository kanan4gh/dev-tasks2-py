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

## データ保存先

タスクデータはホームディレクトリの `~/.task/` に YAML 形式で保存されます。

```
~/.task/
├── config.yaml                    # グローバル設定
├── inbox/
│   └── tasks.yaml                 # Inbox タスク
└── projects/
    └── <name>/
        └── tasks.yaml             # プロジェクト別タスク
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

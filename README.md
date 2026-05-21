# dev-tasks2-py

タスク管理 CLI ツール。TypeScript 版 [dev-tasks2](https://github.com/kanan4gh/dev-tasks2) の Python/uv 再実装。

## 必要環境

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/)

## セットアップ

```bash
git clone https://github.com/kanan4gh/dev-tasks2-py
cd dev-tasks2-py
uv sync
```

## 使い方

### タスクの作成

```bash
uv run task add "ユーザー認証機能の実装"
uv run task add "バグ修正" --description "ログイン画面のバリデーションエラー" --priority high
uv run task add "リリース作業" --due 2026-12-31
```

### タスク一覧

```bash
uv run task list               # open と in_progress のみ表示
uv run task list --all-status  # 全ステータスを表示
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
uv run task show 1
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

## 開発

```bash
uv run pytest                  # テスト実行
uv run pytest --cov=src        # カバレッジ付き
uv run pyright src tests       # 型チェック
```

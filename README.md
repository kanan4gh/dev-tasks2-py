# dev-tasks2-py

タスク管理CLI（dev-tasks2）の Python 版実装。

TypeScript 版 [dev-tasks2](https://github.com/kanan4gh/dev-tasks2) の設計を流用し、Python/uv で再実装。

## セットアップ

> TODO: devcontainer の設定完了後に記載する

## 使い方

```bash
uv run task add "タスクタイトル"
uv run task list
uv run task show <id>
```

## 開発

```bash
uv run pytest
```

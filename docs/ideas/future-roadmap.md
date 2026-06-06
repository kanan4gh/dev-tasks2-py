# 将来のロードマップ（P1 以降）

P0 MVP 完了後に検討する機能。優先度・スコープは未確定。

## G: `task-py edit <id>` — タスク属性の編集

タスクのタイトル・説明・優先度・期限を対話的に編集する。

```bash
task-py edit 1
# → 各フィールドを順に入力（空 Enter でスキップ）
```

**実装の考慮点**:
- `prompt_toolkit` の入力ウィジェットを活用できる
- フィールド単位での部分更新（`update_task` は実装済み）

---

## H: Git ブランチ連携 (`task-py start` / `task-py done`)

`task-py start <id>` 実行時にブランチを自動作成し、`task-py done <id>` でブランチ削除。

```bash
task-py start 1
# → feature/task-1-user-authentication を作成してチェックアウト
# → .taskcli-current に task ID を保存
# → prepare-commit-msg フックをインストール

task-py done 1 --pr
# → ブランチを push → GitHub PR を自動作成
```

**実装の考慮点**:
- `gitpython` または `subprocess` で Git 操作
- ブランチ名生成: `feature/task-<id>-<slug>` （非 ASCII 除去）
- `.taskcli-current` を `.gitignore` に追加
- TypeScript 版の `GitService` / `GitHubService` を参照

---

## I: GitHub Issues 連携 (`task-py config` / `task-py sync` / `task-py import`)

GitHub Issues と双方向同期。

```bash
task-py config set github-token ghp_xxxx
task-py config set github-owner kanan4gh
task-py config set github-repo dev-tasks2-py

task-py sync          # GitHub Issues ↔ ローカルタスクを同期
task-py import --github  # GitHub Issues からインポート
```

**実装の考慮点**:
- `httpx` または標準 `urllib` で GitHub REST API v3 を呼び出す
- プロジェクト別設定を `~/.task-py/projects/<name>/config.yaml` に保存（chmod 600）
- TypeScript 版の `GitHubService` / `ConfigService` を参照

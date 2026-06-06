# 要求内容

## 概要

v0.1.2 で実装済みの add/list/show に続き、残りのすべてのコマンドを一括実装する。
サービス・ユースケース層のメソッドは実装済みのため、主に CLI コマンド追加とプロジェクト管理機能の追加が中心。

## 背景

TypeScript 版 dev-tasks2 の Python 再実装として、MVP に必要な全コマンドを揃える。

## 関連 Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/5

## 実装対象の機能

### 1. ステータス操作コマンド

- `task-py start <id>` — タスクを `in_progress` に変更
- `task-py done <id>` — タスクを `completed` に変更
- `task-py delete <id>` — タスクを削除（「削除しますか？ [y/N]」確認プロンプト付き）
- `task-py archive <id>` — タスクを `archived` に変更

### 2. プロジェクト管理コマンド

- `task-py project create <name>` — プロジェクトを作成し、アクティブに設定
- `task-py project list` — プロジェクト一覧表示（タスク数・アクティブマーク付き）
- `task-py project use <name>` — アクティブプロジェクトを切り替え
- `task-py project remove <name>` — プロジェクト削除（確認プロンプト付き）

### 3. タスク移動・Inbox

- `task-py move <id> <project>` — タスクを別プロジェクト（または `inbox`）に移動
- `task-py inbox` — アクティブプロジェクトを解除し Inbox モードに切り替え

## 受け入れ条件

### ステータス操作
- [ ] `task-py start <id>` でステータスが `in_progress` に変わる
- [ ] `task-py done <id>` でステータスが `completed` に変わる
- [ ] `task-py archive <id>` でステータスが `archived` に変わる
- [ ] `task-py delete <id>` で確認プロンプトが出て、y で削除、N でキャンセル
- [ ] 不正なステータス遷移は AppError で弾かれる

### プロジェクト管理
- [ ] `project create <name>` で `~/.task-py/projects/<name>/tasks.yaml` が作られる
- [ ] `project list` でプロジェクト一覧とタスク数が表示される
- [ ] `project use <name>` でアクティブプロジェクトが切り替わる
- [ ] `project remove <name>` で確認後に削除される
- [ ] 存在しないプロジェクト名はエラーになる

### タスク移動・Inbox
- [ ] `move <id> <project>` でタスクが移動する
- [ ] `move <id> inbox` で Inbox に移動する
- [ ] `inbox` コマンドで Inbox モードに切り替わる

### 品質
- [ ] pytest 全通過（既存 66 件 + 新規テスト）
- [ ] pyright エラーゼロ

## スコープ外

以下はこのフェーズでは実装しません:

- P1 機能（Git ブランチ自動連携、GitHub Issues 同期）
- `task project rename`（後フェーズ）
- `task-py search`（後フェーズ）
- `task-py edit`（後フェーズ）

## 参照ドキュメント

- `docs/functional-design.md` - 機能設計書
- `docs/architecture.md` - アーキテクチャ設計書

# 要求内容

## 概要

TypeScript 版（dev-tasks2）から Python 版（dev-tasks2-py）へのデータ移行コマンド `task-py migrate` と、ユーザー向け移行ガイドドキュメントを実装する。

## 背景

v0.5.0 で TypeScript 版との機能同等性が達成された。ユーザーが Python 版に切り替える際に、蓄積したタスク・ルーティンデータを失わずに移行できる手段が必要。

関連 Issue: https://github.com/kanan4gh/dev-tasks2-py/issues/13

## 実装対象の機能

### 1. `task-py migrate` コマンド

- `~/.task/`（TypeScript 版 JSON、camelCase）を読み込み、`~/.task-py/`（Python 版 YAML、snake_case）に変換して書き込む
- `--dry-run` オプション: 実際の書き込みを行わず、変換内容をプレビュー表示
- 変換対象のファイル:
  - `config.json` → `config.yaml`（フィールド名変換）
  - `inbox/tasks.json` → `inbox/tasks.yaml`（フィールド名変換）
  - `projects/*/tasks.json` → `projects/*/tasks.yaml`（フィールド名変換）
  - `daily/routines.json` → `daily/routines.yaml`（フィールド名変換）
  - `daily/log.json` → `daily/log.yaml`（entries 形式変換）

### 2. `docs/migration-from-ts.md`

- TypeScript 版から Python 版への移行手順をドキュメント化
- 前提条件・データの互換性の説明
- ステップバイステップの移行手順
- トラブルシューティング

## 受け入れ条件

### `task-py migrate`

- [ ] `~/.task/` が存在しない場合、エラーメッセージを表示して終了する
- [ ] `--dry-run` フラグで、変換内容のプレビューを表示する（ファイルは書き込まない）
- [ ] config（activeProject → active_project, lastProjectId → last_project_id）が正しく変換される
- [ ] タスクの camelCase フィールド（dueDate, scheduledDate, createdAt, updatedAt）が snake_case に変換される
- [ ] ルーティンの createdAt → created_at が変換される
- [ ] DailyLog の entries: `Record<number, status>` → `list[{routine_id, status}]` に変換される
- [ ] 既存の `~/.task-py/` データが存在する場合、上書き前に確認を求める
- [ ] 移行結果（変換したファイル数・タスク数等）をサマリー表示する

### `docs/migration-from-ts.md`

- [ ] TypeScript 版のデータ構造と Python 版の差異が記載されている
- [ ] `task-py migrate` コマンドの使い方が記載されている
- [ ] `--dry-run` での動作確認手順が記載されている

## 成功指標

- TypeScript 版ユーザーが、データロスなく Python 版に移行できる
- `--dry-run` で事前確認でき、安心して移行を実行できる

## スコープ外

以下はこのフェーズでは実装しません:

- Python 版 → TypeScript 版への逆移行
- 増分マイグレーション（差分のみ反映）
- TypeScript 版の自動アンインストール

## 参照ドキュメント

- `docs/product-requirements.md` - プロダクト要求定義書
- `docs/functional-design.md` - 機能設計書
- `docs/architecture.md` - アーキテクチャ設計書

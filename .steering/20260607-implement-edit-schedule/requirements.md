# 要求内容

## 概要

TypeScript 版に実装済みだが Python 版に未実装の `edit` と `schedule` コマンドを追加し、両版を完全に機能同等にする。

## 背景

Python 版 v0.4.0 で P0 MVP は揃ったが、TypeScript 版には `edit`（タスク属性の編集）と `schedule`（解禁日の設定）が実装されており、追随が必要。

## 関連 Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/11

## 実装対象の機能

### 1. `task-py edit <id>`
タスクの属性をフラグ指定で更新する。

```bash
task-py edit 1 --title "新しいタイトル"
task-py edit 1 -d "詳細説明"
task-py edit 1 --priority high
task-py edit 1 --due 2026-12-31
task-py edit 1 --due-clear
task-py edit 1 --scheduled 2026-07-01
task-py edit 1 --scheduled-clear
```

オプションが1つも指定されていない場合は AppError。

### 2. `task-py schedule <id> [date]`
解禁日（scheduled_date）を設定・削除する専用コマンド。

```bash
task-py schedule 1 2026-07-01   # 解禁日を設定
task-py schedule 1 --clear      # 解禁日を削除
```

解禁日以降でないと `task-py start` できない（start 時にチェック）。

## 受け入れ条件

### edit
- [ ] `edit 1 --title "X"` でタイトルが更新される
- [ ] `edit 1 --priority high` で優先度が更新される
- [ ] `edit 1 --due 2026-12-31` で期限が設定される
- [ ] `edit 1 --due-clear` で期限が削除される
- [ ] `edit 1 --scheduled 2026-07-01` で解禁日が設定される
- [ ] `edit 1 --scheduled-clear` で解禁日が削除される
- [ ] オプションなしで AppError

### schedule
- [ ] `schedule 1 2026-07-01` で解禁日が設定される
- [ ] `schedule 1 --clear` で解禁日が削除される
- [ ] 日付なし・--clear なしで AppError

### start の解禁日チェック
- [ ] 解禁日が未来のタスクに `start` すると AppError になる
- [ ] 解禁日が今日以前のタスクは `start` できる
- [ ] 解禁日未設定のタスクは従来通り `start` できる

### 共通
- [ ] pytest 全通過・pyright エラーゼロ

## スコープ外

- `task-py add` 時の `--scheduled` オプション（TypeScript 版にはあるが今回は追加しない）
- `list` での `excludeScheduled` フィルタ（TypeScript 版にある）

## 参照ドキュメント

- `docs/functional-design.md` — 機能設計書
- TypeScript 版: `src/cli/commands/edit.ts` / `src/cli/commands/schedule.ts`
- TypeScript 版: `src/services/TaskManager.ts`

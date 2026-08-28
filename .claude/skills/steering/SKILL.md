---
name: steering
description: 作業指示毎の作業計画、タスクリストをドキュメントに記録するためのスキル。ユーザーからの指示をトリガーとした作業計画時、実装時、検証時に読み込む。
allowed-tools: Read, Write, Edit, Bash
---

# Steering スキル

**手順の正は `docs/procedures/steering.md`(ハーネス中立の手順書)にある。必ず読み込み、記載のモード(1: 作業計画 / 2: 実装 / 3: 振り返り)に従うこと。** テンプレートは `docs/procedures/templates/` にある。

## Claude Code 固有の注記

- Stopフックは使用しない。通常の応答終了は作業状態を変更しない
- `.claude/hooks/remind_tasklist_update.py`のPostToolUseフックは、実装ファイルの編集が続いた場合にtasklist更新を非強制で促す
- 明示的な中断・再開・完了では`python3 scripts/steering_state.py pause / resume / complete`を使う
- 手順書の「ハーネス内部のタスク管理機能」はTodoWriteを指す(補助であり、正はtasklist.md)
- tasklist.mdの更新はEditツールでリアルタイムに行う

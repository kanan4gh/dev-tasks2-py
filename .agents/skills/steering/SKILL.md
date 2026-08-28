---
name: steering
description: 作業指示毎の作業計画、タスクリストをドキュメントに記録するためのスキル。作業計画時、実装時、検証(振り返り)時に「steeringを実行して」等と依頼されたとき、またはSDDフローの各段階で使う。
---

# Steering スキル(Codexアダプタ)

**手順の正は `docs/procedures/steering.md`(ハーネス中立の手順書)にある。必ず読み込み、記載のモード(1: 作業計画 / 2: 実装 / 3: 振り返り)に従うこと。** テンプレートは `docs/procedures/templates/` にある。

## Codex 固有の注記

- CodexではStopフックを使用しない。通常の応答終了は作業状態を変更せず、tasklist.mdのリアルタイム更新は自律的に徹底する
- 明示的な中断・再開・完了では`python3 scripts/steering_state.py pause / resume / complete`を使い、変更後に通常lintまたは完了lintで確認する
- 承認が必要な場面では、AGENTS.md正文のテキスト方式(選択肢を明示して回答を待つ)を使う
- **再開依頼を受けたら**: 最新の日付付きtasklistの`paused`状態と中断記録を読み、`resume --harness Codex`で`active`へ戻してからモード2を続行する。ハーネス切り替え時はrequirements.mdの使用ハーネス欄に「Codex」を追記する

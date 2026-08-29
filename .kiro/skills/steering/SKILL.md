---
name: steering
description: 作業指示ごとの要求・設計・タスクリストを作成、更新、振り返るSDDスキル。「steeringを実行して」「作業を再開して」「続きをやって」と依頼されたとき、またはSDDフローの計画・実装・検証で使う。
---

# Steering（Kiroアダプタ）

**手順の正は `docs/procedures/steering.md` にある。必ず全文を読み、モード1（計画）・モード2（実装）・モード3（振り返り）に従うこと。** テンプレートは `docs/procedures/templates/` にある。

## Kiro固有の割当

- Kiroはルート`AGENTS.md`を常時読み込むため、SDDの基本規範は追加のsteeringファイルへ複製しない
- Kiro IDE / CLIともStopフックを使用しない。通常の応答終了は作業状態を変更しない
- 明示的な中断・再開・完了では`python3 scripts/steering_state.py pause / resume / complete`を使う
- 承認が必要な場面では、選択肢を明示してユーザーの回答を待つ
- 再開依頼では最新の日付付きtasklistの`paused`状態と中断記録を読み、`resume --harness Kiro`で`active`へ戻してからモード2を続ける。ハーネス切り替え時はrequirements.mdの使用ハーネス欄に`Kiro`を追記する
- tasklist.mdは完了直後に更新し、ローカル品質ゲートを全環境共通の最終ゲートとする

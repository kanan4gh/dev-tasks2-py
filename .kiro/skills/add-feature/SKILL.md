---
name: add-feature
description: 新機能・バグ修正・既存機能変更をスペック駆動開発（SDD）フローで実装する。「add-featureを実行して」「新機能を追加して」「機能を実装して」と依頼されたときに使う。文書編集だけの依頼には使わない。
---

# 新機能追加（Kiroアダプタ）

**手順の正は `docs/procedures/add-feature.md` にある。必ず全文を読み、ステップ0〜8と完了条件に従うこと。**

## Kiro固有の割当

- ステップ4の計画は`.kiro/skills/steering/SKILL.md`から中立なsteering手順へ接続する
- ステップ4.5は唯一の承認ゲートである。計画要点と選択肢（承認して実装開始／修正を指示する／中止する）を示し、回答を待つ
- 承認後はtasklist.mdをリアルタイム更新しながらステップ5〜8を継続する。ステップ5が実装、ステップ6が4段検証、ステップ7が振り返りと`complete`遷移、ステップ8が単一最終ゲートを担当する
- ステップ8-BのG3受け入れは、ステップ4で「要」と判定した場合のみ実行する。Kiro IDEまたは`kiro-cli --agent sdd`で`docs/procedures/harness-acceptance.md`のKiro節を実施し、候補ゲート → 候補コミット → G3 → `acceptance-record.md`へ記録 → 最終ゲート再実行 → 記録コミット → PR の順序を守る
- 段4の独立検証は`.kiro/agents/implementation-validator.md`、docs変更時のレビューは`.kiro/agents/doc-reviewer.md`をサブエージェントとして使う。利用できない場合は独立した別コンテキストへ同じ手順を委譲する
- Kiro IDE / CLIともStopフックを使用せず、状態遷移と通常/完了lintを共通の決定論的経路とする
- 作業ツリー分離の専用機構を前提にせず、中立手順どおりフィーチャーブランチでmainから隔離する

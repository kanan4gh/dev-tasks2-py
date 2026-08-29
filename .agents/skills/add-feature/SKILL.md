---
name: add-feature
description: 新機能をスペック駆動開発(SDD)フローで実装する。「add-featureを実行して」「新機能を追加して」「〜機能を実装して」と依頼されたときに使う。バグ修正や既存機能の変更にも適用できる。ドキュメントの編集だけの依頼には使わない。
---

# 新機能の追加ワークフロー(Codexアダプタ)

**手順の正は `docs/procedures/add-feature.md`(ハーネス中立の手順書)にある。必ず読み込み、ステップ0〜8と完了条件に従うこと。**

## Codex 固有の注記(手順書の抽象記述への割当)

- **ステップ4のsteering手順**: `.agents/skills/steering/`(=`docs/procedures/steering.md`)を使う
- **ステップ4.5の承認ゲート**: テキスト方式(選択肢[承認して実装開始/修正を指示する/中止する]を明示して回答を待つ)
- **ステップ6・段1の検証コマンド**: AGENTS.md技術スタック固有層の「主要コマンド」を使う
- **ステップ6・段4のスペック準拠検証**: `.codex/agents/implementation-validator.toml` のサブエージェントに委譲する。docs/を変更した場合のドキュメントレビューは `.codex/agents/doc-reviewer.toml` に委譲する
- **ステップ8-Aの最終品質ゲート**: 振り返り・docs更新と`complete`遷移を終えた後、AGENTS.md技術スタック固有層の単一ゲートコマンドを1回実行して全緑にする
- **ステップ8-BのG3受け入れ**: ステップ4で「要」と判定した場合のみ実行する。Codex IDEまたは対話型CLIで `docs/procedures/harness-acceptance.md` の Codex 節を実施し、候補ゲート → 候補コミット → G3 → `acceptance-record.md` へ記録 → 最終ゲート再実行 → 記録コミット → PR の順序を守る。非対話LLM実行を代替手段にしない
- **作業ツリー分離**: 専用機構がないため、手順書の正文どおりフィーチャーブランチのみで隔離する(mainで実装を始めない)
- 実装ループ中のリマインド機構とStopフックはない。tasklist.mdの更新と明示的な状態遷移を自律的に徹底する

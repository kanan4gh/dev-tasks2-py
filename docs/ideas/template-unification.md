# テンプレート体制の単一正典化(後継作業メモ)

> 2026-07-15 環流第3回の体制判断の記録。本メモの作業自体は環流第3回のスコープ外。

## 決定(2026-07-15)

platform-harness(本リポジトリ)を「**中立コア+ハーネス別アダプタ**」の単一正典とする(project-uroboros-neo のハーネス換装第1〜5弾で実証済みの構成)。

## 現状のテンプレート体制

- **platform-harness**(本リポジトリ): 単一正典。中立コア(AGENTS.md・docs/procedures/・steering lint+CI)+Claudeアダプタ(CLAUDE.md・.claude/)+Codexアダプタ(.codex/・.agents/skills/)
- **platform-harness-engineering**: テンプレート工場(codex-template / kiro-template)
- **platform-harness-for-codex**: codex-template からの配布物

## 後継作業(未着手)

1. **codex-template の統合**: 同テンプレートのフック自前実装を本リポジトリのロジック共有方式(steering_lint import)へ更新し、エージェントTOMLの観点全文複製を手順書参照ラッパへ更新する。最終的に本リポジトリのCodexアダプタへ一本化
2. **platform-harness-for-codex の扱い**: 本リポジトリが単一正典化したため、Codex専用配布物の要否を再検討(本リポジトリの複製で足りる可能性)
3. **kiro-template**: 中立コアが確立したため、kiroアダプタ(.kiro相当+スキルラッパ)の追加として再実装できる見込み

## 参考

- 換装の構想と経緯: docs/ideas/harness-swap.md
- 実証プロジェクト: github.com/kanan4gh/project-uroboros-neo(v0.5.0〜v0.6.0)

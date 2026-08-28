# .codex/ ディレクトリ ガイド(Codexアダプタ)

このディレクトリと`.agents/skills/`は、SDDハーネスのCodex CLI用アダプタです。プロセスの正典は`AGENTS.md`、手順の正は`docs/procedures/`にあり、ここにはCodex固有の実装だけを置きます。

## 構成

```text
.codex/
├── README.md
└── agents/
    ├── implementation-validator.toml
    └── doc-reviewer.toml
.agents/
└── skills/
    ├── steering/
    ├── distill/
    ├── add-feature/
    ├── review-docs/
    └── setup-project/
```

スキルはチャットで「steeringを実行して」「add-featureを実行して」等と依頼します。スラッシュコマンドではありません。

## trust要件

`.codex/`配下のエージェント定義は、Codex CLIでプロジェクトをtrustした場合にロードされます。Stopフックと`.codex/hooks.json`は配布しないため、フック固有のtrust承認はありません。初回trustと実機受け入れは`docs/procedures/harness-acceptance.md`に従い、対話型セッションで行います。

## 推奨設定

`~/.codex/config.toml`は、Claude Code側と同じ「読み取り・検証=自動 / 書き込み・外部操作=都度確認」の境界を推奨します。

- 承認ポリシーは「失敗時・要求時に確認」相当を既定とし、確認なしとサンドボックス無効の組み合わせは避ける
- add-featureを使う場合も、ステップ4.5の計画承認は必ず経る

## steering状態と検証

CodexはStopフックを使いません。未完了の`active`作業があっても通常の応答は終了できます。

- 意図的中断: `python3 scripts/steering_state.py pause ...`
- 再開: `python3 scripts/steering_state.py resume ...`
- 完了: `python3 scripts/steering_state.py complete --harness Codex`
- 通常診断: `python3 scripts/steering_lint.py`
- PR前: `uv run python3 scripts/local_quality_gate.py`

ローカル品質ゲートは`steering_lint.py --require-complete`を1回起動し、全履歴の通常規則と対象ステアリングの完了規則を同じ走査で評価します。

## Claude Codeアダプタとの差分

| 項目 | Claude Code | Codex |
|---|---|---|
| Stopフック | なし | なし |
| 編集中のtasklistリマインド | PostToolUseで非強制通知 | なし。tasklistを自律的に即時更新 |
| 承認UI | 構造化UI | テキストまたはCodexの計画UI |
| サブエージェント | `.claude/agents/*.md` | `.codex/agents/*.toml` |

状態遷移・通常lint・完了lintはハーネス中立スクリプトを共有するため、上記のUI差が成果物の意味を変えることはありません。

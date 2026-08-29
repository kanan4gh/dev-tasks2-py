# Kiroアダプタガイド

`.kiro/`は、ハーネス中立のSDDコアをKiro IDE / Kiro CLIから使うための薄いアダプタです。プロセスの正典は`AGENTS.md`、手順の正は`docs/procedures/`にあります。

## 構成

```text
.kiro/
├── README.md
├── skills/
└── agents/
    ├── doc-reviewer.md
    ├── implementation-validator.md
    └── sdd.json
```

Kiroはワークスペースルートの`AGENTS.md`を読み込みます。`.kiro/skills/`はIDE / CLIの両方で発見され、依頼とのdescription一致または`/skill-name`で有効になります。

## Kiro IDE

1. リポジトリを開き、workspace agentのtrust確認を承認する
2. Agent Steering & Skillsで5つのworkspace skillが認識されていることを確認する
3. 例として`/steering`、`/add-feature ユーザープロフィール編集`を実行する
4. Agent selectorに`doc-reviewer`と`implementation-validator`が表示されることを確認する

## Kiro CLI

Kiro CLI 2.7.0以降、かつ`chat.disableInheritingDefaultResources=false`を対象とします。この条件ではカスタムエージェントも`AGENTS.md`、workspace skills、steeringを既定で継承するため、`sdd.json`はこれらをresourcesへ重複登録しません。

```bash
kiro-cli --version
kiro-cli agent validate --path .kiro/agents/sdd.json
kiro-cli --agent sdd
```

起動後に`/context`を実行し、`Active agent context: sdd`、`AGENTS.md`、5つのworkspace skillが各1回だけ表示されることを確認します。`sdd.json`はread / write / shell / subagentを利用可能にしますが、事前許可するのはreadだけです。書き込みとshellはKiroの確認対象のままです。

## steering状態と検証

Kiro IDE / CLIともStopフックを使いません。未完了の`active`作業があっても通常の応答は終了できます。

- 意図的中断: `python3 scripts/steering_state.py pause ...`
- 再開: `python3 scripts/steering_state.py resume ...`
- 完了: `python3 scripts/steering_state.py complete --harness Kiro`
- 通常診断: `python3 scripts/steering_lint.py`
- PR前: `uv run python3 scripts/local_quality_gate.py`

ローカル品質ゲートは`steering_lint.py --require-complete`を1回起動し、全履歴の通常規則と対象ステアリングの完了規則を同じ走査で評価します。

## 実機受け入れ

共通の受け入れ方針、fixture、証跡様式、headless modeを使わない規則は`docs/procedures/harness-acceptance.md`を参照してください。受け入れは対象commitの隔離cloneで実施し、製品作業用のステアリングと混同しません。

### IDE

- workspaceをtrustする
- 5 skillsと2 agentsが表示される
- 未完了の`active` fixtureを読んで確認文字列だけ返す依頼が、終了ブロックなく完了する
- 状態遷移CLIと通常／完了lintの結果を共通手順どおり観察する

### CLI

- `kiro-cli agent validate --path .kiro/agents/sdd.json`がexit 0になる
- `kiro-cli --agent sdd`を起動し、`/context`で5 skillsが各1回だけ表示される
- shellとwriteが事前許可されず、承認画面で拒否できる
- 未完了の`active` fixtureを読んで確認文字列だけ返す依頼が、終了ブロックなく完了する
- 状態遷移CLIと通常／完了lintの結果を共通手順どおり観察する

### 過去の受け入れ記録

2026-07-15には旧Stop契約のKiro CLI受け入れを行いました。これは当時の履歴であり、現行契約ではありません。現行の合格条件は、Stop登録がないこと、応答が正常終了すること、状態遷移とlintが共通経路として機能することです。

## スキル

| スキル | 用途 | 中立手順 |
|---|---|---|
| `steering` | 計画・実装・振り返り | `docs/procedures/steering.md` |
| `add-feature` | IssueからPRまでの機能実装 | `docs/procedures/add-feature.md` |
| `setup-project` | 6つの永続ドキュメント作成 | `docs/procedures/setup-project.md` |
| `review-docs` | ドキュメント品質レビュー | `docs/procedures/review-docs.md` |
| `distill` | 振り返りの蒸留と環流候補化 | `docs/procedures/distill.md` |

## IDEとCLIの差分

| 項目 | Kiro IDE | Kiro CLI |
|---|---|---|
| `AGENTS.md` | 自動読込 | 自動読込 |
| workspace skills | `.kiro/skills/` | `.kiro/skills/` |
| カスタムエージェント | Markdown(`*.md`) | JSON(`*.json`) |
| Stopフック | なし | なし |
| 最終ゲート | ローカル品質ゲート | ローカル品質ゲート |

## 既知の差分

- Claude CodeのPostToolUse tasklistリマインド相当はありません。tasklist.mdを完了直後に更新してください
- Kiro本体のインストールとアカウント認証はテンプレートの配布対象外です
- setup-project用の6つの詳細ガイドは、中立配置へ移すまで暫定的に`.claude/skills/`を参照します

## トラブルシューティング

- スキルが見えない: workspaceをtrustし、`/context`またはAgent Steering & Skillsで確認する
- CLIでスキルが二重表示される: `sdd.json`が既定継承される資源をresourcesへ再登録していないか確認する
- CLIの`sdd`だけスキルが見えない: workspace設定の`chat.disableInheritingDefaultResources`を`false`にする
- 状態遷移やlintが失敗する: tasklist.mdの状態ブロック・中断記録・未完了・振り返りを確認する
- カスタムサブエージェントが見えない: IDEではworkspace trust後に`.kiro/agents/*.md`を再読込する

## 公式仕様

- https://kiro.dev/docs/steering/
- https://kiro.dev/docs/skills/
- https://kiro.dev/docs/custom-agents/
- https://kiro.dev/docs/cli/skills/
- https://kiro.dev/docs/cli/custom-agents/configuration-reference/

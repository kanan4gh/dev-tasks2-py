# ハーネス対話型受け入れ手順

Claude Code、Codex、Kiroの表示・読込・権限・状態操作と応答終了を、従量課金型headless modeを使わずに確認する。構造と状態/lintロジックはpytestへ寄せ、本手順では実セッションでしか確認できない項目だけを扱う。

## 実施条件

- ローカル品質ゲートが1回で全緑になっている
- 対象commitが固定されている
- `/private/tmp`等の使い捨てclean cloneで実施する
- 対話型IDEまたは対話型CLIを使う
- Claude Codeのprint mode、Codexの非対話exec mode等、従量課金型headless modeを使わない

## add-feature ステップ8-Bとの接続

受け入れ結果を記録すると候補ゲート後にファイルが増える。この循環は、**受け入れ記録が製品ファイルを変更しない**ことを使って次の順序で直線化する。

1. **候補ゲート**: ローカル品質ゲートを1回で全緑にする
2. **候補コミット**: 全変更をコミットし、G3の固定commitにする
3. **G3実施**: 固定commitをclean cloneして対話型受け入れを行う
4. **結果記録**: 観察結果を元リポジトリ側の`acceptance-record.md`へ記録する
5. **最終ゲート**: 記録を含む最終状態でゲートを1回実行し全緑にする
6. **記録コミット**: acceptance recordをコミットする
7. **push / PR作成**: PR本文にG3結果を含める

不合格・保留で製品ファイルを修正した場合は、状態を`active`へ戻し、影響する検証・振り返り・`complete`遷移・候補ゲートからやり直す。G3不要の変更ではadd-featureステップ8-Aを使う。

## 自動検証との境界

| 観点 | 検証方法 |
|---|---|
| ファイル存在、JSON / Markdown構造 | pytest |
| 状態解析、pause / resume / complete、通常/完了lint | pytestと実スクリプト |
| Stopフック登録・実装の不在 | pytest |
| 禁止headlessシグネチャの不在 | metered automation lint |
| スキル・エージェントの表示と実読込 | 対話型実機確認 |
| read / write / shellの承認UI | 対話型実機確認 |
| 未完了tasklistを読むだけの依頼が正常終了すること | 対話型実機確認 |

## 共通準備

1. 対象commitを`/private/tmp`配下へclean cloneする
2. clone開始時点で未コミット変更がないことを確認する
3. 既存ステアリングより辞書順で後になる確認専用の日付付きsteeringを人が作る
4. requirements.mdへ検証用Issue URLを記載し、design.mdを置く
5. tasklist.mdを次の状態で作る
6. `python3 scripts/steering_lint.py`が通常検査で成功することを確認する
7. `docs/procedures/templates/harness-acceptance-record.md`の記録項目を確認する。fixture内へ記録ファイルは作らない
8. ハーネス名、バージョン、IDE / CLI、設定・承認ポリシー、対象commitを、clone外の一時メモへ記録する

```markdown
# タスクリスト

## 作業状態

- **状態**: active
- **状態更新日時**: {現在のタイムゾーン付きISO 8601}
- **使用ハーネス**: {対象ハーネス}

## 確認タスク

- [x] fixture準備
- [ ] 応答終了を妨げない未完了タスク

## 実装後の振り返り

{通常検査ではactiveのためプレースホルダーを許容}
```

fixtureは使い捨て複製の中だけに作る。agentへfixtureを完了・更新させず、読み取り確認だけを依頼する。
実施時点の未コミット変更はこの意図したfixtureだけであることを確認し、その他の変更があれば受け入れを止める。

観察中はclone外の一時メモへ記録し、終了後に**元リポジトリ側**の`.steering/[日付]-[タスク名]/acceptance-record.md`へテンプレート形式で転記する。fixture内の記録を正式証跡にせず、clone破棄前に転記漏れがないことを確認する。

## 共通の状態・lint確認

対話型ハーネス確認の前後で、人が次を実行して結果を記録する。

1. activeかつ未完了のfixtureで通常lintがexit 0
2. 同じfixtureを完了対象にするとG1だけでexit 1
3. `steering_state.py pause`でpausedと中断記録を生成
4. pausedの通常lintがexit 0
5. `steering_state.py resume`でactiveへ戻る
6. fixture内の全チェックと振り返りを人が完了
7. `steering_state.py complete`でcompleteへ遷移
8. `steering_lint.py --require-complete`がexit 0

この操作は製品リポジトリではなく使い捨てfixtureに限定する。

## Claude Code

1. clean cloneをClaude Code IDEまたは対話型CLIで開く
2. `AGENTS.md`、`CLAUDE.md`、主要スキルが表示されることを確認する
3. `@`候補または名前を明示した依頼で必要なsubagentを実起動できることを確認する
4. fixture tasklistを読み、状態・先頭の未完了タスク・再開位置候補だけを回答するよう依頼する
5. agentがfixtureを変更せず、未完了が残ったまま応答を正常終了することを確認する
6. read、write、shellを別々に依頼し、承認境界を観察する
7. PostToolUseリマインドは非強制であり、Stop blockが登録されていないことを設定表示と照合する
8. 実結果と証跡を記録する

## Codex

1. clean cloneをCodex IDEまたは対話型CLIで開く
2. `AGENTS.md`、`.agents/skills/`、必要なagentsが表示されることを確認する
3. fixture tasklistを読み、状態・先頭の未完了タスク・再開位置候補だけを回答するよう依頼する
4. agentがfixtureを変更せず、未完了が残ったまま応答を正常終了することを確認する
5. `.codex/hooks.json`がなく、Stop hookのtrust確認やfeedbackが発生しないことを観察する
6. read、write、shellを別々に依頼し、sandbox / approvalを観察する
7. 実結果と証跡を記録する

## Kiro IDE

1. clean cloneをKiro IDEで開く
2. Agent Steering & SkillsとAgent selectorに必要な項目が表示されることを確認する
3. steeringスキルの実読込を確認する
4. fixture tasklistを読むだけの依頼が変更なしで正常終了することを確認する
5. read / write / shellの承認UIを個別に確認する
6. 状態操作と通常/完了lintの結果を共通確認と照合する
7. 実結果と証跡を記録する

## Kiro CLI

1. agent validate後、`kiro-cli --agent sdd`で対話型起動する
2. `/context`で`AGENTS.md`とskillsが重複せず表示されることを確認する
3. fixture tasklistを読むだけの依頼が変更なしで正常終了することを確認する
4. `.kiro/agents/sdd.json`にstop hookがなく、自動継続やblock decisionが発生しないことを観察する
5. read事前許可とwrite / shellの承認UIを個別に確認する
6. 状態操作と通常/完了lintの結果を共通確認と照合する
7. 実結果と証跡を記録する

## 判定

- **合格**: 必須項目が期待どおりで、禁止headless modeを起動していない
- **不合格**: 期待結果との差異、意図しない変更・権限・自動継続がある
- **保留**: 環境・権限・製品バージョン差で観察できない
- **対象外**: 実行面が対象能力を提供しない。代替経路を記録する

未観察を推測で合格にしない。保留・対象外には理由と再確認条件または代替経路を記録する。

## 誤起動時

課金対象の可能性があるheadless実行に気づいたら直ちに停止し、時刻、呼び出し元、到達点、変更ファイルを記録する。別のheadless実行で再現せず、静的テストまたは対話型確認へ切り替える。

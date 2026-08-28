# 外部自動化ポリシー

## 目的

すべての開発者が同じ品質基準を実行できるよう、利用権限や従量課金を伴う外部自動化へ必須依存しない。品質保証の正はローカルの決定論的ゲートとし、LLMの実挙動は利用許可済みの対話型IDE / CLIで人が確認する。

## 標準の品質保証

### ローカル品質ゲート（必須）

```bash
uv run python3 scripts/local_quality_gate.py
```

pytest、ruff、basedpyright、steering lint、metered automation lintを固定順で実行する。ネットワーク、GitHub API、LLM CLIは呼び出さない。PR前に実行日時と結果を記録する。

### 対話型実機受け入れ（変更種別に応じて必須）

LLMの判断やハーネスUIを確認する場合は`docs/procedures/harness-acceptance.md`に従い、利用を許可されたIDEまたは対話型CLIで行う。自動化できる構造、形式、状態遷移・lint判定、Stop不在契約はpytestへ寄せる。

### GitHub Actions（任意）

workflowは配布互換性のため残すが、既定では無効とし、ファイル上のトリガーも`workflow_dispatch`だけにする。PR、push、scheduleでは起動しない。予算、権限、組織方針を確認した利用者だけが明示操作で有効化・手動実行でき、Actionsの成功はPR完了条件にしない。

## Metered Automation Lint

`scripts/metered_automation_policy.json`が禁止する非対話LLM実行シグネチャと検査範囲を一元管理し、`scripts/metered_automation_lint.py`が実行コード、設定、現行手順、各ハーネスアダプタを検査する。

現行指示面は、利用者がそのまま実行するREADME、手順、agent、skill、設定を指す。`.steering/`や`docs/ideas/`は過去の判断・実施を保持する監査履歴であり、現行指示面として再実行しない。

除外は次に限定する。

- `.steering/`: 実施・中断の監査履歴
- `docs/ideas/`: 正式手順ではない検討履歴
- 本ポリシー: 禁止シグネチャを説明する正典
- lint本体・policy・専用テスト: 検出定義と違反fixtureを保持するため
- `.claude/worktrees/`: 同一リポジトリの別checkout。**新たな指示面ではなく、検査済み指示面の重複**である
- `.git/`、仮想環境、キャッシュ

`.claude/worktrees/`の除外は次の理由による。

- 除外しても検査されない指示面は生まれない。その作業ツリーで作業する間は**その作業ツリー自身がルートとなってlintが走り**(自分の中に`.claude/worktrees/`を持たないため全ファイルが走査される)、マージ後は同じ内容が親リポジトリの実体として次のゲート実行時に検査される
- 除外しない場合、`include_paths`の`.claude`を再帰走査する過程で作業ツリー内の専用テスト・`.steering/`・`docs/ideas/`が拾われる。除外判定はリポジトリルート相対のため、入れ子のcheckout内には効かない
- 作業ツリーはPR作成後に後片付けするが、作業中・並行作業中・後片付け前は正当に存在する。除外がないと、その間に親リポジトリでゲートを回すたびに誤検出で落ちる

`.claude/`直下の現行指示面(command、skill、agent、hooks、settings)は引き続き走査対象である。除外は`.claude/worktrees/`配下に限定し、これを`tests/lint/test_metered_automation_lint.py`が実際の走査結果で固定する。

除外を追加する場合は、技術的理由と誤検出しないテストを同時に追加する。実行手順を隠す目的の除外は禁止する。

## シグネチャの拡張

利用先固有の禁止経路はpolicyの`signatures`へ一意なID、コマンド、headless引数を追加する。`include_paths`または`exclude_paths`を変える場合は、対象の存在、過剰除外、違反検出、正常例を専用テストで確認する。policy破損、読取失敗、Python構文解析失敗はfail-closedとする。

## 誤起動時の対応

1. 課金対象の可能性がある非対話LLM実行に気づいた時点で停止する
2. 実施日時、呼び出し元、到達点、成果物変更の有無を対象ステアリングへ記録する
3. 実行コードだけでなく、指示元の手順・設計・tasklistを特定する
4. 現行経路から除去し、metered automation lintの回帰テストを追加する
5. 利用状況や請求確認が必要な場合は組織管理者へ連絡する

# ハーネス実機受け入れ記録

platform-harness v1.6.1 移行（GitHub issue #26）の G3 対話型受け入れ。
`docs/procedures/harness-acceptance.md` に従い、固定commitの使い捨て clean clone で実施する。

## 共通の実施情報

| 項目 | 内容 |
|---|---|
| 担当者 | kanan4gh |
| OS | macOS 26.5.2 (arm64) |
| 対象リポジトリ | kanan4gh/dev-tasks2-py |
| commit / tag | `5f41e7b4bdca2dc1b0ffb3e771bd62ed3d5f685f` |
| 一時環境 | clean clone `/private/tmp/g3-dev-tasks2-py-v1-6-1` |
| 確認fixture | `.steering/20261231-g3-acceptance-fixture/`（clone内のみ。破棄する） |

## 事前条件

- [x] ローカル品質ゲートが1回で全緑になっている（候補ゲート、2026-08-29）
- [x] 一時環境はclean cloneから開始した
- [x] 実施時点の未コミット変更は意図した確認fixtureだけである
- [x] 意図しないファイル変更がない
- [x] 従量課金型headless modeを使用しないことを確認した

## 共通の状態・lint確認

`docs/procedures/harness-acceptance.md`「共通の状態・lint確認」8項目を clone 内 fixture に対して実行した。

| # | 操作 | 期待 | 実結果 | 判定 |
|---|---|---|---|---|
| 1 | active+未完了で通常lint | exit 0 | exit 0 | 合格 |
| 2 | 同fixtureを完了対象に | G1のみでexit 1 | exit 1、`[G1] 完了検査の対象ですが状態がactiveです` の1件のみ | 合格 |
| 3 | `steering_state.py pause` | pausedと中断記録を生成 | paused へ遷移、`### 中断記録: 2026-08-29T07:48:56+09:00` を生成 | 合格 |
| 4 | pausedで通常lint | exit 0 | exit 0 | 合格 |
| 5 | `steering_state.py resume` | activeへ復帰 | active へ復帰 | 合格 |
| 6 | 全チェックと振り返りを完了 | — | 実施 | 合格 |
| 7 | `steering_state.py complete` | completeへ遷移 | complete へ遷移 | 合格 |
| 8 | `--require-complete` | exit 0 | exit 0 | 合格 |

---

## Claude Code

| 項目 | 内容 |
|---|---|
| バージョン | 2.1.251 |
| 実行面 | 対話型CLI（VS Code 統合ターミナル） |
| 設定・承認ポリシー | `.claude/settings.json`（本移行で導入した正典版。`defaultMode` なし、allowは読み取り・検証系のみ）。再実施時は `--permission-mode manual` で起動 |

| # | 操作 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|---|
| 1 | 文脈・スキル認識 | `AGENTS.md` / `CLAUDE.md` / 主要スキルが表示され、subagentを実起動できる | 期待どおり | 合格 |
| 2 | 読み取り専用指示 | fixture tasklistを読み、状態・先頭の未完了タスク・再開位置候補だけを回答し、fixtureを変更しない | 期待どおり（変更なし） | 合格 |
| 3 | 承認UI | allowlist内(read / `uv run pytest`)はプロンプトなし、allowlist外のshell(`uv run python3 scripts/steering_lint.py`)とwriteはプロンプトあり | 既定権限モードでの再実施により期待どおり | 合格 |
| 4 | 未完了active応答の終了非ブロック | 未完了タスクを残したまま応答が正常終了する | 期待どおり。Stopフックの登録は `.claude/` 全体に存在しない | 合格 |
| 5 | pause / resume / complete状態遷移 | 上記「共通の状態・lint確認」3・5・7と一致 | 一致 | 合格 |
| 6 | 通常lint / 完了lint | 上記「共通の状態・lint確認」1・2・4・8と一致 | 一致 | 合格 |
| 7 | PostToolUseリマインドの非強制性 | 実装編集後に発火するが応答をブロックしない | Writeで実発火し `.claude/hooks/state/edit_count.json` に `{"count": 1}` を記録。応答をブロックせず出力への差し込みもなし。同ディレクトリは `.gitignore` 除外済みで作業ツリーは汚れず | 合格 |

**総合判定: 合格**

差異・保留・対象外理由:

- 初回の確認セッションは auto mode で実施したため、`settings.json` が宣言する「読み取り・検証系のみ自動、書き込み系は都度確認」の境界が権限モードに上書きされ、#3 の観察が成立しなかった。`--permission-mode manual` で再実施し、期待どおりの挙動を確認した。初回結果は証拠として採用しない。

---

## Codex

| 項目 | 内容 |
|---|---|
| バージョン | codex-cli 0.145.0 |
| 実行面 | 対話型CLI（VS Code 統合ターミナル） |
| 設定・承認ポリシー | `--sandbox read-only`。フォルダ信頼は二値のため付与して実施 |

| # | 操作 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|---|
| 1 | 文脈・スキル認識 | `AGENTS.md` / `.agents/skills/` / agents が表示される | スキル一覧の表示を確認 | 合格 |
| 2 | 読み取り専用指示 | fixture tasklistを読み、3点だけ回答し変更しない | 期待どおり。ハッシュ一致で無変更を確認 | 合格 |
| 3 | 承認UI | readは通過、境界外の書き込みは昇格または拒否 | `read-only` sandbox 下で `AGENTS.md` の読み取りは承認なしで通過。ファイル書き込みは承認プロンプトが発生（拒否して終了） | 合格 |
| 4 | 未完了active応答の終了非ブロック | 未完了を残したまま正常終了する | 期待どおり | 合格 |
| 5 | pause / resume / complete状態遷移 | 「共通の状態・lint確認」3・5・7と一致 | 一致 | 合格 |
| 6 | 通常lint / 完了lint | 「共通の状態・lint確認」1・2・4・8と一致 | `uv run python3 scripts/steering_lint.py` が exit 0（共通確認1と一致） | 合格 |
| 7 | Stop hook不在 | hook trust確認・feedbackが発生しない | `.codex/hooks.json` は存在せず、hook trust確認・feedbackとも発生なし | 合格 |

**総合判定: 合格**

差異・保留・対象外理由:

- **能力差（Claude Code との非対称）**: Codex のフォルダ信頼は二値で、信頼しない場合は起動せず終了する。承認ポリシーも `on-request` / `never` のみでモデル裁量となる。したがって Claude Code の「allowlist 外コマンドを都度確認」に対応する観察は Codex では成立しない。**代替した決定論的ゲートは sandbox** であり、`read-only` 下で read 通過・write 昇格を確認した。
- **無効化した初回観察**: 初回セッションはプロジェクト信頼（`~/.codex/config.toml` の `[projects."/private/tmp/g3-dev-tasks2-py-v1-6-1"] trust_level = "trusted"`）が有効で、承認境界が観察できなかった。当該エントリを削除して再実施した。初回結果は証拠として採用しない。
- **エージェント自己申告の不採用**: 初回セッションで Codex は「事前承認済みのコマンド接頭辞に登録されていた」と説明したが、`config.toml` に該当する接頭辞リストは存在せず事実ではなかった。実際の原因はプロジェクト信頼である。自己申告を受け入れ証拠にしない原則どおりに扱った。

---

## Kiro

| 項目 | 内容 |
|---|---|
| バージョン | kiro-cli 2.20.1 |
| 実行面 | 対話型CLI（`kiro-cli --agent sdd`） |
| 設定・承認ポリシー | `.kiro/agents/sdd.json`（`tools`: read / write / shell / subagent、`allowedTools`: read のみ） |

事前検証: `kiro-cli agent validate --path .kiro/agents/sdd.json` が成功（出力なし・exit 0）。

| # | 操作 | 期待結果 | 実結果 | 判定 |
|---|---|---|---|---|
| 1 | 文脈・スキル認識 | `/context` に `AGENTS.md` とskillsが重複せず表示される | 重複なく表示 | 合格 |
| 2 | 読み取り専用指示 | fixture tasklistを読み、3点だけ回答し変更しない | 期待どおり。ハッシュ一致で無変更を確認 | 合格 |
| 3 | 承認UI | readは事前許可、write / shellは承認UI | `allowedTools` のとおり read は承認なし、shell と write は承認プロンプトあり | 合格 |
| 4 | 未完了active応答の終了非ブロック | 未完了を残したまま正常終了する | 期待どおり。`welcomeMessage` の「tasklist完了まで継続」にかかわらず自動継続なし | 合格 |
| 5 | pause / resume / complete状態遷移 | 「共通の状態・lint確認」3・5・7と一致 | 一致 | 合格 |
| 6 | 通常lint / 完了lint | 「共通の状態・lint確認」1・2・4・8と一致 | 一致 | 合格 |
| 7 | Stop hook不在 | 自動継続・block decisionが発生しない | `.kiro/agents/sdd.json` に stop hook のキーなし。自動継続・block decision とも発生なし | 合格 |

**総合判定: 合格（Kiro CLI 面）**

差異・保留・対象外理由:

- **Kiro IDE 面は対象外**: Kiro IDE 本体が本マシンに未導入（`kiro` コマンドが存在しない）。手順書は Kiro IDE と Kiro CLI を別の実行面として定義しており、CLI 面の合格で IDE 面を代替しない。
  - 再確認条件: Kiro IDE を導入した環境で、Agent Steering & Skills パネルの表示・steeringスキルの実読込・read / write / shell の承認UIを確認する
  - 代替経路: Kiro CLI 面での同等項目の合格と、`tests/adapters/test_kiro_adapter.py` による構造の決定論的検証

---

## 監査メモ

- headless誤起動: **なし**（`claude -p` / `codex exec` 等は全ハーネスで不使用）
- 意図しないファイル変更: **なし**。全セッション終了後に clone を検査し、作業ツリーの未追跡は確認fixtureのみ、fixture の `tasklist.md` はハッシュ `2c71042db54d79982954f9e905ad7c348ea164ba` で無変更、HEAD は固定commit `5f41e7b` のまま
- 承認確認用に作成を試みたファイル（`tmp-write-check-codex.txt` / `tmp-write-check-kiro.txt` / `/private/tmp/g3-outside-check.txt`）はいずれも残存なし
- `.claude/hooks/state/edit_count.json` は PostToolUse の発火痕跡として生成されたが `.gitignore` 除外済みで作業ツリーを汚していない
- 後片付け結果: 使い捨て clone `/private/tmp/g3-dev-tasks2-py-v1-6-1` と確認fixtureは記録転記後に破棄する
- 環境側設定の変更: `~/.codex/config.toml` から本clone のプロジェクト信頼エントリを削除した（バックアップ `~/.codex/config.toml.bak-g3-20260829082216`）。他17件のエントリは無変更

## 手順書への還流候補

本受け入れで、`docs/procedures/harness-acceptance.md` の実施条件に**各ハーネスの権限モード・プロジェクト信頼を中立化する手順が無い**ことが判明した。実際に2回、観察が無効化された。

- Claude Code: auto mode が `settings.json` の宣言する境界を上書きした
- Codex: `~/.codex/config.toml` のプロジェクト信頼が `--ask-for-approval` を上書きした。加えて `/private/tmp` 配下の過去G3 clone の信頼が18件蓄積しており、受け入れを繰り返すほど承認境界が観察できなくなる構造になっている

platform-harness へ還流し、実施条件に「権限モードの中立化」と「実施後の信頼エントリ掃除」を追加することを提案する。

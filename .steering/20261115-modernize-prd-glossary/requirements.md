# 要求内容

## 概要

`docs/product-requirements.md`(PRD)と `docs/glossary.md` に残る TypeScript 版時代の記述(`~/.task/`・`*.json`・`task <cmd>`・Node.js / npm / Commander / Vitest・`src/*.ts`)を、Python 版の実態に現行化する。PRD の Git・GitHub 連携(P1)は**要求として残す**(ユーザー決定)。実装が無いことを明示し、実装状況を各機能に書く。#43(`functional-design.md`)と同じく、実装を正とする。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/57
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用
  - 基準3を満たさないため通常パス(下の「パス判定」を参照)

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [x] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。文書の現行化と、既存流儀(`tests/procedures/`)の検査テストのみ
- 基準2: 満たす。`docs/product-requirements.md` と `docs/glossary.md` の2ファイル(テスト除く)
- 基準3: 満たさない。変更の実体が永続ドキュメントそのもので、記録例外に該当しない
- 基準4: 満たす。コード・データ形式・API は変えない

**G3受け入れ**: 不要(アダプタ構成・権限・フックは変更しない)。リリース: 純ドキュメントのため不要。

## 背景

#43 で `functional-design.md` を直した際、同じ陳腐化が PRD と glossary に残ると分かった(Issue #57)。PRD は add-feature の軽量パス基準3の判定対象で、乖離していると変更が文書に影響するかを判断できない。

## ユースケースの軸

別セッションのエージェントや新しい開発者が PRD と glossary を読んだとき、実在するコマンド・保存先・クラス・ファイルパスだけを頼りにでき、「要求としてあるが未実装」のものは未実装と分かる。

## 実装対象

### 1. product-requirements.md
- コマンド名 `task <cmd>` → `task-py <cmd>`、保存先 `~/.task/*.json` → `~/.task-py/*.yaml`、フィールド名を実装の snake_case に、サンプルを YAML に
- Git・GitHub 連携(機能9・10・11)は**要求として残す**。見出しに【未実装】を付け、実装状況の行と、設計が `functional-design.md` の「未実装の設計」節にある旨を足す。関連する受け入れ条件・ワークフロー・CLI 例・非機能要件・リリース計画の行も同様に印を付ける
- 実装済みの要求にも、実装との差があれば注記する(例: `list --status`・`--priority`・`--sort`、期限切れの赤色表示、`list` の列は CLI に無い)
- 配布・実行環境(npm・Node.js)を Python 版の実態に直す
- 実装済みの項目(ローカル Web GUI・MCP・ルーティーン・解禁日・タイマー等)で、PRD に無いものは、現状を壊さない範囲で足す

### 2. glossary.md
- 用語の定義・パス・クラス名を Python 版に直す(`src/task_cli/...`)。`GlobalConfigService`・`TaskManager`・`GlobalConfigStorage`・`Task`・`GlobalConfig`・`AppError`・`Renderer`・レイヤー図など
- TypeScript 版固有の技術用語(Commander.js・Vitest・husky・lint-staged・inquirer・simple-git)は、Python 版の対応物(typer・pytest・ruff / basedpyright・typer.confirm / prompt-toolkit)に置き換えるか、実在しないものは削除する。索引も合わせる
- Git・GitHub 連携の用語(ブランチスラッグ・作業中タスク・コミット自動タグ付け・同期・インポート・GitService・GitHubService・ConfigService・ConfigStorage・ProjectConfig・PAT・PR)は残し、「未実装(要求のみ)」と明記して実装の参照を設計書の節へ向ける
- 実在しない `IStorage` の扱いは実コードを確認して決める

### 3. 検査テスト(`tests/procedures/test_prd_glossary_currency.py`、新規)
- 旧保存先・旧ファイル名・TypeScript 版の語・`.ts` パスが無い
- `task <cmd>` 形式(実在は `task-py`)が無い
- `src/`・`tests/` のパスが実在する
- `task-py <コマンド>` は実在するか、【未実装】の節にある

## 受け入れ条件

- [ ] 2文書から TypeScript 版時代の語・旧パス・旧ファイル名・`task <cmd>` が消えている(Web GUI の JSON API 等の正当な `.json` を除く)
- [ ] Git・GitHub 連携の要求が PRD に残り、【未実装】と実装状況が明記されている
- [ ] glossary の Git・GitHub 連携の用語に、未実装の明記がある
- [ ] 文書内のリンク(アンカー)が切れていない
- [ ] 検査テストが追加され、変更前の文書で失敗し、変更後に通る
- [ ] 全テスト・lint・型検査・品質ゲートが通る

## スコープ外

- Git・GitHub 連携の実装(別作業)
- PRD の要求の追加・削除・優先度の変更(要求の内容は変えない。変えるのは表記と実装状況の注記)
- KPI の目標値の変更(計測手段の表記のみ直す)
- 他のドキュメント

## 参照ドキュメント

- `docs/functional-design.md`(現行化済み。実装との対応の正)
- `docs/architecture.md`、`docs/repository-structure.md`

# 要求内容

## 概要

`docs/functional-design.md` に広範に残っている TypeScript 版時代の記述を、Python 版の実装を正として現行化する(Issue #43)。あわせて、Python 版に実装のない Git・GitHub 連携(P1)の設計を、実装済みの記述から切り離して「未実装の設計」節にまとめる。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/43
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用
  - 基準3(対象文書の更新が不要)を満たさないため、通常パスとする

## パス判定

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [x] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書(`AGENTS.md` とハーネスアダプタの規範記述・AGENTS.md プロダクト固有層が列挙する永続ドキュメント・`docs/procedures/` の手順書とテンプレート)の更新が不要
  - **記録例外**: 該当しない(下の判定理由を参照)
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。新規ライブラリ・レイヤーは導入しない。文書の現行化と、既存の `tests/procedures/` 流儀の文書検査テスト1本の追加のみ
- 基準2: 満たす。変更対象は `docs/functional-design.md` の1ファイル(テストを除く)
- 基準3: 満たさない。`docs/functional-design.md` は AGENTS.md プロダクト固有層が列挙する永続ドキュメントの1つで、**変更の実体が対象文書そのもの**である。記録例外(変更の実体が文書の外にあり、文書の更新が一覧・台帳の項目更新にとどまる)に該当しない
- 基準4: 満たす。コード・データ形式・API契約は変えない。文書を実装に合わせるだけである

## 背景

`docs/functional-design.md` は元々 TypeScript 版(`~/.task/`・JSON・Commander.js)の設計書で、Python 版へ移行した後も記述が残った。Issue の計測(2026-09-06 時点、当時 946 行)では次のとおり実態と食い違う。その後 v1.2〜v1.5 の節が足されて現在 1084 行になっている(これらの節は Python 版の記述で、現行である)。

| 残っているもの | 実態 |
|---|---|
| ` ```typescript ` コードブロック | Python |
| `src/services/*.ts` / `src/storage/*.ts` / `src/cli/*.ts` の実装パス参照 | `src/task_cli/**/*.py` |
| 旧ストレージパス `~/.task/` | `~/.task-py/` |
| `tasks.json` / `config.json` 等 | `tasks.yaml` / `config.yaml` 等 |
| コマンド名 `task ...` | `task-py ...` |
| `Array.prototype.filter` / `AbortController` / `Commander.js` / `Vitest` / `npm` | Python 版に存在しない |
| `TaskManager` / `GlobalConfigService` / `FileStorage` / `Renderer` の TypeScript 型シグネチャ | Python のクラス・関数。さらに `TaskCrudUseCase` / `ProjectService` / `DailyService` / `TimerService` が文書に無い |

この文書は add-feature 手順の軽量パス基準3の判定対象であり、記述が実態と乖離するとパス判定が不定になる。また別セッションのエージェントが、存在しないファイルパスを頼りに探しに行く。

## ユースケースの軸

> この文書を読んだ人(および別セッションのエージェント)が、存在するファイル・コマンド・保存先・型だけを頼りに実装へ辿り着ける。実装されていない機能は、実装済みの機能と取り違えられない。

## 実装対象の機能

### 1. 実装済みの記述の現行化
- データモデル: pydantic のモデル(snake_case のフィールド名)とYAML のファイル構造・例(`~/.task-py/` 配下)
- コンポーネント設計: Python の実在するクラス・関数のパスと責務。文書に無かった `TaskCrudUseCase` / `ProjectService` / `DailyService` / `TimerService` を加える
- コマンド一覧: 実在するコマンド名(`task-py`)とオプションに合わせる(`overview`・`schedule`・`search`・`migrate`・`reset`・`shell`・`web` を含む)。実在しないオプション(`list --priority` / `--sort`)は載せない
- ユースケース図・UI 表示・エラー・パフォーマンス・セキュリティ・テスト戦略を実装に合わせる
- システム構成図を CLI / MCP / Web の3入口 → ユースケース → サービス → ストレージ(YAML)にする

### 2. 実装されていない設計の切り離し
- Git ブランチ連携・コミットフック・GitHub Issues 同期・PR 作成・プロジェクト別設定(`ProjectConfig`)は、Python 版に実装がない(`src/` に `git` / `github` / `sync` の処理は無く、`Task.branch` は移行データの表示用フィールドとして残るだけ)
- 設計の意図(ブランチ命名規則・フック仕様・PR 本文・設定値の検証表・安全上の考慮)は消さず、末尾の「未実装の設計(Git・GitHub 連携 P1)」節に集める。TypeScript のコードブロックと実装パスは持ち込まず、表と文章で言語に依存しない形にする
- 実装済みの記述の側からは、未実装の機能を指す文言(列・エラー表・フロー・「P1」注記)を取り除く

### 3. 再発防止の検査
- `tests/procedures/` に、functional-design.md が TypeScript 版時代の記述を再び持たないことを検査するテストを1本足す(禁止パターンの不在と、文書内の `src/...` パスの実在)

## 受け入れ条件

### 現行化
- [ ] ` ```typescript ` のコードブロックが0件
- [ ] `src/**/*.ts` / `src/services/` / `src/storage/` / `src/cli/*.ts` 形式の実装パス参照が0件
- [ ] 旧ストレージパス `~/.task/` は、`migrate` の説明(移行元)以外に出てこない
- [ ] `tasks.json` / `config.json` 等の永続ファイル名が出てこない(Web の JSON API の説明を除く)
- [ ] `Commander.js` / `Vitest` / `npm` / `Array.prototype` / `AbortController` / `simple-git` / `node-fetch` が実装済みの記述に出てこない
- [ ] 文書内に書かれた `src/...` のファイルパスがすべて実在する
- [ ] コマンド一覧が `task-py --help` と一致する(実在するコマンドを欠かさず、実在しないコマンド・オプションを載せない)

### 未実装の設計
- [ ] Git・GitHub 連携の設計が1つの節にまとまり、冒頭で「Python 版には未実装」と明記されている
- [ ] 実装済みの節(コマンド一覧・UI・エラー表・セキュリティ)に、未実装の機能への言及が残っていない(未実装の節への1行の参照を除く)
- [ ] 元の設計の情報(ブランチ命名規則・スラッグ変換例・コミットフック仕様・PR 本文・設定値の検証表・同期の挙動)が失われていない

### 検査
- [ ] 新テストが、修正前の文書で失敗し、修正後に通る
- [ ] ローカル品質ゲートが全緑

## 成功指標

- Issue #43 を Close できる
- 以後 functional-design.md に TypeScript 版時代の記述やファイルパスの陳腐化が入ると、ローカル品質ゲートで落ちる

## スコープ外

以下はこのフェーズでは実装しません:

- `docs/product-requirements.md` / `docs/architecture.md` / `docs/glossary.md` 等、他の永続ドキュメントの陳腐化の解消(PRD にも Git・GitHub 連携の記述と `~/.task/` が残っている。別 Issue として振り返りに記録する)
- Git・GitHub 連携の実装、または廃止の決定(本作業は「実装されていない」ことを正しく書くだけで、方針は変えない)
- `task-py web --help` の説明文「(読み取り専用)」の修正(コードの文字列。v1.5 で書き込みが入った後も更新されていない)
- ローカル Web GUI 節(v1.4・v1.5)の書き換え(すでに現行の記述)

## 参照ドキュメント

- `docs/product-requirements.md` - プロダクト要求定義書
- `docs/functional-design.md` - 機能設計書(本作業の対象)
- `docs/architecture.md` - アーキテクチャ設計書
- `docs/repository-structure.md` - リポジトリ構造定義書(#40 で現行化済み。実装パスの正)

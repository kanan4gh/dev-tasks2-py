# 要求内容

## 概要

platform-harness `v1.7.0 / 5b858dcf1641bd39c9716a91b7591584ae582bef` を唯一の同期元として、`v1.6.1..v1.7.0` の10 path を direct-sync する。派生固有差分（`LEGACY_PRE_MIGRATION` 等）は温存し、正典側の作業履歴は複製しない。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/30
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [ ] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。`docs/procedures/derived-project-rollout.md` の direct-sync 手順の踏襲であり、v1.6.1 同期と同じ形をとる。新規依存も新しい層も導入しない。
- 基準2: **満たさない**。テストを除く変更対象は6ファイル（`docs/procedures/harness-acceptance.md` / `docs/procedures/templates/harness-acceptance-record.md` / `scripts/steering_lint.py` / `scripts/steering_state.py` / `docs/ideas/` 2件）。
- 基準3: **満たさない**。`docs/procedures/` の手順書とテンプレートを変更する。記録例外は「変更の実体が対象文書の外にある」ことを要件とするが、本作業は手順書の記述そのものを正典版へ差し替えることが目的であり非該当。
- 基準4: 満たす。CLIの引数、tasklistの状態形式、エラー契約は変わらない。v1.6.2 は誤検出の解消（検査が緩む方向）、v1.7.0 は手順書への追加であり、既存の記録が無効になる変更を含まない。

基準2・3を満たさないため**通常パス（3ファイル）**とする。

## G3受け入れの要否判定

- **判定**: 不要
- **理由**: 変更対象は手順書・テンプレート・ハーネス中立スクリプト・テスト・ideas 文書である。スキル・エージェント・コマンドの定義メタデータ、権限設定、フック定義・登録、ハーネス設定ファイルはいずれも変更しない。v1.6.1 展開は migrate-then-sync でアダプタ一式を導入したためG3を実施したが、本作業は direct-sync である（判定基準は `derived-project-rollout.md` フェーズ4と同じ「アダプタ構成・権限・フックを変更したか」）。

## 背景

本リポジトリは 2026-08-29 に platform-harness v1.6.1 へ migrate-then-sync した（PR #27、マージcommit `1d6074c`、authority handoff `e5ff9f6`）。その展開作業の中で正典側の欠陥が2件見つかり、platform-harness へ環流された。

- **#55 / v1.6.2**: C4 のプレースホルダ検査が振り返り本文を生テキストのまま検査しており、コード表記中の波括弧を未置換テンプレートと誤検出する。**本リポジトリの展開中に2件発生**した。1件は移行前ステアリングの既存履歴、もう1件は同期作業そのもののステアリングを執筆中で、回避のため言い換えを強いられた
- **#54 / v1.7.0**: G3 の実施条件に権限モードを中立化する手順がなく、**本リポジトリの展開の G3 で承認境界の観察が2回、静かに無効化された**

本作業は、その2件の修正を発見元へ戻す同期である。

## 同期manifest

`v1.6.1..v1.7.0` の10 path（`.steering/` を除く）を排他的に1分類へ割り当てる。

### Preserve（canonical 10path 外）

- `AGENTS.md`、`CLAUDE.md`、`.claude/**`、`.codex/**`、`.kiro/**`、`.agents/**` — v1.7.0 で変更されておらず、本リポジトリのプロダクト固有記述を保持する
- `docs/` のうち下記 Replace / Add 以外 — 永続ドキュメントは本リポジトリを正とする
- `.gitignore`（`.steering/*` を無視しない）、`pyproject.toml`（`[tool.ruff.lint] select` 明示）、`.devcontainer/` — 派生固有差分として温存する
- `tests/lint/test_legacy_grandfather.py`、`tests/procedures/test_derived_project_rollout.py` の台帳検査除外 — 派生固有差分として温存する
- `.steering/**` — 本作業ディレクトリを除き、本リポジトリの作業履歴を保持する

### Replace from canonical（6 path）

いずれも本リポジトリ側が v1.6.1 と blob 一致であり、固有差分がないことを確認済み。

- `docs/procedures/harness-acceptance.md` — v1.7.0 blob（権限モードの中立化・後片付けの2節追加）
- `docs/procedures/templates/harness-acceptance-record.md` — v1.7.0 blob（権限モード・信頼状態の欄追加）
- `scripts/steering_state.py` — v1.7.0 blob（共有関数 `find_retrospective_placeholders` の利用）
- `tests/adapters/test_harness_acceptance.py` — v1.7.0 blob（契約テスト13件）
- `tests/lint/test_steering_lint.py` — v1.7.0 blob（C4回帰5件）
- `tests/lint/test_steering_state.py` — v1.7.0 blob（complete遷移回帰2件）

### Add from canonical（2 path）

- `docs/ideas/ai-dlc-uroboros-comparison.md`
- `docs/ideas/uroboros-lifecycle-framework-architecture.md`

本リポジトリの `docs/ideas/` は既に正典由来の3件（`harness-engineering.md` / `harness-swap.md` / `template-unification.md`）と本リポジトリ固有の `future-roadmap.md` を併せ持つ。正典由来の ideas 文書を受け取る前例があるため Add とする。

### Merge manually（1 path）

- `scripts/steering_lint.py` — 本リポジトリの `LEGACY_PRE_MIGRATION`（行52〜87のブロック）と lint ループ内の `is_legacy` 分岐を温存したまま、v1.6.2 のコード表記除外（`INLINE_CODE_PATTERN` / `strip_inline_code()` / `find_retrospective_placeholders()` / `_strip_code_fences()` 化 / `check_retrospective()` の差し替え）を取り込む。両者の変更領域は重ならないため3-wayマージで解決できる見込みである

### Exclude（1 path）

- `docs/derived-projects.md` — 派生プロジェクト展開台帳。正典側資産であり派生へ複製しない（`derived-project-rollout.md` の原則）

## ユースケースの軸

> ハーネス管理者が、本リポジトリの展開で発見された2件の正典修正を発見元へ戻し、派生固有差分を失わずに v1.7.0 へ追随できる。

## 受け入れ条件

### 同期の正確性

- [ ] Replace 6 path が v1.7.0 と blob 一致である
- [ ] Add 2 path が v1.7.0 と blob 一致で新規追加されている
- [ ] Exclude 1 path が本リポジトリに存在しない
- [ ] canonical 10 path 以外に差分がない

### 派生固有差分の温存

- [ ] `scripts/steering_lint.py` に `LEGACY_PRE_MIGRATION` の18件と `is_legacy` 分岐が残っている
- [ ] `tests/lint/test_legacy_grandfather.py` が変更されておらず、パスする
- [ ] `.gitignore` / `pyproject.toml` / `.devcontainer/` が変更されていない

### 取り込んだ修正の実効

- [ ] 振り返りにインラインコードとフェンス付きコードブロックを含んでも C4 が誤検出しない
- [ ] 閉じられていないバッククォート・フェンスでは従来どおり検出される（fail-closed）
- [ ] `docs/procedures/harness-acceptance.md` に「権限モードの中立化」「後片付け」の2節がある

## 成功指標

- 移行前ステアリング18件が引き続き lint の対象外であり、適応度計測の基礎データが改変されない
- ローカル品質ゲートが1回で全緑になる

## スコープ外

- 台帳（platform-harness `docs/derived-projects.md`）の更新。フェーズ5-5に従い、正典リポジトリ側の別PRで行う
- open issue #25 / #28 / #29 の対応。いずれも本同期と同一 path を変更しない
- `LEGACY_PRE_MIGRATION` の見直し。v1.6.2 でコード表記の誤検出が解消されるため免除対象を減らせる可能性があるが、判断には移行前18件の再検査が必要であり本作業の範囲を超える

## 参照ドキュメント

- `docs/procedures/derived-project-rollout.md` - 展開手順（フェーズ0〜5）
- `docs/procedures/harness-acceptance.md` - 本作業の Replace 対象

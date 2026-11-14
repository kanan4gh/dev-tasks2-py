# 要求内容

## 概要

(1) 壊れた保存ファイルのとき、MCP の多くのツールがエラーの原因と対処を返せない不具合を直し、shell のエラー表示も揃える(#68)。(2) glossary に、実装済みの機能の用語(ルーティーン・解禁日・MCP サーバー・概況表示)を足す(#66)。(3) 2つの現行化検査テストの共通部分を共有モジュールにまとめる(#69)。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/66 , https://github.com/kanan4gh/dev-tasks2-py/issues/68 , https://github.com/kanan4gh/dev-tasks2-py/issues/69
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用
  - 基準3を満たさないため通常パス(下の「パス判定」を参照)

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [x] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。MCP のエラー整形は、CLI の `handle_app_errors`(#59)と同じ「入口で `AppError` を3要素にする」既存パターン。テストの共有モジュールは既存テストの整理
- 基準2: 満たす。`src/task_mcp/server.py`・`src/task_cli/cli/shell.py`・`docs/glossary.md` の3ファイル(テストと `pyproject.toml` の pyright 設定を除く)
- 基準3: 満たさない。`docs/glossary.md` への用語追加が変更の実体の一つで、記録例外に該当しない
- 基準4: 満たす。正常系の応答は変えない。壊れたファイルのときの MCP の応答が、例外(`ToolError`)から整形済みのテキストに変わるのみ

**G3受け入れ**: 不要(アダプタ構成・権限・フックは変更しない)。リリース: MCP の利用者に見える修正のため PATCH(0.13.2)。

## 背景

- #68: #59 で壊れた YAML を `StorageReadError` にしたが、MCP の28ツールのうち `get_active_project`・`list_projects`・`get_overview`・`list_routines`・`get_daily_stats`・`add_routine` などは `AppError` を捕捉しておらず、FastMCP が `ToolError`(メッセージのみ)にするため、原因と対処が失われる。`shell` の `_run_command` も `エラー: {e}` とメッセージだけを出す
- #66: PRD が実装済みとして扱う語の定義が glossary に無い(#57 のレビューの指摘)
- #69: `test_functional_design_currency.py` と `test_prd_glossary_currency.py` が `cli_commands()`・禁止語・旧ファイル名・パス実在の検査を重複して持つ

## ユースケースの軸

MCP 経由(Claude との会話)でも、壊れたファイルのとき原因と対処が読める。glossary を引けば、ルーティーン・解禁日・MCP・概況表示が分かる。現行化検査を足す・直すとき、1か所を直せば足りる。

## 実装対象

### 1. MCP と shell のエラー整形(#68)
- MCP: 全ツールを、`AppError` を `エラー: / 原因: / 対処:` のテキストにして返すデコレータで包む(既存の `_fmt_error`)。壊れたファイルでの実行テストで、これまで `ToolError` になっていたツールが整形されることを確かめる
- shell: `_run_command` が `AppError` を `render_error` で整形する

### 2. glossary の用語追加(#66)
- ルーティーン・解禁日・MCP サーバー・概況表示を、実装(`models/daily.py`・`services/daily_service.py`・`models/task.py`・`services/task_manager.py`・`src/task_mcp/server.py`・`cli/commands/onboard.py`)と照合して書く。索引も足す

### 3. 検査テストの共通化(#69)
- `tests/procedures/_doc_currency.py` に、`cli_commands()`・TypeScript 版の共通の禁止語・旧ファイル名・`~/.task/` の検査・`src/` `tests/` パスの実在検査を移し、2つのテストから使う。文書ごとの違い(`npm` は `functional-design.md` の Web GUI 節に正当な言及がある)は各テストの追加項目として残す。検査の強さは変えない

## 受け入れ条件

- [ ] 壊れた `config.yaml` / `tasks.yaml` / `routines.yaml` / `log.yaml` で、MCP の全ツール(引数なしで呼べるもの・id を取るもの)が例外にならず、`エラー` / `原因` / `対処` を含むテキストを返す(変更前は `ToolError` になるツールがあり、テストが失敗する)
- [ ] shell が `AppError` を `[Error]` / 原因 / 対処で出す
- [ ] glossary に4用語が追加され、索引に載り、リンク検査が通る
- [ ] 2つの現行化テストが共有モジュールを使い、検査の強さが変わらない(同じ誤りを入れると落ちる)
- [ ] 全テスト・lint・型検査・品質ゲートが通る

## 成功指標

- 既存テストの全通過に加え、MCP と shell の壊れたファイルのテストが足される

## スコープ外

- MCP ツール内の既存の `try/except AppError` の削除(デコレータと重複するが、挙動は同じで、整理は別作業)
- 検査テストの対象文書の追加(`architecture.md` など)
- 時計の注入など、テストの設計の変更

## 参照ドキュメント

- `docs/glossary.md`、`docs/functional-design.md`

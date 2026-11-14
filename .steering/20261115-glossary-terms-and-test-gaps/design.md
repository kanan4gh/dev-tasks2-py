# 設計書

## 方針

(1) 入口で `AppError` を3要素にする既存の方針を MCP と shell にも適用する。(2) 実装を読んで用語を書く。(3) テストの共通部品を1か所にまとめ、検査の強さは変えない。

## コンポーネント設計

### 1. MCP(`src/task_mcp/server.py`)

- `_app_errors_as_text(fn)`: `functools.wraps` で `AppError` を `_fmt_error(e)` のテキストにして返すデコレータ
- 全ツールで `@mcp.tool()` / `@track` の内側に適用する(`@mcp.tool() @track @_app_errors_as_text`)。`track` は結果を記録するだけで、変換後の戻り値を受け取る。既存ツールの `try/except AppError` は挙動が同じなので残す
- 28個あるツールの宣言を機械的に直すので、置き換え後に、全ツールが包まれていることを検査するテスト(登録されたツールの関数が `_app_errors_as_text` の `__wrapped__` 連鎖に含まれる)を足す

### 2. shell(`src/task_cli/cli/shell.py`)

- `_run_command` に `except AppError as e: render_error(e)` を、`except Exception` の前に足す

### 3. glossary(`docs/glossary.md`)

- ドメイン用語に「ルーティーン (Routine)」「解禁日 (Scheduled Date)」「概況表示 (Overview)」、アーキテクチャ用語に「MCP サーバー」を足す。索引は五十音/A-Z の該当位置へ

### 4. 検査テストの共通化

- `tests/procedures/_doc_currency.py`: `ROOT` / `DOCS`、`cli_commands()`、`COMMON_TYPESCRIPT_TERMS`、`OLD_FILE_NAMES`、旧保存先の検査、`src/` `tests/` パスの実在検査
- 2つのテストは、共通部品を使い、文書固有の項目(`functional-design.md` の `Array.prototype` など、PRD の `npm ` など)だけを自分で持つ
- pytest は `tests/procedures`(`__init__.py` 無し)をインポートパスに足すので `from _doc_currency import ...` で動く。pyright は `pyproject.toml` の `extraPaths` に `tests/procedures` を足して解決する

## テスト戦略

- `tests/test_mcp_server.py` に、壊れたファイルでの実行テスト(パラメータ化)と、全ツールが包まれていることの検査を足す
- `tests/test_shell.py` に、`_run_command` が `AppError` を整形するテスト(`task_cli.cli.main.app` を、`AppError` を投げるコマンドだけの小さな typer に差し替える)と、壊れた設定ファイルでトレースバックが出ない統合テスト
- 共通化の前後で、わざと誤りを入れた文書を2つのテストに通し、検出されることを確認する(検査の強さが変わっていない確認)

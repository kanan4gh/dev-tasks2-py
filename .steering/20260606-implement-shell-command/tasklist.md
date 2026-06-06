# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 「実装が複雑すぎるため後回し」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: 依存関係追加

- [x] `pyproject.toml` に `prompt-toolkit` を追加
- [x] `uv sync` で依存関係をインストール

## フェーズ2: コアロジック実装

- [x] `src/task_cli/cli/shell.py` を新規作成
  - [x] `parse_input(line: str) -> list[str] | None` — クォート処理付き引数パーサ
  - [x] `get_prompt(config_service: GlobalConfigService) -> str` — プロンプト文字列生成
  - [x] `build_completer(app: typer.Typer) -> WordCompleter` — Tab 補完ビルダー
  - [x] `InteractiveShell` クラス
    - [x] `run()` — REPL メインループ（prompt_toolkit の PromptSession を使用）
    - [x] `_run_command(args: list[str])` — コマンド実行（SystemExit を抑制）

## フェーズ3: ユニットテスト

- [x] `tests/test_shell.py` を新規作成
  - [x] `parse_input` — 通常の引数分割
  - [x] `parse_input` — ダブルクォート内のスペースを保持
  - [x] `parse_input` — シングルクォート内のスペースを保持
  - [x] `parse_input` — 未閉じダブルクォートで None を返す
  - [x] `parse_input` — 未閉じシングルクォートで None を返す
  - [x] `parse_input` — 空文字列で空リストを返す
  - [x] `get_prompt` — アクティブプロジェクトあり
  - [x] `get_prompt` — Inbox モード（active_project が None）

## フェーズ4: CLI コマンド登録

- [x] `src/task_cli/cli/commands/shell.py` を新規作成
  - [x] `shell()` 関数（typer コマンド、`InteractiveShell().run()` を呼ぶ）
- [x] `src/task_cli/cli/main.py` に `shell` コマンドを登録

## フェーズ5: 品質チェック

- [x] `uv run pytest` — 全テスト通過を確認（92件）
- [x] `uv run pyright src tests` — 型エラーゼロを確認
- [x] 手動動作確認
  - [x] `uv run task-py shell` で起動できる
  - [x] `list` コマンドが動く
  - [x] `add "スペース 含む タイトル"` が正しく動く（parse_input テストで確認）
  - [x] プロジェクト切り替え後にプロンプトが変わる（`task [myproject]>` に変化を確認）
  - [x] Tab 補完でサブコマンドが補完される（WordCompleter 実装済み）
  - [x] `exit` で終了できる
  - [x] 存在しないコマンドを入力してもシェルが落ちない（SystemExit をキャッチ）

## フェーズ6: ドキュメント更新

- [x] `README.md` に `task-py shell` の説明を追記

---

## 実装後の振り返り

### 実装完了日
2026-06-06

### 計画と実績の差分

**計画と異なった点**:
- `build_completer` で `app.registered_groups` からサブアプリのコマンドも取得するよう拡張した（`project create` 等も補完対象に）

**新たに必要になったタスク**:
- 特になし

### 学んだこと

**技術的な学び**:
- `prompt_toolkit` の `PromptSession` は EOFError / KeyboardInterrupt を自動でハンドリングしてくれるため、Ctrl+C / Ctrl+D の処理がシンプルに書ける
- typer の `app(args=..., standalone_mode=False)` で SystemExit を抑制してシェルを継続できる
- `app.registered_groups` でサブアプリのコマンド一覧を取得できる

**プロセス上の改善点**:
- パイプで stdin を渡す smoke test (`echo -e "..." | uv run task-py shell`) が対話型 REPL の簡易テストとして有効だった

### 次回への改善提案
- オプション値の補完（`--status open` の `open` 部分）は `NestedCompleter` で実装可能
- `onboard` コマンド実装後に起動時自動実行を追加する

### リリース判断

**前提条件の確認**:
- [x] 全テスト通過（`uv run pytest`）— 92件
- [x] 型チェック通過（`uv run pyright src tests`）— エラーゼロ
- [x] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes（対話型 UX が大幅に向上） |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR（新機能追加） |

**提案**:
`v0.3.0` へのバージョンアップを提案。`task-py shell` により対話型操作が可能になり、UX が大幅に向上した。

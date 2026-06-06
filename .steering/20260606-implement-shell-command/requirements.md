# 要求内容

## 概要

TypeScript 版の `task shell` コマンドを Python 版に移植する。
`task-py shell` を起動すると、`task-py` プレフィックスなしでサブコマンドを連続実行できる REPL 環境を提供する。

## 背景

TypeScript 版には `task shell` が実装されており、対話的にタスク操作できる。
Python 版でも同等の UX を提供することで、実用性を高める。

## 関連 Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/7

## 実装対象の機能

### 1. `task-py shell` コマンド

- `task-py shell` でインタラクティブシェルを起動
- プロンプト: `task [myapp]>` — アクティブプロジェクトをリアルタイム表示（Inbox モードは `task [inbox]>`）
- コマンドを入力すると `task-py` コマンドと同じ結果が得られる（例: `list` → `task-py list` と同等）
- `exit` / `quit` または Ctrl+C / Ctrl+D で終了

### 2. Tab 補完

- サブコマンド名の補完（`li` → `list`）
- オプションフラグの補完（`list -` → `--status`, `--all-status`, `--all`）

### 3. クォート処理

- ダブルクォート・シングルクォートで囲んだスペース含む文字列を正しく解析
- 例: `add "ユーザー認証 機能"` → タイトルにスペースが含まれる

### 4. エラー処理

- コマンドエラーが発生してもシェルが終了しない
- エラーメッセージを表示してプロンプトに戻る

## 受け入れ条件

- [ ] `task-py shell` で起動できる
- [ ] `list` / `add "タスク名"` / `start 1` など全コマンドが動く
- [ ] プロンプトにアクティブプロジェクト名が表示される
- [ ] `project use myapp` 後にプロンプトが `task [myapp]>` に変わる
- [ ] Tab 補完でサブコマンド名が補完される
- [ ] `exit` / `quit` / Ctrl+D で正常終了する
- [ ] 存在しないコマンドを入力してもシェルが落ちない
- [ ] pytest 全通過・pyright エラーゼロ

## スコープ外

以下はこのフェーズでは実装しません:

- 起動時の `onboard` 自動実行（`onboard` コマンド自体が未実装）
- 入力履歴の永続化（セッション内履歴は prompt_toolkit が自動提供）
- オプション値の補完（`--status open` の `open` 部分など）

## 参照ドキュメント

- `docs/functional-design.md` - 機能設計書
- `docs/architecture.md` - アーキテクチャ設計書
- TypeScript 版: `src/cli/shell/InteractiveShell.ts`（参照済み）

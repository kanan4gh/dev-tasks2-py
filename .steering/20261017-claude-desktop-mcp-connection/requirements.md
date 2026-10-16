# 要求内容

## 概要

Claude Desktop から `task-mcp` を起動すると、互換性のない MCP Python SDK 2.x が読み込まれて接続が切断される問題を修正する。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/52
- **使用ハーネス**: Codex
- **軽量パス**: 適用

## パス判定

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [x] 2. 変更対象が3ファイル以下(テスト除く)
- [x] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。既存の MCP SDK 1.x API を維持し、対応する依存バージョン範囲をパッケージメタデータに明示するだけで、新規依存・新規レイヤー・新規抽象化を導入しない。
- 基準2: 満たす。テストを除く変更対象は `pyproject.toml`、`uv.lock`、`docs/architecture.md` の3ファイル。
- 基準3: 満たす（記録例外を適用）。変更の実体は `pyproject.toml` の依存契約と `uv.lock` にあり、永続ドキュメント `docs/architecture.md` の既存ライブラリ一覧にある `mcp[cli]` のバージョン値を対応範囲へ更新し、その理由を記録するだけである。方針・分類・手順は変更しない。
- 基準4: 満たす。MCPツール名・入力スキーマ・stdioプロトコル・保存データ形式を変更せず、動作していた1.x APIへ解決を限定する互換修正である。

4項目すべてを満たすため、軽量パスを適用する。

## G3受け入れ判定

- **判定**: 不要
- **理由**: ハーネスのアダプタ構成・権限・フック・設定ファイルは変更しない。Claude Desktop の既存MCP登録内容も変更せず、アプリケーションパッケージの依存契約だけを修正する。

## 背景

Claude Desktop の設定は `task-py` サーバーを `task-mcp` コマンドで起動している。インストール済み `dev-tasks2-py 0.12.0` には上限のない `mcp[cli]` 依存があり、2026-10-17時点では `mcp 2.2.0` が解決される。`task_mcp.server` は MCP SDK 1.x の `mcp.server.fastmcp.FastMCP` を使用しているため、起動時に `ModuleNotFoundError` となり、Claude Desktop 側では `Connection closed` と表示される。

リポジトリの `uv.lock` は偶然 `mcp 1.27.2` を保持しているので開発環境のテストは通るが、`uv tool install` は配布メタデータから解決し直すため障害を再現する。したがってロックファイルだけでなく、配布される依存契約そのものに上限を持たせる必要がある。

## ユースケースの軸

TaskCLI利用者がClaude Desktopから`task-py` MCPサーバーへ接続し、既存のタスク管理ツールをエラーなく利用できる。

## 実装対象の機能

### 1. MCP SDKの互換バージョン制約

- `pyproject.toml` の依存を MCP SDK 1.x に限定する。
- パッチリリースとしてプロジェクトバージョンを更新する。
- `uv.lock` とアーキテクチャの依存一覧を契約に追随させる。

### 2. 再発防止と実接続確認

- 配布メタデータから MCP SDK 2.x が解決可能な状態へ戻らないことをテストする。
- 修正版を隔離されたツール環境へインストールし、stdio初期化とツール一覧取得を確認する。
- 現在のローカルツールを修正版へ更新し、Claude Desktopの既存設定で接続できることを確認する。

## 受け入れ条件

### 依存契約

- [x] 配布メタデータが `mcp[cli]>=1,<2` を要求する。
- [x] 新規解決したツール環境に MCP SDK 1.x が入り、2.x が入らない。
- [x] プロジェクトバージョンがパッチ更新される。

### MCP接続

- [x] インストールされた `task-mcp` がimportエラーで終了しない。
- [x] stdio経由で初期化でき、既存MCPツール一覧を取得できる。
- [x] Claude Desktopの既存 `task-py` 登録で接続エラーが解消する。

### 品質

- [x] 依存制約の回帰テストを含む全テストが通る。
- [x] ruffとbasedpyrightが通る。

## 成功指標

- Claude Desktopログに `mcp.server.fastmcp` の `ModuleNotFoundError` が新規発生しない。
- `task-mcp` の初期化とツール一覧取得が成功する。

## スコープ外

- MCP Python SDK 2.x APIへの移行。
- MCPツールの追加・削除・スキーマ変更。
- Claude DesktopのMCP登録方式の変更。

## 参照ドキュメント

- `docs/architecture.md` - MCP SDKとstdio入口の技術仕様
- `docs/repository-structure.md` - `task_mcp` の責務と配置
- `docs/development-guidelines.md` - 依存・テスト・README更新の判断基準
- `README.md` - 利用者向けインストールとClaude Desktop登録方法

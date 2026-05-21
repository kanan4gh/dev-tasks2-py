# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

---

## フェーズ1: リポジトリ作成・プロジェクト初期化

- [x] GitHubリポジトリ `dev-tasks2-py` を作成（既存・空）
- [x] ローカルにクローン
- [x] uv でプロジェクト初期化（`uv init`）
- [x] ディレクトリ構造を作成（src/task_cli/ 以下）
- [x] pyproject.toml に依存関係を設定
- [x] 依存関係をインストール（`uv sync`）
- [x] CLIエントリーポイントを設定（`task` コマンドで起動できる状態）
- [x] `uv run task --help` が動くことを確認
- [x] CLAUDE.md を作成（現行dev-tasks2のものをコピーし、技術依存部分をPython/uv向けに書き換え）

## フェーズ2: データモデル定義

- [x] `models/task.py` を実装
  - [x] `TaskStatus` enum（open / in_progress / completed / archived）
  - [x] `Priority` enum（high / medium / low）
  - [x] `Task` モデル（id, title, status, priority, created_at 等）
  - [x] `GlobalConfig` モデル（active_project 等）
- [x] `tests/test_models.py` を実装（20件全通過）

## フェーズ3: ストレージ層

- [x] `storage/file_storage.py` を実装
  - [x] タスクの読み込み（`~/.task/projects/<name>/tasks.yaml`）
  - [x] タスクの書き込み（バックアップ・リストア付き）
- [x] `storage/global_config_storage.py` を実装
  - [x] グローバル設定の読み込み（`~/.task/config.yaml`）
  - [x] グローバル設定の書き込み
- [x] `tests/test_storage.py` を実装（13件全通過）

## フェーズ4: サービス・ユースケース層

- [x] `services/global_config_service.py` を実装
  - [x] アクティブプロジェクトの取得・設定
- [x] `services/task_manager.py` を実装
  - [x] タスクの追加・取得・更新・削除・検索・ステータス遷移
- [x] `usecases/task_crud_usecase.py` を実装
- [x] `tests/test_usecases.py` を実装（33件全通過、合計66件）

## フェーズ5: CLIコマンド実装

- [x] `cli/main.py` を実装（typerアプリのセットアップ）
- [x] `cli/commands/add.py` を実装（`task add <title>`）
- [x] `cli/commands/list.py` を実装（`task list`、rich テーブル表示）
- [x] `cli/commands/show.py` を実装（`task show <id>`）
- [x] 動作確認
  - [x] `uv run task add "テストタスク"` が動く
  - [x] `uv run task list` が動く
  - [x] `uv run task show <id>` が動く

## フェーズ6: 品質チェック

- [x] `uv run pytest` で全テストが通ることを確認（66件）
- [x] 型チェック（pyright）の導入と確認（src・tests ともにエラーゼロ）

## フェーズ7: ドキュメント整備

- [x] `docs/architecture.md` をPython版として更新
- [x] `docs/repository-structure.md` をPython版として更新
- [x] `README.md` を作成

---

## 実装後の振り返り

### 実装完了日
未定

### 計画と実績の差分

**計画と異なった点**:
-

### 学んだこと
-

### 次回への改善提案
-

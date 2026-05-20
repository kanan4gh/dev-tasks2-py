# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

---

## フェーズ1: リポジトリ作成・プロジェクト初期化

- [x] GitHubリポジトリ `dev-tasks2-py` を作成（既存・空）
- [ ] ローカルにクローン
- [ ] uv でプロジェクト初期化（`uv init`）
- [ ] ディレクトリ構造を作成（src/task_cli/ 以下）
- [ ] pyproject.toml に依存関係を設定
- [ ] 依存関係をインストール（`uv sync`）
- [ ] CLIエントリーポイントを設定（`task` コマンドで起動できる状態）
- [ ] `uv run task --help` が動くことを確認
- [ ] CLAUDE.md を作成（現行dev-tasks2のものをコピーし、技術依存部分をPython/uv向けに書き換え）

## フェーズ2: データモデル定義

- [ ] `models/task.py` を実装
  - [ ] `TaskStatus` enum（todo / in_progress / done / archived）
  - [ ] `Priority` enum（low / medium / high）
  - [ ] `Task` モデル（id, title, status, priority, created_at 等）
  - [ ] `GlobalConfig` モデル（activeProject 等）
- [ ] `tests/test_models.py` を実装

## フェーズ3: ストレージ層

- [ ] `storage/file_storage.py` を実装
  - [ ] タスクの読み込み（`~/.task/projects/<name>/tasks.yaml`）
  - [ ] タスクの書き込み
- [ ] `storage/global_config_storage.py` を実装
  - [ ] グローバル設定の読み込み（`~/.task/config.yaml`）
  - [ ] グローバル設定の書き込み
- [ ] `tests/test_storage.py` を実装

## フェーズ4: サービス・ユースケース層

- [ ] `services/global_config_service.py` を実装
  - [ ] アクティブプロジェクトの取得・設定
- [ ] `services/task_manager.py` を実装
  - [ ] タスクの追加・取得・更新・削除
- [ ] `usecases/task_crud_usecase.py` を実装
- [ ] `tests/test_usecases.py` を実装

## フェーズ5: CLIコマンド実装

- [ ] `cli/main.py` を実装（typerアプリのセットアップ）
- [ ] `cli/commands/add.py` を実装（`task add <title>`）
- [ ] `cli/commands/list.py` を実装（`task list`、rich テーブル表示）
- [ ] `cli/commands/show.py` を実装（`task show <id>`）
- [ ] 動作確認
  - [ ] `uv run task add "テストタスク"` が動く
  - [ ] `uv run task list` が動く
  - [ ] `uv run task show <id>` が動く

## フェーズ6: 品質チェック

- [ ] `uv run pytest` で全テストが通ることを確認
- [ ] 型チェック（mypy or pyright）の導入と確認

## フェーズ7: ドキュメント整備

- [ ] `docs/architecture.md` をPython版として作成
- [ ] `docs/repository-structure.md` をPython版として作成
- [ ] `README.md` を作成

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

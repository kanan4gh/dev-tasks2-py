# 設計書

## アーキテクチャ概要

TypeScript版と同じレイヤードアーキテクチャを採用する。

```
dev-tasks2-py/
├── src/
│   └── task_cli/
│       ├── cli/          # CLIレイヤー（click）
│       ├── usecases/     # ユースケース層
│       ├── services/     # サービス層
│       ├── storage/      # ストレージ層
│       └── models/       # データモデル（pydantic）
├── tests/
├── pyproject.toml        # uv によるプロジェクト定義
└── docs/                 # Python版ドキュメント
```

## 技術選定

| 技術 | 採用 | TypeScript版相当 |
|------|------|-----------------|
| 依存管理 | uv | npm |
| CLIフレームワーク | typer | commander.js |
| データモデル | pydantic | TypeScript型定義 |
| データ永続化 | PyYAML | js-yaml |
| テスト | pytest | vitest |
| カラー出力 | rich | chalk |
| テーブル表示 | rich | cli-table3 |

※ typer は click ベースで型ヒントからCLIを自動生成する。TypeScriptの感覚に近い。

## コンポーネント設計

### 1. models/（データモデル）

**責務**:
- Task, Project, GlobalConfig などのデータ構造を定義
- バリデーションと型安全性の担保

**実装の要点**:
- pydantic の `BaseModel` を継承
- TypeScript版 `types/index.ts` のフィールドを踏襲

### 2. storage/（ストレージ層）

**責務**:
- YAMLファイルへの読み書き
- `~/.task/` 配下のファイル管理

**実装の要点**:
- `FileStorage` クラス: タスクの永続化
- `GlobalConfigStorage` クラス: グローバル設定の管理
- TypeScript版と同じファイルパス構造（`~/.task/projects/<name>/tasks.yaml`）

### 3. services/（サービス層）

**責務**:
- ビジネスロジックの実装
- ストレージ層の操作

**実装の要点**:
- `TaskManager`: タスクCRUD
- `GlobalConfigService`: アクティブプロジェクト管理

### 4. usecases/（ユースケース層）

**責務**:
- CLIコマンドとサービス層の橋渡し
- 複数サービスの組み合わせ

### 5. cli/（CLIレイヤー）

**責務**:
- コマンドの定義と引数解析
- 表示の担当

**実装の要点**:
- typer によるサブコマンド定義
- rich による色付き・テーブル表示

## ディレクトリ構造（詳細）

```
dev-tasks2-py/
├── src/
│   └── task_cli/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py       # エントリーポイント・typer セットアップ
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── add.py
│       │       ├── list.py
│       │       └── show.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── task.py       # Task, Project, GlobalConfig
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── file_storage.py
│       │   └── global_config_storage.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── task_manager.py
│       │   └── global_config_service.py
│       └── usecases/
│           ├── __init__.py
│           └── task_crud_usecase.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_storage.py
│   └── test_usecases.py
├── pyproject.toml
├── README.md
└── docs/
    ├── architecture.md
    └── repository-structure.md
```

## pyproject.toml 構成

```toml
[project]
name = "dev-tasks2-py"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "typer",
    "pydantic",
    "pyyaml",
    "rich",
]

[project.scripts]
task = "task_cli.cli.main:app"

[tool.uv]
dev-dependencies = [
    "pytest",
    "pytest-cov",
]
```

## CLAUDE.md移植時の注意

dev-tasks2のCLAUDE.mdをコピーする際、**書き換えが必要なのは技術スタック固有層だけ**。

- **汎用層**: そのままコピー
- **プロダクト固有層**: そのままコピー（同じプロダクト・TaskCLIなので変更不要）
- **技術スタック固有層**: Python/uv向けに書き換え（Node.js/npm → Python/uv/pytest等）

プロダクト固有層を空にしたり書き直さないよう注意。

## 実装の順序

1. GitHubリポジトリ作成・uv初期化
2. ディレクトリ構造の作成
3. データモデル定義（models/）
4. ストレージ層（storage/）
5. サービス層（services/）
6. ユースケース層（usecases/）
7. CLIコマンド実装（cli/）
8. テスト作成
9. ドキュメント整備（architecture.md, repository-structure.md）

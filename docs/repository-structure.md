# リポジトリ構造定義書 (Repository Structure Document)

## プロジェクト構造

```
dev-tasks2-py/
├── src/
│   └── task_cli/                     # パッケージルート
│       ├── __init__.py
│       ├── exceptions.py             # AppError 定義
│       ├── cli/                      # CLIレイヤー
│       │   ├── __init__.py
│       │   ├── main.py               # エントリーポイント・typer セットアップ
│       │   ├── deps.py               # ブートストラップ（依存関係の組み立て）
│       │   ├── renderer.py           # ターミナル表示（テーブル・カラー・エラー）
│       │   └── commands/             # サブコマンド定義
│       │       ├── __init__.py
│       │       ├── add.py            # task add <title>        P0
│       │       ├── list.py           # task list               P0
│       │       ├── show.py           # task show <id>          P0
│       │       ├── start.py          # task start <id>         P0（未実装）
│       │       ├── done.py           # task done <id>          P0（未実装）
│       │       ├── delete.py         # task delete <id>        P0（未実装）
│       │       ├── archive.py        # task archive <id>       P0（未実装）
│       │       ├── project.py        # task project *          P0（未実装）
│       │       ├── move.py           # task move <id> <proj>   P0（未実装）
│       │       └── inbox.py          # task inbox              P0（未実装）
│       ├── models/                   # データモデル（pydantic）
│       │   ├── __init__.py
│       │   └── task.py               # Task / TaskStatus / Priority / GlobalConfig
│       ├── services/                 # サービスレイヤー
│       │   ├── __init__.py
│       │   ├── task_manager.py       # タスク CRUD・ステータス管理・検索
│       │   └── global_config_service.py  # アクティブプロジェクト管理
│       ├── storage/                  # ストレージレイヤー
│       │   ├── __init__.py
│       │   ├── file_storage.py       # tasks.yaml の読み書き・バックアップ
│       │   └── global_config_storage.py  # ~/.task/config.yaml の読み書き
│       └── usecases/                 # ユースケース層
│           ├── __init__.py
│           └── task_crud_usecase.py  # ストレージパス解決・TaskManager への委譲
├── tests/
│   ├── __init__.py
│   ├── test_models.py                # Task / GlobalConfig のバリデーション・遷移テスト
│   ├── test_storage.py               # FileStorage / GlobalConfigStorage テスト
│   └── test_usecases.py              # TaskManager / TaskCrudUseCase テスト
├── docs/                             # プロジェクトドキュメント
│   ├── product-requirements.md
│   ├── functional-design.md
│   ├── architecture.md               # 本ドキュメントと対（技術仕様）
│   ├── repository-structure.md       # 本ドキュメント
│   ├── development-guidelines.md
│   └── glossary.md
├── .steering/                        # 作業単位のドキュメント
│   └── [YYYYMMDD]-[task-name]/
│       ├── requirements.md
│       ├── design.md
│       └── tasklist.md
├── .devcontainer/
│   └── devcontainer.json
├── pyproject.toml
├── uv.lock
├── CLAUDE.md
└── README.md
```

---

## ディレクトリ詳細

### `src/task_cli/cli/`（CLIレイヤー）

**役割**: ユーザー入力の受付・引数バリデーション・結果の整形表示。ビジネスロジックを持たない。

**配置ファイル**:
- `main.py`: typer アプリ定義。全サブコマンドを登録する
- `deps.py`: ストレージ・サービス・ユースケースの組み立てファクトリ
- `renderer.py`: rich を使ったテーブル表示・詳細表示・エラー表示
- `commands/*.py`: サブコマンドごとの関数定義

**依存関係**:
- 依存可能: `usecases/`, `services/`, `models/`
- 依存禁止: `storage/`（ストレージへの直接アクセス禁止）

---

### `src/task_cli/models/`（データモデル）

**役割**: pydantic `BaseModel` を使ったエンティティ定義とバリデーション。

**主要クラス**:

| クラス | 用途 |
|-------|------|
| `TaskStatus` | ステータス列挙型（open / in_progress / completed / archived） |
| `Priority` | 優先度列挙型（high / medium / low） |
| `Task` | タスクエンティティ。ステータス遷移可否を `can_transition_to()` で検査 |
| `ProjectEntry` | プロジェクト名と ID のペア |
| `GlobalConfig` | グローバル設定（activeProject・projects・lastProjectId） |

**依存関係**:
- 依存可能: なし（他のどのレイヤーにも依存しない）

---

### `src/task_cli/services/`（サービスレイヤー）

**役割**: 個別ドメインのビジネスロジック。

**配置ファイル**:
- `task_manager.py`: タスクの CRUD・ステータス遷移・検索・ソート。`TaskFilter` dataclass を含む
- `global_config_service.py`: アクティブプロジェクトの取得・切り替え

**依存関係**:
- 依存可能: `storage/`, `models/`
- 依存禁止: `cli/`

---

### `src/task_cli/storage/`（ストレージレイヤー）

**役割**: YAML ファイルへのデータ永続化。

**配置ファイル**:
- `file_storage.py`: `tasks.yaml` の読み書き。書き込み前に `.bak` を作成し、失敗時は自動復元
- `global_config_storage.py`: `~/.task/config.yaml` の読み書き

**依存関係**:
- 依存可能: `models/`、Python 標準ライブラリ（`pathlib`, `os`, `shutil`）
- 依存禁止: `cli/`, `services/`

---

### `src/task_cli/usecases/`（ユースケース層）

**役割**: アクティブプロジェクトに応じたストレージパスを解決し、TaskManager に委譲する。

**配置ファイル**:
- `task_crud_usecase.py`: `GlobalConfigService` でアクティブプロジェクトを取得 → `~/.task/projects/<name>/tasks.yaml` または `~/.task/inbox/tasks.yaml` に解決 → `TaskManager` を生成して操作を委譲

---

### `tests/`（テストディレクトリ）

pytest の `tmp_path` フィクスチャで一時ディレクトリを作成し、実ファイルシステムを使用したテストを行う。

| ファイル | 内容 |
|---------|------|
| `test_models.py` | バリデーション・ステータス遷移・GlobalConfig のデフォルト値（20件） |
| `test_storage.py` | FileStorage の読み書き・バックアップ復元、GlobalConfigStorage の読み書き（13件） |
| `test_usecases.py` | TaskManager のCRUD・検索・ソート・エラーケース、TaskCrudUseCase のライフサイクル（33件） |

---

## ファイル配置規則

### ソースファイル

| ファイル種別 | 配置先 | 命名規則 | 例 |
|------------|--------|---------|-----|
| コマンド定義 | `cli/commands/` | `snake_case.py`（サブコマンド名と一致） | `add.py`, `list.py` |
| 表示ロジック | `cli/` | `snake_case.py` | `renderer.py` |
| サービスクラス | `services/` | `snake_case.py`（役割接尾辞: `_manager`, `_service`） | `task_manager.py` |
| ストレージクラス | `storage/` | `snake_case.py`（`_storage` 接尾辞） | `file_storage.py` |
| データモデル | `models/` | `snake_case.py` | `task.py` |
| ユースケース | `usecases/` | `snake_case.py`（`_usecase` 接尾辞） | `task_crud_usecase.py` |

### テストファイル

| テスト種別 | 配置先 | 命名規則 | 例 |
|-----------|--------|---------|-----|
| モデルテスト | `tests/` | `test_models.py` | — |
| ストレージテスト | `tests/` | `test_storage.py` | — |
| サービス・ユースケーステスト | `tests/` | `test_usecases.py` | — |

---

## 依存関係のルール

```
cli/  ──→  usecases/  ──→  services/  ──→  storage/
 │                               │               │
 └──────────────────────────→  models/  ←────────┘
```

**許可される依存**:
- `cli/` → `usecases/`, `services/`, `models/`
- `usecases/` → `services/`, `storage/`, `models/`
- `services/` → `storage/`, `models/`
- `storage/` → `models/`

**禁止される依存**:
- `storage/` → `services/` / `cli/` ❌
- `services/` → `cli/` ❌
- `models/` → 全レイヤー ❌

---

## 設定ファイル

| ファイル | 用途 |
|---------|------|
| `pyproject.toml` | 依存関係・CLIエントリーポイント・pytest設定 |
| `uv.lock` | 依存関係のロックファイル（Git 管理対象） |
| `CLAUDE.md` | Claude Code のプロジェクト指示 |

---

## 除外設定（.gitignore）

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
dist/
```

> タスクデータはグローバルストレージ（`~/.task/`）に保存されるため、`.gitignore` への追記は不要。

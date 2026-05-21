# 技術仕様書 (Architecture Design Document)

## テクノロジースタック

### 言語・ランタイム

| 技術 | バージョン |
|------|-----------|
| Python | 3.12 以上 |
| uv | 0.11 以上 |

**選定理由**:

- **Python 3.12** — 型ヒントの表現力が高く（`X | Y` 構文、`TypeAlias` 等）、pydantic との親和性に優れる。
- **uv** — Rust 製の高速パッケージマネージャー。`uv sync` 1コマンドで仮想環境の作成から依存インストールまで完結。`uv.lock` で再現性を保証。

---

### フレームワーク・ライブラリ（本番依存）

| 技術 | バージョン | 用途 | TypeScript版相当 |
|------|-----------|------|-----------------|
| typer | latest | CLI フレームワーク | commander.js |
| pydantic | latest | データモデル・バリデーション | TypeScript 型定義 |
| pyyaml | latest | YAML 読み書き | js-yaml |
| rich | latest | カラー出力・テーブル表示 | chalk + cli-table3 |

### 開発ツール

| 技術 | バージョン | 用途 | TypeScript版相当 |
|------|-----------|------|-----------------|
| pytest | latest | テストフレームワーク | vitest |
| pytest-cov | latest | カバレッジ計測 | vitest --coverage |
| pyright | latest | 静的型チェック | tsc |

---

## アーキテクチャパターン

### Clean Architecture

TypeScript版と同じ4層構造を採用する。依存は外→内の一方向のみ。

```
┌───────────────────────────────┐
│   CLI レイヤー                 │ ← 入力受付・バリデーション・結果表示
│   src/task_cli/cli/           │   typer + rich (Renderer)
│   （Interface Adapter）        │
├───────────────────────────────┤
│   ユースケース層                │ ← 複数サービスの調整・ストレージパス解決
│   src/task_cli/usecases/      │
│   （Application Service）      │
├───────────────────────────────┤
│   サービスレイヤー               │ ← 個別ドメインロジック
│   src/task_cli/services/      │   TaskManager / GlobalConfigService
│   （Domain Service）           │
├───────────────────────────────┤
│   ストレージレイヤー             │ ← YAML ファイルへの読み書き
│   src/task_cli/storage/       │   FileStorage / GlobalConfigStorage
│   （Infrastructure）           │
└───────────────────────────────┘
         ↓ 外部依存
┌──────────────────┐
│ ~/.task-py/ (FS)    │
└──────────────────┘
```

### データモデル（pydantic）

TypeScript の型定義を pydantic `BaseModel` で表現。バリデーションをモデル層に集約する。

```python
# TypeScript版
type TaskStatus = 'open' | 'in_progress' | 'completed' | 'archived';

# Python版
class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
```

---

## データ永続化戦略

### ストレージ方式

| データ種別 | パス | フォーマット |
|-----------|------|------------|
| グローバル設定 | `~/.task-py/config.yaml` | YAML オブジェクト |
| タスクデータ（プロジェクト） | `~/.task-py/projects/<name>/tasks.yaml` | YAML 配列 |
| タスクデータ（Inbox） | `~/.task-py/inbox/tasks.yaml` | YAML 配列 |

※ TypeScript版は JSON だが、Python版は YAML を採用（pyyaml が標準的なため）。

### バックアップ戦略

`FileStorage.save()` 時に以下のフローを実行:

1. 既存ファイルを `tasks.yaml.bak` にコピー
2. 新データを `tasks.yaml` に書き込み
3. 成功したら `.bak` を削除（失敗したら `.bak` を元のパスに移動して復元）

### ファイルパーミッション

| パス | パーミッション |
|-----|-------------|
| `~/.task-py/` および配下ディレクトリ | `700`（オーナーのみアクセス可） |
| `tasks.yaml`, `config.yaml` | `644`（デフォルト） |

---

## パフォーマンス要件

| 操作 | 目標時間 |
|------|---------|
| ローカル操作全般（add / list / show 等） | 100ms 以内 |
| `task list`（1,000 件） | 1 秒以内 |

---

## テスト戦略

### ユニットテスト（pytest）

- **対象**: `models/`（バリデーション・ステータス遷移）、`storage/`（読み書き・バックアップ）、`services/`（CRUD・ステータス遷移・検索）、`usecases/`（ライフサイクル・エラーケース）
- **方針**: `tmp_path` フィクスチャで実ファイルシステムを使用。ストレージモックは最小限。
- **カバレッジ目標**: 全体 80% 以上

### テスト実行

```bash
uv run pytest                    # 全テスト
uv run pytest --cov=src          # カバレッジ付き
uv run pyright src tests         # 型チェック
```

---

## セキュリティ

- `~/.task-py/` ディレクトリに `chmod 700` を設定し、オーナーのみアクセス可能にする
- GitHub Token 等の機密情報は将来 `~/.task-py/projects/<name>/config.yaml` に保存（P1）。ファイルパーミッション `600` を設定予定

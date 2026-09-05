# 設計書

## 設計方針

2つの永続ドキュメントを現在のリポジトリへ同期すると同時に、同じ乖離を繰り返しにくい情報設計へ改める。

1. **正典の責務を分ける**: 開発手順とコーディング規約は `development-guidelines.md`、配置と依存方向は `repository-structure.md` が担う
2. **既存の正典を参照する**: SDD、品質ゲート、外部自動化、アーキテクチャの詳細を複製せず、役割と参照先を示す
3. **安定した構造を記述する**: 固定テスト件数やツールのパッチバージョンを避け、ディレクトリの責務・検証コマンド・設定ファイルを記述する
4. **実在する例だけを使う**: Pythonコード例、パス、クラス、コマンドは現在の実装と設定から採る

変更は文書2件に限定し、実行可能コード、設定、テスト、ハーネスアダプタは変更しない。

## 正典の責務分担

| 情報 | 正とする場所 | 今回の2文書での扱い |
|---|---|---|
| SDDフロー、steering状態、PR・リリース原則 | `AGENTS.md` / `docs/procedures/` | 日常作業に必要な入口だけ示し、詳細へリンクする |
| Python・依存関係・ツール設定 | `pyproject.toml` | 実行方法と開発上の意味を説明する |
| 外部自動化とローカル品質ゲート | `docs/external-automation-policy.md` | 必須／任意の境界を要約し、詳細へリンクする |
| アーキテクチャと永続化方式 | `docs/architecture.md` | 配置判断に必要な依存方向だけ再掲する |
| 利用者向けコマンド | `README.md` | 開発者向けの動作確認例だけ示す |
| 開発手順・Python規約 | `docs/development-guidelines.md` | 今回全面的に現行化する |
| ディレクトリ責務・ファイル配置 | `docs/repository-structure.md` | 今回全面的に現行化する |

## 文書1: `docs/development-guidelines.md`

### 責務

開発者が環境を準備し、Pythonコードを既存規約に沿って変更し、ローカルで検証してPR・リリースへ進むためのガイドとする。利用者向け操作マニュアルやSDD手順書そのものは担わない。

### 章構成

1. **開発環境セットアップ**
   - 必須: Python 3.12、uv、Git
   - 任意: Docker、VS Code Dev Containers
   - `git clone`、`uv sync`、`uv run task-py --help` による確認
2. **日常の開発フロー**
   - Issue → フィーチャーブランチ → steering →実装→ローカル品質ゲート→PR
   - tasklistの状態操作と詳細手順への参照
3. **Pythonコーディング規約**
   - `snake_case` / `PascalCase` / `UPPER_SNAKE_CASE`
   - 型注釈、pydanticモデル、`dataclass` の使い分け
   - ruffの行長100文字、basedpyright standard
   - 単一責務、依存注入、`AppError`、コメント・docstring
4. **テスト戦略**
   - pytest、`tmp_path`、境界のモック、正常系・異常系
   - 固定件数・根拠のないカバレッジ比率は置かない
5. **品質保証**
   - 個別の pytest / ruff / basedpyright / steering lint / metered automation lint
   - PR前は `local_quality_gate.py` を単一入口とする
   - GitHub Actionsは自動起動しない任意ミラー
   - 純ドキュメントの実挙動検証はスキップし、文書レビューを行う
6. **Git・PR・リリース**
   - `main` 起点の `feature/<task-name>` とPR経由のマージ
   - Conventional Commits
   - `pyproject.toml` のバージョン、Issueクローズ、`gh release create`
7. **README管理とチェックリスト**
   - 利用者向け挙動が変わる場合の更新条件
   - 実装前・PR前の最小チェック

### コード例の選択

- 型とモデル: `Task`, `TaskFilter` に沿う Python 3.12 構文
- エラー処理: `task_cli.exceptions.AppError`
- テスト: pytestの `tmp_path` と `pytest.raises`
- レイヤー分離: CLIでロジックを持たず usecase / service へ委譲する例

長大なサンプルは置かず、規約を判別できる最小例にする。実装と同期しにくい内部メソッドの完全な写しは避ける。

## 文書2: `docs/repository-structure.md`

### 責務

リポジトリ内の主要な成果物、Pythonパッケージのレイヤー、CLIとMCPの2入口、テスト・SDDハーネス・品質スクリプトの配置を説明し、新規ファイルの置き場所を判断できる文書とする。

### 構造図の粒度

- `src/task_cli/`: パッケージ直下、`cli/`、`models/`、`services/`、`storage/`、`usecases/` の現行モジュールを示す
- `src/task_cli/cli/commands/`: コマンドファイルは現在の名前を複数行にまとめ、各機能の仕様説明はしない
- `src/task_mcp/`: 出荷対象である4モジュールを示す
- `tests/`: ルート直下はプロダクトテスト群としてまとめ、分類ディレクトリは個別に示す。個々のテストファイル数・テスト件数は記載しない
- `docs/`: 永続ドキュメント、`ideas/`、`procedures/` の役割を示す。全手順ファイルは列挙しない
- トップレベル: SDD正典、ハーネスアダプタ、品質スクリプト、レポート、GitHub設定、MCP設定例、ビルド設定を示す

この粒度なら、アーキテクチャ上意味のあるモジュール追加は文書更新対象になる一方、テストケースや手順ファイルの増減だけでは構造図が陳腐化しない。

### ディレクトリ詳細

| 対象 | 記載する責務 |
|---|---|
| `task_cli/cli/` | 入力・表示・依存組み立て。ビジネスロジックを持たない |
| `task_mcp/` | MCPツール公開と観測。CLIコマンドや表示は経由せず共有ユースケース／サービスを呼ぶ。依存組み立てには現状 `cli/deps.py` を再利用する |
| `task_cli/models/` | pydanticエンティティと循環依存を避けるモデル方向 |
| `task_cli/services/` | 個別ドメインロジック |
| `task_cli/storage/` | YAML永続化 |
| `task_cli/usecases/` | 複数サービス・ストレージの調整と入口間の挙動統一 |
| `tests/` | プロダクトテストと、adapter / automation / hook / lint / procedure / script の規律テスト |
| `scripts/` | steering状態・lint・単一品質ゲート等の決定論的ツール |

### 依存関係

```text
cli/ ───────────────────→ usecases/ ──→ services/ ──→ storage/
 ▲                            │             │             │
 │                            └──────────→ models/ ←──────┘
 │
task_mcp/ ──→ cli/deps.py ──→ 共有層
     └─────────────────────→ usecases/ / services/ / storage/ / models/

task_cli直下の共有基盤モジュール（exceptions.py / duration.py）は、CLIとMCPから共有可能。duration.py は exceptions.py に依存する
```

実際のimportはユースケースがストレージを直接調整する場合もあるため、本文では `usecases/ → services/, storage/, models/` を許可する。`task_mcp/server.py` は組み立てを再利用するため `task_cli/cli/deps.py` をimportするが、CLIコマンドとrendererには依存しない。この現状を隠さず、CLI固有表示を共有層へ逆流させない境界と区別する。

### ファイル配置規則

- CLIコマンド: `src/task_cli/cli/commands/<command>.py`
- MCP入口: `src/task_mcp/server.py`、観測補助: `src/task_mcp/tracking.py`
- 両入口から共有する小さな例外・変換基盤: `src/task_cli/` 直下
- ドメインモデル・サービス・ストレージ・調整処理: 対応レイヤー
- プロダクトテスト: `tests/test_<対象>.py`
- SDD／ハーネス規律テスト: `tests/<分類>/test_<対象>.py`
- 作業単位の文書: `.steering/YYYYMMDD-<task-name>/`

## 実装順序

1. `development-guidelines.md` を全面的に書き直し、TypeScript版の前提を除去する
2. `repository-structure.md` を現行ツリーと依存関係へ同期する
3. 2文書間、AGENTS.md、pyproject.toml、外部自動化ポリシーとの整合性を確認する
4. 文書内のコマンド、パス、旧技術語を機械的に検索する
5. 4段検証と文書レビューを実施する

## 検証設計

### 段1: 静的検証

- `uv run pytest`
- `uv run ruff check .`
- `uv run basedpyright`
- `uv run python3 scripts/steering_lint.py`
- `uv run python3 scripts/metered_automation_lint.py`
- `git diff --check`

### 段2: 実挙動検証

純ドキュメント変更で観察対象がないため、steering手順に従いスキップし、その理由をtasklistへ記録する。

### 段3: 変更差分レビュー

- Issue #28 / #40 の指摘が差分に対応しているか確認する
- 重複、断定の強さ、将来陳腐化しやすい数値、実在しないパス・コマンドを確認する
- `git diff -- docs/development-guidelines.md docs/repository-structure.md` を対象とする

### 段4: スペック準拠・文書品質レビュー

- requirementsの受け入れ条件と変更差分を照合する
- `docs/procedures/review-docs.md` に従い、正確性・完全性・一貫性・明確性・保守性を確認する
- 正当な指摘を反映後、影響範囲だけ再検証する

### 機械的な内容照合

- 旧技術語: `Node.js|npm|TypeScript|Vitest|Husky|Prettier|develop`
- 必須語: `Python 3.12|uv|pytest|ruff|basedpyright|local_quality_gate.py`
- 構造: `find src tests docs scripts -type f` と構造図・配置規則を照合
- 主要パス: 文書内でコード表記した主要なローカルパスが存在することを確認

## セキュリティ・パフォーマンス・互換性

- 実行可能コードや設定を変更しないため、セキュリティ、実行性能、データ互換性への影響はない
- コマンド例に実トークン、個人パス、秘密情報を含めない
- 外部APIや従量課金LLMのheadless modeを検証で起動しない
- 文書のリンク先はリポジトリ相対パスとし、移植性を保つ

## 将来の保守方針

- 新しいレイヤー、入口、出荷対象パッケージを追加した場合は `repository-structure.md` を更新する
- 開発ツール、品質ゲート、ブランチ・リリース方針を変更した場合は `development-guidelines.md` を更新する
- テストケース数や個別fixtureの増減だけでは文書を更新しない
- 重複する手順に差が出た場合は、AGENTS.mdまたは該当procedureを正とし、本2文書は参照と開発者向け要約へ戻す

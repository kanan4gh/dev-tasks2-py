# リポジトリ構造定義書 (Repository Structure Document)

## 本書の役割

本書は、TaskCLIリポジトリ内の主要な成果物、Pythonパッケージのレイヤー、CLIとMCPの入口、テスト・SDDハーネス・品質スクリプトの配置を定める。機能仕様は `docs/functional-design.md`、技術選定と永続化方式は `docs/architecture.md`、開発手順は `docs/development-guidelines.md` を正とする。

構造図は配置判断に必要な粒度を保ち、テスト件数や個別手順ファイル数のように頻繁に変わる値は固定しない。

---

## プロジェクト構造

```text
dev-tasks2-py/
├── src/
│   ├── task_cli/                         # CLIと共有ドメインのパッケージ
│   │   ├── __init__.py
│   │   ├── exceptions.py                 # AppError
│   │   ├── duration.py                   # CLI・MCP共通の時間変換
│   │   ├── cli/                          # CLI入口、表示、依存組み立て
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── deps.py
│   │   │   ├── editor.py
│   │   │   ├── renderer.py
│   │   │   ├── shell.py
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       ├── add.py / edit.py / list.py / show.py
│   │   │       ├── start.py / done.py / archive.py / delete.py
│   │   │       ├── move.py / inbox.py / project.py
│   │   │       ├── schedule.py / search.py / onboard.py
│   │   │       ├── daily.py / time.py / shell.py
│   │   │       └── migrate.py / reset.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py                   # Task、設定、列挙型
│   │   │   ├── daily.py                  # ルーティーンと日別ログ
│   │   │   └── time.py                   # 作業セッションとタイマー状態
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── task_manager.py
│   │   │   ├── global_config_service.py
│   │   │   ├── project_service.py
│   │   │   ├── daily_service.py
│   │   │   └── timer_service.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── file_storage.py
│   │   │   ├── global_config_storage.py
│   │   │   ├── routine_storage.py
│   │   │   ├── daily_log_storage.py
│   │   │   └── timer_storage.py
│   │   └── usecases/
│   │       ├── __init__.py
│   │       ├── task_crud_usecase.py
│   │       └── time_tracking_usecase.py
│   └── task_mcp/                         # MCPサーバーの第2入口
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py
│       └── tracking.py
├── tests/
│   ├── test_*.py                         # プロダクト機能のテスト
│   ├── adapters/                         # ハーネス受け入れ契約
│   ├── automation/                       # 任意ワークフローの構造
│   ├── hooks/                            # 非強制フック
│   ├── lint/                             # steering・外部自動化規律
│   ├── procedures/                       # SDD手順の不変条件
│   └── scripts/                          # 品質スクリプトの単体テスト
├── docs/
│   ├── product-requirements.md
│   ├── functional-design.md
│   ├── architecture.md
│   ├── repository-structure.md
│   ├── development-guidelines.md
│   ├── glossary.md
│   ├── migration-from-ts.md
│   ├── harness-guide.md
│   ├── external-automation-policy.md
│   ├── ideas/                             # 下書き・調査・構想
│   └── procedures/                        # SDD手順とテンプレート
├── scripts/
│   ├── local_quality_gate.py
│   ├── steering_state.py
│   ├── steering_lint.py
│   ├── metered_automation_lint.py
│   ├── metered_automation_policy.json
│   └── check_pr_file_overlap.py
├── reports/                               # 適応度などの計測成果物
├── .steering/                             # 作業単位の要求・設計・進捗履歴
├── .claude/ + CLAUDE.md                   # Claude Codeアダプタ
├── .agents/ + .codex/                     # Codexスキル・エージェント定義
├── .kiro/                                 # Kiroアダプタ
├── .github/                               # PRテンプレート・任意手動ワークフロー
├── .devcontainer/                         # 任意のコンテナ開発環境
├── .mcp.json.example                      # MCP設定例
├── .gitignore                              # 生成物・キャッシュの追跡除外
├── AGENTS.md                              # SDDプロセスのハーネス中立な正典
├── pyproject.toml                         # パッケージ・ツール設定
├── uv.lock                                # 依存関係ロック
└── README.md                              # 利用者向けマニュアル
```

`src/task_cli/` と `src/task_mcp/` はどちらも `pyproject.toml` のwheel対象である。コマンド入口はそれぞれ `task-py` と `task-mcp` として登録する。

---

## アプリケーションパッケージ

### `src/task_cli/cli/` — CLI入口

**責務**: typerによる入力受付、引数の変換、結果の表示、依存関係の組み立て。共有すべきビジネス判断は持たない。

| ファイル | 責務 |
|---|---|
| `main.py` | typerアプリを定義し、コマンドとサブアプリを登録する |
| `deps.py` | storage、service、usecaseを本番用に組み立てる |
| `renderer.py` | richによる一覧・詳細・成功・エラー表示 |
| `editor.py` | `click.edit()` を使うエディタ連携と例外変換 |
| `shell.py` | prompt-toolkitによる対話シェル |
| `commands/*.py` | コマンド引数を共有層の呼び出しへ変換する |

新しいコマンドは `commands/<command>.py` に置き、`main.py` へ登録する。ドメイン判断はusecaseまたはserviceへ置く。依存生成は `deps.py` を優先する。

現状、プロジェクト一覧など一部の管理・表示処理と対話シェルはstorageを直接組み立てている。新規コードで直接依存を増やす場合は、表示のための単純な読み取り・composition rootとして妥当かを確認し、入口間で共有する判断はusecaseへ移す。

### `src/task_mcp/` — MCP入口

**責務**: FastMCPツールの公開、MCP向け入出力への変換、呼び出し観測。

| ファイル | 責務 |
|---|---|
| `__main__.py` | stdio transportでMCPサーバーを起動する |
| `server.py` | MCPツールを定義し、共有usecase・serviceを呼び出す |
| `tracking.py` | ツール呼び出しを `~/.task-py/mcp_calls.jsonl` へ記録・集計する |

MCPはCLIコマンドや `renderer.py` を経由せず、共有層を直接呼ぶ第2の入口である。ただし、本番依存の組み立てには現状 `task_cli/cli/deps.py` を再利用している。この依存とCLI表示への依存を区別し、MCP固有の文字列変換を共有層へ逆流させない。

### `src/task_cli/models/` — データモデル

**責務**: pydanticによるエンティティ、列挙型、永続化データの検証。

| ファイル | 主な型 |
|---|---|
| `task.py` | `TaskStatus`, `Priority`, `Task`, `ProjectEntry`, `GlobalConfig` |
| `daily.py` | `Routine`, `DailyLogEntry`, `DailyLog` |
| `time.py` | `WorkSession`, `TimerKind`, `TimerState`, `TimerFile` |

`task.py` は `WorkSession` を使うため `time.py` に依存する。循環を避けるため、`time.py` から `task.py` へは依存しない。モデルはservice、storage、usecase、入口へ依存しない。

### `src/task_cli/services/` — ドメインサービス

**責務**: 1つのドメインに閉じたビジネスロジック。

| ファイル | 責務 |
|---|---|
| `task_manager.py` | タスクCRUD、検索、並び替え、状態遷移、作業セッション追記 |
| `global_config_service.py` | グローバル設定とアクティブプロジェクトの操作 |
| `project_service.py` | プロジェクトの作成・削除・改名 |
| `daily_service.py` | ルーティーンと日別達成ログの操作 |
| `timer_service.py` | タイマー状態遷移と時刻計算 |

serviceはmodel、必要なstorage、パッケージ直下の共有基盤モジュールへ依存できるが、CLI・MCP・usecaseへ依存しない。

### `src/task_cli/storage/` — 永続化

**責務**: `~/.task-py/` 配下のYAMLファイルの読み書きと、形式ごとの復元方針。

| ファイル | 保存対象 |
|---|---|
| `file_storage.py` | Inbox・プロジェクト別の `tasks.yaml` |
| `global_config_storage.py` | `config.yaml` |
| `routine_storage.py` | `daily/routines.yaml` |
| `daily_log_storage.py` | `daily/log.yaml` |
| `timer_storage.py` | `timer.yaml` |

storageはmodel、PyYAML、Python標準ライブラリへ依存できる。service、usecase、CLI、MCPへは依存しない。

### `src/task_cli/usecases/` — アプリケーションユースケース

**責務**: 複数のservice・storageを調整し、CLIとMCPで同じドメイン挙動を使えるようにする。

| ファイル | 責務 |
|---|---|
| `task_crud_usecase.py` | アクティブプロジェクトのstorage解決とタスク操作、タイマー後始末 |
| `time_tracking_usecase.py` | タイマーとタスクの接続、作業時間記録、移動時の追従 |

usecaseはmodel、service、storage、共有基盤モジュールと別のusecaseへ依存できる。入口固有の表示やプロンプトは持たない。

### パッケージ直下の共有基盤モジュール

- `exceptions.py`: 入口間で共有する `AppError`
- `duration.py`: CLIとMCPで共有する時間文字列のパース・整形。`exceptions.py` に依存する

小さく安定し、アプリケーションレイヤーに属さない共通要素だけを置く。汎用化を理由にビジネスロジックを直下へ逃がさない。

---

## 依存関係のルール

次の図は代表的な処理経路を示す。入口は用途に応じてservice、storage、model、共有基盤モジュールも直接利用する。

```text
task-py (cli/main.py → cli/commands/) ──┐
                                         ├──→ usecases/ ──→ services/ ──→ storage/
task-mcp (task_mcp/server.py) ───────────┘          │             │             │
       └──→ cli/deps.py（本番依存の組み立て）       └──────────→ models/ ←──────┘

両入口 ──→ service / storage / models / task_cli直下の共有基盤モジュール
```

**許可する方向**:

- CLI・MCP → usecase / service / model / 共有基盤モジュール
- CLI・MCPのcomposition rootと単純表示用の読み取り → storage
- usecase → service / storage / model / 共有基盤モジュール / 別usecase
- service → storage / model / 共有基盤モジュール
- storage → model / PyYAML / Python標準ライブラリ
- `models/task.py` → `models/time.py`
- `duration.py` → `exceptions.py`

**禁止する方向**:

- model → service / storage / usecase / CLI / MCP
- storage → service / usecase / CLI / MCP
- service → usecase / CLI / MCP
- usecase → CLI / MCP
- MCP → CLIコマンド / renderer / editor / shell

`task_mcp/server.py → task_cli/cli/deps.py` は現行のcomposition root再利用であり、CLIプレゼンテーションへの依存ではない。新たな入口が増えて組み立ての共有範囲が広がる場合は、composition rootの配置を別作業で再検討する。

---

## テスト構造

pytestの `tmp_path` などで外部状態を隔離し、利用者の `~/.task-py/` を読み書きしない。テスト件数は機能追加で変わるため、本書では固定しない。

| 配置 | 責務 |
|---|---|
| `tests/test_*.py` | CLI、MCP、model、service、storage、usecaseなどプロダクト機能 |
| `tests/adapters/` | ハーネス構成、実機受け入れ契約、Stop不在契約 |
| `tests/automation/` | GitHub Actionsが任意手動ミラーであること |
| `tests/hooks/` | Claude Codeの非強制tasklistリマインド |
| `tests/lint/` | steering状態・履歴、外部有料自動化、作業ツリー除外 |
| `tests/procedures/` | add-feature、distill、展開手順、軽量パス基準 |
| `tests/scripts/` | ローカル品質ゲートとPRファイル重複検査 |

新しいプロダクト機能のテストはルート直下、SDDハーネスや品質機構の不変条件は対応する分類ディレクトリへ置く。

---

## SDD・品質保証・ハーネス

### `.steering/`

作業単位の履歴を `.steering/YYYYMMDD-<task-name>/` に保存し、gitで追跡する。

- 通常パス: `requirements.md`, `design.md`, `tasklist.md`
- 軽量パス: `requirements.md`, `tasklist.md`
- G3実機受け入れが必要な場合: `acceptance-record.md` を追加する

作業状態とファイル要件は `docs/procedures/steering.md`、パス判定は `docs/procedures/add-feature.md` を正とする。

### `scripts/`

| ファイル | 責務 |
|---|---|
| `local_quality_gate.py` | pytest、ruff、型検査、各lintを固定順で実行する単一ゲート |
| `steering_state.py` | `active / paused / complete` の状態遷移 |
| `steering_lint.py` | steeringの必須ファイル、Issue URL、状態、振り返りを検査 |
| `metered_automation_lint.py` | 禁止する外部有料自動化の再混入を検査 |
| `metered_automation_policy.json` | 検査シグネチャと対象範囲 |
| `check_pr_file_overlap.py` | 複数PRの変更ファイル集合が重なるかを検査 |

### ハーネスアダプタ

| ハーネス | 配置 | 役割 |
|---|---|---|
| Claude Code | `CLAUDE.md`, `.claude/` | コマンド、スキル、エージェント、非強制フック、権限 |
| Codex | `.agents/skills/`, `.codex/` | スキル、エージェント、Codex固有の利用案内 |
| Kiro | `.kiro/` | IDE / CLI向けスキルとエージェント |

成果物の形式と状態遷移は `AGENTS.md` と `docs/procedures/` が共通化し、アダプタはハーネス固有の入口だけを追加する。

---

## ファイル配置規則

| 成果物 | 配置 | 命名例 |
|---|---|---|
| CLIコマンド | `src/task_cli/cli/commands/` | `schedule.py` |
| CLI表示・入力補助 | `src/task_cli/cli/` | `renderer.py`, `editor.py` |
| MCPツール | `src/task_mcp/server.py` | `server.py` 内の `@mcp.tool()` |
| MCP観測補助 | `src/task_mcp/` | `tracking.py` |
| ドメインモデル | `src/task_cli/models/` | `time.py` |
| ドメインサービス | `src/task_cli/services/` | `timer_service.py` |
| 永続化 | `src/task_cli/storage/` | `timer_storage.py` |
| 複数層の調整 | `src/task_cli/usecases/` | `time_tracking_usecase.py` |
| CLI・MCP共通の小さな基盤モジュール | `src/task_cli/` | `exceptions.py`, `duration.py` |
| プロダクトテスト | `tests/` | `test_timer_service.py` |
| SDD・品質機構のテスト | `tests/<分類>/` | `lint/test_steering_state.py` |
| 永続ドキュメント | `docs/` | `architecture.md` |
| 作業単位の記録 | `.steering/YYYYMMDD-<task-name>/` | `tasklist.md` |

新しいレイヤー、入口、出荷対象パッケージを追加した場合は本書を更新する。既存分類内のテストケースやfixtureが増減しただけの場合は更新しない。

規模が拡大した場合は、次を分割判断の目安にする。

- MCPツール群で依存関係や変更理由が分かれたら、`server.py` をドメイン単位へ分割する
- 入口が3種類以上になったら、composition rootを `cli/deps.py` から共有配置へ移す
- 独自のmodel、storage、状態遷移を持つ機能は、既存serviceへ詰め込まず新しいドメインとして分ける

---

## 主要な設定・規範ファイル

| ファイル | 役割 |
|---|---|
| `AGENTS.md` | SDDプロセス、プロダクト、技術スタックのハーネス中立な正典 |
| `pyproject.toml` | パッケージ、依存関係、CLI・MCP entry point、開発ツール設定 |
| `uv.lock` | 解決済み依存関係の再現 |
| `.github/pull_request_template.md` | PRに記録する検証・受け入れ項目 |
| `.github/workflows/steering-lint.yml` | 自動起動しない任意の品質ゲートミラー |
| `.mcp.json.example` | TaskCLI MCPサーバーの設定例 |
| `.gitignore` | 仮想環境、キャッシュ、生成物などの追跡除外 |
| `.devcontainer/devcontainer.json` | 任意のコンテナ開発環境 |
| `docs/external-automation-policy.md` | ローカル品質ゲートと外部自動化の境界 |
| `README.md` | 利用者向けインストール・操作方法 |

除外ファイルと生成物は `.gitignore` を正とする。利用者のタスクデータはリポジトリ外の `~/.task-py/` に保存する。

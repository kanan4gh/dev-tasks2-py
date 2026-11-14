# 設計書

## アーキテクチャ概要

実装を正とし、`docs/functional-design.md` を節ごとに現行化する。文書の骨格(節の並び)は保ち、**実装済みの記述**と**未実装の設計**を物理的に分ける。実装済みの節は事実だけを書き、未実装の設計は末尾の1節に隔離する。

```
functional-design.md
├─ 対象バージョン / システム構成図 / 技術スタック        … 現行化
├─ データモデル定義 / ファイル構造                      … Python(pydantic)・YAML
├─ コンポーネント設計                                  … 実在するクラス・関数
├─ ユースケース図 / UI設計                             … 実在するコマンド・表示
├─ ローカル Web GUI                                    … 変更しない(現行)
├─ エラーハンドリング / パフォーマンス / セキュリティ / テスト戦略 … 現行化
└─ 未実装の設計(Git・GitHub 連携 P1)                 … 新設。TypeScript 由来の設計意図を言語非依存で保存
```

## コンポーネント設計(節ごとの方針)

### 1. 対象バージョン

- 既存の v1.0〜v1.5 の表は残す(v1.2〜v1.5 は現行の記述)
- v1.1(P1)の行を「Git ブランチ・GitHub 連携は**未実装**(末尾の『未実装の設計』節)。絞り込み・検索・タスク編集・優先度/期限は実装済み」と、実装済みと未実装に割る

### 2. システム構成図

- Mermaid を、3入口(CLI=typer / MCP / Web) → `TaskCrudUseCase` → `TaskManager` ほかのサービス → ストレージ → `~/.task-py/*.yaml` に描き直す。Git・GitHub の箱は外す
- 層の名前・依存方向は `docs/architecture.md` と `docs/repository-structure.md` に合わせ、この文書では再定義しない(参照する)

### 3. 技術スタック

- AGENTS.md の技術スタック固有層・`docs/architecture.md` と同じ内容を表にする。選定理由は `architecture.md` を参照する1行にして、二重管理しない

### 4. データモデル・ファイル構造

- `Task` / `GlobalConfig` / `ProjectEntry` / `Routine` / `DailyLog`(`DailyLogEntry`) / `WorkSession` / `TimerState` を、`src/task_cli/models/*.py` の実フィールドで表にする。TypeScript の `interface` は使わず、フィールド名は snake_case(`due_date` / `created_at` / `completed_at` / `scheduled_date` / `work_sessions`)
- `Task.branch` は「移行データから引き継ぐ表示用の欄。Python 版は設定しない」と書く
- 制約(ID の欠番を再利用しない・タイトル 1〜200 文字・ステータス遷移・日付形式)は `Task.can_transition_to` と `validate_date_format` の実挙動に合わせる
- `GlobalConfig` の旧フォーマット(`string[]`)自動マイグレーションの段落は、Python 版の `GlobalConfigStorage.load()` に無いので削除する(TypeScript 版から Python 版への変換は `migrate` コマンドの担当)
- `ProjectConfig`(GitHub 設定)は未実装の節へ移す
- ファイル構造は `~/.task-py/`(`config.yaml` / `inbox/tasks.yaml` / `projects/<name>/tasks.yaml` / `daily/routines.yaml` / `daily/log.yaml` / `timer.yaml`)と、同居する `.bak` / `.lock` / `mcp_calls.jsonl` の実態に合わせる。サンプルは YAML

### 5. コンポーネント設計(クラス・コマンド)

- **CLI レイヤー**: `src/task_cli/cli/`(typer)。コマンド表は `task-py --help` と各 `--help` の実出力に合わせる。`overview`(旧 `onboard` の名前は使わない)・`schedule`・`search`・`migrate`・`reset`・`shell`・`web` を載せ、`list` のオプションは `--all` / `--inbox` / `--all-status` のみ。実在しない `list --priority` / `--sort`、`task config` / `sync` / `import --github` は載せない
- **ユースケース層**: `TaskCrudUseCase`(`usecases/task_crud_usecase.py`)の責務を新たに記述する。対象プロジェクトの解決(`ACTIVE_PROJECT` / `None`=Inbox / 名前)・ステータス変更とタイマーの連動・`guarded()` の排他区間(ロック順 timer.yaml → tasks.yaml)・横断検索・`move`。`TimeTrackingUseCase` も同様に短く
- **サービス**: `TaskManager`(`create_task` / `list_tasks` / `get_task` / `update_task` / `delete_task` / `start_task` / `complete_task` / `archive_task` / `search_tasks` / `append_work_session` / `edit_fields` / `set_scheduled_date` / `next_id`、`TaskFilter`、保存前の検証で `InvalidTaskData`)、`GlobalConfigService`、`ProjectService`、`DailyService`、`TimerService`
- **ストレージ**: `FileStorage` の節は現行(#42 で更新済み)なのでそのまま。`GlobalConfigStorage` / `RoutineStorage` / `DailyLogStorage` / `TimerStorage` / `atomic.py` を短く足す。`ConfigStorage`(プロジェクト設定)は未実装の節へ
- **Renderer**: `src/task_cli/cli/renderer.py` の実関数(`render_task_table` / `render_task_detail` / `render_success` / `render_info` / `render_error`)
- `GitService` / `GitHubService` / `ConfigService` / `ConfigStorage` は、この節から外し、未実装の節へ

### 6. ユースケース図(UC-0〜UC-5)

- UC-0(アクティブプロジェクト解決): 参加者を `GlobalConfigService` → `TaskCrudUseCase.resolve_storage_path` に、パスを `~/.task-py/.../tasks.yaml` に
- UC-1(add) / UC-2 P0(start) / UC-5(delete): 参加者を `CLI → TaskCrudUseCase → TaskManager → FileStorage` に。start の「Inbox での Git 案内メッセージ」は実装に無いので削る。start の説明に、解禁日前は開始できない(`schedule`)ことと、タイマーの連動を足す(実装を確認して書く)
- UC-2 P1(Git ブランチ作成)・UC-3(done --pr)・UC-4(sync): 未実装の節へ移す

### 7. UI 設計

- コマンド名を `task-py` にする
- `list` の表は `ID / Status / Title` の3列(実装どおり)。P1 の追加列(Priority / Branch / Due)は未実装なので載せない。優先度・期限・ブランチは `show` の詳細パネルに出る旨を書く
- 色分けは `renderer.py` の `_STATUS_STYLES` / `_PRIORITY_STYLES` に合わせる(期限の色分けは実装を確認し、無ければ削る)
- `project list` は PR #54 で rich の Table(`*` マーカー・名前は折り返し・Inbox を最終行)になった。現状の表示に合わせ、区切り線 `─` の図を直す

### 8. エラーハンドリング

- `AppError(message, cause, remedy)` と派生(`NotFoundError` / `StateConflictError` / `InvalidTaskData`)を Python で記述
- 表示は `render_error` の実フォーマット(`[Error] ...` / `  原因:` / `  対処:`)
- エラー種別表から Git・GitHub・ネットワーク・Inbox の Git 案内の行を外す(未実装の節へ)
- 「ファイル読み込み失敗」「書き込み失敗」の行は、実装(存在しない→空、`write_atomic` が失敗しても本体は無変更)の事実だけを書く。実装に無いメッセージ文言は書かない

### 9. パフォーマンス・セキュリティ・テスト戦略

- パフォーマンス: JSON → YAML、`Array.prototype.filter` → リスト内包表記(`TaskManager.search_tasks`)、GitHub API のタイムアウトの行は削除。排他・fsync・バックアップの行は現行のまま
- セキュリティ: `~/.task-py/` の `chmod 0o700`(各ストレージの `ensure_directory`)・ロックファイル 0o600 に直す。P1 の3項目(設定ファイルのパーミッション・`.taskcli-current`・コマンドインジェクション防止)は未実装の節へ。Web の面(127.0.0.1・CSRF・Host 検証)は Web GUI 節への参照を1行
- テスト戦略: pytest・`tests/` の実在するファイル名・観点に合わせる(`src/**/*.test.ts` や `GitService` のユニットテスト・Git E2E は削る)

### 10. 未実装の設計(Git・GitHub 連携 P1)— 新設

冒頭に「**Python 版には未実装**。`product-requirements.md` の P1 要求に対する設計案として残す。TypeScript 版(`~/.task/`)時代に書かれた設計で、実装時は Python 版の層構造(`docs/architecture.md`)とストレージ(YAML)に合わせて読み替える」と明記する。内容:

| 小節 | 元の内容 | 書き方 |
|---|---|---|
| サブコマンド(P1) | `start`(ブランチ作成)・`done --pr`・`config setup/set`・`sync`・`import --github` | 表 |
| ブランチ連携 | 命名規則(`feature/task-<id>-<slug>`)・スラッグ変換・最大長・変換例の表 | 文章と表。コードブロックなし |
| コミットフック | `prepare-commit-msg` の動作・`.taskcli-current` のライフサイクル | 仕様を文章で。シェルスクリプトの断片は言語非依存なので残してよい |
| GitHub 連携 | PR 本文テンプレート・同期結果(新規/更新/反映の件数)・Issue インポート | 文章と表 |
| プロジェクト設定 | `ProjectConfig`(token / owner / repo / default branch)と設定値の検証表・パーミッション 600 | 表。保存先は将来 `~/.task-py/projects/<name>/config.yaml`(`architecture.md` の記述と一致) |
| ユースケース | UC-2 P1 / UC-3 / UC-4 の sequenceDiagram | Mermaid(言語非依存)。参加者名は設計上の名前(`GitService` 等)のまま、注記を付ける |
| エラー | Git/GitHub/ネットワークのエラー行・Inbox の案内 | 表 |
| 安全上の考慮 | コマンドインジェクション防止・トークンの扱い・`.gitignore` 追記 | 箇条書き。「ライブラリの API を使いシェル文字列を結合しない」と言語非依存に書く |
| テスト観点 | ブランチ名変換・Git 有無の E2E・PR 作成 | 箇条書き |

## データフロー

該当なし(文書の変更)。実装は次の順で進める。

1. 検査テストを先に書き、現状の文書で失敗することを確認する
2. 実装済みの節を上から現行化する(節ごとに、実コードを読んで事実を確かめてから書く)
3. 未実装の節を新設し、元の設計を移す(元の文面を先に別ファイルへ退避し、移し漏れが無いことを照合する)
4. 検査テストが通ることを確認する

## エラーハンドリング戦略

該当なし。

## テスト戦略

### ユニットテスト

`tests/procedures/test_functional_design_currency.py`(新規)。`docs/functional-design.md` を読み、次を検査する:

- ` ```typescript ` のコードブロックが無い
- `.ts` の実装パス(`src/**/*.ts`)・`Commander.js` / `Vitest` / `Array.prototype` / `AbortController` / `simple-git` が、「未実装の設計」節の**外**に無い
- `~/.task/` が、`migrate` を説明する行以外に無い
- `tasks.json` / `config.json` / `routines.json` / `log.json` が無い
- 文書内の `src/...` で始まるバッククォート付きパス(`src/task_cli/...py` / `src/task_mcp/...` / `src/task_web/...`、ディレクトリを含む)が実在する
- コマンド表: `task-py` の実在するトップレベルコマンドがすべて文書に現れる(typer の `app.registered_commands` / `registered_groups` から取る)
- 「未実装の設計」節が存在し、冒頭に「未実装」の明記がある

**検証の原則**: 追加テストは変更前の文書で失敗することを確認してから文書を変える。

### 統合テスト

- `uv run python3 scripts/local_quality_gate.py --steering 20261114-modernize-functional-design`
- 4段検証の段4で `doc-reviewer`(永続ドキュメントを更新するため)

## 依存ライブラリ

なし。

## ディレクトリ構造

```
docs/functional-design.md                                   (現行化・節の追加)
tests/procedures/test_functional_design_currency.py         (新規)
.steering/20261114-modernize-functional-design/             (本作業)
```

## 実装の順序

上記「データフロー」のとおり。

## セキュリティ考慮事項

- 文書に実際のトークン・個人情報を書かない(サンプルは架空の値)

## パフォーマンス考慮事項

- 検査テストは1ファイルの読み込みと正規表現のみ。ミリ秒で終わる

## 将来の拡張性

- 他の永続ドキュメント(PRD の `~/.task/` と Git・GitHub 連携の記述など)にも同種の検査を広げられる。必要になったら別 Issue で扱う
- Git・GitHub 連携を実装する、または廃止すると決めたとき、「未実装の設計」節を実装済みの節へ移す、または削除すれば足りる

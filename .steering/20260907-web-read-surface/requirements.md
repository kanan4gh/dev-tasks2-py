# 要求内容

## 概要

ローカル Web GUI の**サーバの土台と読み取り面**を作る。`src/task_web/` を3つ目のパッケージとして新設し、`task-py web` でブラウザから一覧・詳細・検索・状況要約を見られるようにする。書き込みは行わない。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/46
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [ ] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [ ] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: **満たさない**。`task_cli` / `task_mcp` に並ぶ3つ目の入口パッケージ `task_web` を新設する。HTTP サーバ・SSE・vendoring した JavaScript という、これまでリポジトリに存在しなかった種類の成果物が入る。`starlette` と `uvicorn` は `mcp[cli]` 経由で**既にインストール済み**なので追加インストールは発生しないが、直接使う以上 `pyproject.toml` への**明示宣言を増やす**。
- 基準2: **満たさない**。新規12・変更5の計17ファイル（テスト除く。うち3つは vendoring した JavaScript）。
- 基準3: **満たさない**。`docs/product-requirements.md`（スコープと機能一覧に GUI を追加）/ `docs/functional-design.md`（画面と API の定義）/ `docs/architecture.md`（入口が3つになる。プロセス構成）/ `docs/repository-structure.md`（新パッケージ）/ `docs/glossary.md`（新用語）。**文書への記述そのものが変更の実体**であり記録例外に該当しない。
- 基準4: **満たす**。既存の CLI・MCP・YAML はいずれも変更しない。追加は `task-py web` サブコマンドと `task-web` エントリポイントのみ。`TaskCrudUseCase.search_all_projects()` と `GlobalConfigService.config_path` は新規追加であり既存シグネチャを変えない。

4項目すべてにチェックが付かないため**通常パス**。

## G3 受け入れの要否

**不要**。`.claude/skills/` `.claude/agents/` `.claude/commands/` の frontmatter・ファイル名・配置、`.claude/settings.json` の権限、`.claude/hooks/` の定義・登録のいずれも変更しない。製品コードと `docs/` のみの変更。

## 背景

2026-09-05 に GUI の追加と形態（ローカル Web）を決定し、形態非依存の土台を #38（v0.9.0）と #42（v0.10.0）で解消した。本作業は GUI 本体の第一段である。

GUI を作る理由は2つとも形態非依存に確定している:

1. **GTD の「整理」「見直し」が CLI / MCP のどちらでも埋まっていない**。一覧を眺めながら仕分ける操作は、1行ずつコマンドを打つ形と相性が悪い
2. **タイマー併走が CLI に構造的に不可能**（`time.py` の `sleep` + `rich.Live` が端末を占有する）

本作業はこのうち1つ目の**土台（見る面）**までを作る。仕分ける操作（書き込み）は作業単位C、タイマー併走は作業単位D に分ける。

## ユースケースの軸

**利用者が `task-py web` を実行してブラウザを開くと、全プロジェクトのタスクを一画面で見渡し、詳細を開き、検索でき、CLI や MCP が別プロセスで加えた変更が数秒以内に画面へ反映される。**

## 実装対象の機能

### 1. サーバの土台（`src/task_web/`）

- `task_cli` / `task_mcp` に並ぶ3つ目の入口パッケージ。`usecases/` と `services/` を呼び、`storage/` には直接触らない
- **starlette + uvicorn**。`pyproject.toml` に明示宣言する。FastAPI と Jinja2 は導入しない
- 起動は `task-py web`（`task-web` も同義のエントリポイントとして用意する）
- **127.0.0.1 の IPv4 にのみバインド**する。既定ポートは 8765
- **`TrustedHostMiddleware` で `Host` ヘッダを検証する**（DNS リバインディング対策）

### 2. 画面の土台

- React / react-dom の UMD ビルドと htm を `src/task_web/static/vendor/` に **vendoring** する
- **ビルド工程を持ち込まない**。node / npm を使わず、JSX の代わりに htm のタグ付きテンプレートリテラルを使う。自前のコードは素の ES モジュールとして書く
- CDN からの実行時読み込みはしない

### 3. 読み取りの JSON API

| エンドポイント | 対応する CLI |
|---|---|
| `GET /api/state` | — （アクティブプロジェクト・プロジェクト一覧・リビジョン） |
| `GET /api/overview` | `overview` |
| `GET /api/tasks` | `list --all`（全プロジェクト横断） |
| `GET /api/inbox/tasks` | `list --inbox` |
| `GET /api/projects/{name}/tasks` | `list` |
| `GET /api/inbox/tasks/{id}` | `show`（Inbox） |
| `GET /api/projects/{name}/tasks/{id}` | `show` |
| `GET /api/search?q=` | `search`（全プロジェクト横断に拡張） |
| `GET /api/events` | — （SSE。他プロセスの変更通知） |

### 4. 他プロセスの変更の反映

`~/.task-py/` 配下の YAML の mtime とサイズからリビジョン値を計算し、変わったら SSE で通知する。クライアントは通知を受けて表示中のものを取り直す。

### 5. 画面

- 全プロジェクト横断の一覧（プロジェクトごとにまとめて表示）
- プロジェクト / Inbox 単位の一覧（ステータス・優先度での絞り込み、並び替え）
- タスク詳細（説明・期限・解禁日・完了日時・合計作業時間・作業セッション）
- 検索
- 状況の要約（`overview` 相当）

## 受け入れ条件

### サーバ

- [ ] `task-py web --help` が動き、`--port` / `--host` / `--no-open` を受け付ける
- [ ] 既定で 127.0.0.1:8765 にバインドし、`http://127.0.0.1:8765/` で画面が返る
- [ ] `Host: evil.example.com` のリクエストが 400 で拒否される
- [ ] `Host: 127.0.0.1:8765` と `Host: localhost:8765` は通る
- [ ] ポートが埋まっているとき、トレースバックではなく原因と対処を示すエラーで終了する
- [ ] `uv build` した wheel に `static/` 配下の `.html` / `.css` / `.js` が含まれる

### API

- [ ] `GET /api/tasks` が全プロジェクトと Inbox のタスクを返し、`GET /api/projects/{name}/tasks` が該当プロジェクトだけを返す
- [ ] タスク詳細に `total_worked_seconds`（`model_dump()` に出ない派生値）が含まれる
- [ ] 存在しないタスク・プロジェクトが 404 と、CLI と同じ原因・対処のメッセージを返す
- [ ] `GET /api/search?q=` が全プロジェクトを横断して返す
- [ ] `status` / `priority` / `sort` のクエリが `TaskFilter` に対応する
- [ ] **読み取り専用である**。`POST` / `PUT` / `DELETE` はいずれのパスでも 405 になる

### 他プロセスの変更の反映

- [ ] 別プロセスの `task-py add` の後、`GET /api/state` のリビジョンが変わる
- [ ] `GET /api/events` が SSE を返し、別プロセスの変更後にイベントが届く
- [ ] `~/.task-py/` が存在しない状態でもサーバが起動し、空の状態を返す

### 画面

- [ ] ブラウザで開いて一覧・詳細・検索・要約が見える（実ブラウザで観察する）
- [ ] 外部ネットワークへのリクエストが発生しない（vendoring の確認）

## 成功指標

- 段2 で実ブラウザを起動して観察し、別プロセスの `task-py add` が画面に反映されるところまで見る
- `uv build` した wheel を展開し、静的ファイルが同梱されていることを確認する

## スコープ外

以下はこのフェーズでは実装しません:

- **すべての書き込み操作**（作業単位C）
- project 管理・daily / routine・タイマー併走ダッシュボード（作業単位D）
- undo / 操作履歴（作業単位C で要否を再判定する）
- 認証・マルチユーザ・リモートアクセス・HTTPS
- `shell` / `migrate` / `reset` / `project use` / `inbox` の GUI 化
- CSRF 対策（書き込みが無いため不要。作業単位C で入れる）
- IPv6 でのアクセス（IPv4 の 127.0.0.1 にのみバインドする）

## 参照ドキュメント

- `docs/product-requirements.md` - プロダクト要求定義書
- `docs/functional-design.md` - 機能設計書
- `docs/architecture.md` - アーキテクチャ設計書
- `docs/repository-structure.md` - リポジトリ構造定義書
- `docs/glossary.md` - ユビキタス言語定義
- `.steering/20260906-explicit-project-and-locking/design.md` - 「作業単位B・Cへの申し送り」

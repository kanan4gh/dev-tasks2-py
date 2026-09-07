# 設計書

## アーキテクチャ概要

`task_web` は `task_cli` / `task_mcp` に並ぶ**3つ目の入口**である。既存の層規則をそのまま適用し、`usecases/` と `services/` を呼び、`storage/` には直接触らない。

```
                       ┌── task_cli/   （端末）
~/.task-py/*.yaml  ←───┼── task_mcp/   （stdio・Claude から）
        ↑              └── task_web/   （HTTP・ブラウザから）  ← 新規
        │                     │
        │                     ├── __main__.py   uvicorn 起動
        │                     ├── server.py     Starlette アプリの組み立て
        │                     ├── api.py        読み取りエンドポイント
        │                     ├── serializers.py  Task 等 → dict
        │                     ├── watcher.py    mtime からリビジョンを作る
        │                     ├── events.py     SSE
        │                     └── static/       vendoring した React + 自前 JS
        │                            │
        └────────────────────────────┘  ブラウザは JSON を取りに来るだけ
```

**貫く原則**: 「サーバは `usecases` の薄いラッパであり、ドメインの判断を持たない」「真実は YAML であり、サーバは状態をメモリに溜めない」。後者により、CLI・MCP がいつ何を書いても、次のリクエストで正しい値が返る。

## コンポーネント設計

### 1. `task_web/server.py`

**責務**: Starlette アプリを組み立てる。ルーティング・ミドルウェア・静的配信の登録だけを行う。

**実装の要点**:

```python
def create_app(allowed_hosts: list[str] | None = None) -> Starlette:
    ...
```

- テストから直接組み立てられるよう、**uvicorn の起動と分離**する（`task_mcp` が `server.py` で `mcp` を組み立て `__main__.py` が起動するのと同じ形）
- `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])`
  - starlette の実装は `headers.get("host", "").split(":")[0]` なので**ポートは自動的に落ちる**。`127.0.0.1:8765` はホスト名 `127.0.0.1` として照合される
  - **IPv6 は対象外**。`[::1]:8765` は上の `split(":")` で `[` になり照合に失敗する。IPv4 の 127.0.0.1 にのみバインドするので到達しない
  - `run()` は**待ち受けたアドレス自体を許可リストへ足す**。足さないと「サーバは起動しているのに全リクエストが 400」という、いちばん分かりにくい壊れ方をする（段3 指摘2）
  - > **段3のコードレビューを受けて変更（2026-09-07）。** 当初は `TestClient` の既定 `base_url` である `testserver` を許可リストに含め、「テストのためだけの分岐を実装に入れないため」と理由づけていた。これは誤り。**本番の許可リストにテスト専用の名前を残すこと自体が、この防御を弱める**（`testserver` を 127.0.0.1 に解決する経路——内部 DNS・検索ドメイン・hosts——があれば、その名前で API に到達できる）。`create_app()` は元から許可リストを引数で受けるので、テスト側が明示的に渡せば済む
- 静的配信は `StaticFiles(directory=..., html=True)` を `/` にマウントする。API は `/api/*` に置くので衝突しない

### 2. `task_web/api.py`

**責務**: HTTP のクエリ・パスを `usecases` の引数へ変換し、戻り値を JSON にする。

**実装の要点**:

- **`AppError` を写すラッパは同期関数のままにする**（段3 指摘5）。`async def` にすると Starlette が非同期エンドポイントとみなしてイベントループ上で直接実行し、YAML の読み込みや `flock` の待ちがループを塞ぐ。塞がれている間は他のリクエストも開いている SSE も止まる
- **読み取りは本当に読み取りだけにする**（段3 指摘1）。`DailyService.list_today()` の既定は「今日のログ」を書き足すため、そのまま呼ぶと画面を開くたびに `daily/log.yaml` へ書き込む（ルーティーンが1件も無いときは毎回）。`ensure=False` を渡す。405 を返すだけでは「読み取り専用」を名乗れない

- **Inbox とプロジェクトを別のパスに分ける**:
  - `/api/inbox/tasks` … Inbox
  - `/api/projects/{name}/tasks` … 名前付きプロジェクト

  クエリ1つ（`?project=`）で両方を表すと、`None`（Inbox）と「未指定」を URL 上で区別できない。しかも `project=inbox` のような予約語方式は、**`inbox` という名前のプロジェクトを作れなくなる**。パスを分ければ `/api/projects/inbox/tasks` と `/api/inbox/tasks` が別物として共存する
- **`project` は常に明示して usecase を呼ぶ**。`ACTIVE_PROJECT`（既定値）は使わない。GUI は全プロジェクトを同時に扱う面であり、プロセス外の共有状態に依存してはいけない（`.steering/20260906-explicit-project-and-locking/design.md` の申し送り）
- `AppError` は `404`（見つからない）または `400` に写し、`{"error": {"message", "cause", "remedy"}}` を返す。**CLI と同じ文面をそのまま使う**（同じ原因に2つの説明を作らない）
- クエリ `status`（繰り返し可）/ `priority` / `sort` を `TaskFilter` に対応させる。未知の値は 400

### 3. `task_web/serializers.py`

**責務**: pydantic モデルを JSON 化し、**永続化されない派生値を足す**。

**実装の要点**:

- `Task.total_worked_seconds` は `@property` なので `model_dump()` に出ない。ここで明示的に足す
- 日時は pydantic v2 既定の ISO 8601 文字列。エイリアス設定は無いのでフィールド名は snake_case のまま
- 一覧では `work_sessions` を落とし、`work_session_count` と `total_worked_seconds` だけを返す（タスク数×セッション数のペイロードを避ける）。詳細では全部返す

### 4. `task_web/watcher.py`

**責務**: 「いま見えているデータが変わったか」を1つの値で表す。

**実装の要点**:

```python
def revision(config_service: GlobalConfigService) -> str:
    """監視対象ファイルの (パス, mtime_ns, サイズ) からダイジェストを作る。"""
```

- 監視対象は `config.yaml` / `inbox/tasks.yaml` / `projects/*/tasks.yaml` / `timer.yaml` / `daily/routines.yaml` / `daily/log.yaml`。**`/api/overview` が返すものはすべて含める**（段3 指摘4。当初はタスク関連だけにしていたが、overview がタイマーとルーティーンも返すため、画面が「変更を監視中」と言いながら古い値を映していた）
- **プロジェクト一覧は毎回 `config.yaml` から取り直す**（新しいプロジェクトが増えても追随する）
- パスは service 経由で取る（`GlobalConfigService.config_path` / `TimerService.timer_path` / `DailyService.log_path` / `routines_path`）。`task_web` から `storage/` へ直接依存しないため
- **差分は作らない。「変わった」とだけ伝える。** クライアントは表示中のものを取り直す。差分同期は状態を2箇所に持つことになり、真実が YAML であるという原則を壊す
- `~/.task-py/` が無い場合は空のダイジェストを返す（初回起動でも落ちない）
- 内容のハッシュではなく mtime とサイズを使う。全ファイルを読む必要がなく、単一利用者の更新頻度では取りこぼしが問題にならない

### 5. `task_web/events.py`

**責務**: リビジョンが変わったことを SSE で流す。

**実装の要点**:

- `sse_starlette.EventSourceResponse` を使う（`mcp[cli]` 経由で導入済み）
- サーバ側で1秒ごとにリビジョンを計算し、前回と違えば送る。同じなら送らない
- 接続直後に現在のリビジョンを1度送る（クライアントが取り逃さないため）
- クライアントの切断は `asyncio.CancelledError` で抜ける

### 6. 静的ファイル（`task_web/static/`）

```
static/
├── index.html          … <script src> で vendor を読み、type="module" で自前コードを読む
├── app.css
├── vendor/
│   ├── react.production.min.js        （UMD・約 11KB）
│   ├── react-dom.production.min.js    （UMD・約 129KB）
│   └── htm.umd.js                     （約 1.4KB）
└── js/
    ├── main.js         … エントリ。ルーティングと状態
    ├── api.js          … fetch のラッパ
    └── ui.js           … 描画するコンポーネント群
```

- vendor は **UMD なのでグローバル**（`window.React` / `window.ReactDOM` / `window.htm`）に載る。自前コードは `type="module"` の ES モジュールでそれを参照する。バンドラもトランスパイラも要らない
- JSX の代わりに ``html`<Task ...親 />` `` の形（`htm.bind(React.createElement)`）
- vendoring するファイルは `# vendored from unpkg.com/<pkg>@<version>` を記した `static/vendor/README.md` を添えて由来を残す

### 7. 既存コードへの追加（いずれも読み取り・追加のみ）

| 変更 | 内容 | 理由 |
|---|---|---|
| `TaskCrudUseCase.search_all_projects(keyword)` | `list_all_projects` と同型の `dict[str \| None, list[Task]]` を返す | `TaskManager.search_tasks` はプロジェクト単位で、横断検索が無い。web 層でループを書くと `list_all_projects` の走査を二重に持つことになる。usecase に置けば将来 CLI の `search --all` も同じものを使える |
| `GlobalConfigService.config_path` | `config.yaml` のパスを返す property | `watcher` が監視対象を組み立てるのに要る。web → storage の直接依存を作らないため、service 経由で取る |
| `cli/commands/web.py` + `main.py` への登録 | `task-py web` | 既存の単発コマンドと同じ `app.command()` 形式 |
| `pyproject.toml` | `packages` に `src/task_web`、`scripts` に `task-web`、依存に `starlette` / `uvicorn`、pytest の `filterwarnings` | 下記参照 |

## データフロー

### ブラウザが全タスクを表示する
```
1. GET /             → static/index.html（+ vendor + js）
2. GET /api/state    → {active_project, projects, revision}
3. GET /api/tasks    → {"inbox": [...], "projects": {"foo": [...], ...}}
4. GET /api/events   → SSE 接続（開いたまま）
```

### 別プロセスが task-py add した
```
1. CLI が ~/.task-py/inbox/tasks.yaml を書き換える（アトミック置換）
2. サーバの SSE ループが1秒後にリビジョンの変化を検出
3. event: changed / data: {"revision": "..."} を送る
4. ブラウザが /api/tasks を取り直して再描画
```

## この「動く状態」の生存中に起こりうる操作

> Issue #38 / #42 の教訓（「動く状態」を足すと周囲のイベントとの取り合いを全部決めなければならない）に従って列挙する。本作業が導入する「動く状態」は**開いたままのブラウザのタブ**と**SSE の接続**である。

| その間に起こりうること | 決定 |
|---|---|
| CLI / MCP がタスクを追加・変更・削除する | サーバは状態を持たないので、次のリクエストで正しい値が返る。SSE で「変わった」を通知し、クライアントが取り直す |
| CLI が `project use` でアクティブプロジェクトを切り替える | **画面は影響を受けない**。API は常に `project` を明示して usecase を呼ぶ。`/api/state` の `active_project` は表示のためだけに使う |
| CLI が `project rename` する | 旧名のパスは 404 になる。SSE でリビジョンが変わるのでクライアントは一覧を取り直し、旧名は消える |
| CLI が `project remove` する | 同上 |
| タスクが `move` されて ID が振り直される | 詳細を開いたままだと 404 になる。SSE で取り直したときに消える |
| ブラウザのタブを複数開く | サーバは状態を持たないので何本でもよい。SSE は接続ごとに独立したループ |
| 画面を続けて切り替える（プロジェクト A → B） | 取得に世代番号を付け、遅れて返った古い応答を捨てる。捨てないと「読み込み中…」から復帰しなくなる（段3 指摘3） |
| 初回取得の最中に SSE がリビジョンを送ってくる | 捨てずに預け、取得完了後に反映する。捨てると、取得結果のほうが古いのに「最新」として居座る（段3 指摘7） |
| 静的ファイルが更新される（利用者が task-py を更新する） | `Cache-Control: no-cache` を付けて毎回 ETag で検証させる。付けないとブラウザが古い JavaScript を実行し続ける（段2 で実際に踏んだ） |
| ブラウザを閉じずにスリープする | SSE が切れたらブラウザが自動再接続する（EventSource の既定動作）。再接続時に現在のリビジョンを1度送るので取りこぼさない |
| `~/.task-py/` がまだ存在しない | `revision()` は空を返し、API は空の一覧を返す。起動は成功する |
| サーバ起動中にポートが埋まる | `AppError` にして原因と対処（`--port` を渡す）を出す。自動で空きポートを探さない（利用者がブックマークした URL が変わると困る） |
| 書き込みリクエストが来る | ルーティングに `GET` しか登録しないので 405。**読み取り専用であることをルーティングで担保する** |

## エラーハンドリング戦略

新しいエラークラスは作らない。

- ドメインのエラーは既存の `AppError` をそのまま HTTP に写す。`{"error": {"message", "cause", "remedy"}}`
- 「見つからない」は 404、クエリの不正は 400、それ以外の想定外は 500 で本文を出さない
- CLI 起動時のエラー（ポート衝突等）は `AppError` にして `render_error` で表示する

## テスト戦略

### ユニットテスト

**新規 `tests/test_web_api.py`**（`TestClient` によるインプロセス）
- `/api/state` / `/api/tasks` / `/api/inbox/tasks` / `/api/projects/{name}/tasks` の形
- 詳細に `total_worked_seconds` が入る
- 存在しないタスク・プロジェクトが 404 と原因・対処を返す
- `?status=` `?priority=` `?sort=` が効く。未知の値は 400
- `POST` / `PUT` / `DELETE` が 405
- **アクティブプロジェクトが `bar` でも `/api/projects/foo/tasks` は `foo` を返す**（プロセス外の状態に依存しないことの証明）
- `Host: evil.example.com` が 400、`127.0.0.1` と `localhost` は 200
- `inbox` という名前のプロジェクトと Inbox が共存する

**新規 `tests/test_web_watcher.py`**
- ファイルを書き換えるとリビジョンが変わる
- 何もしなければ変わらない
- 新しいプロジェクトが増えると監視対象に入る
- `~/.task-py/` が無くても落ちない

### 統合テスト

**新規 `tests/test_web_server.py`**
- `subprocess` で `python -m task_web` を実際に起動し、`http.client` で `/` と `/api/state` を叩いて外形疎通を見る（`tests/test_mcp_server.py::test_stdio_process_initialize` と同じ二段構え）
- SSE: 起動したサーバに接続し、別プロセスでタスクを足して、イベントが届くのを観測する

### テスト環境の注意

- `TestClient` の既定 `base_url` は `http://testserver`。`TrustedHostMiddleware` の許可リストに `testserver` を入れて通す
- starlette 1.x は `starlette.testclient` に `httpx2` を推奨しており、`httpx` だと `StarletteDeprecationWarning` が出る。**新しい依存を足さず**、`pyproject.toml` の pytest 設定で当該警告だけを無視する（理由をコメントで残す）
- `~/.task-py/` の隔離は既存と同じく `monkeypatch.setenv("HOME", str(tmp_path))`

## 依存ライブラリ

**追加インストールはゼロ。** `starlette` と `uvicorn` は `mcp[cli]` が transitive で入れており、`sse-starlette` も同様。ただし直接使うので `pyproject.toml` の `dependencies` に**明示宣言**する（transitive に頼ると、上流が依存を落としたときに黙って壊れる）。

```toml
dependencies = [
    "typer", "pydantic", "pyyaml", "rich", "prompt-toolkit", "mcp[cli]",
    "starlette",      # 追加（既にインストール済み）
    "uvicorn",        # 追加（既にインストール済み）
    "sse-starlette",  # 追加（既にインストール済み）
]
```

vendoring する JavaScript（React 18.3.1 / react-dom 18.3.1 / htm 3.1.1、計 約144KB）は Python の依存ではなくリポジトリ内の成果物として扱う。

## ディレクトリ構造

```
src/task_web/                        ← 新規パッケージ
├── __init__.py
├── __main__.py
├── server.py
├── api.py
├── serializers.py
├── watcher.py
├── events.py
└── static/
    ├── index.html
    ├── app.css
    ├── vendor/{react,react-dom,htm}.js + README.md
    └── js/{main,api,ui}.js

src/task_cli/
├── cli/commands/web.py              ← 新規
├── cli/main.py                      ← 変更（登録）
├── usecases/task_crud_usecase.py    ← 変更（search_all_projects）
└── services/global_config_service.py ← 変更（config_path）

tests/
├── test_web_api.py                  ← 新規
├── test_web_watcher.py              ← 新規
└── test_web_server.py               ← 新規

pyproject.toml                       ← 変更
```

## 実装の順序

1. **`pyproject.toml`** と `task_web` の骨組み（`__init__` / `server.create_app()` / `__main__`）。空のアプリが起動するところまで
2. **`watcher.py`** と `serializers.py`（他に依存しない。単体でテストできる）
3. **`api.py`** の読み取りエンドポイントと `tests/test_web_api.py`
4. **`events.py`**（SSE）
5. **`cli/commands/web.py`** と `main.py` への登録
6. **静的ファイル**（vendoring → `index.html` → JS）
7. **統合テスト**（subprocess で起動）

## セキュリティ考慮事項

- **DNS リバインディング**: 127.0.0.1 にバインドしても、利用者が開いた別のサイトが自分のドメインを 127.0.0.1 に解決させればローカルサーバに到達しうる。`TrustedHostMiddleware` で `Host` を検証して塞ぐ
- **CORS は設定しない**。ブラウザの既定（同一オリジンのみ）に任せる。`Access-Control-Allow-Origin` を出さないので、別オリジンのページは応答を読めない
- **書き込み経路が無い**ため CSRF 対策は不要。作業単位C で書き込みを入れるときに必要になる（`Origin` 検証かトークン）
- **外部通信をしない**。vendoring により、起動しても画面を開いても外へ出ていかない。`--version` の更新確認（`api.github.com`）とは別経路であり、web サーバからは呼ばない
- 待ち受けは IPv4 の 127.0.0.1 のみ。`0.0.0.0` を既定にしない

## パフォーマンス考慮事項

- 一覧 API は `list_all_projects()` を呼ぶのでプロジェクト数ぶんのファイル読み込みが発生する。単一利用者の規模（数〜数十プロジェクト）では問題にならない
- SSE のポーリングは 1 秒間隔で、mtime と size の `stat` のみ。ファイルの内容は読まない
- 一覧のペイロードから `work_sessions` を落とす（タスク数 × セッション数の増え方を避ける）

## 将来の拡張性

- **作業単位C（書き込み面）**: ルーティングに `POST` / `PATCH` / `DELETE` を足す。そのとき `Origin` 検証を同時に入れる。usecase 側は #42 で `project` を明示できるようになっているので、そのまま呼べる
- **作業単位D（タイマー併走）**: `events.py` の仕組みに「タイマーの残り時間」を乗せる。残り時間は `started_at` からの導出なので、サーバがカウントダウンを持つ必要はない（#38 の設計がそのまま効く）
- `serializers.py` を分けてあるので、API の表現を変えたいときの変更点が1箇所に閉じる

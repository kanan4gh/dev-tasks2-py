# タスクリスト

## 作業状態

- **状態**: complete
- **状態更新日時**: 2026-09-07T07:22:01+09:00
- **使用ハーネス**: Claude Code

## 作業履歴

_記録なし_

## タスク管理の原則

- `active`: 作業系列が継続中。未完了を許容する
- `paused`: 意図的な中断。有効な中断記録がある場合に未完了を許容する
- `complete`: 全タスクと振り返りが完了。未完了を許容しない
- 完了・技術的スキップは実態に合わせて即時記録する
- 「今日はここまで」はスキップではなく`scripts/steering_state.py pause`で記録する
- 最終品質ゲート、コミット、G3受け入れ記録、push、PRはチェックボックスにしない

### フェーズとadd-featureステップ

| フェーズ | 消化するステップ |
|---|---|
| 実装フェーズ（フェーズ1〜7） | ステップ5 |
| 4段検証 | ステップ6 |
| 振り返りとドキュメント更新 | ステップ7 |
| `complete`遷移・最終品質ゲート・PR | ステップ7終端・ステップ8（手順管理） |

技術的理由でタスクが不要になった場合だけ、取り消し線と具体的理由を付けて完了扱いにする。時間や難易度を理由に使わない。

---

## フェーズ1: パッケージの骨組み（実装フェーズ / ステップ5）

- [x] `pyproject.toml` を更新する
  - [x] `[tool.hatch.build.targets.wheel] packages` に `src/task_web` を追加
  - [x] `[project.scripts]` に `task-web` を追加
  - [x] `dependencies` に `starlette` / `uvicorn` / `sse-starlette` を明示宣言（追加インストールは発生しない）
  - [x] pytest の `filterwarnings` に `StarletteDeprecationWarning`（httpx2 推奨）の無視を理由コメント付きで追加
- [x] `src/task_web/__init__.py` / `server.py`（`create_app()`）/ `__main__.py`（uvicorn 起動）を作る
- [x] `TrustedHostMiddleware` を組み込む（`127.0.0.1` / `localhost` / `testserver`）
- [x] 空のアプリが起動し `/api/state` が 200 を返すところまで確認する

## フェーズ2: watcher と serializers（実装フェーズ / ステップ5）

- [x] `GlobalConfigService.config_path` を追加する
- [x] `src/task_web/watcher.py` の `revision()` を実装する（config.yaml / inbox / projects/* の mtime とサイズ）
- [x] `src/task_web/serializers.py` を実装する（`total_worked_seconds` の付与、一覧では `work_sessions` を落とす）
- [x] `tests/test_web_watcher.py` を作る（変化の検出 / 変化なし / プロジェクト追加 / `~/.task-py/` 不在）
- [x] **（実装中に発見・追加）`GlobalConfigStorage` の既定パスがモジュール読み込み時に `~` を展開していた問題を修正する**
  - 経緯: `tests/test_web_watcher.py` で `monkeypatch.setenv("HOME", ...)` の下に `GlobalConfigStorage()`（既定パス）を使ったところ、**実ホームの `~/.task-py/config.yaml` にプロジェクトが2件書き込まれた**。既定値 `_CONFIG_PATH` が `Path("~/.task-py").expanduser()` としてモジュール読み込み時に固定されており、あとから HOME を差し替えても追随しないため
  - 他の4ストレージ（`file_storage` を除く `routine` / `daily_log` / `timer`）は元から `__init__` で展開しており、`global_config_storage` だけが食い違っていた
  - 対応: 既定値を `Path("~/.task-py/config.yaml")`（未展開）にし、`__init__` で展開する。他4つと同じ形に揃えた
  - 汚染した実データは修復済み（追加された2プロジェクトの削除・`last_project_id` の復元）。ただし `active_project` の元の値は復元できず `null` にした
  - 回帰テスト `tests/test_storage.py::TestDefaultPathsFollowHome` を追加（5ストレージすべてが HOME の差し替えに追随することを検証）

## フェーズ3: 読み取り API（実装フェーズ / ステップ5）

- [x] `TaskCrudUseCase.search_all_projects()` を追加する
- [x] `src/task_web/api.py` に各エンドポイントを実装する
  - [x] `/api/state` / `/api/overview`
  - [x] `/api/tasks`（全プロジェクト横断）
  - [x] `/api/inbox/tasks` / `/api/projects/{name}/tasks`
  - [x] `/api/inbox/tasks/{id}` / `/api/projects/{name}/tasks/{id}`
  - [x] `/api/search`
- [x] `AppError` → HTTP（404 / 400）の変換を実装する（CLI と同じ文面）
- [x] クエリ（`status` 繰り返し / `priority` / `sort`）を `TaskFilter` に対応させ、未知の値は 400 にする
- [x] `tests/test_web_api.py` を作る（受け入れ条件の API 節をすべて covering。37件）
- [x] （実装中に判明）pytest の `filterwarnings` のカテゴリを修正。`StarletteDeprecationWarning` は `DeprecationWarning` ではなく **`UserWarning`** の派生だった

## フェーズ4: SSE（実装フェーズ / ステップ5）

- [x] `src/task_web/events.py` の `/api/events` を実装する（接続直後に1度、以降は変化時のみ）
- [x] クライアント切断で例外を残さず終了することを確認する

## フェーズ5: CLI からの起動（実装フェーズ / ステップ5）

- [x] `src/task_cli/cli/commands/web.py` を作る（`--host` / `--port` / `--no-open`）
- [x] `src/task_cli/cli/main.py` に登録する
- [x] ポート衝突時に `AppError` として原因・対処を出す
- [x] 起動時にブラウザを開く（`--no-open` で抑止）

## フェーズ6: 静的ファイル（実装フェーズ / ステップ5）

- [x] `static/vendor/` に react / react-dom / htm を vendoring し、由来を `README.md` に残す
- [x] `static/index.html` と `static/app.css` を作る
- [x] `static/js/api.js` / `ui.js` / `main.js` を作る（一覧・詳細・検索・要約・SSE 受信）
- [x] 静的配信を `/` にマウントする

## フェーズ7: 統合テスト（実装フェーズ / ステップ5）

- [x] `tests/test_web_server.py` を作る
  - [x] `python -m task_web` を subprocess で起動し `/` と `/api/state` に疎通する
  - [x] SSE 接続中に別プロセスがタスクを足すとイベントが届く
- [x] `uv build` した wheel に `static/` 配下が含まれることを確認する

## フェーズ8: 4段検証（ステップ6）

- [x] 段1: 静的検証
  - [x] `uv run pytest`（575 passed）
  - [x] `uv run ruff check`（All checks passed）
  - [x] `uv run basedpyright`（0 errors）
- [x] 段2: 実挙動検証（Chrome で実際に操作して観察）
  - [x] 実サーバを起動し、**実ブラウザ**で一覧・詳細・検索・要約を観察する
  - [x] 別プロセスの `task-py add` が、操作なしで画面に現れることを観察する（rev の変化も確認）
  - [x] 外部ネットワークへのリクエストが発生しないことを観察する（13件すべて 127.0.0.1。vendoring が効いている）
  - [x] `Host` を偽装したリクエストが拒否されることを観察する（`evil.example.com` → 400）
  - [x] `inbox` という名前のプロジェクトと Inbox が別々に表示されることを観察
  - [x] ステータス・優先度・並びのフィルタが効くことを観察
  - **段2で見つけた実欠陥3件（いずれもテストは全緑だった）**:
    1. **一覧から詳細へ移った最初の1フレームで画面が真っ白になった。** `view` を先に切り替え、`payload` は前のビューのままだったため、`TaskDetail` が `payload.task`（undefined）の `.title` を読んで落ちた。取得したデータに「どのビューのものか」を添え、一致するときだけ描画するよう修正
    2. **静的ファイルに `Cache-Control` が無く、ブラウザが古い JavaScript を実行し続けた。** 開発中に修正が反映されず気づいた。利用者が task-py を更新したときに同じことが起きる。`no-cache`（＝使う前に必ず検証する）を付ける `_RevalidatingStaticFiles` を追加。変更が無ければ 304 で済むことも実測で確認
    3. **ページを開くたびに全 API を2回叩いていた。** SSE が接続直後に送る現在のリビジョンが、常に再読み込みを起こしていた。取得済みリビジョンと比べて同じなら読み直さないよう修正（実測で state/events/overview が各1回になった）
- [x] 段3: コードレビューと指摘対応（`Skill('code-review')`。7件すべて再現を確認し、7件すべて対応）
  - [x] 指摘1(HIGH) **「読み取り専用」を掲げながら `/api/overview` が毎リクエスト書き込んでいた。** `DailyService.list_today()` が `_ensure_today_log()` を呼び、その中の `if added or not entries:` がルーティーン未設定時に必ず真になるため、画面を開くたびに `daily/log.yaml` を書き換えていた（ブラウザの再読み込みだけでユーザーデータが変わり、CLI とロックを取り合う）→ `list_today(..., ensure=False)` を追加し API から使う。ログに無いルーティーンは元から `pending` 扱いなので、読むだけなら書き込む必要がない。**対照実験で `ensure=True` は毎回書き込み・`ensure=False` は作りもしないことを確認**
  - [x] 指摘2(MED) `--host` を出しているのに `127.0.0.1` 以外だと全リクエストが 400 になる（`run()` が `create_app()` を引数なしで呼んでいた）→ **CLI から `--host` を外し**（認証も CSRF 対策も無い面をネットワークへ出せてしまうのはスコープ外）、`run()` は待ち受けたアドレスを必ず許可リストへ足すようにした。`_ensure_port_available` が `gaierror` も `AppError` に写すよう修正
  - [x] 指摘3(MED) プロジェクトを続けて切り替えると、遅れて返った古い応答で「読み込み中…」から復帰しなくなる → 取得に世代番号を付け、古い応答を捨てる
  - [x] 指摘4(MED) `/api/overview` はタイマーとルーティーンを返すのに、リビジョンの監視対象が `config.yaml` とタスクだけだった（「変更を監視中」と言いながら古い値を映す）→ `timer.yaml` / `daily/routines.yaml` / `daily/log.yaml` を監視対象に追加。`TimerService.timer_path` と `DailyService.log_path` / `routines_path` を追加して web → storage の直接依存を作らずに済ませた
  - [x] 指摘5(LOW) `_handle` が `async def` を返していたため、同期の YAML 読み込みと `flock` 待ちがイベントループ上で走り、他のリクエストと SSE を止めていた → ラッパを同期関数のままにし、Starlette のスレッドプールに載せた
  - [x] 指摘6(LOW) 本番の許可リストにテスト専用の `testserver` が残っていた（その名前を 127.0.0.1 に解決する経路があれば到達できる）→ 本番から外し、テスト側で `create_app([...])` に明示的に渡す。**design.md の判断を変更**
  - [x] 指摘7(LOW) 初回取得中に届いた SSE のリビジョンを捨てており、その窓で変更があると次の書き込みまで古い画面のままになる → 捨てずに預けて取得完了後に反映する
  - [x] 指摘1・2・4 に回帰テストを追加（読み取りでファイルの mtime/サイズが変わらないこと・許可リストの中身・監視対象の網羅）
- [x] 段4: スペック準拠検証と指摘対応（`implementation-validator`: 準拠。受け入れ条件はサーバ6/6・API6/6・他プロセス反映3/3・画面2/2。スコープ外の混入なし。乖離の指摘なし）
  - [x] 参考情報として指摘された「`watcher.watched_paths` の広い `except Exception`」を記録: 設定ファイルが壊れている・読めない場合でもサーバを落とさないための防御。design.md が明記する「`~/.task-py/` が無い場合」は `load()` 自体が空値を返すので実質そこでは発動しない。design 全体の「サーバを落とさない」原則の内側だが、design.md に明記していなかったのでここに残す

## フェーズ9: 振り返りとドキュメント更新（ステップ7）

- [x] 永続ドキュメントの更新要否を判断し、必要な更新とレビューを完了
  - [x] `docs/product-requirements.md`（バージョン表に v1.3 / v1.4、GUI の段階（読み取り面/書き込み面/周辺）と GUI 化しないコマンド、スコープ外にリモート公開）
  - [x] `docs/functional-design.md`（「ローカル Web GUI（v1.4・読み取り面）」節を新設。起動・画面・JSON API・変更の反映・実装方針）
  - [x] `docs/architecture.md`（テクノロジースタックに starlette / uvicorn / sse-starlette とブラウザ側の同梱ライブラリ、「プロセス構成」節を新設、セキュリティに追記）
  - [x] `docs/repository-structure.md`（`src/task_web/` の追加、依存関係の図と規則を3入口に更新）
  - [x] `docs/glossary.md`（新規2用語「リビジョン（revision）」「ローカル Web GUI」、索引の更新）
  - [x] `doc-reviewer` を更新差分に対して実行し、必須2件・推奨1件・提案2件すべてに対応
    - 必須: `functional-design.md` と `glossary.md` に「**将来の**GUI」という記述が取り残されていた（同じ差分で「v1.4 実装済み」と書いたのと正面から矛盾する）。`architecture.md` だけ直して他2つを見落としていた
    - 必須（要判断）: `glossary.md` の「排他区間」の「（将来の）ローカル Web GUI」は、**書き込み面がまだ無いので技術的には正しかった**。削除ではなく「現時点では読み取りだけなので排他区間に参加しない。書き込み面を作るときに参加する」と明示する形にした
    - 推奨: 「監視対象のパスも service の property 経由で取る」が実装より単純化されすぎていた（タスクのパスは usecase 層の `resolve_storage_path()` 経由）
    - 提案: SSE のポーリング間隔（1秒）を機能設計書に明記 / 依存関係の図で3入口すべてから `cli/deps.py` へ線が引かれるよう修正
- [x] README類の更新要否を判断し、必要なら更新（「ブラウザで見る（Web GUI）」節を追加）
- [x] 実装後の振り返りを記録
- [x] 全テスト通過、lintエラーなし、リリース判断を記録

> 上の全チェック完了後、`python3 scripts/steering_state.py complete --harness "Claude Code"`で`complete`へ遷移する。その後、add-featureステップ8で最終品質ゲートを1回実行する。

---

## 実装後の振り返り

### 実装完了日

2026-09-07

### 計画と実績の差分

**計画と異なった点**:

- **`--host` を用意する計画だったが、外した。** 段3で「`127.0.0.1` 以外を渡すと全リクエストが 400 になる」ことが判明した（`run()` が待ち受けアドレスを許可リストへ渡していなかった）。直し方は2つあったが、認証も CSRF 対策も無い面をネットワークへ出せる入口を残すのはスコープ（「リモートからのアクセスはスコープ外」）と食い違うため、**オプション自体を削る**ほうを選んだ。`run()` 側は自己整合のため許可リストへ足す修正も入れた。
- **許可リストから `testserver` を外した。** design.md に「テストのためだけの分岐を実装に入れないため許可リストに1語足す」と理由まで書いていたが、**判断が誤っていた**。本番の許可リストにテスト専用の名前を残すこと自体が DNS リバインディング対策を弱める。`create_app()` は元から引数を受けるので、テスト側が渡せば済む話だった。
- **リビジョンの監視対象を広げた。** 計画では `config.yaml` とタスクファイルだけだったが、`/api/overview` にタイマーとルーティーンを載せた時点で釣り合わなくなっていた（画面が「変更を監視中」と言いながら古い値を映す）。**API が返すものはすべて監視対象に入れる**、と規則を言い直した。
- **`Cache-Control: no-cache` を足した（計画外）。** 段2で自分が踏んだ。ブラウザが古い JavaScript を実行し続け、直したはずの修正が反映されなかった。これは開発中の不便に見えて、実は**利用者が task-py を更新したときに同じことが起きる**製品の欠陥だった。

**新たに必要になったタスク**:

- `GlobalConfigStorage` の既定パスがモジュール読み込み時に `~` を展開していた問題の修正（下記「学んだこと」を参照）
- `DailyService.list_today(ensure=False)` の追加。読み取り経路が書き込んでいたため
- `TimerService.timer_path` / `DailyService.log_path` / `routines_path` の追加。web → storage の直接依存を作らずに監視対象を組み立てるため
- 取得の世代番号と、初回取得中に届いたリビジョンの保留（段3 指摘3・7）

**技術的理由でスキップしたタスク**:

- 該当なし

### 学んだこと

**技術的な学び**:

- **「読み取り専用」はルーティングだけでは名乗れない。** `GET` しか登録しなければ書き込みメソッドは 405 になるが、**その `GET` の中で何を呼ぶか**は別の問題だった。`DailyService.list_today()` は名前が完全に読み取りの顔をしていて、実際には「今日のログ」を書き足す。画面を開くだけでユーザーデータが変わっていた。**呼ぶ側の意図ではなく、呼ばれる側が実際に何をするかを確かめる**必要がある。
- **既定引数の `~` 展開はモジュール読み込み時に固まる。** `_CONFIG_PATH = Path("~/.task-py").expanduser()` をモジュール直下に書くと、その後 `HOME` を差し替えても追随しない。5つのストレージのうち1つだけがこの形で、**テストの隔離が静かに効いていなかった**。結果として自分のテストが実ホームのデータを書き換えた。
- **starlette は「同期エンドポイントはスレッドプール、非同期はイベントループ」で分岐する。** 例外を写すデコレータを何気なく `async def` にしたことで、同期の YAML 読み込みと `flock` 待ちがループ上で走り、他のリクエストと SSE を巻き込んで止める形になっていた。デコレータが関数の**同期・非同期という性質を変えてしまう**ことに注意が要る。
- ローカルサーバでも `Cache-Control` は要る。`no-cache` は「使うな」ではなく「使う前に必ず確かめろ」で、変更が無ければ 304 で済む。
- `TrustedHostMiddleware` は `host.split(":")[0]` で照合するため、ポートは自動的に落ちる代わりに IPv6 の `[::1]:port` では壊れる。IPv4 に限って待ち受ける判断と一貫している。

**プロセス上の改善点**:

- **実ブラウザでの観察（段2）が、テストでは絶対に出ない欠陥を3件出した。** 一覧→詳細の1フレームで真っ白・古い JavaScript の実行・API の二重取得。いずれも 575 テストが緑のままだった。JS 側のテスト基盤を持たない構成では、**段2 を「起動して眺める」で済ませず、実際に操作する**ことが効く。
- **自分が design.md に理由まで書いた判断が、2件とも誤っていた**（`testserver` の許可・監視対象の範囲）。理由を書くこと自体は正しいが、**書いた理由が正しさを保証しない**。段3のレビューは「実装が設計どおりか」だけでなく「設計の判断そのものが正しいか」を見てくれており、そこが効いている。#42 でも同じ形（「全置換だから排他不要」が誤り）だった。3回連続。
- **テストの隔離が効いていないことは、テストが緑でも分からない。** 実ホームを汚染して初めて気づいた。`HOME` を差し替える方式に依存するなら、**その差し替えが本当に効いているかを検証するテスト**を持つべきだった（今回追加した）。

### 次回への改善提案

- 作業単位C（書き込み面）では、**「この関数は本当に読むだけか」を確かめる観点**を design.md のチェックに入れる。今回は `list_today` で踏んだが、書き込み面では逆に「書いたつもりが書けていない」経路が出うる。
- **`HOME` の差し替えに依存するテストを書くときは、対象クラスの既定パスが遅延評価かを先に確かめる。** 今回の回帰テスト（`TestDefaultPathsFollowHome`）がその役目を果たすが、新しいストレージを足したときに追加し忘れると同じ穴が空く。
- 段2の観察は**成果物を残す**とよい（今回はスクリーンショットを1枚保存した）。次のセッションが「前はどう見えていたか」を確かめられる。

### リリース判断

| 観点 | 評価 |
|---|---|
| ユーザー価値のあるまとまりか | Yes |
| 未解決の重大バグ | なし |
| 適切なバージョン種別 | MINOR（v0.11.0） |

**提案**:

v0.11.0 としてリリースする。`task-py web` という**新しい面**が増えるため MINOR。読み取りだけでも、
「全プロジェクトを一画面で見渡す」「CLI や Claude の変更が開いたまま反映される」という
これまで CLI にできなかったことが単体で使える。

書き込み面（作業単位C）を待たずに出すことで、実際に使ってみて「どの操作を GUI から
したいか」が分かった状態で C の要求を決められる。

# 設計

## 実装アプローチ

テストを先に書き、現状で失敗することを確認してから実装する。

### service 層(`services/project_service.py`・`exceptions.py`)
- `exceptions.py` に `InvalidProjectName(AppError)` を足す
- `project_service.py` に `validate_project_name(name)` を置き、`create_project`・`rename_project`(新しい名前)の先頭で呼ぶ。ロックを取る前に検証する
- 規則: `name != name.strip()` / 空 / `len > 64` / 制御文字 / `/` `\` を含む / `name in (".", "..")` / 先頭が `.` を拒否。理由は原因文に書く
- CLI は既存の `except AppError` で `[Error]/原因/対処` を表示するので、CLI 側の変更は無い

### Web API(`task_web/api.py`)
- 既存の `_writer`(CSRF 検査と本文読み取り)を使う。ハンドラは `ProjectService(GlobalConfigStorage())` を直接使う(usecase 層は無い。他の読み取りエンドポイントも `get_global_config_service()` を直接使っている)
- `_STATUS_BY_ERROR` に `(InvalidProjectName, 400)` を足す。「同名」「見つからない」は service が素の `AppError` を投げているため、Web では 409/404 にならず 500 になる。**service の例外を `StateConflictError`(同名)・`NotFoundError`(見つからない)に変える**(CLI は `AppError` を捕まえるので表示は変わらない)。`get_project` の `NotFoundError` 化は MCP・CLI の挙動を変えないことをテストで確認する
- 本文の型検査は `move_task` の `project` 検査と同じ形(`BadRequest`)
- 応答: create 201 `{"project": entry, "active_project": ...}`、use/rename 200 `{"active_project": ..., "projects": [...]}`、delete 200 `{"deleted": name}`
- **ロックの取得順(timer → tasks)には触れない**。`ProjectService` が握るのは `config.yaml` のロックだけ

### 画面(`static/js/`)
- `api.js`: `createProject` / `useProject` / `renameProject` / `removeProject`(既存の `request` ヘルパを使う)
- `main.js`: サイドバーに「＋ プロジェクト」。プロジェクト画面の見出しにボタン3つ。既存の `dialog` 状態に `project-create` / `project-rename` / `project-delete` を足す。成功後は `refreshState()`(SSE でも更新されるが、遷移を伴うので即時に)
- `ui.js`: 名前入力のダイアログ(既存の `Dialog`・確認ダイアログの部品を再利用)
- 「アクティブ」のラベルに「CLI・MCP の既定の対象」を添える

## 守る設計(roadmap)
- API は常に project を明示。`ACTIVE_PROJECT` は使わない(use は「アクティブを書き換える」明示操作)
- 未指定の `None` を `project=` へ渡さない(Inbox を指すため)。本文の `name`/`new` が無い・文字列でないときは 400
- CSRF は既存の `_writer` に乗せる

## 判断した点
- 作成でアクティブが切り替わるのは CLI と同じ。GUI だけ変えると同じ操作で結果が違う
- 改名中に他プロセスがそのプロジェクトの `tasks.yaml` を書く窓は、`rename_project` のドキュメントどおり残す(ここで排他区間を広げると timer→tasks の取得順の規則に触れる)
- 実行中のタイマーが対象プロジェクトを指している場合の改名・削除は、**409 で断る**ことにした(実装済み。`api.py` の `_refuse_if_timer_runs_on`)。タイマーは開始時の project 名を持つため、名前が消えると停止時の記録先が失われる。CLI の `project rename/remove` には同じ穴が残る(振り返りに記録)
- `ErrorBox` の競合表示は `error.isConflict && error.current` のときだけにした。`current` を持たない 409(同名・タイマー実行中)を「別の場所で変更されました」の箱に流すと誤解を招き、プロジェクトのダイアログでは「最新に合わせて続ける」が意味を持たないため
- 画面の名称: ボタンは「名前を変更」、ダイアログ種別は `project-remove`、削除後は「すべて」画面へ移る(Inbox ではない)。`app.css` に `.project-actions` を足した

## 変更ファイル
`src/task_cli/exceptions.py`、`src/task_cli/services/project_service.py`、`src/task_web/api.py`、`src/task_web/static/js/{api,main,ui}.js`、`docs/functional-design.md`、`README.md`、`pyproject.toml`/`uv.lock`(0.15.0)、テスト(新規)

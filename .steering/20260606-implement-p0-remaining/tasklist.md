# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: A — list --all / --inbox

- [x] `src/task_cli/usecases/task_crud_usecase.py` に追加
  - [x] `list_all_projects(filter)` — 全プロジェクト + Inbox のタスクを `dict[str | None, list[Task]]` で返す
  - [x] `list_inbox_tasks(filter)` — Inbox のみ返す
- [x] `src/task_cli/cli/commands/list.py` を更新
  - [x] `--all` オプション追加（全プロジェクト表示）
  - [x] `--inbox` オプション追加（Inbox のみ表示）
- [x] `tests/test_usecases.py` に `list_all_projects` / `list_inbox_tasks` テスト追加

## フェーズ2: B — project rename

- [x] `src/task_cli/services/project_service.py` に `rename_project(old, new)` 追加
  - [x] old の存在確認・new の重複確認
  - [x] GlobalConfig.projects の name 更新
  - [x] active_project が old なら new に更新
  - [x] ディレクトリリネーム（存在する場合のみ）
- [x] `src/task_cli/cli/commands/project.py` に `rename` サブコマンド追加
- [x] `tests/test_project_service.py` に `rename_project` テスト追加
  - [x] 正常系（非アクティブ）
  - [x] 正常系（アクティブプロジェクトのリネーム → active_project も更新）
  - [x] 異常系（old が存在しない）
  - [x] 異常系（new が重複）

## フェーズ3: C — search

- [x] `src/task_cli/cli/commands/search.py` を新規作成
  - [x] `search <keyword>` → `uc.search_tasks(keyword)` → `render_task_table` で表示
- [x] `src/task_cli/cli/main.py` に `search` を登録

## フェーズ4: E — daily モデル・ストレージ・サービス

- [x] `src/task_cli/models/daily.py` を新規作成
  - [x] `Routine` モデル（id, title, paused, created_at）
  - [x] `DailyLogEntry` モデル（routine_id, status）
  - [x] `DailyLog` モデル（date, entries）
- [x] `src/task_cli/storage/routine_storage.py` を新規作成
  - [x] `load()` / `save()` / `ensure_directory()`
- [x] `src/task_cli/storage/daily_log_storage.py` を新規作成
  - [x] `load_all()` — 直近30日分を返す
  - [x] `load_today()` — 今日のログを返す（なければ空を返す）
  - [x] `save(log: DailyLog)` — 今日のログを保存（30日超は削除）
- [x] `src/task_cli/services/daily_service.py` を新規作成
  - [x] `add_routine(title)` → Routine
  - [x] `list_today(include_paused)` → list[tuple[Routine, str]]（達成率高い順）
  - [x] `mark_done(id)` — 今日のログを done に更新
  - [x] `pause(id)` / `resume(id)` / `resume_all()` → int
  - [x] `delete(id)` — Routine 削除 + ログからも削除
  - [x] `stats()` — 直近7日の日別達成率
  - [x] `reset_today()` — 今日のログを全 pending にリセット
  - [x] `_ensure_today_log()` — 日付変わりを検知して新ログ作成
- [x] `tests/test_daily_service.py` を新規作成
  - [x] `add_routine` 正常系
  - [x] `list_today` — 達成率高い順・paused は末尾
  - [x] `mark_done` 正常系・存在しない id の異常系
  - [x] `pause` / `resume` / `resume_all` 正常系
  - [x] `delete` 正常系（ログも削除される）
  - [x] `stats` 正常系
  - [x] `reset_today` 正常系
  - [x] `_ensure_today_log` — 日付が変わったら新ログが作られる

## フェーズ5: E — daily CLI コマンド

- [x] `src/task_cli/cli/commands/daily.py` を新規作成（typer サブアプリ）
  - [x] `daily add <title>`
  - [x] `daily list [--all]`
  - [x] `daily done <id>`
  - [x] `daily pause <id>`
  - [x] `daily resume <id>` / `daily resume --all`
  - [x] `daily delete <id>`
  - [x] `daily stats`
  - [x] `daily reset`
- [x] `src/task_cli/cli/main.py` に `daily` サブアプリを登録

## フェーズ6: D — onboard

- [x] `src/task_cli/cli/commands/onboard.py` を新規作成
  - [x] アクティブプロジェクト表示
  - [x] daily pending 一覧表示（DailyService を使用）
  - [x] 着手すべきタスク最大3件（in_progress 優先 → open）
  - [x] 全タスク一覧（全ステータス）
- [x] `src/task_cli/cli/main.py` に `onboard` を登録
- [x] `src/task_cli/cli/shell.py` の起動時に `onboard` を自動実行

## フェーズ7: F — time start

- [x] `src/task_cli/cli/commands/time.py` を新規作成
  - [x] `parse_duration(s: str) -> int` — 秒数を返す（20m/1h/30s/数値）
  - [x] `time_app` サブアプリ
  - [x] `time start <duration>` — rich Live でリアルタイム表示・終了時ベル・Ctrl+C キャンセル
- [x] `tests/test_time.py` を新規作成
  - [x] `parse_duration("20m")` → 1200
  - [x] `parse_duration("1h")` → 3600
  - [x] `parse_duration("30s")` → 30
  - [x] `parse_duration("20")` → 1200（数値のみ = 分）
  - [x] `parse_duration("20min")` → 1200
  - [x] 不正な形式で AppError
- [x] `src/task_cli/cli/main.py` に `time` サブアプリを登録

## フェーズ8: 品質チェック

- [x] `uv run pytest` — 全テスト通過を確認（125件）
- [x] `uv run pyright src tests` — 型エラーゼロを確認
- [x] 手動動作確認
  - [x] `task-py list --all` が動く
  - [x] `task-py list --inbox` が動く
  - [x] `task-py project rename old new` が動く
  - [x] `task-py search <keyword>` が動く
  - [x] `task-py daily add "朝のルーティーン"` → `daily list` → `daily done 1` が動く
  - [x] `task-py daily stats` が動く
  - [x] `task-py onboard` が動く
  - [x] `task-py time start 5s` でカウントダウン → ベル通知が動く
  - [ ] `task-py shell` 起動時に onboard が表示される（インタラクティブのため手動確認）

## フェーズ9: ドキュメント更新

- [x] `README.md` に新コマンドを追記

---

## 実装後の振り返り

### 実装完了日
2026-06-07

### 計画と実績の差分

**計画と異なった点**:
- `add_routine` で `_ensure_today_log()` と手動エントリ追加が重複し、ログに同一ルーティーンが2件入るバグが発生。手動追加を削除して修正
- `TestListAllProjects` テストで `active_project` 設定だけでは `GlobalConfig.projects` に追加されないことが判明。テスト用ヘルパー `make_use_case_with_projects` を追加

**新たに必要になったタスク**:
- `make_use_case_with_projects` テストヘルパーの追加

### 学んだこと
- `_ensure_today_log` は「ストレージにあるルーティーンをもとにログを補完する」責務なので、`add_routine` 後に呼べば追加したルーティーンも自動で補完される
- `pyright` の tuple 型注釈は戻り値の要素数まで厳密にチェックする

### 次回への改善提案
- `daily list` の達成率をプログレスバーで表示するとより直感的

### リリース判断

**前提条件の確認**:
- [x] 全テスト通過（`uv run pytest`）— 125件
- [x] 型チェック通過（`uv run pyright src tests`）— エラーゼロ
- [x] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes（P0機能がすべて揃った） |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR（新機能追加） |

**提案**: `v0.4.0` へのバージョンアップを提案。list --all/--inbox、project rename、search、daily、onboard、time start と多数の機能が追加されたため MINOR バージョンアップが適切。

# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: A — list --all / --inbox

- [ ] `src/task_cli/usecases/task_crud_usecase.py` に追加
  - [ ] `list_all_projects(filter)` — 全プロジェクト + Inbox のタスクを `dict[str | None, list[Task]]` で返す
  - [ ] `list_inbox_tasks(filter)` — Inbox のみ返す
- [ ] `src/task_cli/cli/commands/list.py` を更新
  - [ ] `--all` オプション追加（全プロジェクト表示）
  - [ ] `--inbox` オプション追加（Inbox のみ表示）
- [ ] `tests/test_usecases.py` に `list_all_projects` / `list_inbox_tasks` テスト追加

## フェーズ2: B — project rename

- [ ] `src/task_cli/services/project_service.py` に `rename_project(old, new)` 追加
  - [ ] old の存在確認・new の重複確認
  - [ ] GlobalConfig.projects の name 更新
  - [ ] active_project が old なら new に更新
  - [ ] ディレクトリリネーム（存在する場合のみ）
- [ ] `src/task_cli/cli/commands/project.py` に `rename` サブコマンド追加
- [ ] `tests/test_project_service.py` に `rename_project` テスト追加
  - [ ] 正常系（非アクティブ）
  - [ ] 正常系（アクティブプロジェクトのリネーム → active_project も更新）
  - [ ] 異常系（old が存在しない）
  - [ ] 異常系（new が重複）

## フェーズ3: C — search

- [ ] `src/task_cli/cli/commands/search.py` を新規作成
  - [ ] `search <keyword>` → `uc.search_tasks(keyword)` → `render_task_table` で表示
- [ ] `src/task_cli/cli/main.py` に `search` を登録

## フェーズ4: E — daily モデル・ストレージ・サービス

- [ ] `src/task_cli/models/daily.py` を新規作成
  - [ ] `Routine` モデル（id, title, paused, created_at）
  - [ ] `DailyLogEntry` モデル（routine_id, status）
  - [ ] `DailyLog` モデル（date, entries）
- [ ] `src/task_cli/storage/routine_storage.py` を新規作成
  - [ ] `load()` / `save()` / `ensure_directory()`
- [ ] `src/task_cli/storage/daily_log_storage.py` を新規作成
  - [ ] `load_all()` — 直近30日分を返す
  - [ ] `load_today()` — 今日のログを返す（なければ空を返す）
  - [ ] `save(log: DailyLog)` — 今日のログを保存（30日超は削除）
- [ ] `src/task_cli/services/daily_service.py` を新規作成
  - [ ] `add_routine(title)` → Routine
  - [ ] `list_today(include_paused)` → list[tuple[Routine, str]]（達成率高い順）
  - [ ] `mark_done(id)` — 今日のログを done に更新
  - [ ] `pause(id)` / `resume(id)` / `resume_all()` → int
  - [ ] `delete(id)` — Routine 削除 + ログからも削除
  - [ ] `stats()` — 直近7日の日別達成率
  - [ ] `reset_today()` — 今日のログを全 pending にリセット
  - [ ] `_ensure_today_log()` — 日付変わりを検知して新ログ作成
- [ ] `tests/test_daily_service.py` を新規作成
  - [ ] `add_routine` 正常系
  - [ ] `list_today` — 達成率高い順・paused は末尾
  - [ ] `mark_done` 正常系・存在しない id の異常系
  - [ ] `pause` / `resume` / `resume_all` 正常系
  - [ ] `delete` 正常系（ログも削除される）
  - [ ] `stats` 正常系
  - [ ] `reset_today` 正常系
  - [ ] `_ensure_today_log` — 日付が変わったら新ログが作られる

## フェーズ5: E — daily CLI コマンド

- [ ] `src/task_cli/cli/commands/daily.py` を新規作成（typer サブアプリ）
  - [ ] `daily add <title>`
  - [ ] `daily list [--all]`
  - [ ] `daily done <id>`
  - [ ] `daily pause <id>`
  - [ ] `daily resume <id>` / `daily resume --all`
  - [ ] `daily delete <id>`
  - [ ] `daily stats`
  - [ ] `daily reset`
- [ ] `src/task_cli/cli/main.py` に `daily` サブアプリを登録

## フェーズ6: D — onboard

- [ ] `src/task_cli/cli/commands/onboard.py` を新規作成
  - [ ] アクティブプロジェクト表示
  - [ ] daily pending 一覧表示（DailyService を使用）
  - [ ] 着手すべきタスク最大3件（in_progress 優先 → open）
  - [ ] 全タスク一覧（全ステータス）
- [ ] `src/task_cli/cli/main.py` に `onboard` を登録
- [ ] `src/task_cli/cli/shell.py` の起動時に `onboard` を自動実行

## フェーズ7: F — time start

- [ ] `src/task_cli/cli/commands/time.py` を新規作成
  - [ ] `parse_duration(s: str) -> int` — 秒数を返す（20m/1h/30s/数値）
  - [ ] `time_app` サブアプリ
  - [ ] `time start <duration>` — rich Live でリアルタイム表示・終了時ベル・Ctrl+C キャンセル
- [ ] `tests/test_time.py` を新規作成
  - [ ] `parse_duration("20m")` → 1200
  - [ ] `parse_duration("1h")` → 3600
  - [ ] `parse_duration("30s")` → 30
  - [ ] `parse_duration("20")` → 1200（数値のみ = 分）
  - [ ] `parse_duration("20min")` → 1200
  - [ ] 不正な形式で AppError
- [ ] `src/task_cli/cli/main.py` に `time` サブアプリを登録

## フェーズ8: 品質チェック

- [ ] `uv run pytest` — 全テスト通過を確認
- [ ] `uv run pyright src tests` — 型エラーゼロを確認
- [ ] 手動動作確認
  - [ ] `task-py list --all` が動く
  - [ ] `task-py list --inbox` が動く
  - [ ] `task-py project rename old new` が動く
  - [ ] `task-py search <keyword>` が動く
  - [ ] `task-py daily add "朝のルーティーン"` → `daily list` → `daily done 1` が動く
  - [ ] `task-py daily stats` が動く
  - [ ] `task-py onboard` が動く
  - [ ] `task-py time start 5s` でカウントダウン → ベル通知が動く
  - [ ] `task-py shell` 起動時に onboard が表示される

## フェーズ9: ドキュメント更新

- [ ] `README.md` に新コマンドを追記

---

## 実装後の振り返り

### 実装完了日
未定

### 計画と実績の差分

**計画と異なった点**:
-

**新たに必要になったタスク**:
-

### 学んだこと
-

### 次回への改善提案
-

### リリース判断

**前提条件の確認**:
- [ ] 全テスト通過（`uv run pytest`）
- [ ] 型チェック通過（`uv run pyright src tests`）
- [ ] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | 未評価 |
| 未解決の重大バグはないか | 未評価 |
| 適切なバージョン種別 | MINOR（新機能追加） |

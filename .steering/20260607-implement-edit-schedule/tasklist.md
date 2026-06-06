# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 「実装が複雑すぎるため後回し」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

---

## フェーズ1: モデル層

- [x] `src/task_cli/models/task.py` を更新
  - [x] `Task` モデルに `scheduled_date: str | None = None` フィールドを追加
  - [x] `due_date` と同じ YYYY-MM-DD バリデータを `scheduled_date` にも適用

## フェーズ2: サービス層（TaskManager）

- [x] `src/task_cli/services/task_manager.py` を更新
  - [x] `update_task(id, title, description, priority, due_date, clear_due_date, scheduled_date, clear_scheduled_date)` を追加
  - [x] `set_scheduled_date(id, date | None)` を追加
  - [x] `start_task` に解禁日チェックを追加（scheduled_date > today → AppError）

## フェーズ3: ユースケース層

- [x] `src/task_cli/usecases/task_crud_usecase.py` を更新
  - [x] `edit_task(id, ...)` を追加（TaskManager.update_task へ委譲）
  - [x] `set_scheduled_date(id, date | None)` を追加（TaskManager.set_scheduled_date へ委譲）

## フェーズ4: テスト

- [x] `tests/test_usecases.py` に `TestEditTask` クラスを追加
  - [x] タイトル更新の正常系
  - [x] 説明・優先度更新の正常系
  - [x] `--due` で期限設定、`clear_due_date=True` で期限削除
  - [x] `--scheduled` で解禁日設定、`clear_scheduled_date=True` で解禁日削除
  - [x] 存在しない ID の異常系
- [x] `tests/test_usecases.py` に `TestSetScheduledDate` クラスを追加
  - [x] 解禁日設定の正常系
  - [x] `None` 渡しで解禁日削除の正常系
- [x] 既存 `TestTaskManagerStatusTransitions` に解禁日チェックテストを追加
  - [x] 解禁日が未来 → start で AppError
  - [x] 解禁日が今日以前 → start 成功
  - [x] 解禁日なし → start 成功（既存動作が壊れていないことの確認）

## フェーズ5: CLI レイヤー

- [x] `src/task_cli/cli/commands/edit.py` を新規作成
  - [x] `edit <id>` コマンド（-t/--title, -d/--description, -p/--priority, --due, --due-clear, --scheduled, --scheduled-clear）
  - [x] オプションが1つも指定されていない場合は AppError
- [x] `src/task_cli/cli/commands/schedule.py` を新規作成
  - [x] `schedule <id> [date] [--clear]` コマンド
  - [x] date も --clear もない場合は AppError
- [x] `src/task_cli/cli/main.py` に `edit` と `schedule` を登録

## フェーズ6: 品質チェック

- [x] `uv run pytest` — 全テスト通過を確認
- [x] `uv run pyright src tests` — 型エラーゼロを確認
- [x] 手動動作確認
  - [x] `task-py edit 1 --title "新タイトル"` が動く
  - [x] `task-py edit 1 --due 2026-12-31 --priority high` が動く
  - [x] `task-py edit 1 --due-clear` が動く
  - [x] `task-py schedule 1 2099-01-01` → `task-py start 1` が解禁日エラーになる
  - [x] `task-py schedule 1 --clear` → `task-py start 1` が成功する

## フェーズ7: ドキュメント更新

- [x] `README.md` に `edit` と `schedule` コマンドを追記

---

## 実装後の振り返り

### 実装完了日
2026-06-07

### 計画と実績の差分

**計画と異なった点**:
- 既存の `update_task(**kwargs)` が内部用に既にあったため、新規の `edit_fields` メソッドを追加して使い分ける構成にした（kwargs のまま拡張すると型安全性が落ちる）
- `due_date` の field_validator が `validate_due_date` という名前だったため、`scheduled_date` を追加する際に `validate_date_format` にリネームして両フィールドをまとめてカバーした

**新たに必要になったタスク**:
- なし

### 学んだこと
- pydantic の `@field_validator` は複数フィールド名を引数に渡すことで共通バリデータを適用できる
- `None` = 変更なし 問題は `clear_*: bool` フラグで解決するのがシンプル

### 次回への改善提案
- `show` コマンドに `scheduled_date` の表示を追加するとユーザーにわかりやすい

### リリース判断

**前提条件の確認**:
- [x] 全テスト通過（`uv run pytest`）— 135件
- [x] 型チェック通過（`uv run pyright src tests`）— エラーゼロ
- [x] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes（TypeScript 版との機能同等性が達成された） |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR（新コマンド追加・モデル拡張） |

**提案**: `v0.5.0` へのバージョンアップを提案。edit/schedule 追加と scheduled_date によるモデル拡張のため MINOR が適切。

# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

### 必須ルール
- **全てのタスクを`[x]`にすること**
- 「時間の都合により別タスクとして実施予定」は禁止
- 「実装が複雑すぎるため後回し」は禁止
- 未完了タスク（`[ ]`）を残したまま作業を終了しない

### タスクスキップが許可される唯一のケース
以下の技術的理由に該当する場合のみスキップ可能:
- 実装方針の変更により、機能自体が不要になった
- アーキテクチャ変更により、別の実装方法に置き換わった
- 依存関係の変更により、タスクが実行不可能になった

---

## フェーズ1: migrate コマンド実装

- [x] `src/task_cli/cli/commands/migrate.py` を新規作成
  - [x] `_convert_config(raw: dict) -> GlobalConfig` を実装（camelCase → snake_case）
  - [x] `_convert_tasks(raw: list[dict]) -> list[Task]` を実装（dueDate, scheduledDate, createdAt, updatedAt の変換）
  - [x] `_convert_routines(raw: list[dict]) -> list[Routine]` を実装（createdAt → created_at）
  - [x] `_convert_logs(raw: list[dict]) -> list[DailyLog]` を実装（entries: dict → list[DailyLogEntry]）
  - [x] `migrate(dry_run, force)` メイン関数を実装
    - [x] `~/.task/` 存在チェック（なければ AppError）
    - [x] `--dry-run` モード: 変換内容を rich でプレビュー、書き込みなし
    - [x] 既存 `~/.task-py/` データの上書き確認（`--force` か typer.confirm）
    - [x] config 変換・書き込み
    - [x] inbox タスク変換・書き込み
    - [x] projects タスク変換・書き込み（ディレクトリ走査）
    - [x] routines 変換・書き込み
    - [x] logs 変換・書き込み
    - [x] サマリー表示（タスク数・ルーティン数・ログ日数）

## フェーズ2: main.py に登録

- [x] `src/task_cli/cli/main.py` に `migrate` コマンドを追加
  - [x] `from task_cli.cli.commands.migrate import migrate` を追加
  - [x] `app.command("migrate")(migrate)` を追加

## フェーズ3: テスト実装

- [x] `tests/test_migrate.py` を新規作成
  - [x] `test_convert_config`: camelCase → snake_case 変換を確認
  - [x] `test_convert_tasks`: 全フィールド（dueDate, scheduledDate, createdAt, updatedAt）が正しく変換される
  - [x] `test_convert_routines`: `createdAt` → `created_at` の変換
  - [x] `test_convert_logs`: `entries` の dict → list 変換（キーが int に変換される）
  - [x] `test_convert_logs_empty`: entries が空の場合

## フェーズ4: ドキュメント作成

- [x] `docs/migration-from-ts.md` を新規作成
  - [x] 前提条件（TypeScript 版がインストール済みで `~/.task/` にデータがある）
  - [x] データ構造の差異を説明
  - [x] `task-py migrate --dry-run` での事前確認手順
  - [x] `task-py migrate` の実行手順
  - [x] トラブルシューティング（よくある問題）

## フェーズ5: 品質チェックと修正

- [x] すべてのテストが通ることを確認
  - [x] `uv run pytest`（148 passed）
- [x] 型エラーがないことを確認
  - [x] `uv run pyright src`（0 errors）
- [x] 動作確認
  - [x] `uv run task-py migrate --help` でヘルプが表示される
  - [x] `uv run task-py migrate --dry-run` で dry-run が動作する（`~/.task/` がある環境）
- [x] 実装後の振り返り（このファイルの下部に記録）

---

## 実装後の振り返り

### 実装完了日
2026-06-07

### 計画と実績の差分

**計画と異なった点**:
- 特になし。設計通りに実装できた。

**新たに必要になったタスク**:
- 特になし。

### 学んだこと

**技術的な学び**:
- TypeScript 版の DailyLog は `entries` が `Record<number, status>` だが、JSON の key は常に string になるため、`int(k)` で変換が必要だった（設計時に把握済みで問題なし）
- 既存の Pydantic モデル（Task, GlobalConfig 等）をそのまま使えたため、変換後のバリデーションが自動で効いた

**プロセス上の改善点**:
- 単体の変換関数を設計 → テスト → main 実装の順にすると、型エラーや変換ロジックのバグを早期発見できた

### リリース判断

> Claude が評価・提案し、プロジェクトオーナーが最終決定する。

**前提条件の確認**:
- [ ] 全テスト通過（`uv run pytest`）
- [ ] 型チェック通過（`uv run pyright src`）
- [ ] リリースノートに記載すべき変更内容が整理されている

**評価**:

| 観点 | 評価 |
|---|---|
| 今回の変更はユーザーにとって価値のあるまとまりか | Yes |
| 未解決の重大バグはないか | なし |
| 適切なバージョン種別 | MINOR |

**提案**:
`v0.6.0` へのバージョンアップを提案。理由: TypeScript 版からの移行を完全サポートするユーザー向け新機能（`task-py migrate`）を追加。

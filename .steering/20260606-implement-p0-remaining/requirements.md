# 要求内容

## 概要

P0 MVP の残機能 A〜F を一括実装する。
G〜I（edit・Git連携・GitHub同期）は `docs/ideas/future-roadmap.md` に残課題として記録済み。

## 関連 Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/9

## 実装対象の機能

### A: `task-py list` オプション拡張

- `--all`: 全プロジェクト + Inbox をプロジェクトごとのセクションに分けて表示。アクティブプロジェクトを強調
- `--inbox`: Inbox タスクのみ表示

### B: `task-py project rename <old> <new>`

- GlobalConfig の projects リストと active_project を更新
- `~/.task-py/projects/<old>/` ディレクトリを `<new>/` にリネーム

### C: `task-py search <keyword>`

- タイトル・説明の全文検索（`search_tasks` はサービス層に実装済み）
- CLI コマンドのみ追加

### D: `task-py onboard`

- アクティブプロジェクト名（または Inbox モード）を表示
- 今日の daily ルーティーン pending 一覧（daily 実装後に有効化。先行実装時は省略）
- 着手すべきタスク最大3件（`in_progress` 優先、次いで `open`）
- 全タスク一覧

### E: `task-py daily` サブコマンド群

新モデル・ストレージ・サービスを追加して以下を実装:

| コマンド | 処理 |
|---------|------|
| `daily add <title>` | ルーティーン登録 |
| `daily list [--all]` | 今日の一覧（達成率高い順、paused は末尾。`--all` で一時停止中も表示） |
| `daily done <id>` | 済にする |
| `daily pause <id>` | 一時停止（list から非表示） |
| `daily resume <id>` | 一時停止を解除 |
| `daily resume --all` | 全一時停止を一括解除 |
| `daily delete <id>` | 削除（実績ログも削除） |
| `daily stats` | 直近7日の日別達成率テーブル |
| `daily reset` | 今日のチェック状態をリセット（確認プロンプト付き） |

データは `~/.task-py/daily/routines.yaml` と `~/.task-py/daily/log.yaml` に保存。

### F: `task-py time start <duration>`

- duration 形式: `20min` / `20m` / `1h` / `30s` / 数値のみ（分として解釈）
- 残り時間をリアルタイム表示（rich の Live を活用）
- 終了時にターミナルベルで通知（`\a`）
- Ctrl+C でキャンセル可能

## 受け入れ条件

### A
- [ ] `list --all` で全プロジェクト + Inbox が表示される
- [ ] `list --inbox` で Inbox タスクのみ表示される

### B
- [ ] `project rename old new` でプロジェクト名が変わる
- [ ] ディレクトリがリネームされる
- [ ] アクティブプロジェクトだった場合は active_project も更新される

### C
- [ ] `search <keyword>` でマッチするタスクが表示される
- [ ] 大文字小文字を区別しない

### D
- [ ] `onboard` でアクティブプロジェクト・着手タスク・全タスクが表示される

### E
- [ ] `daily add` でルーティーンが追加できる
- [ ] `daily list` で今日の一覧が表示される
- [ ] `daily done` / `pause` / `resume` / `delete` が動く
- [ ] `daily stats` で直近7日の達成率が表示される
- [ ] `daily reset` で今日のログがリセットされる

### F
- [ ] `time start 20m` でカウントダウンが始まる
- [ ] 残り時間がリアルタイムで更新される
- [ ] 終了時にベル通知
- [ ] Ctrl+C でキャンセルできる

### 共通
- [ ] pytest 全通過・pyright エラーゼロ

## スコープ外

- G: `task-py edit <id>`（`docs/ideas/future-roadmap.md` に記録）
- H: Git ブランチ連携（同上）
- I: GitHub Issues 同期（同上）

## 参照ドキュメント

- `docs/functional-design.md` — 機能設計書（データモデル・UI 設計含む）
- `docs/ideas/future-roadmap.md` — 残課題（G〜I）

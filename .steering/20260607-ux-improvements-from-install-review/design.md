# 設計書

## 1. `--version` オプション

### 実装方針

`typer` の `callback` に `--version` / `-V` オプションを追加する。

- インストール済みバージョンは `importlib.metadata.version("dev-tasks2-py")` で取得
- GitHub API（`https://api.github.com/repos/kanan4gh/dev-tasks2-py/releases/latest`）を `urllib.request` で叩き、`tag_name` を取得して比較
- タイムアウトは 3 秒、失敗時は静かにスキップ
- 新依存ライブラリは追加しない（標準ライブラリのみ）

### 表示例

```
task-py version 0.6.0

新しいバージョン 0.7.0 が利用可能です。
アップデートするには以下を実行してください:
  uv tool install git+https://github.com/kanan4gh/dev-tasks2-py --force
```

### 変更ファイル

- `src/task_cli/cli/main.py`

---

## 2. `migrate` コマンドの安全性向上

### 実装方針

- 既存データがある場合、上書き前に `~/.task-py.backup/` へ `shutil.copytree` でコピー
- バックアップ先が既存の場合は上書き（`dirs_exist_ok=True`）
- 確認プロンプトの文言を変更:
  - 変更前: `{_PY_DIR} に既存データがあります。上書きしますか？`
  - 変更後: `{_PY_DIR} に既存データがあります。上書きすると現在の task-py のタスクはすべて失われます（バックアップは {_PY_DIR}.backup/ に保存されます）。続行しますか？`

### 変更ファイル

- `src/task_cli/cli/commands/migrate.py`

---

## 3. アンインストールガイド（README）

### 追加セクション

「データ保存先」セクションの後、「開発者向け」セクションの前に追加:

```markdown
## アンインストール

ツール本体を削除するには:

```bash
uv tool uninstall dev-tasks2-py
```

タスクデータも合わせて削除する場合:

```bash
rm -rf ~/.task-py/
```
```

### 変更ファイル

- `README.md`

---

## 4. `reset` コマンド

### 実装方針

- 新コマンド `task-py reset` を追加
- `~/.task-py/` 以下のデータを削除する前に `~/.task-py.backup/` へバックアップ
- 確認プロンプトで「すべてのタスク・プロジェクト・デイリーデータが削除されます」と明示
- `shutil.rmtree` で削除

### フロー

```
task-py reset
  → 確認プロンプト: "すべてのデータ（~/.task-py/）を削除します。この操作は元に戻せません（バックアップは ~/.task-py.backup/ に保存されます）。続行しますか？ [y/N]"
  → Yes: バックアップ作成 → データ削除 → 完了メッセージ
  → No: キャンセルメッセージ
```

### 変更ファイル

- `src/task_cli/cli/commands/reset.py`（新規作成）
- `src/task_cli/cli/main.py`（コマンド登録）

---

## 実装の順序

1. `--version` オプション（`main.py` のみ、影響範囲が小さい）
2. README アンインストールガイド追記
3. `migrate` コマンド安全性向上
4. `reset` コマンド実装

## 依存ライブラリ

新規追加なし。`shutil`・`importlib.metadata`・`urllib.request` はすべて標準ライブラリ。

## テスト戦略

### ユニットテスト
- `--version` の出力フォーマット確認
- GitHub API 失敗時のフォールバック動作
- `reset` のキャンセル動作

### 手動確認
- 実際に `task-py --version` を実行してバージョン表示を確認
- `task-py reset` でデータ削除とバックアップ作成を確認

# 設計書

## アーキテクチャ概要

既存のコマンド層(`task_cli/cli/commands/`)の修正が中心。2コマンドで重複していたバックアップ処理だけを1つのモジュールへ集約する。層は増やさない。

## コンポーネント設計

### 1. `task_cli/backup.py`(新規)

**責務**:
- `create_backup(src, backup_root, keep=5, now=None) -> Path`: `src` を `backup_root` の隣に `<backup_root名>.<YYYYMMDD-HHMMSS>` として複製し、複製先を返す
- 複製に**成功した後**で、世代数が `keep` を超える分を古い順に削除する
- `backup_label(backup_root, keep=5) -> str`: 確認ダイアログ用の文言(退避先の形式と保持世代数)

**実装の要点**:
- 世代名の判定は `^<backup_root名>\.\d{8}-\d{6}(-\d+)?$` に一致するディレクトリのみ。旧 `~/.task-py.backup`(接尾辞なし)は一致しないので世代に数えず、消さない
- 同一秒の衝突は `-1`, `-2` ... の接尾辞で避け、既存の世代を上書きしない
- 古い順は(タイムスタンプ, 接尾辞の数値)で決める。文字列順だと `-10` が `-2` より前に並ぶため
- 複製が途中で失敗したら、作りかけの複製先を削除して例外を再送出する。**この時点で既存世代は1つも消えていない**
- 時刻は `now` 引数で差し替え可能にしてテストしやすくする
- **(段3の指摘で追加)** 今作った世代は削除対象から除く(時計の巻き戻し・DST で名前順が古く見えても、直前の退避を消さない)。`keep < 1` は `ValueError`。`copytree` が `FileExistsError` で失敗したときは、並行実行の相手が作った退避を消さないよう後始末しない

### 2. `reset.py` / `migrate.py`

**責務**: `rmtree` + `copytree` の記述を `create_backup(_PY_DIR, _BACKUP_DIR)` に置き換える。確認ダイアログの文言を `backup_label` に置き換える。

**実装の要点**:
- `_BACKUP_DIR` はモジュール変数のまま残す(テストが monkeypatch で差し替えられるようにする)
- 「バックアップしました」の表示は実際の複製先を表示する

### 3. `project.py` の `list_projects`

**責務**: 行ごとの f-string パディングを rich `Table` に置き換える。

**実装の要点**:
- `Table(box=None, padding=(0, 1), show_header=False)`。列は マーカー / 名前 / タスク数
- 名前列は `overflow="fold"`(**段3の指摘で `no_wrap` から変更**: 狭い端末で `…` に省略すると `project use` に必要な名前が読めなくなるため、折り返す)。タスク数列は `no_wrap=True`。列幅は最長の名前に合わせて自動調整される
- アクティブ行は名前に `green bold`、マーカーに `*`
- Inbox を Table の最終行にし、`dim` スタイルで区別する。`box=None` では `add_section()` が線を描かないため、従来の `─` × 40 の区切りは廃止した(**段3の指摘への対応**)

### 4. `main.py` の `_version_callback`

**責務**: `latest != current` を `Version(latest) > Version(current)` に置き換える。

**実装の要点**:
- 比較は `_is_newer(latest, current) -> bool` に切り出す。`InvalidVersion` は `False`(何も表示しない)
- `_fetch_latest_version` は変更しない

## データフロー

### reset
```
1. 確認ダイアログ(退避先の形式・保持世代数を表示)
2. create_backup: 新世代へ複製 → 成功後に超過分の最古世代を削除
3. ~/.task-py を削除
```
複製が失敗した場合は 3 に進まず、既存の世代も `~/.task-py` も無傷。

## エラーハンドリング戦略

- バックアップ複製の失敗は握りつぶさず例外を伝える。`reset` は削除に進まない(既存と同じ順序を保つ)
- 超過世代の削除に失敗しても、新世代の退避は成功しているので続行する。**(段4の指摘で記録)** 警告は出さず `rmtree(ignore_errors=True)` で黙って無視する簡略化とした(古い世代が1つ余分に残るだけで実害がなく、利用者が取れる対処もないため)

## テスト戦略

### ユニットテスト
- `tests/test_backup.py`(新規): 世代作成 / 保持数超過の削除 / 複製失敗時に既存世代が残る / 同一秒の衝突 / 旧形式ディレクトリに触らない
- `tests/test_cli_reset.py`(新規): `reset` を2回続けても1回目が残る / ダイアログ文言
- `tests/test_migrate.py`(追記): 既存データありの migrate → reset で migrate 前の退避が残る
- `tests/test_project_list.py`(新規): 21文字以上の名前でカラムが揃う / `*` マーカー / Inbox 行
- `tests/test_version_check.py`(新規): `_is_newer` の4ケース + `_version_callback` の出力

**検証の原則**: 追加テストは修正前のコードで失敗することを確認してから修正を入れる(#32 のテストは「前世代が残る」を直接検査する)。

## 依存ライブラリ

```toml
"packaging",
```

transitive で既に環境に入っている(26.2 を確認)。直接 import するため明示宣言する。

## ディレクトリ構造

```
src/task_cli/backup.py              (新規)
src/task_cli/cli/commands/reset.py
src/task_cli/cli/commands/migrate.py
src/task_cli/cli/commands/project.py
src/task_cli/cli/main.py
pyproject.toml
tests/test_backup.py                (新規)
tests/test_cli_reset.py             (新規)
tests/test_project_list.py          (新規)
tests/test_version_check.py         (新規)
tests/test_migrate.py               (追記)
```

## 実装の順序

1. `backup.py` とそのテスト
2. `reset` / `migrate` の置き換えとテスト
3. `project list` の Table 化とテスト
4. `--version` の比較とテスト(`pyproject.toml` に `packaging` を追加)

## セキュリティ考慮事項

- 世代名の正規表現は固定形式のみに一致させ、ユーザー入力は含めない。`rmtree` の対象は一致したディレクトリに限る

## パフォーマンス考慮事項

- 世代の列挙はホーム直下の `iterdir()` 1回のみ

## 将来の拡張性

- `restore` コマンドを足すとき、世代の列挙関数をそのまま使える

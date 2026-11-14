# 設計書

## アーキテクチャ概要

既存の層構造を変えない。`AppError` の階層に読み込み失敗の種別を1つ足し、ストレージの読み込み部で例外を包む。入口(CLI・MCP・Web)は既に `AppError` を扱うので、ストレージが `AppError` を投げれば3つの入口で同じ形(message / cause / remedy)になる。

## コンポーネント設計

### 1. `StorageReadError`(`src/task_cli/exceptions.py`)

- `AppError` のサブクラス。「保存先ファイルを読み込めない」を表す。`InvalidTaskData`(保存前の検証)とは別物

### 2. 読み込み補助(`src/task_cli/storage/yaml_io.py`、新規)

- `read_yaml(path)`: ファイルを開いて `yaml.safe_load` する。`yaml.YAMLError` と `UnicodeDecodeError` を `StorageReadError` に包む。cause は「<パス>: <YAML の問題と行・列>」
- `validated(path, build)`: `build()`(`model_validate` を行う関数)を呼び、pydantic の `ValidationError` を `StorageReadError` に包む。cause は先頭のエラーの項目名と理由
- remedy は共通文言: 「ファイルを手で直す。`<パス>.bak` があればそこから戻す」(`.bak` の有無で文言を分ける)

### 3. ストレージ4本

- `FileStorage.load` / `RoutineStorage.load` / `DailyLogStorage.load_all` / `GlobalConfigStorage.load` が補助を使う
- `TimerStorage` は変更しない(意図的な握りつぶしを維持)

### 4. 入口

- `onboard.overview` と `inbox.inbox` に `except AppError` + `render_error`(他のコマンドと同じ形)を足し、失敗時は終了コード1で終える
- `task_web/api.py` の `_STATUS_BY_ERROR` に `(StorageReadError, 500)` を明記する(既定と同じ値だが、割り当てを意図として残す)

### 5. 文言

- `web.py` の docstring: 「ローカル Web GUI を起動します（127.0.0.1 のみ待ち受け）。」
- `onboard.py` の案内: `💡 task-py daily done <ID> で完了` / `💡 task-py start <ID> でタスクを開始、task-py done <ID> で完了`

## エラーハンドリング戦略

```
[Error] 保存先ファイルを読み込めません
  原因: ~/.task-py/inbox/tasks.yaml: 行3・列1 で構文エラー(...)
  対処: ファイルを手で直してください。~/.task-py/inbox/tasks.yaml.bak があればそこから戻せます
```

## テスト戦略

- `tests/test_storage.py` 等に、壊れた YAML・不正な値・文字コード不正の各ストレージの失敗(`StorageReadError`、cause にパス、remedy)と、タイマーの握りつぶしの回帰
- `tests/test_project_list.py` と同様の CliRunner で、`list` / `overview` / `inbox` が壊れたファイルでトレースバックを出さない
- Web の API で 500 と cause / remedy
- `task-py web --help` に「読み取り専用」が無い
- overview の案内文のコマンドが、typer の登録に実在する

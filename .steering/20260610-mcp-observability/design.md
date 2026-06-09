# 設計書

## アーキテクチャ概要

`@track` デコレータを MCP ツール関数に適用し、呼び出しログを JSONL ファイルに追記する。
FastMCP のミドルウェアは stdio トランスポートに対応していないため、Python デコレータで横断的に実装する。

```
Claude
  → MCP クライアント (stdio)
  → @mcp.tool() + @track でラップされた関数
      → _append_log() → ~/.task-py/mcp_calls.jsonl
      → 元のツール関数（サービス層）
  → 結果を str で返す
```

## コンポーネント設計

### 1. `src/task_mcp/tracking.py`（新規）

**責務**:
- `track` デコレータ: ツール関数をラップし、呼び出しログを記録
- `_append_log()`: JSONL ファイルへの追記
- `read_stats()`: ログファイルを読み込み、集計結果を文字列で返す

**実装の要点**:
- `@functools.wraps(fn)` で `__name__`・`__doc__` を保持（FastMCP の description 登録に必要）
- ログ書き込みは `try/finally` の外側ではなく `finally` 内で行う（例外時も記録）
- ログ書き込み自体が失敗しても例外を握り潰す（ツール本体に影響させない）
- `ok=False` はツール関数が例外を raise した場合のみ（AppError を str で返す場合は `ok=True`）

```python
_LOG_PATH = Path("~/.task-py/mcp_calls.jsonl")

def track(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        ok = True
        try:
            return fn(*args, **kwargs)
        except Exception:
            ok = False
            raise
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            _append_log(fn.__name__, elapsed_ms, ok)
    return wrapper
```

**ログエントリ形式**:
```json
{"ts": "2026-06-10T01:30:00+00:00", "tool": "list_tasks", "elapsed_ms": 12, "ok": true}
```

### 2. `src/task_mcp/server.py`（変更）

**責務**:
- `track` デコレータを全 22 ツールに適用
- `get_mcp_stats` ツールを追加（合計 23 ツール）

**デコレータ適用順序**:
```python
@mcp.tool()   # ① FastMCP に登録（ラップ済み関数を受け取る）
@track        # ② 呼び出し時にログを記録するラッパー
def list_tasks(...) -> str:
    ...
```

`@track` が先に適用されてラッパー関数を作り、`@mcp.tool()` がそのラッパーを登録する。

## データフロー

### ツール呼び出し時

```
1. Claude が list_tasks を呼ぶ
2. wrapper() が start time を記録
3. 元の list_tasks() を実行
4. finally: elapsed_ms を計算し _append_log() を呼ぶ
5. ~/.task-py/mcp_calls.jsonl に 1 行追記
6. 結果を Claude に返す
```

### 統計取得時

```
1. Claude が get_mcp_stats を呼ぶ
2. read_stats() が ~/.task-py/mcp_calls.jsonl を読み込む
3. Counter でツール別呼び出し回数を集計
4. 多い順にソートして文字列を生成
5. Claude に返す
```

## エラーハンドリング戦略

- `_append_log()` 内の例外はすべて握り潰す（`except Exception: pass`）
  - ログ書き込み失敗でツール本体を止めない
- `read_stats()` でログファイルが存在しない場合は「ログがまだありません」を返す
- 不正な JSONL 行は `json.JSONDecodeError` を無視してスキップ

## テスト戦略

### ユニットテスト（`tests/test_mcp_server.py` に追記）

- `track` デコレータが JSONL ファイルに書き込むことを確認
- `read_stats()` が正しい集計文字列を返すことを確認
- `get_mcp_stats` ツールの呼び出しテスト
- ログファイルが存在しない場合のフォールバック確認

## 依存ライブラリ

新規追加なし（`json`・`time`・`functools`・`collections` はすべて標準ライブラリ）

## ディレクトリ構造

```
src/task_mcp/
├── __init__.py
├── __main__.py
├── server.py      # 変更: @track 追加、get_mcp_stats 追加
└── tracking.py    # 新規
```

## 実装の順序

1. `src/task_mcp/tracking.py` を新規作成
2. `src/task_mcp/server.py` に `@track` を全ツールに適用
3. `get_mcp_stats` ツールを `server.py` に追加
4. `tests/test_mcp_server.py` にテストを追加
5. 品質チェック（pytest + pyright）
6. README のツール一覧に `get_mcp_stats` を追記

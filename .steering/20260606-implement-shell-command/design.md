# 設計書

## アーキテクチャ概要

既存の Clean Architecture に `shell` コマンドを追加する。
シェル内部でも既存の CLI コマンド関数をそのまま再利用する。

```
task-py shell
    ↓
InteractiveShell.run()          ← REPL ループ
    ↓ 入力をパース
parse_input(line) → args[]
    ↓ コマンド実行
_run_command(args)
    ↓ typer の app を直接呼び出す
app(args, standalone_mode=False)
```

## コンポーネント設計

### 1. `src/task_cli/cli/shell.py`（新規）

**責務**: REPL ループ・入力パース・Tab 補完・プロンプト生成

```python
class InteractiveShell:
    def run(self) -> None           # REPL メインループ
    def _run_command(args: list[str]) -> None  # コマンド実行

def parse_input(line: str) -> list[str] | None
    # クォート処理付きの引数パーサ（TypeScript 版と同仕様）
    # 未閉じクォートの場合は None を返す

def get_prompt(config_service: GlobalConfigService) -> str
    # 例: "task [myapp]> " or "task [inbox]> "

def build_completer(app: typer.Typer) -> Completer
    # prompt_toolkit の WordCompleter を返す
```

### 2. `src/task_cli/cli/commands/shell.py`（新規）

**責務**: typer コマンドとして `shell` を登録するだけのシム

```python
def shell() -> None:
    """インタラクティブシェルを起動します。"""
    InteractiveShell().run()
```

### 3. `src/task_cli/cli/main.py`（更新）

`shell` コマンドを登録する。

## 実装の要点

### prompt_toolkit の使用

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

session = PromptSession(completer=completer, history=InMemoryHistory())
line = session.prompt(get_prompt(config_service))
```

- `PromptSession` が Tab 補完・Ctrl+C / Ctrl+D ハンドリングを担当
- `WordCompleter` でサブコマンド名を補完
- `EOFError` (Ctrl+D) / `KeyboardInterrupt` (Ctrl+C) で正常終了

### コマンド実行

typer の `app` を `standalone_mode=False` で呼び出す。
これにより `SystemExit` が抑制され、シェルが終了しない。

```python
from task_cli.cli.main import app

try:
    app(args=["task-py"] + args, standalone_mode=False)
except SystemExit:
    pass  # コマンドエラーでも継続
except Exception as e:
    print(f"エラー: {e}")
```

### Tab 補完の実装

typer アプリからサブコマンド名を取得して `WordCompleter` を構築:

```python
from prompt_toolkit.completion import WordCompleter

def build_completer(app: typer.Typer) -> WordCompleter:
    commands = [cmd.name for cmd in app.registered_commands if cmd.name]
    return WordCompleter(commands, sentence=True)
```

## データフロー

```
1. shell 起動
2. PromptSession 生成（Tab 補完・履歴付き）
3. プロンプト表示（アクティブプロジェクトを毎回取得）
4. 入力受付
   - 空行 → 3へ
   - exit / quit → 終了
   - クォートエラー → エラー表示して 3へ
   - それ以外 → app() 実行 → 3へ
5. EOFError / KeyboardInterrupt → 終了
```

## エラーハンドリング戦略

| ケース | 対処 |
|--------|------|
| `SystemExit` (typer がコマンドエラー時に発行) | キャッチして継続 |
| `Exception` | メッセージ表示して継続 |
| `EOFError` (Ctrl+D) | 正常終了 |
| `KeyboardInterrupt` (Ctrl+C) | 正常終了 |
| 未閉じクォート | エラーメッセージ表示して継続 |

## テスト戦略

### ユニットテスト（`tests/test_shell.py`）

- `parse_input` のクォート処理（正常系・異常系）
- `get_prompt` のプロジェクト名表示

### 統合テスト

対話的な REPL は自動テストが困難なため、手動動作確認を重視する。

## 依存ライブラリ

```toml
[project]
dependencies = [
    "prompt-toolkit",  # 追加
    ...
]
```

## ディレクトリ構造

```
src/task_cli/
├── cli/
│   ├── commands/
│   │   ├── shell.py      (新規: typer コマンド登録)
│   │   └── ...
│   ├── shell.py          (新規: InteractiveShell, parse_input 等)
│   └── main.py           (更新: shell コマンド追加)
tests/
└── test_shell.py         (新規)
```

## 実装の順序

1. `prompt-toolkit` を依存関係に追加
2. `src/task_cli/cli/shell.py` — コアロジック実装
3. `tests/test_shell.py` — ユニットテスト
4. `src/task_cli/cli/commands/shell.py` — typer コマンド
5. `main.py` に登録
6. 品質チェック・手動動作確認
7. README 更新

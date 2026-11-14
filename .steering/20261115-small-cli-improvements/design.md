# 設計書

## アーキテクチャ概要

既存の層構造は変えない。表示は `cli/renderer.py` と `cli/commands/daily.py`、補完は `cli/shell.py` に閉じる。

## コンポーネント設計

### 1. show の解禁日(`cli/renderer.py`)

- `render_task_detail` の `Due` の次に `Sched` の行を足す。`scheduled_date > 今日` のとき `（まだ着手できません）` を黄色で併記
- 「今日」は `start` の判定(`services/task_manager.py` の `datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")`)と同じ式にする。判定のずれ(表示は着手可・実際は不可)を作らない
- 日付の文字列比較で足りる(`YYYY-MM-DD` はモデルが保証)

### 2. シェル補完(`cli/shell.py`)

- `build_completer(app)` が `typer.main.get_command(app)`(click のコマンドツリー)をたどって、`Completer` の自作クラス `CommandCompleter` を返す
- 補完のロジック: 入力済みの語を左から読み、(a) グループ・コマンドをたどる、(b) 直前の語が「列挙値を取るオプション」なら、その値の候補、(c) それ以外で現在の語が空か `-` で始まるなら、そのコマンドのオプション名(と、グループならサブコマンド)
- 列挙値は click のオプションの型 `click.Choice` から取る(typer の Enum オプションは `Choice` になる)
- 戻り値の型は従来の `WordCompleter` から変わる。呼び出し元は `InteractiveShell.run` のみで、`PromptSession(completer=...)` に渡すだけ
- 未知のコマンドの後ろでは候補なし(例外を投げない)

### 3. daily stats のバー(`cli/commands/daily.py`)

- `_bar(rate)`: `round(rate * 10)` 個の `█` と残りの `░`(固定幅10)。`None` は呼び出し側で `--` にする
- 列は「バー 数値」(例 `█████░░░░░ 50%`)

## テスト戦略

- `tests/test_cli_show.py`(新規または既存の拡張): 解禁日の有無・未来・過去・今日
- `tests/test_shell.py` に補完のテスト: `prompt_toolkit.document.Document` を `get_completions` に渡す
- `tests/test_daily_stats_bar.py`: `_bar` の 0 / 0.5 / 1 と、`daily stats` の出力で `None` が `--`

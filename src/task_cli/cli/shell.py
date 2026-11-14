from collections.abc import Iterable

import click
import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from task_cli.cli.renderer import render_error
from task_cli.exceptions import AppError
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.storage.global_config_storage import GlobalConfigStorage


def parse_input(line: str) -> list[str] | None:
    """クォート処理付き引数パーサ。未閉じクォートの場合は None を返す。"""
    args: list[str] = []
    current = ""
    in_single = False
    in_double = False

    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == " " and not in_single and not in_double:
            if current:
                args.append(current)
                current = ""
        else:
            current += ch

    if in_single or in_double:
        return None

    if current:
        args.append(current)
    return args


def get_prompt(config_service: GlobalConfigService) -> str:
    project = config_service.get_active_project()
    label = project if project else "inbox"
    return f"task [{label}]> "


class CommandCompleter(Completer):
    """コマンド → サブコマンド → オプション名 → 列挙値の順に補完する。

    候補は typer が組み立てた click のコマンドツリーから取るので、コマンドや
    オプションを足しても、ここを手で直す必要はない。`NestedCompleter` を使わない
    のは、オプションの値を入れたあとに、他のオプションが補完されなくなるため
    （`add x --priority high --` で候補が出ない）。

    プロジェクト名のような実行時に変わる候補は扱わない。
    """

    def __init__(self, root: click.Command) -> None:
        self._root = root

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text_before_cursor
        words = parse_input(text)
        if words is None:  # 閉じていないクォートの中は補完しない
            return
        if text.endswith(" ") or not words:
            done, current = words, ""
        else:
            # 入力中の語にクォートが混ざるときは補完しない（クォートを外した語で
            # 置き換えると、入力行を壊す）
            if any(q in text.rsplit(" ", 1)[-1] for q in "'\""):
                return
            done, current = words[:-1], words[-1]

        command = self._root
        expecting: click.Option | None = None  # 値を待っているオプション
        for word in done:
            if expecting is not None:
                expecting = None  # この語はオプションの値
                continue
            if isinstance(command, click.Group) and word in command.commands:
                command = command.commands[word]
                continue
            option = _find_option(command, word)
            if option is not None:
                if not option.is_flag and option.nargs == 1:
                    expecting = option
                continue
            if word.startswith("-"):
                continue  # 知らないオプションは、値を取らないものとして読み飛ばす
            if isinstance(command, click.Group):
                return  # 知らないコマンドの後ろは補完しない

        candidates: list[str] = []
        if expecting is not None:
            if isinstance(expecting.type, click.Choice):
                candidates = [str(c) for c in expecting.type.choices]
        else:
            if isinstance(command, click.Group):
                candidates += sorted(command.commands)
            if current.startswith("-"):
                for param in command.get_params(click.Context(command)):
                    if isinstance(param, click.Option):
                        candidates += [*param.opts, *param.secondary_opts]
        for candidate in candidates:
            if candidate.startswith(current):
                yield Completion(candidate, start_position=-len(current))


def _find_option(command: click.Command, word: str) -> click.Option | None:
    for param in command.get_params(click.Context(command)):
        if isinstance(param, click.Option) and word in (*param.opts, *param.secondary_opts):
            return param
    return None


def build_completer(app: typer.Typer) -> CommandCompleter:
    return CommandCompleter(typer.main.get_command(app))


class InteractiveShell:
    def __init__(self) -> None:
        self._config_service = GlobalConfigService(GlobalConfigStorage())

    def run(self) -> None:
        from task_cli.cli.main import app

        completer = build_completer(app)
        session: PromptSession[str] = PromptSession(
            completer=completer,
            history=InMemoryHistory(),
        )

        typer.echo("task-py インタラクティブシェル（exit / quit で終了）")

        from task_cli.cli.commands.onboard import overview
        overview()

        while True:
            try:
                prompt = get_prompt(self._config_service)
                line = session.prompt(prompt)
            except EOFError:
                break
            except KeyboardInterrupt:
                break

            trimmed = line.strip()
            if not trimmed:
                continue
            if trimmed in ("exit", "quit"):
                break

            args = parse_input(trimmed)
            if args is None:
                typer.echo("エラー: クォートが閉じられていません")
                continue

            self._run_command(args)

        typer.echo("")

    def _run_command(self, args: list[str]) -> None:
        from task_cli.cli.main import app

        try:
            app(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except AppError as e:
            # コマンドが捕捉しそこねても、原因と対処を出す（メッセージだけにしない）
            render_error(e)
        except Exception as e:
            typer.echo(f"エラー: {e}")

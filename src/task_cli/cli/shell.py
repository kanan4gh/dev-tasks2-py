import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory

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


def build_completer(app: typer.Typer) -> WordCompleter:
    commands = [cmd.name for cmd in app.registered_commands if cmd.name]
    # サブアプリのコマンドも追加（例: project create）
    for group in app.registered_groups:
        if group.name and group.typer_instance:
            for cmd in group.typer_instance.registered_commands:
                if cmd.name:
                    commands.append(f"{group.name} {cmd.name}")
    return WordCompleter(commands, sentence=True)


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

        from task_cli.cli.commands.onboard import onboard
        onboard()

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
        except Exception as e:
            typer.echo(f"エラー: {e}")

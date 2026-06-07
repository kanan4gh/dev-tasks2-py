import json
import urllib.error
import urllib.request
from importlib.metadata import version as pkg_version
from typing import Annotated, Optional

import typer

from task_cli.cli.commands.add import add
from task_cli.cli.commands.migrate import migrate
from task_cli.cli.commands.archive import archive
from task_cli.cli.commands.daily import daily_app
from task_cli.cli.commands.edit import edit
from task_cli.cli.commands.schedule import schedule as schedule_cmd
from task_cli.cli.commands.delete import delete
from task_cli.cli.commands.done import done
from task_cli.cli.commands.inbox import inbox
from task_cli.cli.commands.list import list_tasks
from task_cli.cli.commands.move import move
from task_cli.cli.commands.onboard import onboard
from task_cli.cli.commands.project import project_app
from task_cli.cli.commands.reset import reset
from task_cli.cli.commands.search import search
from task_cli.cli.commands.shell import shell
from task_cli.cli.commands.time import time_app
from task_cli.cli.commands.show import show
from task_cli.cli.commands.start import start

GITHUB_REPO = "kanan4gh/dev-tasks2-py"

app = typer.Typer(help="task-py - タスク管理ツール", invoke_without_command=True)

app.command("add")(add)
app.command("edit")(edit)
app.command("list")(list_tasks)
app.command("show")(show)
app.command("start")(start)
app.command("done")(done)
app.command("delete")(delete)
app.command("archive")(archive)
app.command("move")(move)
app.command("inbox")(inbox)
app.command("schedule")(schedule_cmd)
app.command("search")(search)
app.command("onboard")(onboard)
app.command("migrate")(migrate)
app.command("reset")(reset)
app.command("shell")(shell)
app.add_typer(project_app, name="project")
app.add_typer(daily_app, name="daily")
app.add_typer(time_app, name="time")


def _fetch_latest_version() -> Optional[str]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "task-py"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            return tag.lstrip("v") or None
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _version_callback(value: bool) -> None:
    if not value:
        return
    current = pkg_version("dev-tasks2-py")
    typer.echo(f"task-py version {current}")
    latest = _fetch_latest_version()
    if latest and latest != current:
        typer.echo(
            f"\n新しいバージョン {latest} が利用可能です。\n"
            f"アップデートするには以下を実行してください:\n"
            f"  uv tool install git+https://github.com/{GITHUB_REPO} --force"
        )
    raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=_version_callback, is_eager=True, help="バージョンを表示"),
    ] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()

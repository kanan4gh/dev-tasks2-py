import typer

from task_cli.cli.commands.add import add
from task_cli.cli.commands.archive import archive
from task_cli.cli.commands.delete import delete
from task_cli.cli.commands.done import done
from task_cli.cli.commands.inbox import inbox
from task_cli.cli.commands.list import list_tasks
from task_cli.cli.commands.move import move
from task_cli.cli.commands.project import project_app
from task_cli.cli.commands.show import show
from task_cli.cli.commands.start import start

app = typer.Typer(help="task-py - タスク管理ツール", invoke_without_command=True)

app.command("add")(add)
app.command("list")(list_tasks)
app.command("show")(show)
app.command("start")(start)
app.command("done")(done)
app.command("delete")(delete)
app.command("archive")(archive)
app.command("move")(move)
app.command("inbox")(inbox)
app.add_typer(project_app, name="project")


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()

import typer

from task_cli.cli.commands.add import add
from task_cli.cli.commands.list import list_tasks
from task_cli.cli.commands.show import show

app = typer.Typer(help="Task CLI - タスク管理ツール", invoke_without_command=True)

app.command("add")(add)
app.command("list")(list_tasks)
app.command("show")(show)


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()

import shutil
from pathlib import Path

import typer
from rich.console import Console

_PY_DIR = Path("~/.task-py").expanduser()
_BACKUP_DIR = Path("~/.task-py.backup").expanduser()

console = Console()


def reset() -> None:
    """~/.task-py/ のすべてのデータを削除します（削除前にバックアップを作成します）。"""
    if not _PY_DIR.exists() or not any(_PY_DIR.iterdir()):
        console.print("[yellow]削除するデータがありません。[/yellow]")
        raise typer.Exit()

    confirmed = typer.confirm(
        f"\n{_PY_DIR} のすべてのデータ（タスク・プロジェクト・デイリー）を削除します。\n"
        f"この操作は元に戻せません（バックアップは {_BACKUP_DIR} に保存されます）。\n"
        f"続行しますか？"
    )
    if not confirmed:
        console.print("[yellow]リセットをキャンセルしました。[/yellow]")
        raise typer.Exit()

    if _BACKUP_DIR.exists():
        shutil.rmtree(_BACKUP_DIR)
    shutil.copytree(_PY_DIR, _BACKUP_DIR)
    console.print(f"[dim]データを {_BACKUP_DIR} にバックアップしました。[/dim]")

    shutil.rmtree(_PY_DIR)
    console.print(f"[green]{_PY_DIR} のデータをすべて削除しました。[/green]")

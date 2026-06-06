from task_cli.cli.shell import InteractiveShell


def shell() -> None:
    """インタラクティブシェルを起動します。"""
    InteractiveShell().run()

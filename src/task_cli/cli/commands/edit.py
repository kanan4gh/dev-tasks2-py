import sys
from typing import Optional

import typer

from task_cli.cli.deps import get_use_case
from task_cli.cli.editor import open_editor
from task_cli.cli.renderer import render_error, render_info, render_success
from task_cli.exceptions import AppError
from task_cli.models.task import Priority

_NO_FIELDS_ERROR = AppError(
    "変更するフィールドを指定してください。",
    cause="オプションが何も指定されておらず、対話端末ではないためエディタを起動できません。",
    remedy=(
        "-t/--title, -d/--description, -p/--priority, --due, --due-clear, "
        "--scheduled, --scheduled-clear のいずれかを指定してください。"
        "対話端末では引数なしで実行すると $EDITOR が開きます。"
    ),
)


def _is_interactive() -> bool:
    """エディタを起動してよい端末か。

    非対話（CI・パイプ・リダイレクト）でエディタを開くと戻ってこられないため、
    その場合は従来どおりエラーで終了する。
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def _description_after_edit(edited: str | None, current: str) -> str | None:
    """エディタの結果から、実際に適用する説明を決める。None なら変更しない。

    保存せずに閉じた場合（`edited is None`）と、元の内容へ戻した場合は
    どちらも「やっぱり変えない」という意思とみなす。`-d` の値を初期値として
    渡していた場合でも、戻したのなら `-d` の値を通してはいけない。
    """
    if edited is None or edited == current:
        return None
    return edited


def edit(
    id: int = typer.Argument(..., help="タスクID"),
    title: Optional[str] = typer.Option(None, "-t", "--title", help="タイトルを変更"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="説明を変更"),
    priority: Optional[Priority] = typer.Option(None, "-p", "--priority", help="優先度を変更 (high/medium/low)"),
    due: Optional[str] = typer.Option(None, "--due", help="期限を設定 (YYYY-MM-DD)"),
    due_clear: bool = typer.Option(False, "--due-clear", help="期限を削除"),
    scheduled: Optional[str] = typer.Option(None, "--scheduled", help="解禁日を設定 (YYYY-MM-DD)"),
    scheduled_clear: bool = typer.Option(False, "--scheduled-clear", help="解禁日を削除"),
    use_editor: bool = typer.Option(False, "-e", "--editor", help="説明を $EDITOR で編集する"),
) -> None:
    """タスクを編集します。

    オプションを指定せずに実行すると、対話端末では $EDITOR が開き説明を編集できます。
    """
    other_flags = [title, priority, due, due_clear, scheduled, scheduled_clear]
    has_flags = any(other_flags) or description is not None

    if not has_flags and not use_editor:
        if not _is_interactive():
            render_error(_NO_FIELDS_ERROR)
            raise typer.Exit(code=1)
        use_editor = True

    try:
        uc = get_use_case()

        if use_editor:
            current = uc.get_task(id)
            # -d と -e を併用した場合は、-d の値をエディタの初期値にする
            initial = description if description is not None else current.description
            description = _description_after_edit(open_editor(initial), current.description)
            if description is None and not any(other_flags):
                render_info("変更はありませんでした")
                return

        task = uc.edit_task(
            id,
            title=title,
            description=description,
            priority=priority,
            due_date=due,
            clear_due_date=due_clear,
            scheduled_date=scheduled,
            clear_scheduled_date=scheduled_clear,
        )
        render_success(f"タスク ID {task.id} を更新しました")
    except AppError as e:
        render_error(e)
        raise typer.Exit(code=1)

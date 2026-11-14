from task_cli.cli.deps import get_global_config_service
from task_cli.cli.renderer import handle_app_errors, render_success


@handle_app_errors
def inbox() -> None:
    """Inbox モードに切り替えます（アクティブプロジェクトを解除）。"""
    svc = get_global_config_service()
    svc.set_active_project(None)
    render_success("Inbox モードに切り替えました")

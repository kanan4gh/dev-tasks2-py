from pathlib import Path
from typing import TYPE_CHECKING, Callable

from task_cli.models.task import Priority, Task, TaskStatus
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.task_manager import TaskFilter, TaskManager
from task_cli.storage.atomic import locked
from task_cli.storage.file_storage import FileStorage
from task_cli.usecases.project_target import ACTIVE_PROJECT, ProjectTarget, ActiveProject

if TYPE_CHECKING:
    from task_cli.usecases.time_tracking_usecase import TimeTrackingUseCase


def resolve_storage_path(active_project: str | None) -> Path:
    if active_project:
        return Path(f"~/.task-py/projects/{active_project}/tasks.yaml").expanduser()
    return Path("~/.task-py/inbox/tasks.yaml").expanduser()


class TaskCrudUseCase:
    def __init__(
        self,
        global_config_service: GlobalConfigService,
        storage_factory: Callable[[Path], FileStorage] | None = None,
        time_tracking: "TimeTrackingUseCase | None" = None,
    ) -> None:
        self._global_config_service = global_config_service
        self._storage_factory: Callable[[Path], FileStorage] = storage_factory or FileStorage
        # タスクを終える／消すときに実行中タイマーを孤児にしないための後始末。
        # CLI ではなくここに置くのは、MCP からも同じ経路を通す必要があるため。
        self._time_tracking = time_tracking

    def _resolve(self, project: ProjectTarget) -> str | None:
        """`ProjectTarget` を具体的なプロジェクト名（`None` は Inbox）へ解決する。"""
        if isinstance(project, ActiveProject):
            return self._global_config_service.get_active_project()
        return project

    def _get_manager(self, project: ProjectTarget = ACTIVE_PROJECT) -> TaskManager:
        path = resolve_storage_path(self._resolve(project))
        return TaskManager(self._storage_factory(path))

    def _release_timer(self, id: int, record: bool, project: ProjectTarget) -> None:
        """対象タスクのタイマーが実行中なら解除する。

        `time_tracking` を渡さずに組み立てた場合は何もしない。既定でタイマー
        ストレージを掴みに行くと、単体テストが実ホームの `~/.task-py/timer.yaml`
        を読み書きしてしまうため、依存を暗黙に生成しない。本番の組み立ては
        `cli/deps.py` の `get_use_case()` に集約されている。

        照合に使うのは**解決後のプロジェクト名**であってグローバルのアクティブ
        ではない。`project` を明示して別プロジェクトのタスクを完了させたとき、
        アクティブ側のタイマーを巻き添えで畳んでしまうため。
        """
        if self._time_tracking is None:
            return
        self._time_tracking.clear_timer_for_task(self._resolve(project), id, record=record)

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
        project: ProjectTarget = ACTIVE_PROJECT,
    ) -> Task:
        return self._get_manager(project).create_task(title, description, priority, due_date)

    def list_tasks(
        self, filter: TaskFilter | None = None, project: ProjectTarget = ACTIVE_PROJECT
    ) -> list[Task]:
        return self._get_manager(project).list_tasks(filter)

    def list_all_projects(self, filter: TaskFilter | None = None) -> dict[str | None, list[Task]]:
        config = self._global_config_service.get_all()
        result: dict[str | None, list[Task]] = {}
        result[None] = TaskManager(self._storage_factory(resolve_storage_path(None))).list_tasks(filter)
        for project in config.projects:
            result[project.name] = TaskManager(self._storage_factory(resolve_storage_path(project.name))).list_tasks(filter)
        return result

    def list_inbox_tasks(self, filter: TaskFilter | None = None) -> list[Task]:
        return TaskManager(self._storage_factory(resolve_storage_path(None))).list_tasks(filter)

    def get_task(self, id: int, project: ProjectTarget = ACTIVE_PROJECT) -> Task:
        return self._get_manager(project).get_task(id)

    def start_task(self, id: int, project: ProjectTarget = ACTIVE_PROJECT) -> Task:
        return self._get_manager(project).start_task(id)

    def complete_task(self, id: int, project: ProjectTarget = ACTIVE_PROJECT) -> Task:
        return self._transition_with_timer(id, TaskStatus.COMPLETED, project)

    def archive_task(self, id: int, project: ProjectTarget = ACTIVE_PROJECT) -> Task:
        return self._transition_with_timer(id, TaskStatus.ARCHIVED, project)

    def _transition_with_timer(
        self, id: int, new_status: TaskStatus, project: ProjectTarget = ACTIVE_PROJECT
    ) -> Task:
        """タイマーを畳んでから状態遷移する。

        遷移できるかを先に確かめるのは、遷移が失敗する場合に実行中タイマーを
        巻き添えで止めないためである（ユーザーにはエラーしか見えないので、
        裏でタイマーが止まっていることに気づけない）。
        遷移そのものの検証と例外送出は `TaskManager` 側に任せる。
        """
        manager = self._get_manager(project)
        if manager.get_task(id).can_transition_to(new_status):
            # 先にタイマーを畳んで作業時間を確定させる。逆順にすると
            # 完了済みタスクに後からセッションが足される。
            self._release_timer(id, record=True, project=project)
        if new_status is TaskStatus.COMPLETED:
            return manager.complete_task(id)
        return manager.archive_task(id)

    def delete_task(self, id: int, project: ProjectTarget = ACTIVE_PROJECT) -> None:
        # 記録先ごと消えるため、記録はせずタイマーの解除だけ行う
        self._release_timer(id, record=False, project=project)
        self._get_manager(project).delete_task(id)

    def edit_task(
        self,
        id: int,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: str | None = None,
        clear_due_date: bool = False,
        scheduled_date: str | None = None,
        clear_scheduled_date: bool = False,
        project: ProjectTarget = ACTIVE_PROJECT,
    ) -> Task:
        return self._get_manager(project).edit_fields(
            id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            clear_due_date=clear_due_date,
            scheduled_date=scheduled_date,
            clear_scheduled_date=clear_scheduled_date,
        )

    def set_scheduled_date(
        self, id: int, date: str | None, project: ProjectTarget = ACTIVE_PROJECT
    ) -> Task:
        return self._get_manager(project).set_scheduled_date(id, date)

    def search_tasks(self, keyword: str, project: ProjectTarget = ACTIVE_PROJECT) -> list[Task]:
        return self._get_manager(project).search_tasks(keyword)

    def move_task(
        self, id: int, target_project: str | None, project: ProjectTarget = ACTIVE_PROJECT
    ) -> Task:
        src_project = self._resolve(project)
        src_storage = self._storage_factory(resolve_storage_path(src_project))
        dst_storage = self._storage_factory(resolve_storage_path(target_project))

        # ロックの取得にはロックファイルを置く場所が要るので、先に
        # `ensure_directory()` が必要になる。ただしそれを無条件に行うと、
        # 存在しないタスクを move しようとしただけで空のプロジェクト
        # ディレクトリが残る（`config.yaml` に載らない見えないゴミになる）。
        # そこでロックの外で存在確認だけ先に済ませ、失敗はここで返す。
        # 権威ある読み取りはロックを取ったあとで改めて行う。
        TaskManager(src_storage).get_task(id)

        src_storage.ensure_directory()
        dst_storage.ensure_directory()

        # 2ファイルに跨る操作なので、両方のロックを1つの区間で握る。`locked` が
        # パスを正規化してソート順に取得するため、A→B と B→A の move を同時に
        # 走らせてもデッドロックしない。
        with locked(src_storage.path, dst_storage.path):
            src_manager = TaskManager(src_storage)
            task = src_manager.get_task(id)
            dst_manager = TaskManager(dst_storage)

            new_id = dst_manager.next_id()
            new_task = task.model_copy(update={"id": new_id})
            dst_tasks = dst_storage.load()
            dst_tasks.append(new_task)
            dst_storage.save(dst_tasks)

            src_manager.delete_task(id)

        # 移動先で採番し直されるため、実行中タイマーの向き先も付け替える。
        # 付け替えないと存在しない ID を指したままになり、停止時に記録が黙って
        # 落ちるうえ、移動元で ID が再利用されると別のタスクに記録されてしまう。
        if self._time_tracking is not None:
            self._time_tracking.retarget_timer_for_task(
                src_project,
                id,
                target_project,
                new_id,
            )
        return new_task

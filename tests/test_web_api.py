from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from task_cli.cli.deps import get_use_case
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_web.server import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """`~/.task-py/` を tmp_path に隔離した状態のクライアント。

    既定パスは `__init__` で `~` を展開するので、HOME の差し替えが効く
    （`tests/test_storage.py::TestDefaultPathsFollowHome` が担保）。
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # `testserver` は TestClient の既定 base_url。本番の許可リストには入れず、
    # ここで明示的に渡す（本番に残すと DNS リバインディング対策が弱まる）。
    with TestClient(create_app(["127.0.0.1", "localhost", "testserver"])) as c:
        yield c


def seed(active: str | None = None, projects: tuple[str, ...] = ()) -> None:
    service = ProjectService(GlobalConfigStorage())
    for name in projects:
        service.create_project(name)
    if active is None:
        config = GlobalConfigStorage().load()
        config.active_project = None
        GlobalConfigStorage().save(config)
    else:
        service.use_project(active)


class TestState:
    def test_returns_projects_and_revision(self, client: TestClient) -> None:
        seed(active="foo", projects=("foo", "bar"))
        body = client.get("/api/state").json()

        assert body["active_project"] == "foo"
        assert [p["name"] for p in body["projects"]] == ["foo", "bar"]
        assert body["revision"]

    def test_works_on_a_fresh_machine(self, client: TestClient) -> None:
        """~/.task-py/ がまだ無くても 200 で空の状態を返す。"""
        response = client.get("/api/state")
        assert response.status_code == 200
        assert response.json()["projects"] == []


class TestTaskListing:
    def test_all_tasks_groups_inbox_and_projects(self, client: TestClient) -> None:
        seed(projects=("foo",))
        uc = get_use_case()
        uc.add_task("Inbox のタスク", project=None)
        uc.add_task("foo のタスク", project="foo")

        body = client.get("/api/tasks").json()
        assert [t["title"] for t in body["inbox"]] == ["Inbox のタスク"]
        assert [t["title"] for t in body["projects"]["foo"]] == ["foo のタスク"]

    def test_project_listing_ignores_the_active_project(self, client: TestClient) -> None:
        """アクティブが bar でも /api/projects/foo/tasks は foo を返す。

        GUI は全プロジェクトを同時に扱う面なので、プロセス外の共有状態
        （config.yaml の activeProject）に依存してはいけない。
        """
        seed(active="bar", projects=("foo", "bar"))
        uc = get_use_case()
        uc.add_task("foo のタスク", project="foo")
        uc.add_task("bar のタスク", project="bar")

        body = client.get("/api/projects/foo/tasks").json()
        assert body["project"] == "foo"
        assert [t["title"] for t in body["tasks"]] == ["foo のタスク"]

    def test_inbox_and_a_project_named_inbox_coexist(self, client: TestClient) -> None:
        """`inbox` という名前のプロジェクトを作っても Inbox と衝突しない。"""
        seed(projects=("inbox",))
        uc = get_use_case()
        uc.add_task("本物の Inbox", project=None)
        uc.add_task("inbox という名前のプロジェクト", project="inbox")

        real_inbox = client.get("/api/inbox/tasks").json()
        named = client.get("/api/projects/inbox/tasks").json()

        assert [t["title"] for t in real_inbox["tasks"]] == ["本物の Inbox"]
        assert real_inbox["project"] is None
        assert [t["title"] for t in named["tasks"]] == ["inbox という名前のプロジェクト"]
        assert named["project"] == "inbox"

    def test_summary_omits_work_sessions(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        task = client.get("/api/inbox/tasks").json()["tasks"][0]

        assert "work_sessions" not in task
        assert task["total_worked_seconds"] == 0
        assert task["work_session_count"] == 0


class TestTaskDetail:
    def test_includes_total_worked_seconds(self, client: TestClient) -> None:
        """`@property` なので model_dump() には出ない派生値。"""
        get_use_case().add_task("タスク", project=None)
        body = client.get("/api/inbox/tasks/1").json()

        assert body["task"]["title"] == "タスク"
        assert body["task"]["total_worked_seconds"] == 0
        assert body["task"]["work_sessions"] == []

    def test_missing_task_is_404_with_cause_and_remedy(self, client: TestClient) -> None:
        response = client.get("/api/inbox/tasks/999")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["message"] == "タスクが見つかりません。"
        assert "999" in error["cause"]
        assert error["remedy"]

    def test_missing_project_is_404(self, client: TestClient) -> None:
        response = client.get("/api/projects/nope/tasks")
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "プロジェクトが見つかりません。"


class TestFilters:
    def test_status_and_priority_and_sort(self, client: TestClient) -> None:
        from task_cli.models.task import Priority

        uc = get_use_case()
        uc.add_task("低", priority=Priority.LOW, project=None)
        uc.add_task("高", priority=Priority.HIGH, project=None)
        uc.start_task(1, project=None)

        in_progress = client.get("/api/inbox/tasks?status=in_progress").json()
        assert [t["title"] for t in in_progress["tasks"]] == ["低"]

        high = client.get("/api/inbox/tasks?priority=high").json()
        assert [t["title"] for t in high["tasks"]] == ["高"]

        by_priority = client.get("/api/inbox/tasks?sort=priority").json()
        assert [t["title"] for t in by_priority["tasks"]] == ["高", "低"]

    def test_repeated_status(self, client: TestClient) -> None:
        uc = get_use_case()
        uc.add_task("A", project=None)
        uc.add_task("B", project=None)
        uc.start_task(2, project=None)

        body = client.get("/api/inbox/tasks?status=open&status=in_progress").json()
        assert len(body["tasks"]) == 2

    @pytest.mark.parametrize(
        "query", ["status=bogus", "priority=bogus", "sort=bogus"]
    )
    def test_unknown_values_are_400(self, client: TestClient, query: str) -> None:
        """黙って全件を返さない。絞り込みが効いていないことに気づけなくなる。"""
        response = client.get(f"/api/inbox/tasks?{query}")
        assert response.status_code == 400
        assert response.json()["error"]["remedy"]


class TestSearch:
    def test_searches_across_projects(self, client: TestClient) -> None:
        seed(projects=("foo",))
        uc = get_use_case()
        uc.add_task("検索対象 Inbox", project=None)
        uc.add_task("検索対象 foo", project="foo")
        uc.add_task("無関係", project="foo")

        body = client.get("/api/search?q=検索対象").json()
        assert [t["title"] for t in body["inbox"]] == ["検索対象 Inbox"]
        assert [t["title"] for t in body["projects"]["foo"]] == ["検索対象 foo"]
        assert body["query"] == "検索対象"

    def test_empty_query_is_400(self, client: TestClient) -> None:
        assert client.get("/api/search?q=").status_code == 400
        assert client.get("/api/search").status_code == 400


class TestOverview:
    def test_returns_the_pieces_the_cli_shows(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        body = client.get("/api/overview").json()

        assert set(body) == {"active_project", "routines", "daily_stats", "timer", "tasks"}
        assert body["timer"] is None
        assert [t["title"] for t in body["tasks"]["inbox"]] == ["タスク"]


class TestReadOnly:
    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    @pytest.mark.parametrize(
        "path", ["/api/tasks", "/api/inbox/tasks", "/api/inbox/tasks/1", "/api/state"]
    )
    def test_write_methods_are_rejected(
        self, client: TestClient, method: str, path: str
    ) -> None:
        """読み取り専用であることをルーティングで担保していることの確認。"""
        assert getattr(client, method)(path).status_code == 405


class TestTrustedHost:
    """DNS リバインディング対策。

    127.0.0.1 に待ち受けるだけでは、利用者が開いた別のサイトが自分のドメインを
    127.0.0.1 に解決させることでこのサーバに到達できる。
    """

    def test_rejects_a_foreign_host(self, client: TestClient) -> None:
        response = client.get("/api/state", headers={"Host": "evil.example.com"})
        assert response.status_code == 400

    @pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.1:8765", "localhost:8765"])
    def test_accepts_loopback(self, client: TestClient, host: str) -> None:
        assert client.get("/api/state", headers={"Host": host}).status_code == 200


class TestReallyReadOnly:
    """405 を返すだけでなく、**ディスクにも書かない**ことの確認（段3 指摘1）。

    `/api/overview` は `DailyService.list_today()` を呼ぶが、その既定動作は
    「今日のログ」を書き足す。ルーティーンが1件も無いと毎リクエスト書き込むため、
    読み取り専用のはずの画面を開くだけでユーザーデータが変わっていた。
    """

    PATHS = (
        "/api/state",
        "/api/overview",
        "/api/tasks",
        "/api/inbox/tasks",
        "/api/search?q=%E3%82%BF",
    )

    def _snapshot(self, home: Path) -> dict[str, tuple[int, int]]:
        return {
            str(p.relative_to(home)): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(home.rglob("*"))
            if p.is_file()
        }

    def test_reads_do_not_touch_the_filesystem(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from task_cli.services.daily_service import DailyService

        get_use_case().add_task("タスク", project=None)
        for path in self.PATHS:
            client.get(path)
        before = self._snapshot(tmp_path)

        for path in self.PATHS:
            assert client.get(path).status_code == 200
        assert self._snapshot(tmp_path) == before, "読み取りだけでファイルが変わった"

        # ルーティーンがある場合も同じ（無いほうが毎回書き込んでいた）
        DailyService().add_routine("朝会")
        for path in self.PATHS:
            client.get(path)
        with_routine = self._snapshot(tmp_path)
        for path in self.PATHS:
            client.get(path)
        assert self._snapshot(tmp_path) == with_routine, "読み取りだけでファイルが変わった"

    def test_overview_still_reports_routines(self, client: TestClient) -> None:
        """書き込まなくてもルーティーンは pending として見える。"""
        from task_cli.services.daily_service import DailyService

        DailyService().add_routine("朝会")
        routines = client.get("/api/overview").json()["routines"]
        assert [(r["title"], r["status"]) for r in routines] == [("朝会", "pending")]


class TestAllowedHosts:
    def test_production_list_excludes_the_test_host(self) -> None:
        """本番の許可リストにテスト専用の名前を残さない（段3 指摘6）。"""
        from task_web.server import ALLOWED_HOSTS

        assert "testserver" not in ALLOWED_HOSTS
        assert ALLOWED_HOSTS == ["127.0.0.1", "localhost"]

    def test_the_bound_host_is_always_allowed(self) -> None:
        """待ち受けたアドレスは必ず許可する（段3 指摘2）。

        足さないと「サーバは起動しているのに全部 400」という状態になる。
        """
        from task_web.server import _allowed_hosts_for

        assert _allowed_hosts_for("127.0.0.1") == ["127.0.0.1", "localhost"]
        assert "192.168.1.5" in _allowed_hosts_for("192.168.1.5")


class TestWatcherCoversWhatTheApiReturns:
    """`/api/overview` が返すものは、すべてリビジョンの監視対象に入っていること
    （段3 指摘4）。漏れると「変更を監視中」と言いながら古い値を映し続ける。
    """

    def test_timer_and_daily_are_watched(self, client: TestClient) -> None:
        from task_cli.cli.deps import get_global_config_service
        from task_web.watcher import watched_paths

        names = {p.name for p in watched_paths(get_global_config_service())}
        assert {"config.yaml", "tasks.yaml", "timer.yaml", "routines.yaml", "log.yaml"} <= names

    def test_revision_changes_when_a_routine_is_added(self, client: TestClient) -> None:
        from task_cli.services.daily_service import DailyService

        before = client.get("/api/state").json()["revision"]
        DailyService().add_routine("朝会")
        assert client.get("/api/state").json()["revision"] != before

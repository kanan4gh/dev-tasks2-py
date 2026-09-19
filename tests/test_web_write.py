"""ローカル Web GUI の書き込み面。

読み取り面（`tests/test_web_api.py`）と同じく `TestClient` でインプロセスに叩く。
実プロセスでの外形は `tests/test_web_server.py` が見る。
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from task_cli.cli.deps import get_use_case
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_web.server import create_app

ALLOWED = ["127.0.0.1", "localhost", "testserver"]
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("HOME", str(tmp_path))
    with TestClient(create_app(ALLOWED)) as c:
        yield c


def make_project(name: str) -> None:
    ProjectService(GlobalConfigStorage()).create_project(name)


def version_of(client: TestClient, path: str) -> str:
    """いま保存されている版（`updated_at`）を取る。"""
    return client.get(path).json()["task"]["updated_at"]


def write(
    client: TestClient,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    if_match: str | None = None,
    headers: dict[str, str] | None = None,
):
    merged = {**JSON, **(headers or {})}
    if if_match is not None:
        merged["If-Match"] = if_match
    return client.request(method, path, json=body if body is not None else {}, headers=merged)


class TestCreate:
    def test_adds_to_inbox(self, client: TestClient) -> None:
        response = write(client, "POST", "/api/inbox/tasks", {"title": "新しいタスク"})

        assert response.status_code == 201
        body = response.json()
        assert body["project"] is None
        assert body["task"]["title"] == "新しいタスク"
        assert [t.title for t in get_use_case().list_tasks(project=None)] == ["新しいタスク"]

    def test_adds_to_the_named_project_regardless_of_active(self, client: TestClient) -> None:
        """アクティブが bar でも、パスで指した foo に入る。"""
        make_project("foo")
        make_project("bar")
        ProjectService(GlobalConfigStorage()).use_project("bar")

        write(client, "POST", "/api/projects/foo/tasks", {"title": "foo のタスク"})

        assert [t.title for t in get_use_case().list_tasks(project="foo")] == ["foo のタスク"]
        assert get_use_case().list_tasks(project="bar") == []

    def test_accepts_optional_fields(self, client: TestClient) -> None:
        body = write(
            client,
            "POST",
            "/api/inbox/tasks",
            {"title": "詳しいタスク", "description": "説明", "priority": "high",
             "due_date": "2026-12-31"},
        ).json()

        assert body["task"]["description"] == "説明"
        assert body["task"]["priority"] == "high"
        assert body["task"]["due_date"] == "2026-12-31"

    def test_needs_no_if_match(self, client: TestClient) -> None:
        """新規は照合する相手がいない。"""
        assert write(client, "POST", "/api/inbox/tasks", {"title": "X"}).status_code == 201

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"title": ""},
            {"title": "X", "due_date": "bogus"},
            {"title": "X", "priority": "bogus"},
        ],
    )
    def test_invalid_values_are_400(self, client: TestClient, body: dict[str, Any]) -> None:
        response = write(client, "POST", "/api/inbox/tasks", body)
        assert response.status_code == 400
        assert response.json()["error"]["remedy"]

    def test_unknown_project_is_404(self, client: TestClient) -> None:
        response = write(client, "POST", "/api/projects/nope/tasks", {"title": "X"})
        assert response.status_code == 404


class TestEdit:
    def test_changes_only_what_was_sent(self, client: TestClient) -> None:
        get_use_case().add_task("元のタイトル", description="元の説明", project=None)
        path = "/api/inbox/tasks/1"

        body = write(
            client, "PATCH", path, {"title": "新しいタイトル"}, if_match=version_of(client, path)
        ).json()

        assert body["task"]["title"] == "新しいタイトル"
        assert body["task"]["description"] == "元の説明"

    def test_null_clears_a_field(self, client: TestClient) -> None:
        """「キーが無い＝変更しない」と「null＝消す」を区別する。

        区別しないと、一度入れた期限を画面から消せなくなる。
        """
        get_use_case().add_task("タスク", due_date="2026-12-31", project=None)
        path = "/api/inbox/tasks/1"

        body = write(
            client, "PATCH", path, {"due_date": None}, if_match=version_of(client, path)
        ).json()

        assert body["task"]["due_date"] is None

    def test_sets_scheduled_date(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"

        body = write(
            client, "PATCH", path, {"scheduled_date": "2026-12-31"},
            if_match=version_of(client, path),
        ).json()

        assert body["task"]["scheduled_date"] == "2026-12-31"

    def test_bad_date_is_400_and_nothing_is_saved(self, client: TestClient) -> None:
        """保存**前**に弾く。保存後だとそのプロジェクトが読めなくなる。"""
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"

        response = write(
            client, "PATCH", path, {"due_date": "bogus"}, if_match=version_of(client, path)
        )

        assert response.status_code == 400
        assert client.get(path).json()["task"]["due_date"] is None
        assert client.get("/api/inbox/tasks").status_code == 200


class TestTransitions:
    def test_start_done_archive(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"

        started = write(client, "POST", f"{path}/start", if_match=version_of(client, path)).json()
        assert started["task"]["status"] == "in_progress"

        done = write(client, "POST", f"{path}/done", if_match=version_of(client, path)).json()
        assert done["task"]["status"] == "completed"
        assert done["task"]["completed_at"] is not None

        archived = write(
            client, "POST", f"{path}/archive", if_match=version_of(client, path)
        ).json()
        assert archived["task"]["status"] == "archived"

    def test_invalid_transition_is_404_with_reason(self, client: TestClient) -> None:
        """open から直接 done にはできない（CLI と同じ規則）。"""
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"

        response = write(client, "POST", f"{path}/done", if_match=version_of(client, path))
        assert response.status_code == 404
        assert response.json()["error"]["remedy"]


class TestDelete:
    def test_removes_the_task(self, client: TestClient) -> None:
        get_use_case().add_task("消すタスク", project=None)
        path = "/api/inbox/tasks/1"

        response = write(client, "DELETE", path, if_match=version_of(client, path))

        assert response.status_code == 200
        assert response.json()["deleted"] == {"project": None, "id": 1}
        assert get_use_case().list_tasks(project=None) == []


class TestMove:
    def test_moves_between_projects(self, client: TestClient) -> None:
        make_project("dst")
        get_use_case().add_task("移動するタスク", project=None)
        path = "/api/inbox/tasks/1"

        body = write(
            client, "POST", f"{path}/move", {"project": "dst"}, if_match=version_of(client, path)
        ).json()

        assert body["project"] == "dst"
        assert [t.title for t in get_use_case().list_tasks(project="dst")] == ["移動するタスク"]
        assert get_use_case().list_tasks(project=None) == []

    def test_moves_to_inbox_with_null(self, client: TestClient) -> None:
        make_project("src")
        get_use_case().add_task("Inbox へ", project="src")
        path = "/api/projects/src/tasks/1"

        body = write(
            client, "POST", f"{path}/move", {"project": None}, if_match=version_of(client, path)
        ).json()

        assert body["project"] is None
        assert [t.title for t in get_use_case().list_tasks(project=None)] == ["Inbox へ"]

    def test_unknown_target_is_rejected(self, client: TestClient, tmp_path: Path) -> None:
        """成功を報告しながらタスクを見えなくしない。"""
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"

        response = write(
            client, "POST", f"{path}/move", {"project": "typo"}, if_match=version_of(client, path)
        )

        assert response.status_code == 404
        assert not (tmp_path / ".task-py/projects/typo").exists()
        assert [t.title for t in get_use_case().list_tasks(project=None)] == ["タスク"]

    def test_missing_target_is_400(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"
        response = write(client, "POST", f"{path}/move", {}, if_match=version_of(client, path))
        assert response.status_code == 400


class TestOptimisticLocking:
    """画面を開いたまま別の場所で変更されたときに、黙って上書きしないこと。"""

    def test_matching_version_succeeds(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"
        response = write(client, "PATCH", path, {"title": "新"}, if_match=version_of(client, path))
        assert response.status_code == 200

    def test_stale_version_is_409_with_the_current_task(self, client: TestClient) -> None:
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"
        stale = version_of(client, path)

        # 別プロセス相当の変更
        get_use_case().edit_task(1, title="CLI が変えたタイトル", project=None)

        response = write(client, "PATCH", path, {"title": "画面が送ったタイトル"}, if_match=stale)

        assert response.status_code == 409
        body = response.json()
        # 画面が最新を出し直せるよう、現在の内容を添える
        assert body["current"]["title"] == "CLI が変えたタイトル"
        assert body["error"]["remedy"]
        # 上書きされていない
        assert client.get(path).json()["task"]["title"] == "CLI が変えたタイトル"

    def test_missing_if_match_is_428(self, client: TestClient) -> None:
        """省略を「上書きしてよい」と解釈しない。"""
        get_use_case().add_task("タスク", project=None)
        response = write(client, "PATCH", "/api/inbox/tasks/1", {"title": "新"})
        assert response.status_code == 428

    @pytest.mark.parametrize(
        ("method", "suffix", "body"),
        [
            ("PATCH", "", {"title": "新"}),
            ("DELETE", "", None),
            ("POST", "/start", None),
            ("POST", "/move", {"project": None}),
        ],
    )
    def test_every_mutation_requires_a_version(
        self, client: TestClient, method: str, suffix: str, body: dict[str, Any] | None
    ) -> None:
        get_use_case().add_task("タスク", project=None)
        response = write(client, method, f"/api/inbox/tasks/1{suffix}", body)
        assert response.status_code == 428

    def test_quoted_if_match_is_accepted(self, client: TestClient) -> None:
        """ETag の形（引用符つき）で送られても通す。"""
        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"
        response = write(
            client, "PATCH", path, {"title": "新"}, if_match=f'"{version_of(client, path)}"'
        )
        assert response.status_code == 200

    def test_work_sessions_do_not_cause_a_conflict(self, client: TestClient) -> None:
        """タイマーを止めて作業セッションが足されても 409 にしない。

        `append_work_session` は `updated_at` を動かさない（#38 の設計）。
        編集と競合していないものを競合と呼ばない。
        """
        from datetime import datetime, timedelta, timezone

        from task_cli.models.time import WorkSession

        get_use_case().add_task("タスク", project=None)
        path = "/api/inbox/tasks/1"
        seen = version_of(client, path)

        started = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
        get_use_case()._get_manager(None).append_work_session(  # pyright: ignore[reportPrivateUsage]
            1,
            WorkSession(
                started_at=started, ended_at=started + timedelta(seconds=600), seconds=600
            ),
        )

        response = write(client, "PATCH", path, {"title": "新しいタイトル"}, if_match=seen)

        assert response.status_code == 200
        assert response.json()["task"]["total_worked_seconds"] == 600


class TestCsrf:
    """`Host` の検証では CSRF は防げない。

    攻撃者のページから `fetch("http://127.0.0.1:8765/...", {method:"POST"})` を
    投げられた場合、`Host` はこちらの正しい値になる。出自を別に確かめる。
    """

    def test_non_json_is_415(self, client: TestClient) -> None:
        """フォーム形式や text/plain はプリフライト無しで届いてしまうので受けない。"""
        response = client.post(
            "/api/inbox/tasks", content=b"title=X", headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 415

    def test_missing_content_type_is_415(self, client: TestClient) -> None:
        response = client.post("/api/inbox/tasks", content=b"{}")
        assert response.status_code == 415

    @pytest.mark.parametrize("site", ["cross-site", "same-site", "none"])
    def test_cross_origin_fetch_is_403(self, client: TestClient, site: str) -> None:
        response = write(
            client, "POST", "/api/inbox/tasks", {"title": "X"},
            headers={"Sec-Fetch-Site": site},
        )
        assert response.status_code == 403

    def test_same_origin_fetch_is_allowed(self, client: TestClient) -> None:
        response = write(
            client, "POST", "/api/inbox/tasks", {"title": "X"},
            headers={"Sec-Fetch-Site": "same-origin"},
        )
        assert response.status_code == 201

    def test_foreign_origin_is_403(self, client: TestClient) -> None:
        response = write(
            client, "POST", "/api/inbox/tasks", {"title": "X"},
            headers={"Origin": "http://evil.example.com"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "origin", ["http://127.0.0.1:8765", "http://localhost:8765", "http://testserver"]
    )
    def test_own_origin_is_allowed(self, client: TestClient, origin: str) -> None:
        response = write(
            client, "POST", "/api/inbox/tasks", {"title": "X"}, headers={"Origin": origin}
        )
        assert response.status_code == 201

    def test_no_headers_at_all_is_allowed(self, client: TestClient) -> None:
        """curl やテストは通す。ブラウザは必ず送るので CSRF は塞がる。"""
        assert write(client, "POST", "/api/inbox/tasks", {"title": "X"}).status_code == 201

    def test_reads_are_not_checked(self, client: TestClient) -> None:
        response = client.get(
            "/api/state",
            headers={"Sec-Fetch-Site": "cross-site", "Origin": "http://evil.example.com"},
        )
        assert response.status_code == 200


class TestMalformedBody:
    def test_broken_json_is_400(self, client: TestClient) -> None:
        response = client.post("/api/inbox/tasks", content=b"{not json", headers=JSON)
        assert response.status_code == 400

    def test_non_object_json_is_400(self, client: TestClient) -> None:
        response = client.post("/api/inbox/tasks", content=b"[1,2,3]", headers=JSON)
        assert response.status_code == 400

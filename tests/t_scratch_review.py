from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from task_web.server import create_app

ALLOWED = ["127.0.0.1", "localhost", "testserver"]
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("HOME", str(tmp_path))
    with TestClient(create_app(ALLOWED)) as c:
        yield c


def test_scheduled_date_on_create(client):
    r = client.post(
        "/api/inbox/tasks",
        json={"title": "X", "scheduled_date": "2026-12-31"},
        headers=JSON,
    )
    print("CREATE:", r.status_code, r.json())
    assert r.json()["task"]["scheduled_date"] == "2026-12-31"


def test_priority_null_on_edit(client):
    client.post("/api/inbox/tasks", json={"title": "X", "priority": "high"}, headers=JSON)
    v = client.get("/api/inbox/tasks/1").json()["task"]["updated_at"]
    r = client.request(
        "PATCH",
        "/api/inbox/tasks/1",
        json={"title": "Y", "priority": None},
        headers={**JSON, "If-Match": v},
    )
    print("PRIORITY AFTER NULL:", r.json()["task"]["priority"])
    assert r.json()["task"]["priority"] == "high"


def test_move_to_same_project(client):
    client.post("/api/inbox/tasks", json={"title": "X"}, headers=JSON)
    v = client.get("/api/inbox/tasks/1").json()["task"]["updated_at"]
    r = client.post(
        "/api/inbox/tasks/1/move", json={"project": None}, headers={**JSON, "If-Match": v}
    )
    print("SELF MOVE:", r.status_code, r.json())
    assert r.json()["task"]["id"] == 1

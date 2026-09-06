"""実プロセスで起動した外形の確認。

`tests/test_web_api.py` はアプリをインプロセスで叩く。ここではそれと二段構えで、
`python -m task_web` を実際に立ち上げて、静的ファイルの配信・API・SSE が
プロセスとして成立していることを見る（`tests/test_mcp_server.py` が
`test_stdio_process_initialize` で外形を見ているのと同じ考え方）。
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until_serving(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("サーバが待ち受けを始めなかった")


@pytest.fixture
def server(tmp_path: Path) -> Iterator[int]:
    port = free_port()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "TASK_WEB_PORT": str(port),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-c", _BOOT, str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_until_serving(port)
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()


# `python -m task_web` は既定ポート固定なので、テスト用にポートだけ差し替えて
# 同じ入口（server.run）を呼ぶ。
_BOOT = """
import sys
from task_web.server import run
run(port=int(sys.argv[1]))
"""


def request(port: int, path: str, headers: dict[str, str] | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path, headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


class TestRealProcess:
    def test_serves_the_page(self, server: int) -> None:
        status, body = request(server, "/")
        assert status == 200
        assert b"<title>task-py</title>" in body
        assert b"/vendor/react.production.min.js" in body

    def test_serves_vendored_assets(self, server: int) -> None:
        for path in (
            "/vendor/react.production.min.js",
            "/vendor/react-dom.production.min.js",
            "/vendor/htm.umd.js",
            "/js/main.js",
            "/app.css",
        ):
            status, body = request(server, path)
            assert status == 200, path
            assert body, path

    def test_serves_state(self, server: int) -> None:
        status, body = request(server, "/api/state")
        assert status == 200
        payload = json.loads(body)
        assert payload["projects"] == []
        assert payload["revision"]

    def test_rejects_a_foreign_host(self, server: int) -> None:
        status, _ = request(server, "/api/state", headers={"Host": "evil.example.com"})
        assert status == 400

    def test_events_notice_another_process(self, server: int, tmp_path: Path) -> None:
        """別プロセスがタスクを足すと SSE でリビジョンの変化が届く。

        ここがこの作業単位の要件そのもの（開いたままの画面が最新を映す）。
        """
        conn = http.client.HTTPConnection("127.0.0.1", server, timeout=20)
        conn.request(
            "GET",
            "/api/events",
            headers={"Host": f"127.0.0.1:{server}", "Accept": "text/event-stream"},
        )
        response = conn.getresponse()
        assert response.status == 200
        try:
            first = _read_revision(response)

            subprocess.run(
                [sys.executable, "-c", _ADD_TASK],
                env={**os.environ, "HOME": str(tmp_path), "PYTHONPATH": str(REPO_ROOT / "src")},
                check=True,
                capture_output=True,
            )

            assert _read_revision(response) != first
        finally:
            conn.close()


_ADD_TASK = """
from task_cli.cli.deps import get_use_case
get_use_case().add_task("別プロセスが足したタスク", project=None)
"""


def _read_revision(response, timeout: float = 15.0) -> str:
    """`event: revision` に続く `data:` 行を1つ読む。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = response.fp.readline()
        if not line:
            break
        text = line.decode("utf-8").strip()
        if text.startswith("data:"):
            return text[len("data:") :].strip()
    raise AssertionError("リビジョンのイベントが届かなかった")


class TestWheelContents:
    def test_static_files_are_packaged(self, tmp_path: Path) -> None:
        """`packages` 指定で `.py` 以外も wheel に入ることを実ビルドで確かめる。

        入っていないと、`uv tool install` した利用者の画面が真っ白になる。
        """
        out = tmp_path / "dist"
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(out)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        wheels = list(out.glob("*.whl"))
        assert wheels, "wheel が作られなかった"
        names = set(zipfile.ZipFile(wheels[0]).namelist())

        for expected in (
            "task_web/static/index.html",
            "task_web/static/app.css",
            "task_web/static/js/main.js",
            "task_web/static/vendor/react.production.min.js",
        ):
            assert expected in names, f"{expected} が wheel に含まれていない"

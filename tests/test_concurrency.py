"""別 OS プロセス2本を同時に走らせ、ロストアップデートが起きないことを確かめる。

本物のプロセス2本で確かめるのは、これがこの作業の要件そのものだからである。
GUI（ローカル Web サーバー）は CLI や MCP サーバーとは別のプロセスとして
同じ `~/.task-py/` を更新する。スレッドで代用すると、`fcntl.flock` が
「同一プロセス内の別 fd」と「別プロセス」で振る舞いを変えないことに依存した
検証になってしまう。

各シナリオには**ロックを無効化した対照**を置く。対照側で実際にデータが失われる
ことを確認することで、テストの仕掛け（load と save の間を人為的に広げる）が
本当に競合を作れていることを示す。
"""

import subprocess
import sys
from pathlib import Path

import pytest

# 1本目が load を終えてから save するまでの待ち時間。2本目はこの窓の中で
# 走り出す（合図ファイルで同期するので、プロセス起動のばらつきに依存しない）。
_SLOW = 0.4

_PREAMBLE = """
import sys, time
from pathlib import Path

path, title, delay, use_lock, signal = (
    sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
)

def wait_for_signal():
    # 相手が load を終えるまで待つ。時計ではなく合図で同期するので、
    # プロセス起動のばらつきで競合が起きたり起きなかったりしない。
    deadline = time.time() + 30
    while not signal.exists():
        if time.time() > deadline:
            raise SystemExit("合図が来ないままタイムアウトした")
        time.sleep(0.005)

if delay > 0:
    pass          # 1本目: load 後に合図を出して待つ
else:
    wait_for_signal()   # 2本目: 1本目が load を終えるまで開始しない
"""

_ADD_TASK = _PREAMBLE + """
from task_cli.services.task_manager import TaskManager
from task_cli.storage import atomic
from task_cli.storage.file_storage import FileStorage

if use_lock == "no":
    atomic._flock = None


class SlowStorage(FileStorage):
    def load(self):
        tasks = super().load()
        if delay > 0:
            signal.touch()
            time.sleep(delay)
        return tasks


TaskManager(SlowStorage(path)).create_task(title)
"""

_CREATE_PROJECT = _PREAMBLE + """
from task_cli.services.project_service import ProjectService
from task_cli.storage import atomic
from task_cli.storage.global_config_storage import GlobalConfigStorage

if use_lock == "no":
    atomic._flock = None


class SlowStorage(GlobalConfigStorage):
    _signalled = False

    def load(self):
        config = super().load()
        if delay > 0 and not SlowStorage._signalled:
            SlowStorage._signalled = True
            signal.touch()
            time.sleep(delay)
        return config


ProjectService(SlowStorage(path)).create_project(title)
"""


def _run_pair(script: Path, first: list[str], second: list[str]) -> None:
    """2つの子プロセスを走らせる。

    2本目は「1本目が load を終えた」という合図ファイルを待ってから動き出す。
    時計ではなく合図で同期するので、インタプリタ起動のばらつきに関係なく
    毎回同じ順序（1本目 load → 2本目 load → 1本目 save）になる。
    ロックが無ければ2本目は1本目の変更前の内容を読むことになる。
    """
    procs = [
        subprocess.Popen([sys.executable, str(script), *first]),
        subprocess.Popen([sys.executable, str(script), *second]),
    ]
    for proc in procs:
        assert proc.wait(timeout=60) == 0, "子プロセスが異常終了した"


@pytest.fixture
def add_task_script(tmp_path: Path) -> Path:
    script = tmp_path / "add_task_child.py"
    script.write_text(_ADD_TASK, encoding="utf-8")
    return script


@pytest.fixture
def create_project_script(tmp_path: Path) -> Path:
    script = tmp_path / "create_project_child.py"
    script.write_text(_CREATE_PROJECT, encoding="utf-8")
    return script


class TestConcurrentTaskCreation:
    def test_both_tasks_survive(self, tmp_path: Path, add_task_script: Path) -> None:
        from task_cli.storage.file_storage import FileStorage

        path = tmp_path / "tasks.yaml"
        _run_pair(
            add_task_script,
            [str(path), "プロセス1のタスク", str(_SLOW), "yes", str(tmp_path / "sig")],
            [str(path), "プロセス2のタスク", "0", "yes", str(tmp_path / "sig")],
        )

        titles = sorted(t.title for t in FileStorage(path).load())
        assert titles == ["プロセス1のタスク", "プロセス2のタスク"]

    def test_control_without_lock_loses_a_task(
        self, tmp_path: Path, add_task_script: Path
    ) -> None:
        """対照実験: ロックが無ければ実際に片方が消える。"""
        from task_cli.storage.file_storage import FileStorage

        path = tmp_path / "tasks.yaml"
        _run_pair(
            add_task_script,
            [str(path), "プロセス1のタスク", str(_SLOW), "no", str(tmp_path / "sig")],
            [str(path), "プロセス2のタスク", "0", "no", str(tmp_path / "sig")],
        )

        assert len(FileStorage(path).load()) == 1, "この仕掛けでは競合が起きていない"


class TestConcurrentProjectCreation:
    def test_ids_do_not_collide(self, tmp_path: Path, create_project_script: Path) -> None:
        from task_cli.storage.global_config_storage import GlobalConfigStorage

        path = tmp_path / "config.yaml"
        _run_pair(
            create_project_script,
            [str(path), "proj-a", str(_SLOW), "yes", str(tmp_path / "sig")],
            [str(path), "proj-b", "0", "yes", str(tmp_path / "sig")],
        )

        config = GlobalConfigStorage(path).load()
        names = sorted(p.name for p in config.projects)
        ids = sorted(p.id for p in config.projects)
        assert names == ["proj-a", "proj-b"]
        assert ids == [1, 2], f"ID が重複または欠落した: {ids}"
        assert config.last_project_id == 2

    def test_control_without_lock_collides(
        self, tmp_path: Path, create_project_script: Path
    ) -> None:
        """対照実験: ロックが無ければプロジェクトが消えるか ID が重複する。"""
        from task_cli.storage.global_config_storage import GlobalConfigStorage

        path = tmp_path / "config.yaml"
        _run_pair(
            create_project_script,
            [str(path), "proj-a", str(_SLOW), "no", str(tmp_path / "sig")],
            [str(path), "proj-b", "0", "no", str(tmp_path / "sig")],
        )

        config = GlobalConfigStorage(path).load()
        ids = [p.id for p in config.projects]
        assert len(config.projects) < 2 or len(set(ids)) < len(ids), (
            "この仕掛けでは競合が起きていない"
        )

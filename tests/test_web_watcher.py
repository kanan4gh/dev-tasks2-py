from pathlib import Path

import pytest

from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_web.watcher import revision, watched_paths


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def make_service() -> GlobalConfigService:
    # 既定パスを使う。HOME が差し替えられているので tmp_path 配下を指す。
    return GlobalConfigService(GlobalConfigStorage())


class TestWatchedPaths:
    def test_includes_config_and_inbox(self, home: Path) -> None:
        paths = watched_paths(make_service())
        assert home / ".task-py/config.yaml" in paths
        assert home / ".task-py/inbox/tasks.yaml" in paths

    def test_picks_up_new_projects(self, home: Path) -> None:
        service = make_service()
        before = watched_paths(service)
        ProjectService(GlobalConfigStorage()).create_project("later")

        after = watched_paths(service)
        assert home / ".task-py/projects/later/tasks.yaml" in after
        assert len(after) == len(before) + 1


class TestRevision:
    def test_is_stable_without_changes(self, home: Path) -> None:
        service = make_service()
        assert revision(service) == revision(service)

    def test_survives_missing_task_dir(self, home: Path) -> None:
        """~/.task-py/ がまだ無くても落ちない（初回起動）。"""
        assert not (home / ".task-py").exists()
        assert revision(make_service())

    def test_changes_when_a_task_file_changes(self, home: Path) -> None:
        service = make_service()
        before = revision(service)

        tasks = home / ".task-py/inbox/tasks.yaml"
        tasks.parent.mkdir(parents=True, exist_ok=True)
        tasks.write_text("- id: 1\n", encoding="utf-8")

        assert revision(service) != before

    def test_changes_when_a_project_is_added(self, home: Path) -> None:
        service = make_service()
        before = revision(service)
        ProjectService(GlobalConfigStorage()).create_project("fresh")
        assert revision(service) != before

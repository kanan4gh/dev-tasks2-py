from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.models.task import GlobalConfig
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage


def make_service(tmp_path: Path, config: GlobalConfig | None = None) -> ProjectService:
    storage = GlobalConfigStorage(tmp_path / "config.yaml")
    if config is not None:
        storage.save(config)
    return ProjectService(storage)


class TestCreateProject:
    def test_creates_project_and_sets_active(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        entry = svc.create_project("myapp")
        assert entry.name == "myapp"
        assert entry.id == 1
        config = svc.get_config()
        assert config.active_project == "myapp"
        assert len(config.projects) == 1

    def test_increments_last_project_id(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        e1 = svc.create_project("proj1")
        e2 = svc.create_project("proj2")
        assert e1.id == 1
        assert e2.id == 2

    def test_duplicate_name_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("myapp")
        with pytest.raises(AppError):
            svc.create_project("myapp")


class TestListProjects:
    def test_returns_empty_list_initially(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        assert svc.list_projects() == []

    def test_returns_all_projects(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("a")
        svc.create_project("b")
        names = [p.name for p in svc.list_projects()]
        assert "a" in names
        assert "b" in names


class TestGetProject:
    def test_returns_matching_project(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("myapp")
        entry = svc.get_project("myapp")
        assert entry.name == "myapp"

    def test_not_found_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        with pytest.raises(AppError):
            svc.get_project("nonexistent")


class TestUseProject:
    def test_switches_active_project(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("a")
        svc.create_project("b")
        svc.use_project("a")
        assert svc.get_config().active_project == "a"

    def test_not_found_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        with pytest.raises(AppError):
            svc.use_project("nonexistent")


class TestRemoveProject:
    def test_removes_non_active_project(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("a")
        svc.create_project("b")
        svc.use_project("a")
        svc.remove_project("b")
        names = [p.name for p in svc.list_projects()]
        assert "b" not in names
        assert svc.get_config().active_project == "a"

    def test_removes_active_project_resets_active(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("myapp")
        assert svc.get_config().active_project == "myapp"
        svc.remove_project("myapp")
        assert svc.get_config().active_project is None
        assert svc.list_projects() == []

    def test_not_found_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        with pytest.raises(AppError):
            svc.remove_project("nonexistent")


class TestRenameProject:
    def test_renames_non_active_project(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("old")
        svc.create_project("other")
        svc.use_project("other")
        svc.rename_project("old", "new")
        names = [p.name for p in svc.list_projects()]
        assert "new" in names
        assert "old" not in names
        assert svc.get_config().active_project == "other"

    def test_renames_active_project_updates_active(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("myapp")
        svc.rename_project("myapp", "renamed")
        assert svc.get_config().active_project == "renamed"
        names = [p.name for p in svc.list_projects()]
        assert "renamed" in names
        assert "myapp" not in names

    def test_old_not_found_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        with pytest.raises(AppError):
            svc.rename_project("nonexistent", "new")

    def test_new_duplicate_raises(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path)
        svc.create_project("a")
        svc.create_project("b")
        with pytest.raises(AppError):
            svc.rename_project("a", "b")

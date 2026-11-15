"""プロジェクト名の検証(#75)。

名前は `~/.task-py/projects/{name}/` のパスにそのまま使われる。作成・改名の
新しい名前だけを検査し、すでに登録された名前は読めるままにする。
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from task_cli.cli.commands.project import project_app
from task_cli.exceptions import InvalidProjectName, NotFoundError, StateConflictError
from task_cli.models.task import GlobalConfig, ProjectEntry
from task_cli.services.project_service import ProjectService
from task_cli.storage.global_config_storage import GlobalConfigStorage

BAD_NAMES = ["", " a", "a ", "../x", "a/b", "a\\b", ".", "..", ".hidden", "a\x00b", "a\nb", "x" * 65]


def make_service(tmp_path: Path, config: GlobalConfig | None = None) -> ProjectService:
    storage = GlobalConfigStorage(tmp_path / "config.yaml")
    if config is not None:
        storage.save(config)
    return ProjectService(storage)


@pytest.mark.parametrize("name", BAD_NAMES)
def test_create_rejects_bad_names(tmp_path: Path, name: str) -> None:
    svc = make_service(tmp_path)
    with pytest.raises(InvalidProjectName) as info:
        svc.create_project(name)
    assert info.value.cause and info.value.remedy
    assert svc.list_projects() == []


@pytest.mark.parametrize("name", BAD_NAMES)
def test_rename_rejects_bad_new_names(tmp_path: Path, name: str) -> None:
    svc = make_service(tmp_path)
    svc.create_project("ok")
    with pytest.raises(InvalidProjectName):
        svc.rename_project("ok", name)
    assert [p.name for p in svc.list_projects()] == ["ok"]


@pytest.mark.parametrize("name", ["inbox", "日本語の名前", "my-app_2", "a" * 64, "a b"])
def test_accepts_ordinary_names(tmp_path: Path, name: str) -> None:
    svc = make_service(tmp_path)
    assert svc.create_project(name).name == name


def test_already_registered_odd_names_stay_usable(tmp_path: Path) -> None:
    config = GlobalConfig(projects=[ProjectEntry(name=".old", id=1)], last_project_id=1)
    svc = make_service(tmp_path, config)
    assert svc.get_project(".old").name == ".old"
    svc.use_project(".old")
    svc.remove_project(".old")


def test_duplicate_is_a_state_conflict(tmp_path: Path) -> None:
    svc = make_service(tmp_path)
    svc.create_project("a")
    with pytest.raises(StateConflictError):
        svc.create_project("a")


def test_missing_project_is_not_found(tmp_path: Path) -> None:
    svc = make_service(tmp_path)
    for call in (
        lambda: svc.get_project("nope"),
        lambda: svc.use_project("nope"),
        lambda: svc.remove_project("nope"),
        lambda: svc.rename_project("nope", "x"),
    ):
        with pytest.raises(NotFoundError):
            call()


def test_cli_shows_error_for_bad_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = CliRunner().invoke(project_app, ["create", "../x"])
    assert result.exit_code == 1
    assert "[Error]" in result.output
    assert "原因" in result.output and "対処" in result.output
    assert not (tmp_path / ".task-py" / "x").exists()

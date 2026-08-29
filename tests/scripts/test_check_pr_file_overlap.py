"""Tests for deterministic pull-request file-set overlap checking."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "check_pr_file_overlap.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pr_file_overlap", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_module()


def test_planned_sets_pass_with_stable_summary(capsys: pytest.CaptureFixture[str]) -> None:
    result = checker.main(
        ["--set", "issue-b=docs/b.md", "--set", "issue-a=docs/a.md"]
    )
    assert result == 0
    assert capsys.readouterr().out == "PASS: 2 sets, 1 pairs, no overlapping files\n"


def test_reports_every_overlap_in_stable_order(capsys: pytest.CaptureFixture[str]) -> None:
    result = checker.main(
        [
            "--set",
            "c=shared/z.md",
            "--set",
            "a=shared/z.md",
            "--set",
            "a=shared/a.md",
            "--set",
            "b=shared/a.md",
            "--set",
            "b=shared/z.md",
        ]
    )
    assert result == 1
    assert capsys.readouterr().out == (
        "FAIL: 3 overlapping pair(s)\n"
        "  a <> b\n"
        "    shared/a.md\n"
        "    shared/z.md\n"
        "  a <> c\n"
        "    shared/z.md\n"
        "  b <> c\n"
        "    shared/z.md\n"
    )


def test_same_name_aggregates_and_deduplicates_paths() -> None:
    file_sets = checker.planned_file_sets(
        ["b=z.md", "a=b.md", "a=a.md", "a=a.md"]
    )
    assert list(file_sets) == ["a", "b"]
    assert file_sets["a"] == frozenset({"a.md", "b.md"})


@pytest.mark.parametrize("path", ["./a.md", "/a.md", "../a.md", "a//b.md", "a/", r"a\b.md"])
def test_planned_sets_reject_noncanonical_paths(path: str) -> None:
    with pytest.raises(checker.InputError, match="canonical repository-relative POSIX path"):
        checker.planned_file_sets([f"a={path}", "b=b.md"])


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--set", "only=a.md"], "at least two named file sets"),
        (["--set", "missing", "--set", "b=b.md"], "must use NAME=VALUE"),
        (["--set", "=a.md", "--set", "b=b.md"], "non-empty NAME and VALUE"),
        (["--set", "a=", "--set", "b=b.md"], "non-empty NAME and VALUE"),
        (["--set", "a=a.md", "--set", "b=b.md", "--base", "main"], "only valid"),
    ],
)
def test_invalid_planned_input_returns_two(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert checker.main(argv) == 2
    assert message in capsys.readouterr().err


def test_actual_sets_use_safe_git_arguments(tmp_path: Path) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def runner(argv: tuple[str, ...], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        output = "docs/a.md\0" if argv[5].endswith("feature/a") else "docs/b.md\0"
        return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

    file_sets = checker.actual_file_sets(
        "origin/main",
        ["issue-b=feature/b", "issue-a=feature/a"],
        root=tmp_path,
        runner=runner,
    )
    assert file_sets == {
        "issue-a": frozenset({"docs/a.md"}),
        "issue-b": frozenset({"docs/b.md"}),
    }
    assert [call[0] for call in calls] == [
        (
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            "origin/main...feature/a",
            "--",
        ),
        (
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            "origin/main...feature/b",
            "--",
        ),
    ]
    assert all(
        kwargs
        == {
            "cwd": tmp_path,
            "check": False,
            "shell": False,
            "capture_output": True,
            "text": True,
        }
        for _argv, kwargs in calls
    )


@pytest.mark.parametrize(
    "base, refs, message",
    [
        ("main", ["a=one"], "at least two named Git refs"),
        ("main", ["a=one", "a=two"], "duplicate --ref name"),
        ("main", ["a=", "b=two"], "non-empty NAME and VALUE"),
        ("-main", ["a=one", "b=two"], "invalid base Git ref"),
        ("main", ["a=-one", "b=two"], "invalid Git ref"),
    ],
)
def test_actual_sets_reject_invalid_refs(
    tmp_path: Path, base: str, refs: list[str], message: str
) -> None:
    with pytest.raises(checker.InputError, match=message):
        checker.actual_file_sets(base, refs, root=tmp_path)


def test_actual_sets_fail_closed_for_git_failure(tmp_path: Path) -> None:
    def runner(argv: tuple[str, ...], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 128, stdout="", stderr="bad revision")

    with pytest.raises(checker.InputError, match="Git diff failed for a.*exit 128") as error:
        checker.actual_file_sets(
            "main", ["a=one", "b=two"], root=tmp_path, runner=runner
        )
    assert "bad revision" not in str(error.value)


def test_actual_sets_fail_closed_for_empty_diff(tmp_path: Path) -> None:
    def runner(argv: tuple[str, ...], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        output = "" if argv[5].endswith("one") else "b.md\0"
        return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

    with pytest.raises(checker.InputError, match="file set is empty: a"):
        checker.actual_file_sets(
            "main", ["a=one", "b=two"], root=tmp_path, runner=runner
        )


def test_actual_sets_accept_nul_separated_unicode_paths(tmp_path: Path) -> None:
    def runner(argv: tuple[str, ...], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        output = "docs/日本語.md\0" if argv[5].endswith("one") else "docs/english.md\0"
        return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

    assert checker.actual_file_sets(
        "main", ["a=one", "b=two"], root=tmp_path, runner=runner
    ) == {
        "a": frozenset({"docs/日本語.md"}),
        "b": frozenset({"docs/english.md"}),
    }


def test_cli_set_mode_exit_codes(tmp_path: Path) -> None:
    clean = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--set",
            "a=a.md",
            "--set",
            "b=b.md",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    overlap = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--set",
            "a=same.md",
            "--set",
            "b=same.md",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    invalid = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--set", "a=only.md"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert (clean.returncode, overlap.returncode, invalid.returncode) == (0, 1, 2)


def test_cli_rejects_mixed_set_and_ref_modes(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--set",
            "a=a.md",
            "--ref",
            "b=feature/b",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr

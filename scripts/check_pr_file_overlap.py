"""Check that planned or actual pull-request file sets do not overlap."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from itertools import combinations
from pathlib import Path, PurePosixPath
import subprocess
import sys


class InputError(ValueError):
    """Raised when overlap-check input cannot be evaluated safely."""


FileSets = dict[str, frozenset[str]]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def parse_assignment(value: str, *, kind: str) -> tuple[str, str]:
    if "=" not in value:
        raise InputError(f"{kind} must use NAME=VALUE: {value!r}")
    name, item = (part.strip() for part in value.split("=", 1))
    if not name or not item:
        raise InputError(f"{kind} requires non-empty NAME and VALUE: {value!r}")
    return name, item


def planned_file_sets(values: Sequence[str]) -> FileSets:
    mutable: dict[str, set[str]] = {}
    for value in values:
        name, path = parse_assignment(value, kind="--set")
        mutable.setdefault(name, set()).add(normalize_path(path))
    return normalize_file_sets(mutable)


def normalize_path(value: str) -> str:
    path = value.strip()
    pure = PurePosixPath(path)
    if (
        not path
        or path.startswith("/")
        or path.startswith("./")
        or path.endswith("/")
        or "\\" in path
        or ".." in pure.parts
        or pure.as_posix() != path
    ):
        raise InputError(f"path must be a canonical repository-relative POSIX path: {value!r}")
    return path


def normalize_file_sets(values: dict[str, set[str]]) -> FileSets:
    if len(values) < 2:
        raise InputError("at least two named file sets are required")
    normalized: FileSets = {}
    for name in sorted(values):
        paths = frozenset(normalize_path(path) for path in values[name] if path.strip())
        if not paths:
            raise InputError(f"file set is empty: {name}")
        normalized[name] = paths
    return normalized


def actual_file_sets(
    base: str,
    values: Sequence[str],
    *,
    root: Path,
    runner: Runner = subprocess.run,
) -> FileSets:
    base = base.strip()
    if not base or base.startswith("-"):
        raise InputError(f"invalid base Git ref: {base!r}")

    refs: dict[str, str] = {}
    for value in values:
        name, ref = parse_assignment(value, kind="--ref")
        if name in refs:
            raise InputError(f"duplicate --ref name: {name}")
        if ref.startswith("-"):
            raise InputError(f"invalid Git ref for {name}: {ref!r}")
        refs[name] = ref
    if len(refs) < 2:
        raise InputError("at least two named Git refs are required")

    file_sets: dict[str, set[str]] = {}
    for name in sorted(refs):
        ref = refs[name]
        argv = (
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            f"{base}...{ref}",
            "--",
        )
        try:
            result = runner(
                argv,
                cwd=root,
                check=False,
                shell=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise InputError(f"Git diff could not start for {name} ({ref}): {exc}") from exc
        if result.returncode != 0:
            raise InputError(f"Git diff failed for {name} ({ref}), exit {result.returncode}")
        file_sets[name] = {
            normalize_path(path) for path in result.stdout.split("\0") if path.strip()
        }
    return normalize_file_sets(file_sets)


def find_overlaps(file_sets: FileSets) -> list[tuple[str, str, tuple[str, ...]]]:
    overlaps: list[tuple[str, str, tuple[str, ...]]] = []
    for left, right in combinations(sorted(file_sets), 2):
        shared = tuple(sorted(file_sets[left] & file_sets[right]))
        if shared:
            overlaps.append((left, right, shared))
    return overlaps


def report(file_sets: FileSets) -> int:
    pair_count = len(file_sets) * (len(file_sets) - 1) // 2
    overlaps = find_overlaps(file_sets)
    if not overlaps:
        print(f"PASS: {len(file_sets)} sets, {pair_count} pairs, no overlapping files")
        return 0
    print(f"FAIL: {len(overlaps)} overlapping pair(s)")
    for left, right, paths in overlaps:
        print(f"  {left} <> {right}")
        for path in paths:
            print(f"    {path}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--set", dest="sets", action="append", metavar="NAME=PATH")
    mode.add_argument("--ref", dest="refs", action="append", metavar="NAME=GIT_REF")
    parser.add_argument("--base", metavar="GIT_REF")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.sets is not None:
            if args.base is not None:
                raise InputError("--base is only valid with --ref")
            file_sets = planned_file_sets(args.sets)
        else:
            if args.base is None:
                raise InputError("--base is required with --ref")
            file_sets = actual_file_sets(args.base, args.refs, root=Path.cwd().resolve())
    except InputError as exc:
        print(f"overlap check: {exc}", file=sys.stderr)
        return 2
    return report(file_sets)


if __name__ == "__main__":
    raise SystemExit(main())

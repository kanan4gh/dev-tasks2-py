"""永続ドキュメントの現行化検査(`test_*_currency.py`)の共通部品。

`docs/functional-design.md`(#43)と `docs/product-requirements.md`・`docs/glossary.md`(#57)は、
どれも TypeScript 版の文書として書かれ、Python 版へ移った後も記述が残った。検査は「存在しない
ものを指していないこと」で、部品はここに置き、文書ごとの違い(禁止語の追加分・未実装の節の
扱い)だけを各テストが持つ。同じ部品を複数のテストに写すと、片方だけ更新されて基準が割れる。

名前の先頭を `_` にしているのは、テストとして収集されないため。
"""

import re
from pathlib import Path

import typer.main

from task_cli.cli.main import app

ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs"

# TypeScript 版時代の道具立てのうち、どの文書でも禁止するもの。
# 文書ごとの追加分(`npm` のように、ある文書には正当な言及があるもの)は各テストが持つ。
COMMON_TYPESCRIPT_TERMS = (
    "Commander.js",
    "Vitest",
    "simple-git",
    "node-fetch",
    "Node.js",
)

# 旧い永続ファイル名。Python 版は YAML(Web の JSON API の説明は別物)。
OLD_FILE_NAMES = ("tasks.json", "config.json", "routines.json", "log.json")


def cli_commands() -> tuple[set[str], dict[str, set[str]]]:
    """task-py の実在するコマンド。(トップレベル全体, グループ → サブコマンド)。"""
    root = typer.main.get_command(app)
    top: set[str] = set(getattr(root, "commands", {}))
    groups: dict[str, set[str]] = {}
    for name, command in getattr(root, "commands", {}).items():
        subs = getattr(command, "commands", None)
        if subs:
            groups[name] = set(subs)
    return top, groups


def old_storage_location_offenders(text: str) -> list[str]:
    """旧保存先 `~/.task/` を、移行の説明以外で書いている行。"""
    return [
        line.strip()
        for line in text.splitlines()
        if "~/.task/" in line and "migrate" not in line and "移行" not in line
    ]


def missing_source_paths(text: str) -> list[str]:
    """バッククォートで書かれた `src/`・`tests/` のパスのうち、実在しないもの。"""
    missing = []
    for path in sorted(set(re.findall(r"`((?:src|tests)/[^`\s]+)`", text))):
        if any(mark in path for mark in "*<>{}"):
            continue
        if not (ROOT / path).exists():
            missing.append(path)
    return missing

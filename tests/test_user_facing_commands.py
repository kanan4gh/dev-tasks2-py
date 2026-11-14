"""利用者に見える文字列が、存在しないコマンド名 `task <コマンド>` を案内していないこと(Issue #64)。

実在するコマンド名は `task-py`。`task`(TypeScript 版時代の名前)を対処文などに書くと、
利用者がそのまま実行できない。Web と MCP も同じ文言を返す。
"""

import ast
import re
from pathlib import Path

import typer.main

from task_cli.cli.main import app

SRC = Path(__file__).parents[1] / "src"


def _command_words() -> set[str]:
    root = typer.main.get_command(app)
    return set(getattr(root, "commands", {}))


def _string_constants(tree: ast.AST) -> list[ast.Constant]:
    """docstring を除く文字列定数。docstring はコードの説明で、利用者には見えない。"""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def test_user_facing_strings_do_not_name_a_nonexistent_task_command() -> None:
    words = "|".join(sorted(re.escape(w) for w in _command_words()))
    bare = re.compile(rf"(?<![\w\-/.])task (?:{words})\b")
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in _string_constants(tree):
            assert isinstance(node.value, str)
            if bare.search(node.value):
                offenders.append(f"{path.relative_to(SRC.parent)}:{node.lineno}: {node.value.strip()[:60]}")
    assert offenders == [], f"存在しないコマンド名 `task <cmd>` を案内しています(`task-py` が正): {offenders}"


def test_the_check_itself_detects_a_bare_command() -> None:
    """検査が空振りしていないこと(わざと誤った文字列で、検出されることを確かめる)。"""
    tree = ast.parse('remedy = "task list で有効なIDを確認してください。"\n\ndef f():\n    """task list の説明"""\n')
    found = [n.value for n in _string_constants(tree)]
    assert found == ["task list で有効なIDを確認してください。"]  # docstring は除かれる

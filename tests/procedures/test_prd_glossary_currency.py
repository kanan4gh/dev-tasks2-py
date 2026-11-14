"""docs/product-requirements.md と docs/glossary.md が実装の実態から乖離していないことを検査する。

どちらも TypeScript 版(`~/.task/`・JSON・Commander.js・コマンド名 `task`)の文書として
書かれ、Python 版へ移った後も記述が残った(Issue #57)。PRD は add-feature の軽量パス
基準3の判定対象でもあるため、実在しないパス・コマンドを頼りに読まれると、変更が文書に
影響するかどうかの判断が不定になる。`test_functional_design_currency.py` と同じ流儀で、
「存在しないものを指していないこと」を検査する(文面の細部は見ない)。

Git・GitHub 連携は要求として残すが Python 版には実装が無い。そうした節・用語は見出しに
`【未実装】` を付け、本検査は、実在するコマンドの照合からそれらを除く。
"""

import re
from pathlib import Path

import pytest
import typer.main

from task_cli.cli.main import app

ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs"
TARGETS = ("product-requirements.md", "glossary.md")

UNIMPLEMENTED = "【未実装】"

# TypeScript 版時代の道具立て。Python 版のどこにも存在しないので、文書全体で禁止する。
TYPESCRIPT_ERA_TERMS = (
    "Commander.js",
    "Vitest",
    "simple-git",
    "node-fetch",
    "Node.js",
    "npm ",
    "husky",
    "lint-staged",
    "inquirer",
    "chalk",
    "cli-table3",
    "TypeScript 型",
    "src/types/index.ts",
)

# 旧い永続ファイル名。Python 版は YAML。
OLD_FILE_NAMES = ("tasks.json", "config.json", "routines.json", "log.json")

# コマンド名は `task-py`。`task <サブコマンド>` の形は実在しない。
TASK_COMMAND_WORDS = (
    "add|list|show|start|done|delete|archive|move|inbox|edit|search|project|daily|time|"
    "config|sync|import|assign|schedule|overview|shell|web|migrate|reset|--help|<subcommand>"
)
BARE_TASK_COMMAND = re.compile(rf"(?<![\w\-/.])task (?:{TASK_COMMAND_WORDS})")


def read(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def sections(text: str) -> list[tuple[str, list[str]]]:
    """(見出し, 本文の行) に分ける。コードブロック内の `#` は見出しとして扱わない。"""
    result: list[tuple[str, list[str]]] = [("", [])]
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"#{1,6} ", line):
            result.append((line, [line]))
        else:
            result[-1][1].append(line)
    return result


# 実装が無いことを文書が明記しているコマンド。実在するコマンドとは見なさないが、
# 【未実装】の節か「未実装」と書いた行でだけ名前を出してよい。これ以外の存在しない
# コマンドは、未実装と書いてあっても許さない(古いコマンド名が未実装の注記に隠れない)。
UNIMPLEMENTED_COMMANDS = {"config", "sync", "import", "assign"}


def heading_level(heading: str) -> int:
    return len(heading) - len(heading.lstrip("#"))


def command_mentions(text: str) -> list[tuple[str, str | None, bool]]:
    """(コマンド, サブコマンド, 未実装の文脈か) の一覧。

    未実装の文脈 = 見出しに 【未実装】 を持つ節(その下位の見出しを含む)の中、
    または「未実装」と書いた行。
    """
    mentions: list[tuple[str, str | None, bool]] = []
    marked_level: int | None = None
    for heading, lines in sections(text):
        if heading:
            level = heading_level(heading)
            if marked_level is not None and level <= marked_level:
                marked_level = None
            if marked_level is None and UNIMPLEMENTED in heading:
                marked_level = level
        for line in lines:
            context = marked_level is not None or "未実装" in line
            for first, second in re.findall(r"`?task-py ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?", line):
                mentions.append((first, second or None, context))
    return mentions


def cli_commands() -> tuple[set[str], dict[str, set[str]]]:
    root = typer.main.get_command(app)
    top: set[str] = set(getattr(root, "commands", {}))
    groups: dict[str, set[str]] = {}
    for name, command in getattr(root, "commands", {}).items():
        subs = getattr(command, "commands", None)
        if subs:
            groups[name] = set(subs)
    return top, groups


@pytest.mark.parametrize("name", TARGETS)
def test_no_typescript_era_tools_or_paths(name: str) -> None:
    text = read(name)
    found = [term for term in TYPESCRIPT_ERA_TERMS if term in text]
    assert found == [], f"TypeScript 版時代の語が残っています: {found}"
    assert re.findall(r"`[\w/.\-]*\.ts`", text) == [], "TypeScript のソースパスが残っています"
    assert re.findall(r"src/(?:services|storage|cli|utils)/[\w/.]*\.ts", text) == []


@pytest.mark.parametrize("name", TARGETS)
def test_old_storage_location_only_appears_when_describing_migration(name: str) -> None:
    offenders = [
        line.strip()
        for line in read(name).splitlines()
        if "~/.task/" in line and "migrate" not in line and "移行" not in line
    ]
    assert offenders == [], "旧保存先 ~/.task/ は移行の説明以外に出てはならない"


@pytest.mark.parametrize("name", TARGETS)
def test_no_old_json_storage_file_names(name: str) -> None:
    text = read(name)
    found = [n for n in OLD_FILE_NAMES if n in text]
    assert found == [], f"旧い永続ファイル名が残っています: {found}"


@pytest.mark.parametrize("name", TARGETS)
def test_command_name_is_task_py(name: str) -> None:
    offenders = [line.strip() for line in read(name).splitlines() if BARE_TASK_COMMAND.search(line)]
    assert offenders == [], f"実在しないコマンド名 `task <cmd>` が残っています（`task-py`）: {offenders[:5]}"


@pytest.mark.parametrize("name", TARGETS)
def test_source_and_test_paths_named_in_the_document_exist(name: str) -> None:
    missing = []
    for path in sorted(set(re.findall(r"`((?:src|tests)/[^`\s]+)`", read(name)))):
        if any(mark in path for mark in "*<>{}"):
            continue
        if not (ROOT / path).exists():
            missing.append(path)
    assert missing == [], f"存在しないパスを指しています: {missing}"


@pytest.mark.parametrize("name", TARGETS)
def test_documented_commands_exist(name: str) -> None:
    top, groups = cli_commands()
    unknown = []
    for first, second, unimplemented_context in command_mentions(read(name)):
        if unimplemented_context and first in UNIMPLEMENTED_COMMANDS:
            continue
        if first not in top:
            unknown.append(f"task-py {first}")
        elif first in groups and second and second not in groups[first]:
            unknown.append(f"task-py {first} {second}")
    assert unknown == [], f"実在しないコマンドを載せています: {sorted(set(unknown))}"


def github_slug(heading: str) -> str:
    text = re.sub(r"^#+\s*", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


@pytest.mark.parametrize("name", TARGETS)
def test_internal_and_cross_document_links_resolve(name: str) -> None:
    slugs: dict[str, set[str]] = {}
    broken = []
    for target, anchor in re.findall(r"\]\(((?:\./)?[\w\-]+\.md)?#([^)]+)\)", read(name)):
        doc = (target or name).removeprefix("./")
        if doc not in slugs:
            slugs[doc] = {github_slug(h) for h, _ in sections(read(doc)) if h} if (DOCS / doc).exists() else set()
        if anchor not in slugs[doc]:
            broken.append(f"{doc}#{anchor}")
    assert broken == [], f"切れたアンカー(または存在しないファイル): {broken}"


def headings(name: str) -> list[str]:
    return [h for h, _ in sections(read(name)) if h]


def test_git_and_github_requirements_are_kept_and_marked_unimplemented() -> None:
    """要求として残し(消さず)、未実装と明記している。"""
    marked = [h for h in headings("product-requirements.md") if UNIMPLEMENTED in h]
    for keyword in ("Git ブランチ", "完了時の自動処理", "GitHub Issues"):
        assert any(keyword in h for h in marked), f"PRD の『{keyword}』の節に {UNIMPLEMENTED} がありません"


def test_glossary_git_and_github_terms_are_marked_unimplemented() -> None:
    all_headings = headings("glossary.md")
    for term in (
        "ブランチスラッグ",
        "作業中タスク",
        "コミット自動タグ付け",
        "同期",
        "インポート",
        "GitService",
        "GitHubService",
        "ConfigService",
        "ConfigStorage",
        "ProjectConfig",
    ):
        # 見出しの語を単語として探す(`ConfigService` が `GlobalConfigService` に当たらないように)
        own = [h for h in all_headings if re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", h)]
        assert own, f"glossary に『{term}』の見出しがありません(用語を残す方針)"
        assert all(UNIMPLEMENTED in h for h in own), f"glossary の『{term}』に {UNIMPLEMENTED} がありません"

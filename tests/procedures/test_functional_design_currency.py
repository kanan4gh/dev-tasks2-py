"""docs/functional-design.md が実装の実態から乖離していないことを検査する。

この文書は TypeScript 版(`~/.task/`・JSON・Commander.js)の設計書として書かれ、
Python 版へ移った後も記述が残った(Issue #43)。add-feature の軽量パス基準3の
判定対象でもあるため、実在しないパスやコマンドを頼りに読まれると、変更が文書に
影響するかどうかの判断が不定になる。同じ陳腐化を再び入れないための検査である。

検査するのは「存在しないものを指していないこと」であり、文面の細部ではない。
"""

import re
from pathlib import Path

import typer.main

from task_cli.cli.main import app

ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs" / "functional-design.md"

UNIMPLEMENTED_HEADING = "## 未実装の設計"

# TypeScript 版時代の道具立て。Python 版のどこにも存在しないので、文書全体で禁止する。
TYPESCRIPT_ERA_TERMS = (
    "Commander.js",
    "Vitest",
    "simple-git",
    "node-fetch",
    "Array.prototype",
    "AbortController",
    "Node.js",
    "encodeURIComponent",
)

# 旧い永続ファイル名。Python 版は YAML(Web の JSON API の説明は別物)。
OLD_FILE_NAMES = ("tasks.json", "config.json", "routines.json", "log.json")

# Python 版に実装のない Git・GitHub 連携の識別子。実装済みの節に出てはならない
# (「未実装」と書いた参照行を除く)。`GlobalConfigService` を巻き込まないよう単語境界で見る。
UNIMPLEMENTED_IDENTIFIERS = (
    r"(?<![A-Za-z])GitService",
    r"(?<![A-Za-z])GitHubService",
    r"(?<![A-Za-z])ConfigService",
    r"(?<![A-Za-z])ConfigStorage",
    r"\.taskcli-current",
    r"prepare-commit-msg",
    r"task-py (?:sync|config|import)\b",
    r"task-py done \S+ --pr",
)


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def split_sections(text: str) -> tuple[str, str]:
    """(実装済みの節, 未実装の設計の節) に分ける。後者が無ければ空文字。"""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(UNIMPLEMENTED_HEADING)]
    if not starts:
        return text, ""
    return "\n".join(lines[: starts[0]]), "\n".join(lines[starts[0] :])


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


def test_no_typescript_code_blocks() -> None:
    assert "```typescript" not in read_doc()


def test_no_typescript_source_paths() -> None:
    text = read_doc()
    assert re.findall(r"src/[\w/.\-]*\.ts\b", text) == []
    # TypeScript 版のレイヤー配置(`src/services/` `src/storage/` `src/cli/` 直下)
    assert re.findall(r"`src/(?:services|storage|cli|utils)/", text) == []


def test_no_typescript_era_tools_or_apis() -> None:
    text = read_doc()
    found = [term for term in TYPESCRIPT_ERA_TERMS if term in text]
    assert found == [], f"TypeScript 版時代の語が残っています: {found}"


def test_old_storage_location_only_appears_when_describing_migration() -> None:
    offenders = [
        line.strip()
        for line in read_doc().splitlines()
        if "~/.task/" in line and "migrate" not in line and "移行" not in line
    ]
    assert offenders == [], "旧保存先 ~/.task/ は移行の説明以外に出てはならない"


def test_no_old_json_storage_file_names() -> None:
    text = read_doc()
    found = [name for name in OLD_FILE_NAMES if name in text]
    assert found == [], f"旧い永続ファイル名が残っています: {found}"


def test_source_and_test_paths_named_in_the_document_exist() -> None:
    text = read_doc()
    missing = []
    for path in sorted(set(re.findall(r"`((?:src|tests)/[^`\s]+)`", text))):
        if any(mark in path for mark in "*<>{}"):
            continue
        if not (ROOT / path).exists():
            missing.append(path)
    assert missing == [], f"存在しないパスを指しています: {missing}"


def command_rows(text: str) -> list[tuple[tuple[str, ...], set[str]]]:
    """コマンド表の行を (コマンドの語の並び, 載っているオプション名) にする。

    行は `| `task-py <コマンド> ...` | <オプション> | <説明> |` の形。引数(`<id>` `[date]`)に
    当たるまでの語がコマンド、その後ろは引数やオプションとして読む。
    """
    rows = []
    for match in re.finditer(r"^\| `(task-py [^`]+)` \| ([^|]*) \|", text, re.MULTILINE):
        command_cell, options_cell = match.group(1), match.group(2)
        words: list[str] = []
        for token in command_cell.split()[1:]:
            if token[0] in "<[-":
                break
            words.append(token)
        flags = set(re.findall(r"(?<![\w-])(--?[A-Za-z][\w-]*)", command_cell))
        flags |= set(re.findall(r"`(--?[A-Za-z][\w-]*)`", options_cell))
        rows.append((tuple(words), flags))
    return rows


def resolve_command(path: tuple[str, ...]) -> object | None:
    command: object = typer.main.get_command(app)
    for word in path:
        children = getattr(command, "commands", None)
        if not children or word not in children:
            return None
        command = children[word]
    return command


def test_every_real_command_has_a_row_in_the_command_tables() -> None:
    """実在するコマンドが、実装済みの節のコマンド表に行として載っている。

    本文や図に名前が出ているだけでは足りない(表の行を消しても通ってしまう)。
    """
    implemented, _ = split_sections(read_doc())
    documented = {path for path, _ in command_rows(implemented)}
    top, groups = cli_commands()
    expected: set[tuple[str, ...]] = set()
    for name in top:
        if name in groups:
            expected |= {(name, sub) for sub in groups[name]}
        else:
            expected.add((name,))
    assert sorted(expected - documented) == [], "コマンド表に行が無い実在コマンド"


def test_command_tables_only_name_real_commands_and_options() -> None:
    """表に載っているコマンドとオプションが実在する(実在しないオプションを載せない)。"""
    implemented, _ = split_sections(read_doc())
    problems = []
    for path, flags in command_rows(implemented):
        command = resolve_command(path)
        if command is None:
            problems.append(f"task-py {' '.join(path)}: 実在しないコマンド")
            continue
        real_flags: set[str] = set()
        for param in getattr(command, "params", []):
            real_flags |= set(getattr(param, "opts", [])) | set(getattr(param, "secondary_opts", []))
        for flag in sorted(flags - real_flags):
            problems.append(f"task-py {' '.join(path)}: 実在しないオプション {flag}")
    assert problems == []


def test_documented_commands_exist_in_the_implemented_sections() -> None:
    implemented, _ = split_sections(read_doc())
    top, groups = cli_commands()
    unknown = []
    for first, second in re.findall(r"`task-py ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?", implemented):
        if first not in top:
            unknown.append(f"task-py {first}")
        elif first in groups and second and second not in groups[first]:
            unknown.append(f"task-py {first} {second}")
    assert unknown == [], f"実在しないコマンドを載せています: {sorted(set(unknown))}"


def test_unimplemented_design_is_isolated_in_its_own_section() -> None:
    implemented, unimplemented = split_sections(read_doc())
    assert unimplemented, f"『{UNIMPLEMENTED_HEADING}』節が必要です"

    # 節の冒頭で、Python 版には実装がないことを明記している
    intro = "\n".join(unimplemented.splitlines()[1:12])
    assert "未実装" in intro

    # 実装済みの節には、未実装の機能の識別子が残っていない(未実装と断った参照行を除く)
    leaked = []
    for line in implemented.splitlines():
        if "未実装" in line:
            continue
        for pattern in UNIMPLEMENTED_IDENTIFIERS:
            if re.search(pattern, line):
                leaked.append(line.strip())
                break
    assert leaked == [], f"実装済みの節に未実装の機能への言及が残っています: {leaked}"


def test_unimplemented_section_is_the_last_section() -> None:
    """実装済みの節を、未実装の節より後ろに足せないようにする。

    未実装の節より後ろは、禁止語・コマンド・識別子の検査の対象外になるため、
    そこへ実装済みの節を足すと検査をすり抜ける。
    """
    _, unimplemented = split_sections(read_doc())
    in_fence = False
    headings = []
    for line in unimplemented.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            headings.append(line)
    assert len(headings) == 1, f"『{UNIMPLEMENTED_HEADING}』より後ろに節があります: {headings[1:]}"

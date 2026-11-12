"""~/.task-py のバックアップを世代管理する（reset / migrate で共有）。

退避先は ``<backup_root名>.<YYYYMMDD-HHMMSS>`` の世代別ディレクトリ。新しい世代の退避に
成功した後でだけ、保持数を超えた最古の世代を削除する（先に消すと、退避に失敗したときに
前回のバックアップだけが失われる）。接尾辞なしの旧形式（``~/.task-py.backup``）は世代に
数えず、触らない。
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_KEEP = 5

_STAMP_FORMAT = "%Y%m%d-%H%M%S"


def _generation_pattern(backup_root: Path) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(backup_root.name)}\.(\d{{8}}-\d{{6}})(?:-(\d+))?$")


def _list_generations(backup_root: Path) -> list[Path]:
    """世代ディレクトリを古い順に返す（同一秒の接尾辞は数値として比較する）。"""
    pattern = _generation_pattern(backup_root)
    found: list[tuple[str, int, Path]] = []
    for path in backup_root.parent.iterdir():
        match = pattern.match(path.name)
        if match and path.is_dir():
            found.append((match.group(1), int(match.group(2) or 0), path))
    found.sort(key=lambda item: (item[0], item[1]))
    return [path for _, _, path in found]


def create_backup(
    src: Path,
    backup_root: Path,
    keep: int = DEFAULT_KEEP,
    now: datetime | None = None,
) -> Path:
    """``src`` を新しい世代として複製し、複製先を返す。

    複製に失敗した場合は作りかけを消して例外を伝える。その時点で既存の世代は1つも
    削除されていない。今作った世代は、時計の巻き戻し等で名前順が古く見えても削除しない。
    """
    if keep < 1:
        raise ValueError("keep は 1 以上を指定してください（0 以下では今作った退避まで消える）")
    stamp = (now or datetime.now()).strftime(_STAMP_FORMAT)
    base = backup_root.parent / f"{backup_root.name}.{stamp}"
    dest = base
    suffix = 0
    while dest.exists():
        suffix += 1
        dest = base.with_name(f"{base.name}-{suffix}")

    try:
        shutil.copytree(src, dest)
    except FileExistsError:
        # 並行実行が同じ名前を先に作った。相手の退避を消さないよう後始末しない
        raise
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise

    _prune(backup_root, keep, protect=dest)
    return dest


def _prune(backup_root: Path, keep: int, protect: Path) -> None:
    """保持数を超えた最古の世代を削除する（``protect`` は対象外）。削除の失敗は退避の成否に影響させない。"""
    generations = _list_generations(backup_root)
    for old in generations[: max(len(generations) - keep, 0)]:
        if old != protect:
            shutil.rmtree(old, ignore_errors=True)


def backup_label(backup_root: Path, keep: int = DEFAULT_KEEP) -> str:
    """確認ダイアログ用の文言。退避先の形式と保持世代数を示す。"""
    return f"バックアップは {backup_root}.<日時> に保存されます（直近 {keep} 世代を保持し、古い世代から削除されます）"

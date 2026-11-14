"""「今日」の日付の定義が1か所にあること(Issue #67)。

`start` の解禁日の判定・`show` の「着手できません」の表示・ルーティーンの日付が同じ
定義を使う。どれか1つだけ変えると、表示と判定がずれる。
"""

import re
from datetime import datetime
from pathlib import Path

from task_cli.clock import today_str

SRC = Path(__file__).parents[1] / "src"


def test_today_str_is_the_local_date_in_iso_format() -> None:
    before = datetime.now().strftime("%Y-%m-%d")
    got = today_str()
    after = datetime.now().strftime("%Y-%m-%d")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", got)
    assert got in (before, after)  # 日付をまたぐ瞬間でも落ちない


def test_the_today_expression_exists_only_in_clock() -> None:
    """同じ式のコピーを作らせない(`clock.py` 以外にあれば、定義が重複している)。"""
    # 同じ式の別の書き方(`date.today()` や `strftime("%Y-%m-%d")`)も、定義の重複として数える
    idioms = (".astimezone().strftime(", "date.today(", 'strftime("%Y-%m-%d")', "strftime('%Y-%m-%d')")
    offenders = [
        f"{path.relative_to(SRC.parent)}: {idiom}"
        for path in sorted(SRC.rglob("*.py"))
        if path.name != "clock.py"
        for idiom in idioms
        if idiom in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"『今日』の式が clock.py 以外にもあります: {offenders}"

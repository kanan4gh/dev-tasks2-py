"""「今日」の日付の定義。

解禁日（`scheduled_date`）の判定と表示、ルーティーンの日付が、すべてこの関数を使う。
別々に同じ式を書くと、1つだけ変えたときに、表示（`show` の「着手できません」）と
判定（`start` の拒否）がずれる。定義はここ1か所に置く。
"""

from datetime import datetime, timezone


def today_str() -> str:
    """ローカルタイムゾーンの今日の日付（`YYYY-MM-DD`）。"""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

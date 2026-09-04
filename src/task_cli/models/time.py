"""タイマーと作業時間のデータモデル。

`models/daily.py` と同じく `models/task.py` とは別ファイルに分ける。
このモジュールは `models/task.py` を import しない（`Task` 側が `WorkSession` を
取り込むため、逆向きに依存すると循環する）。
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class WorkSession(BaseModel):
    """タスクに対して実際に作業した1区間。"""

    started_at: datetime
    ended_at: datetime
    seconds: int
    source: Literal["timer", "manual"] = "timer"


class TimerKind(str, Enum):
    COUNTDOWN = "countdown"
    STOPWATCH = "stopwatch"


class TimerState(BaseModel):
    """実行中タイマーの宣言的な記録。

    残り時間や経過時間はここに持たず、`started_at` と `duration_seconds` から
    都度計算する。そうすることで、書いたプロセスが落ちても・別プロセスから読んでも
    ・端末がスリープしても、同じ値が得られる。
    """

    kind: TimerKind = TimerKind.COUNTDOWN
    # 開始時のアクティブプロジェクト（None = Inbox）。停止時のパス解決に使うので、
    # 実行中に project use で切り替えられても記録先がぶれない。
    project: str | None = None
    task_id: int | None = None
    # 表示用の非正規化コピー。正本は Task 側で、ズレても表示が古くなるだけ。
    task_title: str | None = None
    duration_seconds: int | None = None  # STOPWATCH なら None
    started_at: datetime
    # 参考情報。プロセスの生死判定には使わない（PID は再利用されるため信用できない）。
    pid: int | None = None


class TimerFile(BaseModel):
    """timer.yaml のトップレベル。

    将来タイマーを複数本に広げたり履歴を足したりできるよう、
    リストではなくオブジェクトで包んでおく。
    """

    active: TimerState | None = None

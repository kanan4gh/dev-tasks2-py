"""「いま見えているデータが変わったか」を1つの値で表す。

CLI や MCP サーバーは別プロセスとして同じ `~/.task-py/` を書き換える。ブラウザを
開いたまま放置しても最新が見えるように、サーバは監視対象のファイルから
リビジョン値を作り、変わったことだけをクライアントへ伝える。

**差分は作らない。** 差分同期は「いま何が表示されているか」という状態をサーバ側
にも持つことになり、「真実は YAML」という原則を壊す。クライアントは通知を受けて
表示中のものを取り直せばよい。
"""

import hashlib
from pathlib import Path

from task_cli.services.daily_service import DailyService
from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.timer_service import TimerService
from task_cli.usecases.task_crud_usecase import resolve_storage_path


def watched_paths(config_service: GlobalConfigService) -> list[Path]:
    """リビジョンの計算対象。

    **API が返すものはすべて含める。** `/api/overview` はタイマーと
    ルーティーンも返すので、`timer.yaml` と `daily/` も見る。ここに漏れがあると、
    画面は「変更を監視中」と言いながら古い値を映し続ける。

    プロジェクト一覧は毎回 `config.yaml` から取り直す。実行中に新しい
    プロジェクトが増えても次の計算から追随させるためである。
    """
    daily = DailyService()
    paths = [
        config_service.config_path,
        resolve_storage_path(None),
        TimerService().timer_path,
        daily.routines_path,
        daily.log_path,
    ]
    try:
        projects = config_service.get_all().projects
    except Exception:
        # 設定が壊れている・読めない場合でもサーバを落とさない。次の計算で
        # 読めるようになれば自然に追随する。
        return paths
    paths.extend(resolve_storage_path(p.name) for p in projects)
    return paths


def revision(config_service: GlobalConfigService) -> str:
    """監視対象の (パス, mtime_ns, サイズ) からダイジェストを作る。

    内容のハッシュではなく `stat` を使う。全ファイルを読まずに済み、単一利用者の
    更新頻度では取りこぼしが問題にならない。`~/.task-py/` がまだ無い場合も
    例外にせず、空の状態を表す値を返す。
    """
    digest = hashlib.sha256()
    for path in watched_paths(config_service):
        digest.update(str(path).encode("utf-8"))
        try:
            stat = path.stat()
        except OSError:
            digest.update(b"-")
            continue
        digest.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode())
    return digest.hexdigest()[:16]

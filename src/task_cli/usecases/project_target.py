"""操作対象プロジェクトの指定を表す語彙。

`~/.task-py/config.yaml` の `activeProject` はプロセスの外にある共有状態である。
これを暗黙の引数として使うと、複数のプロセス（CLI・MCP サーバー・ローカル Web
GUI）が同時に動いたときに「画面で選んだタスク」と「実際に書き換わるタスク」が
食い違う。タスク ID はストレージローカルなので、別プロジェクトにも同じ ID が
存在しうるからである。

そこで呼び出し側が対象を明示できるようにする。ただし `None` は Inbox という
**実在する保存先**を意味するため、「未指定（アクティブに従う）」の意味に流用
できない。両者を型で区別する。
"""


class ActiveProject:
    """「グローバル設定のアクティブプロジェクトに従う」ことを表す番兵の型。

    直接インスタンス化せず、唯一の値である `ACTIVE_PROJECT` を使う。公開名に
    しているのは、解決側（`TaskCrudUseCase` / `TimeTrackingUseCase`）が
    `isinstance()` で分岐する必要があり、モジュールをまたいでアンダースコア
    付きの名前を import させたくないためである。
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "ACTIVE_PROJECT"


ACTIVE_PROJECT = ActiveProject()
"""既定値。CLI と MCP は従来どおりアクティブプロジェクトに追従する。"""

ProjectTarget = str | None | ActiveProject
"""プロジェクト名 / Inbox（`None`）/ アクティブ追従（`ACTIVE_PROJECT`）。"""

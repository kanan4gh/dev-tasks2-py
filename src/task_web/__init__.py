"""ローカル Web GUI。

`task_cli`（端末）・`task_mcp`（stdio）に並ぶ3つ目の入口である。既存の層規則を
そのまま適用し、`usecases/` と `services/` を呼び、`storage/` には直接触らない。

サーバは状態をメモリに溜めない。真実は `~/.task-py/` の YAML であり、CLI や
MCP サーバーがいつ何を書いても、次のリクエストで正しい値が返る。
"""

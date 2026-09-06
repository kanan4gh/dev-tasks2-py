"""`python -m task_web` / `task-web` のエントリポイント。

`task_mcp/__main__.py` と同じ形にしてある: 組み立ては `server.py` が持ち、
ここは起動するだけの薄い入口である。
"""

from task_web.server import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()

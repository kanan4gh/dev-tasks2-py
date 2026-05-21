#!/bin/bash
set -e

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

export PATH="$HOME/.local/bin:$PATH"

# よく使うPython系
uv tool install ruff
uv tool install basedpyright

# Claude確認
claude --version || true

# AWS確認
aws --version || true
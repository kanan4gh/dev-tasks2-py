# 要求定義

## 関連Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/4

## 概要

スペック駆動開発用のClaude Code環境とAWS開発用のDevcontainer設定一式を提供するGitHubテンプレートリポジトリを作成する。

## 要求内容

### リポジトリの種類
- GitHubテンプレートリポジトリ（"Use this template"で新プロジェクト開始）

### Devcontainer構成
- ベースイメージ: `mcr.microsoft.com/devcontainers/python:3.12-bookworm`
- 含めるFeature:
  - Claude Code（`ghcr.io/anthropics/devcontainer-features/claude-code:1.0`）
  - AWS CLI（`ghcr.io/devcontainers/features/aws-cli:1`）
  - Docker-in-Docker（`ghcr.io/devcontainers/features/docker-in-docker:2`）
  - GitHub CLI（`ghcr.io/devcontainers/features/github-cli:1`）
- `postCreate.sh` でインストール:
  - uv（Pythonパッケージマネージャー）
  - ruff・basedpyright（Python開発ツール）
  - AWS CDK（`npm install -g aws-cdk`）
  - AWS SAM CLI（pip経由）
  - Claude・AWS CLIのバージョン確認
- AWS認証: `~/.aws/` をバインドマウント（プロファイル名・リージョンはプレースホルダー）

### 言語・ランタイム
- Python 3.12 + uv

### スペック駆動開発テンプレート
- `CLAUDE.md`: 汎用層 + プロダクト固有層プレースホルダー + 技術スタック固有層（CDK/SAM CLI/uv向け）
- `docs/`: 以下6ファイルのひな形（プレースホルダー記入済み）
  - product-requirements.md
  - functional-design.md
  - architecture.md
  - repository-structure.md
  - development-guidelines.md
  - glossary.md
- `.steering/example/`: ステアリングファイルのひな形（requirements.md・design.md・tasklist.md の3ファイル）
- `.claude/commands/`: カスタムコマンド
  - `setup-project.md` - プロジェクト初期セットアップ
  - `add-feature.md` - 機能追加フロー
  - `review-docs.md` - ドキュメントレビュー
- `.claude/agents/`: カスタムエージェント
  - `doc-reviewer.md`
  - `implementation-validator.md`
- `.claude/skills/`: カスタムスキル
  - `steering/` - ステアリング管理（作業計画・実装管理・振り返りの3モード、テンプレート3ファイル付き）
  - `prd-writing/` - PRD作成
  - `functional-design/` - 機能設計
  - `architecture-design/` - アーキテクチャ設計
  - `repository-structure/` - リポジトリ構造定義
  - `development-guidelines/` - 開発ガイドライン
  - `glossary-creation/` - 用語集作成
- `.claude/settings.json`: スキル実行許可設定（`settings.local.json` は `.gitignore` で除外）

### ドキュメント
- `README.md`: セットアップ手順（AWS Profile設定方法を含む）

## 対象ユーザー

個人開発者。スペック駆動開発とAWSクラウド開発を組み合わせて使いたい人。

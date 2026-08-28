# 実装設計

## リポジトリ名

`claude-aws-devcontainer-starter`

## リポジトリ作成場所

devcontainer内の `/workspaces/` 以下に新規作成し、GitHubへプッシュ後にテンプレートリポジトリとして設定する。

## ディレクトリ構造

```
claude-aws-devcontainer-starter/
├── .devcontainer/
│   ├── devcontainer.json
│   └── postCreate.sh
├── .claude/
│   ├── agents/
│   │   ├── doc-reviewer.md
│   │   └── implementation-validator.md
│   ├── commands/
│   │   ├── add-feature.md
│   │   ├── review-docs.md
│   │   └── setup-project.md
│   ├── skills/
│   │   ├── architecture-design/
│   │   ├── development-guidelines/
│   │   ├── functional-design/
│   │   ├── glossary-creation/
│   │   ├── prd-writing/
│   │   ├── repository-structure/
│   │   └── steering/
│   └── settings.json
├── .steering/
│   └── example/
│       ├── requirements.md
│       ├── design.md
│       └── tasklist.md
├── docs/
│   ├── product-requirements.md
│   ├── functional-design.md
│   ├── architecture.md
│   ├── repository-structure.md
│   ├── development-guidelines.md
│   └── glossary.md
├── .gitignore
├── CLAUDE.md
└── README.md
```

## 各コンポーネントの設計方針

### `.devcontainer/devcontainer.json`

現行プロジェクト（dev-tasks2-py）をベースに以下を変更:
- `name` を `claude-aws-devcontainer-starter` に変更
- `AWS_PROFILE` を `your-profile` に変更（プレースホルダー）
- `AWS_REGION` / `AWS_DEFAULT_REGION` を `ap-northeast-1` に変更（プレースホルダー）
- `postCreateCommand` を `bash .devcontainer/postCreate.sh` のまま維持
- VSCode拡張はPython・Docker・AWS Toolkit・TOML を維持

### `.devcontainer/postCreate.sh`

現行の内容に加えて以下を追加:
- AWS CDK: `npm install -g aws-cdk`
- AWS SAM CLI: `pip install aws-sam-cli`
- Node.js は AWS CDK インストール前提のため Feature で追加（`ghcr.io/devcontainers/features/node:1`）

### `CLAUDE.md`

3層構造を維持し、技術スタック固有層をこのテンプレート向けに書き換える:
- 汎用層: dev-tasks2-py の CLAUDE.md からそのままコピー
- プロダクト固有層: プレースホルダーのみ（`[YOUR PRODUCT NAME]` 等）
- 技術スタック固有層: Python/uv/AWS CDK/SAM CLI/typer 構成を記述

### `docs/` ひな形ファイル

各ファイルは最低限のセクション構造のみを持つプレースホルダー。
内容は `/setup-project` コマンド実行時に対話的に作成するため、空に近い状態でよい。

### `.steering/example/`

現行の `.steering/20260402-dev-tasks2-py-setup/` を参考に、
プロジェクト固有の内容を削除してひな形として整備する。

### `.claude/` コンテンツ

dev-tasks2-py にコピーされた内容をそのまま使用する。
`settings.json` も同様。

### `README.md`

以下のセクションを含む:
1. このテンプレートについて
2. 前提条件（Docker・VSCode・AWS Profile設定済みであること）
3. セットアップ手順
   - GitHub でテンプレートからリポジトリ作成
   - `devcontainer.json` の AWS_PROFILE・AWS_REGION を自分の環境に合わせて変更
   - devcontainerを開く
4. 使い方（スペック駆動開発フロー）
5. 含まれるツール一覧

### `.gitignore`

- Python標準除外
- `.claude/settings.local.json`

## 実装上の注意点

- CDK インストールには Node.js が必要なため、devcontainer Feature に `node` を追加する
- SAM CLI は `pip install aws-sam-cli` で導入できるが、バージョン固定を検討する
- テンプレートリポジトリの設定は `gh repo edit --template` で行う

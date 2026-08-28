# タスクリスト

## 🚨 タスク完全完了の原則

**このファイルの全タスクが完了するまで作業を継続すること**

---

## フェーズ1: リポジトリ作成

- [ ] GitHubリポジトリ `claude-aws-devcontainer-starter` を作成（`gh repo create`）
- [ ] `/workspaces/` 以下にクローン
- [ ] `.gitignore` を作成（Python標準 + `.claude/settings.local.json`）
- [ ] 初回コミット

## フェーズ2: Devcontainer構成

- [ ] `.devcontainer/devcontainer.json` を作成
  - [ ] 現行プロジェクトをベースにプレースホルダー（AWS_PROFILE・リージョン）を設定
  - [ ] Node.js Feature を追加（CDK用）
- [ ] `.devcontainer/postCreate.sh` を作成
  - [ ] uv インストール
  - [ ] ruff・basedpyright インストール
  - [ ] AWS CDK インストール（`npm install -g aws-cdk`）
  - [ ] AWS SAM CLI インストール（`pip install aws-sam-cli`）
  - [ ] Claude・AWS CLIのバージョン確認

## フェーズ3: Claude Code構成

- [ ] `.claude/` を dev-tasks2-py からコピー（agents/・commands/・skills/・settings.json）
- [ ] `settings.json` の内容を確認・必要に応じて調整

## フェーズ4: CLAUDE.md 作成

- [ ] 汎用層: dev-tasks2-py の CLAUDE.md からコピー
- [ ] プロダクト固有層: プレースホルダーに書き換え
- [ ] 技術スタック固有層: Python/uv/AWS CDK/SAM CLI 向けに記述

## フェーズ5: docs/ ひな形作成

- [ ] `docs/product-requirements.md` を作成（セクション構造のみ）
- [ ] `docs/functional-design.md` を作成（セクション構造のみ）
- [ ] `docs/architecture.md` を作成（セクション構造のみ）
- [ ] `docs/repository-structure.md` を作成（セクション構造のみ）
- [ ] `docs/development-guidelines.md` を作成（セクション構造のみ）
- [ ] `docs/glossary.md` を作成（セクション構造のみ）

## フェーズ6: .steering/ ひな形作成

- [ ] `.steering/example/requirements.md` を作成
- [ ] `.steering/example/design.md` を作成
- [ ] `.steering/example/tasklist.md` を作成

## フェーズ7: README.md 作成

- [ ] 「このテンプレートについて」セクション
- [ ] 「前提条件」セクション（Docker・VSCode・AWS Profile）
- [ ] 「セットアップ手順」セクション（AWS_PROFILE・リージョンの変更方法を含む）
- [ ] 「使い方」セクション（スペック駆動開発フロー）
- [ ] 「含まれるツール一覧」セクション

## フェーズ8: 仕上げ

- [ ] devcontainerが正常に起動することを確認
- [ ] `aws --version`・`cdk --version`・`sam --version` が通ることを確認
- [ ] GitHubリポジトリをテンプレートとして設定（`gh repo edit --template`）
- [ ] 関連Issue（#4）をクローズ（`gh issue close 4 -R kanan4gh/dev-tasks2-py`）

---

## 実装後の振り返り

### 実装完了日
未定

### 計画と実績の差分

**計画と異なった点**:
-

### 学んだこと
-

### 次回への改善提案
-

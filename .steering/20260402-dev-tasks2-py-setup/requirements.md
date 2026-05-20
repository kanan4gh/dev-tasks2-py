# 要求内容

## 関連Issue

- GitHub Issue: kanan4gh/dev-tasks2#37
- ※ このステアリングはIssue作成より先に作られた（通常はIssue → ステアリングの順が基本）

## 概要

TypeScript製タスク管理CLI（dev-tasks2）をPythonで再実装した `dev-tasks2-py` リポジトリを新規作成する。
Python学習を目的として、設計はTypeScript版から流用しつつ実装はPythonで書き直す。

## 背景

- ユーザーがPythonでプロダクトを作る全体的なイメージを掴みたい
- TypeScript版の設計（レイヤー構造・データモデル）は参照資産として活用する
- 依存管理ツールとして `uv` を採用し、モダンなPythonプロジェクト構成を学ぶ

## 実装対象の機能

### 1. Pythonプロジェクト初期セットアップ
- GitHubリポジトリ `dev-tasks2-py` の作成
- uv によるプロジェクト初期化
- ディレクトリ構成の確立
- CLIエントリーポイントの設定

### 2. データモデル定義
- TypeScript版 `types/index.ts` に相当するPythonのデータモデル
- pydantic を使った型定義

### 3. ストレージ層の実装
- `FileStorage.ts` 相当のYAML読み書き実装
- `GlobalConfigStorage.ts` 相当のグローバル設定管理

### 4. 基本CLIコマンド（add / list / show）
- `click` または `typer` によるCLIフレームワークの構築
- タスクの追加・一覧・詳細表示

### 5. ドキュメント整備
- architecture.md のPython版作成
- repository-structure.md のPython版作成

## 受け入れ条件

### プロジェクトセットアップ
- [ ] `uv run task` でCLIが起動できる
- [ ] `uv run pytest` でテストが実行できる
- [ ] GitHubリポジトリが作成されている

### データモデル
- [ ] Task, Project, GlobalConfig のモデルが定義されている
- [ ] TypeScript版と同等のフィールドを持っている

### 基本コマンド
- [ ] `task add <title>` でタスクを追加できる
- [ ] `task list` でタスク一覧が表示できる
- [ ] `task show <id>` でタスクの詳細が表示できる

## スコープ外

以下はこのフェーズでは実装しません:

- daily / schedule / timer 等の複雑なコマンド
- インタラクティブシェル
- GitHub連携
- onboard / project系コマンド（次フェーズ以降）

## 参照ドキュメント

- `docs/ideas/python-migration.md` - 移行検討メモ
- `docs/product-requirements.md` - プロダクト要求定義書（流用）
- `docs/functional-design.md` - 機能設計書（流用）
- `src/types/index.ts` - TypeScript版データモデル（参照）
- `src/storage/FileStorage.ts` - TypeScript版ストレージ（参照）

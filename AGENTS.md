# エージェント向けプロジェクト規範（SDDプロセス正典）

本書はSDDハーネスの**ハーネス中立な正典**である。AIコーディングエージェント(ハーネス)固有の運用差分は、各ハーネスのアダプタファイル(例: Claude Code の `CLAUDE.md`)が本書への追記として定義する。

---

# 汎用層（AIエージェントとの協働原則）

<!-- SOURCE: github.com/kanan4gh/platform-harness -->
<!-- UPDATED: 2026-07-28 (Stopフックを廃止し、steeringライフサイクル状態・通常/完了lint・明示対象の単一最終ゲートへ移行) -->
<!-- 他のリポジトリへの移植時: このセクションはそのままコピーする -->

## スペック駆動開発の基本原則

### 基本フロー

1. **ドキュメント作成**: 永続ドキュメント(`docs/`)で「何を作るか」を定義
2. **作業計画**: ステアリングファイル(`.steering/`)で「今回何をするか」を計画
3. **実装**: tasklist.mdに従って実装し、進捗を随時更新
4. **検証**: テストと動作確認
5. **更新**: 必要に応じてドキュメント更新
6. **PR作成・マージ**: フィーチャーブランチからPRを作成し、mainにマージ
   - **機能実装コードを直接 main にコミット・プッシュしない**
7. **リリース**: PRマージ後、リリースコマンドを実行
   - リリース前に関連 GitHub Issues をクローズする

### 重要なルール

#### ドキュメント作成時

**1ファイルずつ作成し、必ずユーザーの承認を得てから次に進む**

承認は選択肢(承認して次へ/修正を指示する/スキップ)を明確に提示して確認し、ユーザーの回答を得てから次に進む:

```
「[ドキュメント名]の作成が完了しました。内容を確認してください。
承認いただけたら次のドキュメントに進みます。」
```

ハーネスが構造化された承認UI(選択式の質問ツール等)を提供する場合はそれを優先する。利用方法はハーネスアダプタが定義する。

#### 実装前の確認

新しい実装を始める前に、必ず以下を確認:

1. 本書(AGENTS.md)と、使用中ハーネスのアダプタ追記を読む
2. 関連する永続ドキュメント(`docs/`)を読む
3. 既存の類似実装を検索する
4. 既存パターンを理解してから実装開始

#### ステアリングファイルの作成規則

作業ごとに `.steering/[YYYYMMDD]-[タスク名]/` を作成:

- `requirements.md`: 今回の要求内容（関連IssueのURLを必ず記載）
- `design.md`: 実装アプローチ
- `tasklist.md`: 具体的なタスクリスト

**通常パスは上記3ファイル、軽量パスは `design.md` を省略した2ファイル**とする。軽量パスは add-feature 手順の適用基準4項目をすべて満たす場合にのみ選択でき、`requirements.md` に `- **軽量パス**: 適用` の宣言行を置く。**判定結果(基準4項目それぞれ)は通常パス・軽量パスのどちらでも `requirements.md` の「パス判定」セクションに記録し、add-feature 手順ステップ4.5で選択したパスにかかわらずユーザーへ提示する**(設計判断が発生しないことが適用条件のため、設計の記述は requirements.md の実装対象セクションで足りる)。基準と判定手順の正は `docs/procedures/add-feature.md` ステップ4にある。

命名規則: `20250115-add-user-profile` 形式

**IssueとステアリングはセットでGitHub Issueを先に作成し、ステアリングの `requirements.md` に紐づける。**

#### ステアリング手順の実行

**作業計画・実装・検証は steering 手順に従う。**

- **作業計画時**: steering 手順のモード1(ステアリングファイル作成)
- **実装時**: steering 手順のモード2(実装とtasklist.md更新管理)
- **検証時**: steering 手順のモード3(振り返り)

steering 手順の実体は `docs/procedures/steering.md`(テンプレートは `docs/procedures/templates/`)にある。呼び出し方法(エントリポイント)は各ハーネスのアダプタが定義する。

#### 品質ゲートと実機受け入れ

- **必須の正**: `uv run python3 scripts/local_quality_gate.py`で、テスト・lint・型検査・steering規律・外部有料自動化の再混入をローカル検証する
- **作業状態**: tasklist.mdの`active / paused / complete`をsteering手順で遷移する。通常の応答終了は状態変更ではなく、意図的な中断だけを`paused`と中断記録で表す
- **通常/完了lint**: 作業中は通常lintが正当な未完了を許容し、PR前のローカル品質ゲートは明示対象だけ`complete`を要求する
- **GitHub Actions**: 自動起動しない任意の手動ミラーであり、成功をPR完了の必須証拠にしない
- **実機受け入れ**: `docs/procedures/harness-acceptance.md`に従い、利用許可済みのIDEまたは対話型CLIで行う。従量課金型LLM headless modeを標準受け入れに使わない
- Stopフックによる応答終了ブロックは使わない。各ハーネスの差にかかわらず、状態遷移スクリプトとローカル品質ゲートを決定論的な共通経路とする

## ディレクトリ構造

### 永続的ドキュメント(`docs/`)

アプリケーション全体の「何を作るか」「どう作るか」を定義:

#### 下書き・アイデア（`docs/ideas/`）
- 壁打ち・ブレインストーミングの成果物
- 技術調査メモ
- 自由形式（構造化は最小限）
- `/setup-project`実行時に自動的に読み込まれる

#### 正式版ドキュメント（推奨セット）
- **product-requirements.md** - プロダクト要求定義書
- **functional-design.md** - 機能設計書
- **architecture.md** - 技術仕様書
- **repository-structure.md** - リポジトリ構造定義書
- **development-guidelines.md** - 開発ガイドライン
- **glossary.md** - ユビキタス言語定義

プロダクトによって不要なものは省略し、必要なものを追加してよい。実際の構成はプロダクト固有層で定義する。

追加例:
- **game-design.md** - ゲームメカニクス・レベル設計（ゲーム開発の場合）
- **api-design.md** - エンドポイント設計（API公開の場合）
- **onboarding.md** - メンバー向け入門ガイド（チーム開発の場合）

### 作業単位のドキュメント(`.steering/`)

特定の開発作業における「今回何をするか」を定義:

- `requirements.md`: 今回の作業の要求内容
- `design.md`: 変更内容の設計（軽量パス適用時は省略する）
- `tasklist.md`: タスクリスト

### 手順書(`docs/procedures/`)

SDDプロセスの各手順(steering / distill / add-feature / review-docs / validate-implementation / setup-project)のハーネス中立な手順書と、ステアリング用テンプレート(`templates/`)を置く。**手順の正はここにあり**、各ハーネスのスキル・コマンド・カスタムプロンプトは手順書を参照する薄いラッパとして実装する。

### ツール設定

外部システムへアクセスするツール(MCPサーバー等)の設定形式はハーネス固有のため、各ハーネスのアダプタが定義する。ツール層の考え方は `docs/ideas/harness-engineering.md` のツール層セクションを参照。

## 開発プロセス

### 日常的な使い方

**基本は普通に会話で依頼してください:**

```bash
# ドキュメントの編集
> PRDに新機能を追加してください
> architecture.mdのパフォーマンス要件を見直して
> glossary.mdに新しいドメイン用語を追加

# 機能追加(定型フローはエントリポイント)
> /add-feature ユーザープロフィール編集

# 詳細レビュー(詳細なレポートが必要なとき)
> /review-docs docs/product-requirements.md
```

`/setup-project` `/add-feature` `/review-docs` は各ハーネスが同名のエントリポイントとして提供する。

**ポイント**: スペック駆動開発の詳細を意識する必要はありません。エージェントが適切な手順を判断して参照します。

## ドキュメント管理の原則

### 永続的ドキュメント(`docs/`)

- 基本設計を記述
- 頻繁に更新されない
- プロジェクト全体の「北極星」

### 作業単位のドキュメント(`.steering/`)

- 特定の作業に特化
- 作業ごとに新規作成
- 履歴として保持

---

# プロダクト固有層

<!-- 他のリポジトリへの移植時: このセクションをプロダクトの情報に書き換える -->

## プロダクト固有設定

TaskCLI（`task-py`）は、ローカルの YAML ファイルにタスクを保存する CLI ツールである。
MCP サーバー（`task-mcp`）を同梱し、Claude との会話からタスクを操作できる。

### 永続的ドキュメント一覧（`docs/`）

推奨セットをすべて採用:

- **product-requirements.md** - プロダクト要求定義書
- **functional-design.md** - 機能設計書
- **architecture.md** - 技術仕様書
- **repository-structure.md** - リポジトリ構造定義書
- **development-guidelines.md** - 開発ガイドライン
- **glossary.md** - ユビキタス言語定義

本プロダクト固有の追加:

- **migration-from-ts.md** - TypeScript 版からの移行記録
- **harness-guide.md** - ハーネス運用ガイド
- **external-automation-policy.md** - 外部自動化ポリシー（禁止する非対話LLM実行と検査範囲の正典）

**この一覧は add-feature 手順の軽量パス基準3（対象文書の更新が不要）の判定対象そのものである。** `docs/` 直下にドキュメントを追加・削除したら必ずこの一覧も更新する（一覧と実態が食い違うとパス判定が不定になる。両者の一致は `tests/procedures/test_lightweight_path_criteria.py` が検証する）。

### 記憶層の運用

セッションをまたぐ知見は、使用中ハーネスが提供する記憶機能に記録する(自作の `memory/` ディレクトリは作らない。具体的な機構はハーネスアダプタが定義する)。ハーネスが記憶機能を提供しない場合は、`.steering/` の振り返りへの記録で代替する。

- **書くべきもの**: セッションをまたいで必要になるユーザー決定・まだドキュメント化されていない作業方針
- **書かないもの**: リポジトリが既に記録しているもの(コード・docs/・git履歴・.steering/)
- `/distill` が分類した「プロジェクト内知見」は、セッション横断で有用なものに限り保存を提案する

### ステアリング履歴の追跡

`.steering/` は git で追跡する。platform-harness テンプレートは `.steering/*` を無視するが、本プロダクトは
ステアリング履歴を適応度計測（`reports/fitness-report-dev-tasks2-py.md`）の基礎データとして使うため、この方針を採らない。

移行前（platform-harness v1.6.1 導入以前）に作られた18ディレクトリは旧形式のため、
`scripts/steering_lint.py` が名前の限定列挙で検査を免除する。**移行後に作るステアリングは一切免除しない。**

### 初回セットアップ

1. `AGENTS.md` のプロダクト固有層・技術スタック固有層をプロダクトに合わせて書き換える
2. `/setup-project` で永続的ドキュメント作成（対話的に6つ作成）
3. `/add-feature [機能]` で機能実装

---

# 技術スタック固有層

<!-- 他のリポジトリへの移植時: このセクションを新しい技術スタックの情報に書き換える -->

## 技術スタック

- 開発環境: devcontainer（任意。必須要件は Python 3.12 と uv のみ）
- Python 3.12
- パッケージマネージャー: uv
- CLIフレームワーク: typer
- データモデル: pydantic
- データ保存: pyyaml（`~/.task-py/` 以下の YAML ファイル）
- ターミナル表示: rich
- インタラクティブシェル: prompt-toolkit
- MCP: mcp[cli]
- テスト: pytest / pytest-cov
- 型チェック: basedpyright
  - テストで動的モジュールロード(importlib)を使う場合、reportAny警告が大量に出るため `typeCheckingMode = "standard"` を既定とする(pyproject.toml)
- リンター: ruff

## 主要コマンド

```bash
uv sync                  # 依存関係インストール
uv run task-py --help    # CLI 動作確認
uv run pytest            # テスト実行
uv run ruff check .      # リント
uv run basedpyright      # 型チェック
uv run python3 scripts/steering_lint.py            # ステアリング規律lint
uv run python3 scripts/metered_automation_lint.py  # 外部有料自動化lint
uv run python3 scripts/local_quality_gate.py       # 必須の単一ローカル品質ゲート
```

## PR・リリースフロー

### PR作成
- `gh pr create` でフィーチャーブランチからPRを作成し、mainにマージ

### リリース
- バージョンは `pyproject.toml` の `version` フィールドを更新する
- `gh release create` でGitHub Releaseを作成
- リリース前に関連 GitHub Issues をクローズする（`gh issue close <番号>`）

---

# 補足：この文書の運用方法

AGENTS.mdはSDDプロセスの正典であり、3層構造になっています。ハーネス固有の運用差分は各ハーネスのアダプタファイル(Claude Code の `CLAUDE.md` 等)が定義します。状況に応じて以下のように運用してください。

### 新しいプロダクトを始めるとき

1. このテンプレートリポジトリを "Use this template" で複製する
2. **汎用層はそのまま残す**
3. **プロダクト固有層**を新しいプロダクトの情報に書き換える
4. **技術スタック固有層**を新しい技術スタックの情報に書き換える

### 技術スタックを変更するとき

- **技術スタック固有層だけ**書き換える
- 汎用層・プロダクト固有層はそのまま

### ハーネスを換装・併用するとき

- 本書(正典)は変更しない。使用するハーネスのアダプタ(Claude Code: `CLAUDE.md`+`.claude/`、Codex: `.codex/`+`.agents/skills/`、Kiro: `.kiro/`)を追加・調整する(換装の構想と経緯は `docs/ideas/harness-swap.md` を参照)
- **併用規約**:
  - 作業開始時に requirements.md の「使用ハーネス」欄に使用ハーネスを記録する(蒸留時にハーネス差を分析するため)
  - 成果物(`.steering/` のステアリングファイル(通常パス3ファイル・軽量パス2ファイル)・tasklist更新形式)は手順書とテンプレートが固定しており、どのハーネスでも同一ステアリングを継続できる
  - 編集中のtasklistリマインドはClaude Codeのみ。他ハーネスではリアルタイム更新を自律的に徹底する。中断・再開・完了は全ハーネスで同じ状態遷移スクリプトを使い、ローカル品質ゲートを共通の最終ゲートとする

### 汎用層を更新したとき（スペック駆動開発の原則を改善した等）

1. `platform-harness` リポジトリを更新する
2. 各プロジェクトのAGENTS.mdの汎用層を手動で同期する
3. `UPDATED` の日付を更新して同期済みであることを記録する

### チームで使うとき

- 汎用層は `platform-harness` リポジトリを正典として共有する
- プロダクト固有層・技術スタック固有層は各リポジトリで管理する
- 新メンバーは `platform-harness` から汎用層をコピーしてプロジェクトに参加する

# .claude/ ディレクトリ ガイド

このディレクトリはClaude Codeのカスタマイズファイル一式です。ハーネスエンジニア（Claude Code環境の設定・拡張を行う人）向けのリファレンスです。

## ディレクトリ構成

```
.claude/
├── README.md              # このファイル
├── settings.json          # Claude Code設定（パーミッション・非強制フック登録）
├── hooks/                 # 非強制リマインド
│   ├── remind_tasklist_update.py    # PostToolUseフック
│   └── state/             # 揮発状態（Git管理外）
├── commands/              # スラッシュコマンド（/コマンド名で呼び出す）
│   ├── setup-project.md   # /setup-project
│   ├── add-feature.md     # /add-feature
│   └── review-docs.md     # /review-docs
├── agents/                # サブエージェント定義
│   ├── doc-reviewer.md
│   └── implementation-validator.md
└── skills/                # スキル定義（Skill()で呼び出す）
    ├── steering/
    ├── distill/
    ├── prd-writing/
    ├── functional-design/
    ├── architecture-design/
    ├── repository-structure/
    ├── development-guidelines/
    └── glossary-creation/
```

---

## settings.json

パーミッション(スキル8つ+検証系・読み取り系コマンドのallow)と非強制PostToolUseフックを登録している。Stopフックは登録しない。

**設計方針**: `defaultMode` は設定しない(通常モード)。「読み取り・検証=自動 / 書き込み・外部操作=都度確認」の境界で allow リストを構成する。完全自動実行フロー(`/add-feature`)と bypassPermissions の組み合わせはガードレールゼロになるため採用しない。allow の追加は `/fewer-permission-prompts` による実績ベースで行う。

### 設定の意味

| 項目 | 値 | 説明 |
|------|----|------|
| `permissions.allow` | スキル8つ | ドキュメント作成6+steering+distillは確認なしに実行される |
| `permissions.allow` | `uv run pytest*` 等の検証系、`git status/diff/log` の読み取り系 | 副作用のないコマンドのみ自動実行 |
| `hooks.PostToolUse` | remind_tasklist_update.py | Edit/Writeが5回続いてもtasklist.mdが更新されない場合にリマインドを注入(非強制) |

### フック（hooks/）

編集中のtasklist更新忘れを減らす非強制の補助層。状態と完了規律の正は`scripts/steering_state.py`と`scripts/steering_lint.py`にある。

- フックの追加は「スクリプト+テスト(`tests/hooks/`)+settings.json登録」の3点セットで行う
- テストは `uv run pytest` で実行する
- Stopイベントへは登録しない。応答終了は状態変更や完了判定の契機ではない
- 初回trust、承認UI、応答の終了非ブロック確認は`docs/procedures/harness-acceptance.md`に従う

### settings.local.json について

個人環境のパーミッション設定（例: `gh issue *` の許可）は `settings.local.json` に記述します。このファイルは `.gitignore` で除外されているため、リポジトリにはコミットされません。

---

## コマンド（commands/）

スラッシュコマンドは `claude` セッション内で `/コマンド名` として呼び出します。

### `/setup-project`

**用途**: プロジェクト開始時に `docs/` 以下の6つの永続ドキュメントを対話的に作成する。

**実行タイミング**: このテンプレートから新しいリポジトリを作成した直後。

**動作フロー**:
1. `docs/ideas/` 内のファイルを読み込み、インプットとして利用
2. `prd-writing` スキルで `docs/product-requirements.md` を作成し、**AskUserQuestionで承認確認**（承認/修正の選択式。PRDはスキップ不可）
3. 以降、`functional-design` → `architecture-design` → `repository-structure` → `development-guidelines` → `glossary-creation` の順に作成し、各ドキュメントごとにAskUserQuestionで承認確認（承認して次へ/修正を指示する/スキップ）

**カスタマイズ方法**: `commands/setup-project.md` の「ステップ」を編集することで、作成するドキュメントの順序・内容を変更できます。

---

### `/add-feature <機能名>`

**用途**: 新機能を完全自動で実装する（ステアリングファイル作成 → 実装ループ → 検証 → 振り返り）。

**実行例**:
```
/add-feature ユーザー認証
```

**動作フロー**:
1. worktree+フィーチャーブランチを作成し作業を隔離（mainを汚さない機構的担保）
2. `.steering/YYYYMMDD-機能名/` ディレクトリを作成
3. ビルトイン `Explore` エージェントで既存パターンを調査
4. ビルトイン `Plan` エージェントの実装計画を下敷きに、`steering` スキル（計画モード）でステアリングファイル3点を生成
5. **計画をプランモードで提示し、ユーザー承認を得る**（このワークフロー唯一の承認ゲート）
6. 承認後、`tasklist.md` の**実装フェーズ**が完了するまで実装ループを自動実行（後続フェーズの先取りは禁止）
7. 4段検証を実行し、4段検証フェーズを消化（段1: pytest/ruff/basedpyright → 段2: 変更種別に応じた実挙動確認 → 段3: `/code-review` → 段4: `implementation-validator`＋docsを変更した場合は `doc-reviewer` を並列起動）
8. `steering` スキル（振り返りモード）で振り返りとdocs更新を完了し、全チェックを`[x]`にして`steering_state.py complete`を実行
9. 最終品質ゲートを1回実行→コミット→push→PR作成→worktree後片付け（マージはユーザー判断）。ハーネスのアダプタ構成・権限・フックを変更した場合はステップ8-BのG3実機受け入れを挟む

**重要な設計思想**: **「計画は承認必須・実装は自動」**。承認ゲートは計画提示の1箇所だけです。`tasklist.md`のチェックボックスは実装=ステップ5 / 4段検証=ステップ6 / 振り返りとdocs更新=ステップ7へ排他的に分け、`complete`遷移・最終品質ゲート・コミット・PRは手順が管理します。

**カスタマイズ方法**: 他の技術スタックのプロジェクトへ複製する場合は、ステップ6・段1のコマンド（現在は `uv run pytest` 等）をそのスタックの検証コマンドに変更してください。

---

### `/review-docs <ドキュメントパス>`

**用途**: 特定のドキュメントの品質を詳細レビューする。

**実行例**:
```
/review-docs docs/product-requirements.md
```

**動作フロー**:
1. `doc-reviewer` エージェントを起動
2. 完全性・明確性・一貫性・実装可能性・測定可能性の5観点で評価
3. スコアと改善提案をレポートとして出力

---

## エージェント（agents/）

サブエージェントは専用のコンテキストで動作するため、メインエージェントのコンテキストを消費しません。`/add-feature` や `/review-docs` コマンドから自動的に起動されます。

### モデル配分表

役割ごとに必要な能力とトークン消費のプロファイルが異なるため、以下の配分を既定とする:

| 役割 | 担当 | モデル | 根拠 |
|------|------|--------|------|
| 統合・判断・実装 | メインエージェント | ユーザー選択（最上位推奨） | 全体文脈の保持と最終判断の質が成果物の質を決める |
| 調査 | `Explore`（ビルトイン） | sonnet（起動時に指定） | 大量のファイルを読む=トークン消費大、判断は浅い |
| 計画 | `Plan`（ビルトイン） | 既定（メイン継承） | 計画の質は判断力に依存する |
| 判断を伴うレビュー | doc-reviewer / implementation-validator | sonnet（frontmatterで明示） | スコープ限定の深い推論。**著者(メイン)と別モデルにすることで誤り相関を低減する狙いも含む** |
| 軽量な形式チェック | （将来追加時） | haiku | 定型判定に高い判断力は不要 |
| 蒸留の分類 | `/distill` 実行主体 | 既定 | 環流はプラットフォーム全体に波及するため、上位モデルのセッションでの実行を推奨 |

**根拠の要点**:
- **コスト構造**: トークンを大量に消費する仕事（調査）を軽いモデルへ、高価なモデルには結論だけを渡す。メインの記憶も調査ノイズで埋まらない
- **モデル多様性**: 同一モデルは同じ盲点を持ちやすい。検証を著者と別モデルに担わせると、著者が「自然」と思い込んだ誤りを拾える（実例: メインの実装に混入した観点名の用語ゆれを、Sonnet製validatorが検出）

調査・計画はビルトインの `Explore` / `Plan` エージェントを優先し、同等の自作エージェントを作らない（ビルトイン優先原則）。

### `doc-reviewer`

- **モデル**: Claude Sonnet
- **用途**: `/review-docs` コマンドから呼び出され、ドキュメントを5観点（完全性・明確性・一貫性・実装可能性・測定可能性）で評価してレポートを作成する
- **観点の正**: `docs/procedures/review-docs.md`(エージェント定義はそれを参照する役割宣言のみ)

### `implementation-validator`

- **モデル**: Claude Sonnet
- **用途**: `/add-feature` の4段検証・段4で呼び出される。ステアリングファイル（通常パス: requirements.md / design.md / tasklist.md、軽量パス: design.md を省略した2ファイル）と実装の整合性検証に特化
- **観点の正**: `docs/procedures/validate-implementation.md`(エージェント定義はそれを参照する役割宣言のみ)

---

## スキル（skills/）

スキルはClaude Codeの内部で `Skill('スキル名')` として呼び出されます。**プロセス系スキル(steering / distill)は、手順の正である `docs/procedures/` の手順書を参照する薄いラッパ**です(ハーネス換装第3弾。SKILL.mdにはfrontmatterとClaude固有注記のみを置く)。ドキュメント作成系スキルは従来どおり `SKILL.md`（手順）とテンプレートで構成されています。

### `steering` スキル

**最重要スキル**。スペック駆動開発の中核を担います。

**3つのモード**:

| モード | 呼び出しタイミング | 主な動作 |
|--------|-----------------|---------|
| 計画モード | `/add-feature` 開始時 | `.steering/` にステアリングファイルを生成（通常パス: requirements.md・design.md・tasklist.md の3ファイル、軽量パス: design.mdを省略した2ファイル） |
| 実装モード | タスク実行中 | tasklist.mdをリアルタイムで更新（`[ ]`→`[x]`）し、進捗を追跡 |
| 振り返りモード | 実装フェーズと4段検証フェーズの完了後 | tasklist.mdの振り返りセクションに完了日・学びを記録 |

**手順の正**: `docs/procedures/steering.md`(SKILL.mdはそれを参照するラッパ)

**テンプレートファイル** (`docs/procedures/templates/`):
- `requirements.md` - ステアリング要求定義のひな形
- `design.md` - 実装設計のひな形
- `tasklist.md` - タスクリストのひな形

**設計上の重要原則**: `active`は作業中、`paused`は中断記録付き中断、`complete`は全チェックと振り返りが完了した状態です。通常の応答終了は状態を変えず、Stopフックで妨げません。スキップは技術的な理由がある場合だけ許可し、状態遷移CLIと通常／完了lintが決定論的に検証します。

---

### `distill` スキル

**用途**: 進化のサイクル「④蒸留」の半自動化。`.steering/*/tasklist.md` の振り返りを横断収集し、環流3基準(普遍性・再現性・抽象性)で分類して `.steering/distill-YYYYMMDD.md` に蒸留レポートを出力する。環流候補には platform-harness へのPR下書き(変更対象ファイル+変更案)が付く。

**実行タイミング**: プロジェクトの節目、platform-harness 更新前の棚卸し、またはユーザーの指示。

**重要**: PR作成の最終判断は人間が行う。スキルは候補の提示まで。処理済みディレクトリをレポートに記録するため、再実行時は未処理分のみ扱う(冪等)。

---

### ドキュメント作成スキル（6種）

`/setup-project` コマンドから順番に呼び出され、`docs/` 以下の永続ドキュメントを作成します。各スキルは `SKILL.md`（手順）・`guide.md`（作成指針）・`template.md`（ひな形）で構成されています。

| スキル名 | 生成ファイル | 概要 |
|---------|------------|------|
| `prd-writing` | `docs/product-requirements.md` | ユーザーストーリー・受け入れ条件・成功指標を含むPRD |
| `functional-design` | `docs/functional-design.md` | 機能一覧・入出力・UIフロー |
| `architecture-design` | `docs/architecture.md` | システム構成・技術スタック・AWSアーキテクチャ・データ設計 |
| `repository-structure` | `docs/repository-structure.md` | ディレクトリ構造・命名規則・依存関係ルール |
| `development-guidelines` | `docs/development-guidelines.md` | ブランチ戦略・コーディング規約・テスト方針・デプロイ手順 |
| `glossary-creation` | `docs/glossary.md` | プロジェクト固有用語の定義・ユビキタス言語 |

---

## このテンプレートをカスタマイズする場合

### テストコマンドを変更する（他スタックへの複製時）

現在の `commands/add-feature.md` はこのプロジェクトの技術スタック（uv/pytest/ruff/basedpyright）に合わせてあります。他のスタックのプロジェクトへ複製する場合は、ステップ6「4段検証」の段1を編集します:

```markdown
### 段1: 静的検証

1. 以下のコマンドを順番に実行し...
  ```bash
  Bash('npm test')            # ← Node.jsの場合の例
  Bash('npm run lint')
  Bash('npm run typecheck')
  ```
```

**注意**: 技術スタック定義（AGENTS.md技術スタック固有層）と検証コマンドの不整合は検証層を無効化します。複製時のチェックリストに含めてください。

### 新しいスキルを追加する

1. プロセス系(他ハーネスでも使う手順)の場合、手順本文は `docs/procedures/新手順名.md` に置き、`skills/新スキル名/SKILL.md` はそれを参照する薄いラッパにする。Claude専用スキルなら `SKILL.md` に直接書いてよい
2. 必要に応じてテンプレートを追加(プロセス系は `docs/procedures/` 側に同居)
3. `settings.json` の `permissions.allow` に `"Skill(新スキル名)"` を追加
4. 呼び出し元コマンドやスキルから `Skill('新スキル名')` で参照

### パーミッションを追加する

`settings.json` に追記するか、個人設定なら `settings.local.json` に記述します:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv *)",
      "Bash(gh *)"
    ]
  }
}
```

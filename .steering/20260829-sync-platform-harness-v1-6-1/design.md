# 設計書

## 移行方式

`migrate-then-sync`。`Last source: none`（platform-harness を一度も受け取っていない）ため、
release差分の取り込みではなく、旧構成から中立コア＋アダプタへのフル移行を行う。

`docs/procedures/derived-project-rollout.md` フェーズ3「Migrate then sync」の7ステップに従う。

## 分類の枠組み

各pathはちょうど1分類に属する。

- **Preserve** は対象リポジトリのpathを正とする（正典側の同名pathはコピーしない）
- **Replace** / **Add** は v1.6.1 の内容を正とする
- **Merge manually** はG2でユーザーが裁定するまで、どちらも上書きしない
- **Exclude** は正典側にのみ存在し、本プロジェクトへ持ち込まないもの

---

## 同期manifest

### Preserve（派生固有のまま保持。正典側の同名pathはコピーしない）

- `src/task_cli/`、`src/task_mcp/` — プロダクト実装
- `tests/__init__.py`、`tests/test_*.py`（既存9ファイル） — プロダクトテスト
- `README.md` — プロダクトREADME
- `docs/product-requirements.md`、`docs/functional-design.md`、`docs/architecture.md`、`docs/repository-structure.md`、`docs/development-guidelines.md`、`docs/glossary.md` — プロダクト永続ドキュメント
- `docs/ideas/future-roadmap.md`、`docs/migration-from-ts.md` — 本プロジェクト固有ドキュメント
- `reports/fitness-report-dev-tasks2-py.md` — ouroboros計測レポートのコピー
- `.steering/` の既存18ディレクトリ — 作業履歴。内容を改変しない
- `.devcontainer/devcontainer-lock.json` — 再生成可能だが本プロジェクトの構成に対応

### Replace from canonical（正典で置換）

| 対象path | 正典source path |
|---|---|
| `CLAUDE.md` | `CLAUDE.md`（薄いアダプタ。旧内容のプロダクト/技術スタック層は `AGENTS.md` へ移設） |
| `.claude/agents/doc-reviewer.md` | 同 |
| `.claude/agents/implementation-validator.md` | 同 |
| `.claude/commands/add-feature.md` | 同 |
| `.claude/commands/review-docs.md` | 同 |
| `.claude/commands/setup-project.md` | 同 |
| `.claude/skills/steering/SKILL.md` | 同（手順書を参照する薄いラッパ） |
| `.claude/skills/architecture-design/**` | 同 |
| `.claude/skills/development-guidelines/**` | 同 |
| `.claude/skills/functional-design/**` | 同 |
| `.claude/skills/glossary-creation/**` | 同 |
| `.claude/skills/prd-writing/**` | 同 |
| `.claude/skills/repository-structure/**` | 同 |

### Add from canonical（正典から新規導入）

| 対象path | 正典source path |
|---|---|
| `AGENTS.md` | `AGENTS.md`（汎用層と「補足」はそのまま。固有2層は本プロジェクトの内容を注入） |
| `docs/procedures/*.md`（8本） | 同 |
| `docs/procedures/templates/*.md`（4本） | 同 |
| `docs/harness-guide.md` | 同 |
| `docs/external-automation-policy.md` | 同 |
| `docs/ideas/harness-engineering.md` | 同 |
| `docs/ideas/harness-swap.md` | 同 |
| `docs/ideas/template-unification.md` | 同 |
| `.agents/skills/*/SKILL.md`（5本） | 同 |
| `.codex/README.md`、`.codex/agents/*.toml`（2本） | 同 |
| `.kiro/README.md`、`.kiro/agents/*`（3本）、`.kiro/skills/*/SKILL.md`（5本） | 同 |
| `.claude/README.md` | 同 |
| `.claude/hooks/remind_tasklist_update.py` | 同 |
| `.claude/skills/distill/SKILL.md` | 同 |
| `scripts/*.py`（5本）、`scripts/metered_automation_policy.json` | 同 |
| `tests/adapters/`（3本）、`tests/automation/`（1本）、`tests/hooks/`（1本）、`tests/lint/`（4本）、`tests/procedures/`（4本）、`tests/scripts/`（2本） | 同 |
| `.github/pull_request_template.md` | 同 |
| `.github/workflows/steering-lint.yml` | 同（`workflow_dispatch` のみの任意ミラー） |
| `.mcp.json.example` | 同 |

### Merge manually（G2でユーザーが裁定するまで、どちらも上書きしない）

1. **`scripts/steering_lint.py`** — 既存18ステアリングが正典lintで **27件違反**する。詳細と選択肢は後述
2. **`.gitignore`** — 正典は `.steering/*` を無視（`!.steering/example/` のみ許可）。本プロジェクトは18ステアリングを追跡しており、ouroboros計測の基礎データ。加えて `.claude/settings.json` の扱いが逆（本プロジェクトは無視、正典は追跡）
3. **`pyproject.toml`** — `[project]` とプロダクト依存は本プロジェクトを正。dev依存を `pyright` → `basedpyright` へ替え、`ruff` を追加し、`[tool.ruff]` / `[tool.basedpyright]` を導入する必要がある
4. **`.claude/settings.json`** — 現在 `.gitignore` 対象（`defaultMode: bypassPermissions` を含むため）。正典は追跡し、読み取り・検証系のみ自動・書き込み系は都度確認という別方針
5. **`.devcontainer/devcontainer.json`、`.devcontainer/postCreate.sh`** — 本プロジェクトの構成（AWS CLI手動インストール + Obsidianマウント）を正とし、正典のCDK / SAMは取り込まない想定。ただし品質ゲートに必要なツールの追加要否を確認する
6. **`.claude/skills/steering/templates/`（`micro.md` 含む4本）** — 正典ではテンプレートが `docs/procedures/templates/` へ移動しており、この配置自体が廃止される。ouroboros由来の `micro.md`（軽量レーン）の去就を決める必要がある
7. **`uv.lock`** — dev依存の変更に伴い再生成する

### Exclude（同期・コミット対象外）

- `docs/derived-projects.md` — platform-harness自身の台帳であり派生側に持ち込まない
- platform-harness側の `.steering/`（作業履歴12件と `example/`） — 正典の開発履歴
- platform-harness側の `README.md`・`docs/` のプロダクト永続ドキュメント・`pyproject.toml` の `[project]` — Preserveの対象が正
- `**/__pycache__/`、`.claude/hooks/state/`、`.pytest_cache/`、`.ruff_cache/`、`.venv/` — 再生成可能な実行時資産

---

## G2競合の詳細: 既存ステアリング27件の違反

正典 `scripts/steering_lint.py` を現状の `.steering/` へ適用した実測結果。

| 検査 | 件数 | 内容 |
|---|---|---|
| C1 必須ファイル | 21 | `*-express` 7ディレクトリが `micro.md` 1枚のみで、`requirements.md` / `design.md` / `tasklist.md` を持たない |
| C3 作業状態 | 3 | 旧形式tasklistに未完了タスクがあるが `- **状態**:` 宣言がない |
| C2 Issue URL | 1 | `20260402-dev-tasks2-py-setup` にIssue URLがない（Issue必須化以前の履歴） |
| C4 振り返り | 1 | `20260606-implement-remaining-commands` の振り返り本文中の `` `{parent}_{name}` `` をプレースホルダ未置換と誤検出 |

C1の21件は、ouroboros軽量レーンの `micro.md` 形式と、platform-harness軽量パス（`requirements.md` + `tasklist.md` の2ファイル）の形式差が原因であり、
作業実体の欠落ではない。C4は本文中のコード参照に対する誤検出である。

### 選択肢

**案A: LEGACY grandfather（outfit-studio先行事例と同型）**

`scripts/steering_lint.py` に移行前ステアリングの限定列挙を追加し、既存履歴を検査対象外にする。
outfit-studioは `LEGACY_WITHOUT_ISSUE_URL` の限定列挙とPLACEHOLDERパターンの絞り込みで同種の問題を解決済み。

- 長所: 履歴を1文字も改変しない。ouroboros計測の帰属が保たれる。移行のスコープが小さい
- 短所: 正典 `steering_lint.py` に派生固有差分が生まれ、以後のrelease同期で温存が必要（台帳にその旨の記載が要る）

**案B: 既存18ステアリングを正典形式へ遡及変換**

`micro.md` 7件を `requirements.md` + `tasklist.md` へ展開し、状態宣言・Issue URL・振り返りを補う。

- 長所: 正典 `steering_lint.py` を無改変で使える。以後の同期が単純
- 短所: **履歴の事後改変**にあたる。ouroboros計測レポートが参照する `micro.md` との対応が崩れ、`reports/` の再計測が必要。起草日・承認記録の意味も変わる

**案C: 併用**

C1（express 7件）は案A、C2・C3・C4の5件は内容を補って解消する。

- C2: Issue URLは当時Issueが存在しないため補えない → grandfather
- C3: 未完了タスクの残る3件へ `- **状態**: complete` を追記（実態は完了済み）
- C4: 誤検出のため `steering_lint.py` 側でインラインコードを除外する（正典への還流候補）

**起草時点の推奨: 案A。** 理由は、`.steering/` が ouroboros 計測の基礎データであり、
`reports/fitness-report-dev-tasks2-py.md` の帰属・観測被覆率がディレクトリ構成に依存しているため。
履歴の改変は移行の副作用として払うには代償が大きい。C4の誤検出だけは正典側の改善として別Issueで還流したい。

---

## authority handoff

`AGENTS.md` と `.claude/` アダプタを導入し、人がレビューした時点をhandoffとする。
handoff以降の残タスクは、新しい `AGENTS.md` とClaude Codeアダプタに従って実行し、
handoff対象commit SHAと使用ハーネスをtasklistへ記録する。

bootstrap executorは Claude Code。旧ハーネスもClaude専用のため、外部エージェントによるbootstrapは発生しない。

## 検証方針

1. 既存プロダクトテスト `uv run pytest`（163件）が引き続き全件通ること
2. 導入した `tests/{adapters,automation,hooks,lint,procedures,scripts}/` が通ること
3. `uv run python3 scripts/local_quality_gate.py` の全5検査（pytest / ruff / basedpyright / steering lint / metered automation lint）がパスすること
4. G3対話型受け入れの要否を確定する。アダプタ・権限・hooksを新規導入するため **G3は必要** と見込む
5. GitHub Actions自動run 0件、有料LLM headless mode 0件を記録する

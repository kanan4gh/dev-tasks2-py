# 要求定義

## 関連Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/26

## 概要

本リポジトリのハーネスを、旧世代（`legacy-sdd`: `CLAUDE.md` にSDD原則を内包するClaude Code専用構成）から、
platform-harness の現行中立世代（`current-neutral`: `AGENTS.md` を正典とし、複数ハーネスのアダプタを持つ構成）へ移行する。

- 正典: https://github.com/kanan4gh/platform-harness
- 同期元: **v1.6.1** / `6b13140461916167ae1144055e2652d8aa20fa20`
- 手順の正: platform-harness `docs/procedures/derived-project-rollout.md`
- 台帳: platform-harness `docs/derived-projects.md`
- Strategy: **`migrate-then-sync`**（`Last source: none` のため差分同期ではなくフル移行）

## 展開preflight

- 対象remote: `kanan4gh/dev-tasks2-py`
- default branch / OID: `main` / `81cb51abc70d1aeb158bfc05c51811982eeb6dce`
- remote確認日時・方法: 2026-08-28T22:28:36Z / `git fetch origin --prune` + `gh repo view`
- archive / template状態: どちらも `false`、public
- local checkout: `/Users/akiraishihara/aiwork/dev-tasks2-py`（参考。一意キーではない）
- dirty / ahead / behind: clean / 0 / 0
- active Issue / PR / branch: open PRなし、branchは `main` のみ。open issue #25 はハーネス無関係の機能要望
- 同期元: platform-harness v1.6.1 / `6b13140461916167ae1144055e2652d8aa20fa20`
- bootstrap executor: **Claude Code**（旧ハーネスがClaude専用のため通常実行者と同一。外部エージェントは使わない）
- 作業隔離: git worktree / `/Users/akiraishihara/aiwork/dev-tasks2-py-sync-v1-6-1`（リポジトリ外に配置し、入れ子worktreeのlint走査問題を回避）

`on-hold` の理由だった「local mainがremoteより3 commits ahead、tracked / untracked変更あり」は、
2026-08-28 のリポジトリ整理（`e7fd912` / `addddae` / `81cb51a`）で解消済み。
`docs/procedures/derived-project-rollout.md` のStop条件には1件も該当しない。

## 要求内容

### 導入するもの

- `AGENTS.md`（ハーネス中立の正典）。現行 `CLAUDE.md` のプロダクト固有層・技術スタック固有層を移設する
- `CLAUDE.md` をClaude Code用の薄いアダプタへ置換する
- `docs/procedures/` 手順書8本 + `templates/` 4本
- `.agents/` / `.codex/` / `.kiro/` の各ハーネスアダプタ
- `scripts/` のローカル品質ゲート6本
- `tests/` のハーネス構造テスト15本
- `.github/` のPRテンプレートと手動ミラーworkflow
- `.claude/hooks/`、`distill` スキル、`.claude/README.md`

### 保持するもの

- `src/`・既存 `tests/test_*.py`・`README.md`・`docs/` のプロダクト永続ドキュメント
- `.steering/` の既存18ディレクトリ（作業履歴。**内容を改変しない**）
- `reports/fitness-report-dev-tasks2-py.md`（ouroboros計測レポートのコピー）
- `.devcontainer/` の本プロジェクト設定（AWS CLI手動インストール + Obsidianマウント）

### 明示的にやらないこと

- platform-harness のAWS向けdevcontainer（CDK / SAM）を盲目的に上書きしない
- platform-harness の空のプロダクト永続ドキュメントで本プロジェクトの `docs/` を上書きしない
- `.steering/` の既存履歴の内容を、lintを通すために書き換えない（計測の基礎データであるため）
- GitHub Actions自動run・有料LLM headless modeを必須経路にしない

## 受け入れ条件

- [ ] `AGENTS.md` が存在し、汎用層はv1.6.1と一致、プロダクト固有層・技術スタック固有層が本プロジェクトの実態を記述している
- [ ] `CLAUDE.md` が `@AGENTS.md` をインポートする薄いアダプタになっている
- [ ] `docs/procedures/` と `templates/` が導入され、`.claude/skills/steering/SKILL.md` が手順書を参照する薄いラッパになっている
- [ ] Claude / Codex / Kiro の3アダプタが揃い、`tests/adapters/` が通る
- [ ] `uv run python3 scripts/local_quality_gate.py` が全5検査パスする
- [ ] 既存の `uv run pytest`（163件）が引き続き全件通る
- [ ] 既存18ステアリングの扱いがG2で裁定され、その結果が `scripts/steering_lint.py` または各ステアリングに反映されている
- [ ] GitHub Actions自動run 0件、有料LLM headless mode 0件
- [ ] authority handoff の時点（commit SHA）と、handoff後に使用したハーネスが記録されている

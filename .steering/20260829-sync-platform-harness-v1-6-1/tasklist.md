# タスクリスト

## 作業状態

- **状態**: complete
- **状態更新日時**: 2026-08-29T07:47:54+09:00
- **使用ハーネス**: Claude Code

## 同期元

- platform-harness **v1.6.1** / `6b13140461916167ae1144055e2652d8aa20fa20`
- base OID: `81cb51abc70d1aeb158bfc05c51811982eeb6dce`

---

## フェーズ0: G0対象選択とpreflight

- [x] 対象remoteの再確認（default branch / OID / archive / template状態）
- [x] ローカルcheckoutのdirty / ahead / behind確認
- [x] active Issue / PR / branchの確認
- [x] 同期元release tagとcommitの固定
- [x] preflight記録（requirements.md）
- [x] 対象側Issue作成（#26）
- [x] clean worktree確保（`feature/sync-platform-harness-v1-6-1`）

## フェーズ1: 対象側SDDとG1計画承認

- [x] 同期用steeringのrequirements / design / tasklist作成
- [x] 差分調査と同期manifest作成（design.md）
- [x] bootstrap executorとauthority handoff時点の明記
- [x] **G1: ユーザーによる計画承認**（2026-08-29 承認）

## フェーズ2: G2競合裁定

- [x] **G2: 既存18ステアリング27違反の処遇裁定** → 案A（LEGACY grandfather）
- [x] `.gitignore` の `.steering/*` 無視は採用しない（追跡継続）
- [x] `.claude/settings.json` は正典の方針を採用して追跡
- [x] `.claude/skills/steering/templates/` は廃止し `docs/procedures/templates/` へ移行
- [x] 裁定結果をdesign.mdへ反映

## フェーズ3: 移行

- [x] 旧 `CLAUDE.md` からプロダクト固有層・技術スタック固有層を抽出
- [x] `AGENTS.md` を作成し、汎用層（v1.6.1）と抽出した固有2層を配置
- [x] `CLAUDE.md` をClaude Codeアダプタへ置換
- [x] `docs/procedures/` と `templates/` を導入
- [x] `.claude/` の既存資産を手順書参照の薄いアダプタへ更新（Replace分類）
- [x] `.claude/README.md` / `hooks/` / `distill` スキルを導入
- [x] `.agents/` アダプタを導入
- [x] `.codex/` アダプタを導入
- [x] `.kiro/` アダプタを導入
- [x] `scripts/` の品質ゲート6本を導入（G2裁定を `steering_lint.py` へ反映）
- [x] `pyproject.toml` にdev依存と `[tool.ruff]` / `[tool.basedpyright]` を統合
- [x] `.gitignore` をG2裁定どおり統合
- [x] `.github/` のPRテンプレートと手動ミラーworkflowを導入
- [x] `.mcp.json.example` を導入
- [x] `uv sync` で `uv.lock` を再生成
- [x] **authority handoff**: commit `e5ff9f6`。以降の作業はこのリポジトリの `AGENTS.md` と Claude Code アダプタに従う

## フェーズ4: 検証とG3対話型受け入れ

- [x] 既存プロダクトテスト `uv run pytest`（163件）が全件通ることを確認
- [x] 導入した `tests/` のハーネス構造テスト15本が通ることを確認
- [x] `uv run ruff check .` が通ることを確認
- [x] `uv run basedpyright` が通ることを確認
- [x] `uv run python3 scripts/steering_lint.py`（通常モード）が通ることを確認（27件 → 0件）
- [x] `uv run python3 scripts/metered_automation_lint.py` が通ることを確認
- [x] ローカル品質ゲート 4/5 パス。5番目(`--require-complete`)は完了状態を要求するためフェーズ5の最終ゲートで満たす
- [x] docs変更を独立した文脈でレビュー
- [x] G3要否の確定 → **必要**（Claude/Codex/Kiroアダプタ・settings.json権限方針・PostToolUseフックを新規導入したため）
- [x] GitHub Actions自動run 0件・有料LLM headless mode 0件を記録

## フェーズ5: PR、G4マージ、台帳更新

> `docs/procedures/add-feature.md` ステップ8-B に従う。**状態遷移・品質ゲート・コミット・
> PR作成・G3受け入れ記録はチェックボックスにしない**（実行後にしか完了できず自己参照になるため、
> 実行管理は手順書へ委ねる）。実行順序は次のとおり。

1. 候補ゲート（明示対象を指定したローカル品質ゲートを1回で全緑）
2. 候補コミット（`Closes #26` を含む。これがG3の固定commitになる）
3. G3実施（候補コミットを使い捨ての clean clone へ複製し、対話型IDE / CLIで受け入れ）
4. 結果記録（元リポジトリ側の `acceptance-record.md`。製品ファイルは変更しない）
5. 最終ゲート（同じ明示対象で1回全緑）
6. 記録コミット
7. push、PR作成（本文にG3判定結果を含む）
8. G4: 人によるPRレビューとマージ
9. platform-harness 側 `docs/derived-projects.md` を別PRで更新（State / Last source / Last inspected）

## 別Issue候補（本移行のスコープ外）

- `steering_lint.py` のPLACEHOLDER検出がインラインコード（波括弧で囲んだ変数名）を誤検出する件を platform-harness へ還流する
- `docs/development-guidelines.md` が TypeScript 版時代（Node.js / npm）の記述のまま。Python + uv + ローカル品質ゲートの構成へ書き直す

---

## 移行記録

### 同期元
- platform-harness **v1.6.1** / `6b13140461916167ae1144055e2652d8aa20fa20`
- base OID: `81cb51abc70d1aeb158bfc05c51811982eeb6dce`

### bootstrap executor / authority handoff
- bootstrap executor: Claude Code（旧ハーネスもClaude専用のため外部エージェントは不使用）
- authority handoff: commit `e5ff9f6`。以降は本リポジトリの `AGENTS.md` + Claude Code アダプタに従う

### manifestの訂正
- `tests/procedures/test_derived_project_rollout.py` のカタログ検査6件を取り込まない。
  対象の `docs/derived-projects.md` は platform-harness 自身の台帳であり Exclude 分類のため。
  手順書の契約検査8件は保持した。承認済み計画のExclude判断から直接導かれる訂正であり、方針変更ではない。

### 派生固有差分（以後のrelease同期で温存すること）
1. `scripts/steering_lint.py` の `LEGACY_PRE_MIGRATION`（移行前18ステアリングの限定列挙）
2. `tests/lint/test_legacy_grandfather.py`（上記の契約テスト。本プロジェクト独自）
3. `tests/procedures/test_derived_project_rollout.py` のカタログ検査除外
4. `.gitignore` で `.steering/*` を無視しない
5. `pyproject.toml` の `[tool.ruff.lint] select`（ruff既定のバージョン変動対策）
6. `.devcontainer/`（AWS CLI手動インストール + Obsidianマウント）

### ローカル品質ゲート
- 日時: 2026-08-29
- pytest: 350 passed（既存プロダクト163 + ハーネス構造187）
- ruff: All checks passed
- basedpyright: 0 errors / 0 warnings / 0 notes
- steering lint（通常）: 違反なし（移行前は27件）
- metered automation lint: passed
- GitHub Actions自動run: 0件（`workflow_dispatch` のみ）
- 有料LLM headless mode: 0件

## 実装後の振り返り

### 計画と実績の差分

**計画と異なった点**:
- `tests/procedures/test_derived_project_rollout.py` のカタログ検査6件が、Exclude分類した `docs/derived-projects.md` を必要として失敗した。承認済みのExclude判断から直接導かれる訂正として、当該6件を取り込まない形へ修正した（手順書の契約検査8件は保持）
- ruff の既定ルールセットがバージョン間で異なり（正典環境0.15系 / 本環境0.16系）、固定しないと品質ゲートの結果が ruff のバージョンだけで変動することが判明した。`[tool.ruff.lint] select` を明示して固定した
- 上記の固定後も既存コードに13件の指摘が残ったため解消した（未使用 import 6・未使用変数 2・E741 5）。ハーネス移行としては範囲外だが、導入した品質ゲートを実際に通すために必要だった

**新たに必要になったタスク**:
- `tests/lint/test_legacy_grandfather.py` の追加。免除の境界（移行前18件のみ、移行後は一切免除しない）を契約として固定するため

### 学んだこと

**技術的な学び**:
- 正典の品質ゲートは ruff の**既定**ルールセットに依存しており、派生側の ruff バージョンが異なると再現しない。派生プロジェクトでは `select` の明示が要る
- 正典の `tests/` には、正典リポジトリ自身の資産（台帳等）を検査するものが混在する。派生へ持ち込む際はプロダクト検査とハーネス検査の切り分けが必要
- `steering_lint.py` の免除は `lint()` のループ1箇所に集約でき、検査関数側を改変せずに済んだ。以後のrelease同期で温存すべき差分が最小になる

**プロセスの学び**:
- 台帳の `on-hold` 理由（dirty checkout）は、移行の前提としてのリポジトリ整理を促すシグナルとして機能していた。整理が先行したことで preflight のStop条件に一つも触れずに進められた

### docs更新の要否

- `AGENTS.md`: 新規作成（プロダクト固有層・技術スタック固有層を本プロジェクトの実態で記述）
- `docs/harness-guide.md` / `docs/external-automation-policy.md`: 正典から導入
- **未対応（別Issue化する）**: `docs/development-guidelines.md` が TypeScript 版時代の記述（Node.js / npm）のまま残っている。本移行以前からの乖離だが、品質ゲート導入でさらに実態と離れたため、Python + uv + ローカル品質ゲートの構成へ書き直す必要がある

### 残課題

- `steering_lint.py` のPLACEHOLDER検出が、振り返り本文中のインラインコード（波括弧で囲んだ変数名をバッククォート内に書いたもの）をプレースホルダ未置換と誤検出する。本ステアリングの執筆中にも実際に踏んだ（`20260606-implement-remaining-commands` と同じ原因）。platform-harness へ還流する候補
- `reports/fitness-report-dev-tasks2-py.md` の再計測。今回の整理で `20260522-aws-devcontainer-starter` にコミットが紐づき、対応付け率が 10/11 → 11/11 になる見込み

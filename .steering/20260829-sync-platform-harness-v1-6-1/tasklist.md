# タスクリスト

## 作業状態

- **状態**: active
- **状態更新日時**: 2026-08-29T07:34:09+09:00
- **使用ハーネス**: Claude Code（bootstrap executor。authority handoff以降も同一）

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
- [ ] **G1: ユーザーによる計画承認**

## フェーズ2: G2競合裁定

- [ ] **G2: 既存18ステアリング27違反の処遇裁定（案A / 案B / 案C）**
- [ ] `.gitignore` の `.steering/*` 無視と `.claude/settings.json` の扱いを裁定
- [ ] `.claude/settings.json` の権限方針を裁定
- [ ] `.claude/skills/steering/templates/` と `micro.md` の去就を裁定
- [ ] 裁定結果をdesign.mdへ反映

## フェーズ3: 移行

- [ ] 旧 `CLAUDE.md` からプロダクト固有層・技術スタック固有層を抽出
- [ ] `AGENTS.md` を作成し、汎用層（v1.6.1）と抽出した固有2層を配置
- [ ] `CLAUDE.md` をClaude Codeアダプタへ置換
- [ ] `docs/procedures/` と `templates/` を導入
- [ ] `.claude/` の既存資産を手順書参照の薄いアダプタへ更新（Replace分類）
- [ ] `.claude/README.md` / `hooks/` / `distill` スキルを導入
- [ ] `.agents/` アダプタを導入
- [ ] `.codex/` アダプタを導入
- [ ] `.kiro/` アダプタを導入
- [ ] `scripts/` の品質ゲート6本を導入（G2裁定を `steering_lint.py` へ反映）
- [ ] `pyproject.toml` にdev依存と `[tool.ruff]` / `[tool.basedpyright]` を統合
- [ ] `.gitignore` をG2裁定どおり統合
- [ ] `.github/` のPRテンプレートと手動ミラーworkflowを導入
- [ ] `.mcp.json.example` を導入
- [ ] `uv sync` で `uv.lock` を再生成
- [ ] **authority handoff**: `AGENTS.md` とアダプタを人がレビューし、commit SHAと以降の使用ハーネスを記録

## フェーズ4: 検証とG3対話型受け入れ

- [ ] 既存プロダクトテスト `uv run pytest`（163件）が全件通ることを確認
- [ ] 導入した `tests/` のハーネス構造テスト15本が通ることを確認
- [ ] `uv run ruff check .` が通ることを確認
- [ ] `uv run basedpyright` が通ることを確認
- [ ] `uv run python3 scripts/steering_lint.py --require-complete` が通ることを確認
- [ ] `uv run python3 scripts/metered_automation_lint.py` が通ることを確認
- [ ] `uv run python3 scripts/local_quality_gate.py` の全5検査がパスすることを確認
- [ ] docs変更を独立した文脈でレビュー
- [ ] G3要否の確定（アダプタ・権限・hooks新規導入のため必要と見込む）
- [ ] GitHub Actions自動run 0件・有料LLM headless mode 0件を記録

## フェーズ5: PR、G4マージ、台帳更新

- [ ] tasklistへ同期元・manifest・bootstrap executor・authority handoff・検証を記録
- [ ] 候補ゲート → 候補コミット
- [ ] **G3: 人による対話型受け入れ**（Claude / Codex / Kiro）
- [ ] `acceptance-record.md` へ受け入れ結果を記録
- [ ] 最終ゲート → 記録コミット
- [ ] PR作成
- [ ] **G4: ユーザーによるPRレビューとマージ**
- [ ] platform-harness側 `docs/derived-projects.md` を別PRで更新（State / Last source / Last inspected）

## 別Issue候補（本移行のスコープ外）

- [ ] `steering_lint.py` のPLACEHOLDER検出がインラインコード（`` `{parent}_{name}` ``）を誤検出する件を platform-harness へ還流

---

## 実装後の振り返り

（フェーズ5完了後に記入）

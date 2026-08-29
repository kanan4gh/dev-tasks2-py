# タスクリスト

## 作業状態

- **状態**: complete
- **状態更新日時**: 2026-08-29T14:15:01+09:00
- **使用ハーネス**: Claude Code

## 作業履歴

_記録なし_

## タスク管理の原則

- `active`: 作業系列が継続中。未完了を許容する
- `paused`: 意図的な中断。有効な中断記録がある場合に未完了を許容する
- `complete`: 全タスクと振り返りが完了。未完了を許容しない
- 完了・技術的スキップは実態に合わせて即時記録する
- 最終品質ゲート、コミット、G3受け入れ記録、push、PRはチェックボックスにしない

---

## フェーズ1: Replace と Add の適用（実装フェーズ / ステップ5）

- [x] Replace 6 path を v1.7.0 blob で置換する
  - [x] `docs/procedures/harness-acceptance.md`
  - [x] `docs/procedures/templates/harness-acceptance-record.md`
  - [x] `scripts/steering_state.py`
  - [x] `tests/adapters/test_harness_acceptance.py`
  - [x] `tests/lint/test_steering_lint.py`
  - [x] `tests/lint/test_steering_state.py`
- [x] Add 2 path を v1.7.0 blob で新規作成する
  - [x] `docs/ideas/ai-dlc-uroboros-comparison.md`
  - [x] `docs/ideas/uroboros-lifecycle-framework-architecture.md`
- [x] Replace / Add 8 path の blob 一致を機械的に検証する

## フェーズ2: steering_lint.py の3-wayマージ（実装フェーズ / ステップ5）

- [x] base=v1.6.1 / ours=現在 / theirs=v1.7.0 で `git merge-file` を実行する
- [x] コンフリクトの有無を確認する（出た場合は自動解決せずG2裁定へ回す）
- [x] 派生固有差分の残存を検証する（`LEGACY_PRE_MIGRATION` 18件、`is_legacy` 分岐）
- [x] 取り込んだ要素の存在を検証する（`INLINE_CODE_PATTERN` / `strip_inline_code` / `find_retrospective_placeholders` / `_strip_code_fences`）

## フェーズ3: manifest 全体の検証（実装フェーズ / ステップ5）

- [x] Exclude 1 path（`docs/derived-projects.md`）が存在しないことを確認する
- [x] canonical 10 path 以外に差分がないことを確認する
- [x] Preserve 対象（`.gitignore` / `pyproject.toml` / `.devcontainer/` / `test_legacy_grandfather.py`）が未変更であることを確認する

## フェーズ4: 4段検証（ステップ6）

- [x] 段1: 静的検証
  - [x] `uv run pytest`
  - [x] `uv run ruff check .`
  - [x] `uv run basedpyright`
- [x] 段2: 実挙動検証
  - [x] #55 が実例に挙げた移行前ステアリングの振り返りで C4 が誤検出しないこと
  - [x] 閉じていないバッククォートでは従来どおり検出されること（fail-closed）
  - [x] `harness-acceptance.md` に「権限モードの中立化」「後片付け」の2節があり配置順が正しいこと
  - [x] 移行前18ステアリングが通常lintの対象外であり続けること
- [x] 段3: コードレビューと指摘対応（通常パスのため差分全体が対象。指摘なし。`diff(v1.6.1, 同期前)` と `diff(v1.7.0, 同期後)` がともに53行で完全一致することを確認し、マージが正典側の変更だけを取り込んだことを機械的に示した）
- [x] 段4: スペック準拠検証と指摘対応（受け入れ条件と実装の対応を確認、指摘なし。変更pathがmanifestの9件と完全一致。独立文脈ではなく著者セッションでの実施）

## フェーズ5: 振り返りとドキュメント更新（ステップ7）

- [x] 永続ドキュメントの更新要否を判断し、必要な更新とレビューを完了（不要: 変更は`docs/procedures/`・`docs/ideas/`・`scripts/`・`tests/`に閉じ、永続ドキュメントは未変更）
- [x] README類の更新要否を判断し、必要なら更新（不要: 利用者向けの操作・コマンドは変わらない）
- [x] 実装後の振り返りを記録
- [x] 全テスト通過、lintエラーなし、リリース判断を記録

> 上の全チェック完了後、`python3 scripts/steering_state.py complete --harness "Claude Code"` で `complete` へ遷移する。その後、add-featureステップ8-Aで最終品質ゲートを1回実行する。

---

## 実装後の振り返り

### 実装完了日

2026-08-29

### 計画と実績の差分

**計画と異なった点**:

- なし。manifest の分類（Replace 6 / Merge 1 / Add 2 / Exclude 1）は計画どおりで、G2 裁定を要する競合は発生しなかった
- `steering_lint.py` の3-wayマージはコンフリクトなしで通った。設計時に「変更領域が重ならない見込み」と書いた見立てが当たった

**新たに必要になったタスク**:

- 段3で `diff(v1.6.1, 同期前)` と `diff(v1.7.0, 同期後)` の一致検証を追加した。計画では「両側の要素が残っていることを個別に検証する」までだったが、**派生固有差分が同期で一切変化していない**ことを1つの等式で示せるため、こちらのほうが強い

**技術的理由でスキップしたタスク**:

- 該当なし

### 学んだこと

**技術的な学び**:

- **3-wayマージは direct-sync の検証を1つの等式に還元できる。** `diff(base, ours) == diff(theirs, merged)` が成り立てば、派生固有差分は変化しておらず、正典側の変更だけが入ったことになる。今回は両者とも53行で完全一致した。「LEGACY が残っているか」「新関数が入ったか」を個別に数えるより、この等式のほうが漏れがない
- 段4の自動検査で `canonical 10path 以外の差分: 1件` と出たが、grep パターンが `harness-acceptance`（ハイフン）で `test_harness_acceptance.py`（アンダースコア）を拾えていなかっただけだった。**検査スクリプトの偽陽性を「実装の問題」と読み違えかけた。** path の集合比較（`diff` で差集合を取る）に切り替えたら完全一致が確認できた。パターンマッチではなく集合演算で書くべきだった

**プロセス上の改善点**:

- 段2で「本リポジトリの実データ」を使えたのが大きい。取り込んだ v1.6.2 の修正は、もともと**この リポジトリの `20260606-implement-remaining-commands` の振り返り**が誤検出された事例から生まれたものであり、その当のファイルで修正前 `['{parent}', '{name}']` → 修正後 `[]` を確認できた。合成 fixture では得られない確度がある
- 環流が一巡した。本リポジトリへの v1.6.1 展開で見つかった2件（platform-harness #54 / #55）が、正典で修正され、v1.6.2 / v1.7.0 として発見元へ戻ってきた。**発見から修正の受け取りまでが同じ日のうちに閉じた**

### 次回への改善提案

- `LEGACY_PRE_MIGRATION` の見直しを別Issueで検討したい。移行前18ステアリングの免除理由の一部は「現行の C1〜C5 を満たさない」であり、そのうち C4 のプレースホルダ誤検出は v1.6.2 で解消された。**免除しなくても通るステアリングが混じっている可能性がある**。免除は少ないほど観測被覆率が上がるため、18件を再検査して減らせるか確認する価値がある
- 台帳（platform-harness `docs/derived-projects.md`）の `Last source` を `v1.7.0 / 5b858dc` へ更新する別PRが必要である（`derived-project-rollout.md` フェーズ5-5）

### リリース判断

| 観点 | 評価 |
|---|---|
| ユーザー価値のあるまとまりか | 保留 |
| 未解決の重大バグ | なし |
| 適切なバージョン種別 | リリース不要 |

**提案**:

リリース不要。本作業はハーネス層の同期であり、`task-py` としてのユーザー向け機能・CLI・データ形式は一切変わらない。本リポジトリの直近リリースは v0.8.3 であり、次のプロダクト機能リリースにこの同期を含める。

# 設計書

## アーキテクチャ概要

direct-sync は「正典の blob を取り込む」操作と「派生固有差分を残す」操作の組み合わせである。両者が同一ファイル内で交差するのは `scripts/steering_lint.py` の1件だけであり、そこにだけ3-wayマージを使う。

```
  canonical v1.6.1 ──────────► canonical v1.7.0
        │  (base)                    │  (theirs)
        │                            │
        ▼                            ▼
  dev-tasks2-py 現在 ──────────► dev-tasks2-py v1.7.0相当
        (ours)                    LEGACY差分を保持したまま
                                  コード表記除外を取り込む
```

Replace 6 path は ours == base（blob一致を確認済み）であるため、theirs をそのまま書き出せば足りる。マージは不要で、`git show v1.7.0:<path>` の出力を配置する。

## コンポーネント設計

### 1. Replace / Add の適用

**責務**:
- 正典 blob を取り込み、取り込み元 commit を記録する

**実装の要点**:
- `git --git-dir` で platform-harness のリポジトリを参照し、`git show v1.7.0:<path>` の出力を対象 path へ書き出す
- 適用後に **blob 一致を機械的に検証する**。目視やdiffの読み下しで代替しない
- Add 2 path は `docs/ideas/` への新規作成。既存の同名ファイルがないことを事前に確認する

### 2. `scripts/steering_lint.py` の3-wayマージ

**責務**:
- `LEGACY_PRE_MIGRATION` と `is_legacy` 分岐を失わずに、v1.6.2 のコード表記除外を取り込む

**実装の要点**:
- `git merge-file` を使う。base = canonical v1.6.1、ours = 本リポジトリの現在版、theirs = canonical v1.7.0
- 変更領域は次のとおり重ならない見込みである
  - 派生固有: 行52〜87（`LEGACY_PRE_MIGRATION` ブロック）、lint ループ内（`is_legacy`）
  - v1.6.2: `INLINE_CODE_PATTERN` の定義（`FENCE_PATTERN` 直後）、`strip_code_fences` の `_strip_code_fences` 化と新関数2つ、`check_retrospective()` 内
- **コンフリクトが出た場合は自動解決しない。** G2 の裁定対象としてユーザーへ選択肢を提示する
- マージ後、両側の要素が残っていることを個別に検証する（LEGACY 18件、`is_legacy`、`find_retrospective_placeholders`、`strip_inline_code`）

### 3. 検証

**責務**:
- 同期が manifest どおりであり、かつ派生固有の振る舞いが壊れていないことを示す

**実装の要点**:
- **manifest の全分類を機械的に検査する**。Replace / Add は blob 一致、Exclude は不在、canonical 10 path 以外に差分がないこと
- 派生固有差分は「ファイルが変更されていないこと」ではなく「**振る舞いが残っていること**」で確認する。`test_legacy_grandfather.py` のパスがその証拠になる
- 取り込んだ v1.6.2 の効果は、**本リポジトリの実データで確認する**。移行前ステアリング `20260606-implement-remaining-commands` の振り返りは、platform-harness #55 が誤検出の実例として挙げた当のファイルである

## 検証設計

### 段2（実挙動検証）で観察するもの

| 取り込んだ修正 | 本リポジトリでの確認 |
|---|---|
| v1.6.2 コード表記除外 | #55 が実例に挙げた移行前ステアリングの振り返りで、C4 が誤検出しないこと |
| v1.6.2 fail-closed | 閉じていないバッククォートでは従来どおり検出されること |
| v1.7.0 手順書の2節 | `harness-acceptance.md` に「権限モードの中立化」「後片付け」が存在し、配置順が正しいこと |
| 派生固有差分の温存 | 移行前18ステアリングが通常lintの対象外であり続けること |

### 段3・段4

通常パスのため縮約しない。段3は差分全体、段4は本ステアリングと実装の整合を検証する。

## 代替案と不採用理由

| 案 | 不採用理由 |
|---|---|
| v1.6.2 と v1.7.0 を別々の PR で2回同期する | 展開単位は「1 release × 1 remote × 1 branch × 1 PR」であり、最新 release を同期元とすれば足りる。2回に割ると manifest と検証が2重になるだけで、得られる保証は変わらない |
| `steering_lint.py` を v1.7.0 で丸ごと置換し、LEGACY ブロックを手で書き戻す | 書き戻しの正しさを人が保証することになる。3-wayマージなら base との差分として機械的に扱える |
| 既存 checkout の main で直接作業する | `derived-project-rollout.md` の原則「dirtyな既存checkoutを清掃・stash・上書きして移行を始めない」に従い、clean worktree を用意する |
| `LEGACY_PRE_MIGRATION` を本作業で見直す | v1.6.2 で誤検出が解消されるため免除を減らせる可能性はあるが、判断には移行前18件の再検査が必要であり、同期の検証と設計判断が混ざる。別Issueとする |

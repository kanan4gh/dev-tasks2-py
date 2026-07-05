> [!note] これは project-ouroboros の計測レポートのコピー(2026-07-06 計測)。正典は project-ouroboros/reports/。再計測のたびに更新される。

# 適応度レポート: dev-tasks2-py

- 計測日時: 2026-07-05
- 欠陥漏出の観測窓: マージ後 30 日
- 率はすべて生の分数で報告する(nが小さいためパーセント単独の報告は精度を偽装する)
- 判定ファイル kernel-map: **reviewed**(reviewed_by: ai_assisted_human)
- 判定ファイル consumption-map: **reviewed**(reviewed_by: ai_assisted_human)

## ステアリング↔コミット対応付け

| ステアリング | 対応 | 信頼度 | スコープファイル数 |
|---|---|---|---|
| 20260402-dev-tasks2-py-setup | 2b53f3b (PR #1) | fuzzy | 26 |
| 20260522-aws-devcontainer-starter | — | unmatched | 0 |
| 20260606-implement-p0-remaining | 605a6ec (PR #10) | exact | 23 |
| 20260606-implement-remaining-commands | 2a918e7 (PR #6) | exact | 16 |
| 20260606-implement-shell-command | ae19fda (PR #8) | exact | 10 |
| 20260607-fix-shell-onboard-display | dbba2b8 (PR #18) | exact | 3 |
| 20260607-implement-edit-schedule | f1dd68d (PR #12) | exact | 13 |
| 20260607-implement-migrate | a19e1c6 (PR #14) | exact | 7 |
| 20260607-ux-improvements-from-install-review | fdaa529 (PR #16) | exact | 9 |
| 20260608-implement-mcp-server | 14ed028 (PR #20) | fuzzy | 10 |
| 20260610-mcp-observability | 97bc3cf (PR #23) | exact | 7 |

**対応付け率: 10/11**(H2の照合材料)

### express ユニット(軽量レーン)

- 20260521-change-storage-dir-express → bd28a66(exact)
- 20260521-rename-command-task-py-express → b4227ee(exact)
- 20260607-migrate-priority-keyerror-express → d64e146(exact)
- 20260609-restore-japanese-descriptions-express → e9a0866(exact)
- 20260610-rename-onboard-to-overview-express → cb4b8e8(exact)
- 20260617-mcp-overview-task-details-express → 45da7ed(exact)
- 20260706-harness-rollout-express → 75049ec(unmatched)

### シャドー作業(ステアリング外の実質作業)

**シャドー作業率: 0/16**(実質作業単位 = 全マージPR + chore/version bump を除く直接コミット)


**観測被覆率: 16/16**(正規 10 + express 6)
ガード指標 — 正規:express 比率: 10:7(軽量レーンが正規レーンを侵食していないかの監視用)

## 指標1: 欠陥漏出

| ステアリング | 強い帰属 | 弱い帰属(共有ファイルのみ) | 暴露期間(日) |
|---|---|---|---|
| 20260402-dev-tasks2-py-setup | b8a804f | 0 | 45 |
| 20260522-aws-devcontainer-starter | 0 | 0 | — |
| 20260606-implement-p0-remaining | e189b4d | 0 | 28 |
| 20260606-implement-remaining-commands | 0 | 0 | 29 |
| 20260606-implement-shell-command | 0 | 0 | 28 |
| 20260607-fix-shell-onboard-display | 0 | 0 | 28 |
| 20260607-implement-edit-schedule | 0 | 0 | 28 |
| 20260607-implement-migrate | d64e146 | 0 | 28 |
| 20260607-ux-improvements-from-install-review | 0 | 0 | 28 |
| 20260608-implement-mcp-server | 61e12a6 | 0 | 26 |
| 20260610-mcp-observability | 0 | 0 | 26 |

集計: 強い帰属 4 件 / 弱い帰属 0 件

### 帰属の注記(v2: 導入コミット追跡)

- 帰属差分 61e12a6: v1(last-touched)=20260610-mcp-observability → v2(blame)=20260608-implement-mcp-server
- 帰属差分 d64e146: v1(last-touched)=20260607-ux-improvements-from-install-review → v2(blame)=20260607-implement-migrate
- 帰属差分 e9a0866: v1(last-touched)=20260608-implement-mcp-server → v2(blame)=帰属なし
- シャドー起源(導入者がステアリング外) e9a0866: fix: get_overview の description を日本語に戻す

## 指標2: 振り返り消費率

**1/9**(正式消費された提案/判定済み提案)。未判定: 0 件

| 区分 | 件数 |
|---|---|
| 正式消費(後続ステアリングの計画文書経由) | 1 |
| ステアリング外消費の可能性 | 2 |
| 未消費 | 6 |

> 補助注記: 「ステアリング外消費の可能性」は、提案の趣旨がステアリングを経ない直接作業で実現された可能性を示す。振り返り→計画の回路が働いた証拠では**ない**が、改善が死んだわけでもない。計測器はこの区別を消費率に混ぜずに別掲する。

## 指標3: 自己申告の較正度

「計画と異なった点: 特になし」申告のうち強い欠陥漏出あり: **2/4**
- 20260402-dev-tasks2-py-setup
- 20260607-implement-migrate

## 指標4: 核被覆率

受け入れ条件のうち自動テスト対応: **65/114**。未判定: 0 件

## 領域別集計(H5照合)

| 領域 | auto | manual | none | 未判定 | 漏出 |
|---|---|---|---|---|---|
| logic | 36 | 2 | 0 | 0 | 1 |
| display | 9 | 6 | 0 | 0 | 1 |
| interaction | 1 | 9 | 0 | 0 | 0 |
| ops | 7 | 18 | 0 | 0 | 0 |
| external | 12 | 13 | 1 | 0 | 1 |

## H1照合: 欠陥漏出と受け入れ条件の検証状態

| 漏出が紐づいた条件の検証状態 | 件数 |
|---|---|
| 自動テストあり | 2 |
| 手動確認のみ | 1 |
| 検証なし | 0 |
| 未判定/条件外 | 0 |

## 未消費の改善提案

- [未消費] (20260606-implement-p0-remaining) `daily list` の達成率をプログレスバーで表示するとより直感的
- [未消費] (20260606-implement-remaining-commands) `project list` の表示で rich の Table を使うとより整列が綺麗になる
- [未消費] (20260606-implement-shell-command) オプション値の補完（`--status open` の `open` 部分）は `NestedCompleter` で実装可能
- [未消費] (20260607-implement-edit-schedule) `show` コマンドに `scheduled_date` の表示を追加するとユーザーにわかりやすい
- [未消費] (20260607-ux-improvements-from-install-review) `--version` のバージョン比較を semver ライブラリで行うとより堅牢になる（現状は文字列比較）
- [未消費] (20260607-ux-improvements-from-install-review) バックアップの世代管理（`.backup.1`, `.backup.2` 等）を将来追加すると安全性が増す
- [ステアリング外消費の可能性] (20260608-implement-mcp-server) `onboard` ツールの返却フォーマットを JSON にすると Claude が構造化データとして扱いやすくなる可能性がある
- [ステアリング外消費の可能性] (20260608-implement-mcp-server) Claude への実登録後にツールの description をチューニングして、Claude が適切なツールを選びやすくする

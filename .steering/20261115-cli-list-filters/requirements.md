# 要求内容

## 概要

PRD の要求と CLI の差(Issue #65)を解消する。ユーザー決定(2026-11-15、壁打ちの結果):

1. **実装する**: `list` の `--status` / `--priority` / `--sort`、一覧の Priority 列・Due 列、期限切れの赤色表示
2. **要求を変える**: 一覧のブランチ列(Git 連携とセットなので未実装のまま)と作成日列は、Priority・Due に置き換える
3. **`archived` のタスクは編集できる**を仕様にする(PRD の「編集できない」を直す。実装は変えない)
4. **`edit` 後は「更新したことを示すメッセージ」**で足りる(PRD の「更新後の詳細を表示」を緩める。実装は変えない)

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/65
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用
  - 基準3を満たさないため通常パス(下の「パス判定」を参照)

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [x] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。`TaskFilter`(status / priority / sort)は既にあり、Web の一覧 API が使っている。CLI のオプションと表示を足すだけ
- 基準2: 満たす。コードは `cli/commands/list.py` と `cli/renderer.py` の2ファイル(テスト除く)
- 基準3: 満たさない。PRD(機能4・6・7・8・CLI インターフェース・リリース計画)・`functional-design.md`(コマンド表・一覧の表示)・`glossary.md`・`README.md` の記述を直すのが変更の実体の一部
- 基準4: 満たす。保存データ・API は変えない。一覧の表示列が増える(`search` も同じ表を使う)のみ

**G3受け入れ**: 不要(アダプタ構成・権限・フックは変更しない)。リリース: 利用者に見える機能追加のため MINOR(0.14.0)。

## 背景

#57 で PRD を現行化した際に、PRD の要求を CLI が満たしていない項目が見つかった(Issue #65)。実装するか要求を変えるかを項目ごとに壁打ちで決めた。`TaskFilter` は Web の一覧 API が既に使っているので、CLI への露出は小さい。

## ユースケースの軸

利用者が `task-py list --status completed`・`--priority high`・`--sort due_date` で絞り込み・並べ替えでき、一覧で優先度と期限を見て、期限切れに気づける。PRD の要求と実装が一致している。

## 実装対象

### 1. `list` のオプション
- `--status <status>`(複数指定可): そのステータスだけを出す。`--all-status` とは同時に指定できない(エラー)。既定は `open` + `in_progress` のまま
- `--priority <high|medium|low>`: 優先度で絞り込む
- `--sort <id|priority|due_date|created_at>`: 並べ替え。既定は `id`。`TaskFilter.sort` の4種類
- 3つとも、`--all`(全プロジェクト)・`--inbox` と組み合わせられる

### 2. 一覧の表示(`render_task_table`。`search` も同じ表を使う)
- 列を ID・Status・Priority・Title・Due にする。Due が無いタスクは `-`
- 期限切れ(`open` または `in_progress` で、期限が今日より前)は Due を赤で表示する。「今日」は `today_str()`(`start` の判定と同じ定義)。完了・アーカイブ済みは赤にしない

### 3. 文書
- PRD: 機能4(列)・6(archived の編集・edit 後の表示)・7・8(実装状況の注記)・CLI インターフェース(未実装の例から実装済みへ)・リリース計画を直す。要求の変更(作成日列→Priority・Due 列、archived の編集可、edit 後の表示)は、決定日と理由を書く
- `functional-design.md`: `list` のコマンド表と一覧の表示(列・期限切れ)、`edit` の archived の記述
- `glossary.md`: 優先度の用語の `--sort` の注記を直す。`README.md`: `list` の例と出力例

## 受け入れ条件

- [ ] `list --status completed` で completed だけ、`--status open --status in_progress` で両方が出る。`--status` と `--all-status` の併用はエラー
- [ ] `list --priority high` で high だけが出る
- [ ] `list --sort priority` で high → medium → low の順、`--sort due_date` で期限の早い順(期限なしは末尾)に出る
- [ ] 3つとも `--all`・`--inbox` と併用できる
- [ ] 一覧に Priority 列と Due 列が出る。期限切れの Due が赤で、完了済み・期限が今日以降のものは赤でない
- [ ] `search` の出力も同じ列になる
- [ ] 文書の記述が実装と一致し、PRD の「CLI 未実装」の注記が外れている(現行化検査テストが通る)
- [ ] 全テスト・lint・型検査・品質ゲートが通る

## 成功指標

- 既存テストの全通過に加え、絞り込み・並べ替え・期限切れ表示のテストが足される

## スコープ外

- Web GUI の期限切れ強調(別の作業)
- ブランチ列(Git 連携の実装とセットで扱う)
- `archived` の編集の禁止、`edit` 後の詳細表示(決定により実装しない)
- MCP の `list_tasks` への priority / sort の追加

## 参照ドキュメント

- `docs/product-requirements.md`(機能4・6・7・8)、`docs/functional-design.md`

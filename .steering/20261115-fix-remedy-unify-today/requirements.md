# 要求内容

## 概要

(1) エラーの対処文が、存在しないコマンド名 `task list` / `task start` を案内している不具合を直し、同種の再発を検査する。(2) 「今日」の日付の定義が3か所に同じ式で重複しているのを、共有の関数1つにまとめる。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/64 , https://github.com/kanan4gh/dev-tasks2-py/issues/67
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用
  - 基準2・3を満たさないため通常パス(下の「パス判定」を参照)

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [x] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [ ] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: 満たす。新しい層・依存は無い。小さな共有関数(`task_cli/clock.py`)を足すだけで、既存の `duration.py` と同じ位置づけの単機能モジュール
- 基準2: 満たさない。`services/task_manager.py`・`services/daily_service.py`・`cli/renderer.py`・新規 `clock.py` の4ファイル(テスト除く)に、文書3つが加わる
- 基準3: 満たさない。`docs/functional-design.md`(エラー表の例)・`docs/architecture.md`(性能表のコマンド名)・`docs/development-guidelines.md`(エラー処理のサンプルコード)が、同じ誤ったコマンド名を載せている
- 基準4: 満たす。保存データ・API は変えない。エラーの対処文の文言と、内部関数の置き換えのみ

**G3受け入れ**: 不要(アダプタ構成・権限・フックは変更しない)。リリース: 利用者に見える修正のため PATCH(0.13.1)。

## 背景

#64: `task_manager.py` の NotFoundError の対処文など5か所が `task list` / `task start <id>`(TypeScript 版時代のコマンド名)を案内している。実在するのは `task-py`。Web・MCP も同じ文言を返す。#67: `datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")` が `task_manager.py`・`daily_service.py`・`renderer.py` にあり、どれか1つだけ変えると、`show` の表示と `start` の判定がずれる。

## ユースケースの軸

利用者が (1) エラーの対処文をそのままコピーして実行でき、(2) 「今日」の定義が1か所にあるので、解禁日・ルーティーンの判定と表示が常に一致する。

## 実装対象

### 1. 対処文のコマンド名(#64)
- `task_manager.py` の `task list`(4か所)と `task start <id>`(1か所)を `task-py ...` に直す
- 文書の同じ誤り(`functional-design.md`・`architecture.md`・`development-guidelines.md`)を直す
- 再発を防ぐ検査: `src/` の利用者向け文字列(docstring を除く)に、`task <コマンド>` の形が無いことを AST で検査するテスト

### 2. 「今日」の一本化(#67)
- `src/task_cli/clock.py` に `today_str()` を置く。式は現状と同じ(ローカルタイムゾーンの日付)
- 3か所から使う。`daily_service.py` は既存のテストが `task_cli.services.daily_service._today_str` を差し替えているので、その名前(`_today_str`)を保つ
- 再重複を防ぐ検査: 式 `.astimezone().strftime(` が `clock.py` 以外に無いことを検査するテスト

## 受け入れ条件

- [ ] エラーの対処文に `task list` / `task start` が出ない。`task-py list で有効なIDを確認してください。` になる
- [ ] 文書3つから誤ったコマンド名が消えている
- [ ] `src/` の利用者向け文字列に `task <コマンド>` が無いことを検査するテストがあり、変更前のコードで失敗する
- [ ] 「今日」の式が `clock.py` の1か所だけで、`show` の表示・`start` の判定・ルーティーンが同じ関数を使う
- [ ] 既存のテスト(`_today_str` の差し替えを含む)が通る
- [ ] 全テスト・lint・型検査・品質ゲートが通る

## 成功指標

- 既存テストの全通過に加え、再発防止の検査2本が足される

## スコープ外

- タイムゾーンを設定可能にする(今回は定義の一本化のみ)
- `src/` 以外(Web の静的ファイルなど)の文言の総点検
- 対処文の言い回しの変更(コマンド名のみ直す)

## 参照ドキュメント

- `docs/functional-design.md`、`docs/architecture.md`、`docs/development-guidelines.md`

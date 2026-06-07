# 要求内容

## 概要

`task-py shell` 起動時の onboard 表示を TypeScript 版に合わせる。

## 関連 Issue

https://github.com/kanan4gh/dev-tasks2-py/issues/17

## 実装対象

### 1. ルーティーンセクション
- 見出し: `📅 今日の毎日やること (X/Y 完了)`
- 各行: `  ○ [rN] タイトル`（pending）/ done は非表示
- ヒント: `  💡 done r<ID> で完了`

### 2. 今とりかかるべきタスク
- 見出し: `📌 今とりかかるべきタスク`
- 各行: `  N. [status] ID  タイトル  (Project)`
- ヒント: `  💡 start <ID> でタスクを開始、done <ID> で完了`

### 3. 全タスク
- 見出し: `💼 全タスク (open + in_progress)`
- 全プロジェクト横断、open + in_progress のみ
- グループ: `  [Project: name]  N 件 (in_progress: M)` → `    • ID  [status]  タイトル`
- Inbox は最後に表示

## 受け入れ条件

- [ ] ルーティーンに達成数・○アイコン・ヒントが表示される
- [ ] 今とりかかるべきタスクが番号付きリスト形式で表示される
- [ ] 全タスクが全プロジェクト横断・open+in_progress のみ表示される
- [ ] テスト全通過・型エラーなし

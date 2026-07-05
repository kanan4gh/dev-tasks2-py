# express: コマンド名を task → task-py に変更

- **対象**: PR #2 / マージ b4227ee
- **作業日**: 2026-05-21 / **起草日**: 2026-07-06
- **起草**: AI / **承認**: kanan4gh(2026-07-06。reports/express-drafts-dev-tasks2-py/REVIEW.md にて6/6承認)

## 意図

TypeScript 版の task コマンドと衝突するため、併用期間中に両方を使い分けられるよう Python 版を task-py に改名する。

## 受け入れ条件

- [ ] task-py でCLIが起動する
- [ ] TypeScript 版の task コマンドと共存できる

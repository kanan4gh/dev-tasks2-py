# express: ストレージパスを ~/.task/ → ~/.task-py/ に変更

- **対象**: PR #3 / マージ bd28a66
- **作業日**: 2026-05-21 / **起草日**: 2026-07-06
- **起草**: AI / **承認**: kanan4gh(2026-07-06。reports/express-drafts-dev-tasks2-py/REVIEW.md にて6/6承認)

## 意図

TypeScript 版(~/.task/)と Python 版が同じストレージディレクトリを使うとデータが衝突する。併用期間の安全のため Python 版を ~/.task-py/ に分離する。

## 受け入れ条件

- [ ] Python 版のデータが ~/.task-py/ に読み書きされる
- [ ] TypeScript 版のデータ(~/.task/)に影響しない

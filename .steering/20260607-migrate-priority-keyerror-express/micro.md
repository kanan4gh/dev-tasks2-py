# express: migrate で priority フィールドがないタスクの KeyError を修正

- **対象**: コミット d64e146
- **作業日**: 2026-06-07 / **起草日**: 2026-07-06
- **起草**: AI / **承認**: kanan4gh(2026-07-06。reports/express-drafts-dev-tasks2-py/REVIEW.md にて6/6承認)

## 意図

TypeScript 版の古いデータには priority フィールドがないタスクが存在し、migrate が KeyError で落ちる。フィールド欠落時は既定値で補完して移行を完走させる。

## 受け入れ条件

- [ ] priority がないタスクを含むデータでも migrate が完走する
- [ ] 欠落フィールドは既定値で補完される

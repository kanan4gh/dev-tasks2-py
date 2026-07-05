# express: onboard を overview / get_overview にリネーム

- **対象**: PR #21 / マージ cb4b8e8
- **作業日**: 2026-06-10 / **起草日**: 2026-07-06
- **起草**: AI / **承認**: kanan4gh(2026-07-06。reports/express-drafts-dev-tasks2-py/REVIEW.md にて6/6承認)

## 意図

「onboard」という名前は初回セットアップを連想させ、MCP ツールとして Claude が用途を誤解しやすい。現状の概観を返すツールとしての実態に合わせ overview / get_overview に改名する。

## 受け入れ条件

- [ ] CLI コマンドとMCPツールが overview / get_overview に改名されている
- [ ] 旧名の参照が残っていない(ドキュメント含む)

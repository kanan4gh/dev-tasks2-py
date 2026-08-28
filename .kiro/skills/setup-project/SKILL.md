---
name: setup-project
description: テンプレート複製直後に6つの永続ドキュメントを対話的に作成してプロジェクトを初期化する。「setup-projectを実行して」と依頼されたときに使う。
---

# 初回プロジェクトセットアップ（Kiroアダプタ）

**手順の正は `docs/procedures/setup-project.md` にある。必ず全文を読み、ステップ0〜6と文書ごとの承認ゲートに従うこと。**

## Kiro固有の割当

- 各文書の作成後、選択肢（承認して次へ／修正を指示する／スキップ）を明示して回答を待つ
- 作成ガイドは現時点では`.claude/skills/`配下のprd-writing / functional-design / architecture-design / repository-structure / development-guidelines / glossary-creationにある。内容は中立なので、各SKILL.md・guide.md・template.mdを読んで使用する
- ルート`AGENTS.md`のプロダクト固有層と技術スタック固有層を前提に文書を具体化する

---
description: 初回セットアップ: 6つの永続ドキュメントを対話的に作成する
---

# 初回プロジェクトセットアップ

> **手順の正は `docs/procedures/setup-project.md`(ハーネス中立の手順書)。本コマンドはそのClaude Code最適化版であり、差分は承認ゲートのAskUserQuestion指定とスキルロードのみ。手順の骨格を変更する場合は手順書→本コマンドの順で更新すること。**

このコマンドは、プロジェクトの6つの永続ドキュメントを対話的に作成します。

## 実行方法

```bash
claude
> /setup-project
```

## 実行前の確認

`docs/ideas/` ディレクトリ内のファイルを確認します。
```bash
# 確認
ls docs/ideas/

# ファイルが存在する場合
✅ docs/ideas/initial-requirements.md が見つかりました
   この内容を元にPRDを作成します

# ファイルが存在しない場合
⚠️  docs/ideas/ にファイルがありません
   対話形式でPRDを作成します
```

## 手順

### ステップ0: インプットの読み込み

1. `docs/ideas/` 内のマークダウンファイルを全て読む
2. 内容を理解し、PRD作成の参考にする

### 承認ゲート(全ドキュメント共通)

各ドキュメントの作成後、**AskUserQuestionツール**で承認を確認する。テキストで「承認をお待ちします」と書いて待つ方式は使わない(機構が待機を担保する)。

```
質問: 「[ドキュメント名]を作成しました。内容を確認してください。どうしますか?」
選択肢:
  1. 承認して次へ (Recommended)
  2. 修正を指示する → 修正点を聞き、反映後に再度この質問を行う
  3. このドキュメントをスキップ → 既定テンプレートのまま残し、次のステップへ
```

**フォールバック**: AskUserQuestionが使えない環境では、従来どおりテキストで承認を求めて待機する。

### ステップ1: プロダクト要求定義書の作成

1. **prd-writingスキル**をロード
2. `docs/ideas/`の内容を元に`docs/product-requirements.md`を作成
3. 壁打ちで出たアイデアを具体化：
   - 詳細なユーザーストーリー
   - 受け入れ条件
   - 非機能要件
   - 成功指標
4. 承認ゲートを実行(PRDは以降すべてのドキュメントの土台になるため、**スキップ選択肢は提示しない**。承認/修正の2択+Other)

### ステップ2: 機能設計書の作成

1. **functional-designスキル**をロード
2. `docs/product-requirements.md`を読む
3. スキルのテンプレートとガイドに従って`docs/functional-design.md`を作成
4. 承認ゲートを実行

### ステップ3: アーキテクチャ設計書の作成

1. **architecture-designスキル**をロード
2. 既存のドキュメントを読む
3. スキルのテンプレートとガイドに従って`docs/architecture.md`を作成
4. 承認ゲートを実行

### ステップ4: リポジトリ構造定義書の作成

1. **repository-structureスキル**をロード
2. 既存のドキュメントを読む
3. スキルのテンプレートに従って`docs/repository-structure.md`を作成
4. 承認ゲートを実行

### ステップ5: 開発ガイドラインの作成

1. **development-guidelinesスキル**をロード
2. 既存のドキュメントを読む
3. スキルのテンプレートに従って`docs/development-guidelines.md`を作成
4. 承認ゲートを実行

### ステップ6: 用語集の作成

1. **glossary-creationスキル**をロード
2. 既存のドキュメントを読む
3. スキルのテンプレートに従って`docs/glossary.md`を作成
4. 承認ゲートを実行

## 完了条件

- 6つの永続ドキュメントが全て作成されていること

完了時のメッセージ:
```
「初回セットアップが完了しました!

作成したドキュメント:
✅ docs/product-requirements.md
✅ docs/functional-design.md
✅ docs/architecture.md
✅ docs/repository-structure.md
✅ docs/development-guidelines.md
✅ docs/glossary.md

これで開発を開始する準備が整いました。

今後の使い方:
- ドキュメントの編集: 普通に会話で依頼してください
  例: 「PRDに新機能を追加して」「architecture.mdを見直して」

- 機能の追加: /add-feature [機能名] を実行してください
  例: /add-feature ユーザー認証

- ドキュメントレビュー: /review-docs [パス] を実行してください
  例: /review-docs docs/product-requirements.md
」
```
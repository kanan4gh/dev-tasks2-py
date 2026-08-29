---
name: distill
description: ステアリングの振り返りを横断収集し、環流3基準で分類して環流候補のPR下書きを提示する。プロジェクトの節目や「distillを実行して」と依頼されたときに使う。
---

# Distill（Kiroアダプタ）

**手順の正は `docs/procedures/distill.md` にある。必ず全文を読み、処理手順1〜6に従うこと。**

## Kiro固有の割当

- 振り返りのファイル列挙にはKiroのread/glob/grepまたはshellを使う
- Kiroのユーザー横断steeringへ記録する場合も、リポジトリが既に保持するコード・docs・git履歴・`.steering/`を重複保存しない
- プロジェクト用の永続記憶を設定していない場合は、中立手順どおり`.steering/`の振り返りを記憶層の代替とする
- platform-harnessへのPR作成は、環流候補の提示後にユーザーの最終判断を得る

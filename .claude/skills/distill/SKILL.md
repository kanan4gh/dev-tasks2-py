---
name: distill
description: ステアリングの振り返りを横断収集し、環流3基準で分類して環流候補のPR下書きを提示する蒸留スキル。プロジェクトの節目やユーザーの指示で実行する。
allowed-tools: Read, Write, Glob
---

# Distill スキル(蒸留)

**手順の正は `docs/procedures/distill.md`(ハーネス中立の手順書)にある。必ず読み込み、処理手順1〜6に従うこと。**

## Claude Code 固有の注記

- 手順書の「ファイル列挙」はGlobツールで行う(`Glob('.steering/distill-*.md')` / `Glob('.steering/[0-9]*-*/tasklist.md')`)
- 手順書の「記憶層」はClaude Codeのネイティブ永続メモリを指す(プロジェクト内知見の保存提案先)

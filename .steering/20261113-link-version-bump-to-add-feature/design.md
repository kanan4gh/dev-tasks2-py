# 設計書

## アーキテクチャ概要

手順書(中立の正)→ Claude アダプタ → テンプレート → 契約テストの既存の依存関係に沿って、**1項目を足すだけ**。新しい仕組みは作らない。

```
docs/procedures/add-feature.md (正)  ──同一内容──  .claude/commands/add-feature.md (アダプタ)
docs/procedures/templates/tasklist.md (フェーズ4のチェックボックス)
AGENTS.md / docs/development-guidelines.md (リリース節: どの PR で上げるか)
tests/procedures/ (上記の記述を固定)
```

## コンポーネント設計

### 1. `docs/procedures/templates/tasklist.md`(フェーズ4: 振り返りとドキュメント更新)

**変更**: 「全テスト通過、lintエラーなし、リリース判断を記録」の前に1項目を足す。

```markdown
- [ ] リリース判断に従い、リリースする場合はバージョン定義(技術スタック固有層のリリース節を参照)を更新する。リリースしない場合は、その旨と理由を振り返りに記録する
```

**実装の要点**:
- 「リリース判断を記録」(判断)と「バージョンを更新」(作業)を別の行にする。これが #49 の本質(判断だけで作業が紐づいていない)の修正
- 手順書側は特定の言語・ファイル名を書かない(汎用層に近いため)

### 2. `docs/procedures/add-feature.md` / `.claude/commands/add-feature.md`(ステップ7)

**変更**: ステップ7の手順に「リリース判断の作業」を足す。既存の番号付き手順のうち、振り返り(モード3)の後・`complete` 遷移の前に置く。

要点:
- 順序は「リリース種別の判断(振り返りの表)→ バージョン更新 → 全チェック → `complete`」。`complete` の後に更新すると最終ゲートの後に変更が入るため、必ず前に置く
- 中立手順書の記述を正とし、アダプタは同じ文言にする(順序契約テストが両者の同一性を要求する)

### 3. `AGENTS.md`(PR・リリースフロー > リリース)

**変更**: 「バージョンは `pyproject.toml` の `version` フィールドを更新する」に、フィーチャー PR に含める旨を足す。

```markdown
- バージョンは `pyproject.toml` の `version` フィールドを更新する。**リリース対象の機能は、そのフィーチャー PR に含める**(add-feature ステップ7)。マージ後に更新だけの PR を出さない
```

### 4. `docs/development-guidelines.md`(バージョニングとリリース)

**変更**: 手順1を「フィーチャー PR 内で `pyproject.toml` の `version` を更新する(`uv lock` で `uv.lock` も更新する)」とする。

### 5. `pyproject.toml` / `uv.lock`

`version = "0.12.1"` → `"0.12.2"`。`uv lock` で `uv.lock` の自パッケージのバージョンも更新する。

### 6. `tests/procedures/test_add_feature_ordering.py` への追記(または新規ファイル)

**責務**: 次を固定する。
- テンプレートのフェーズ4に「バージョン」「更新」を含むチェックボックス行がある
- 中立手順書とアダプタのステップ7に、同じバージョン更新の手順がある
- そのバージョン更新の手順が `complete` 遷移より前にある(順序)
- AGENTS.md のリリース節が「フィーチャー PR」に含めると読める

## データフロー

### add-feature のステップ7(変更後)
```
1. docs 影響判断 → 必要なら更新とレビュー
2. 振り返り(リリース判断の表: 種別を決める)
3. リリースする場合: バージョン定義を更新(uv lock も)  ← 追加
4. 全チェック → complete 遷移
5. ステップ8: 最終ゲート → コミット(バージョン更新を含む)→ PR
```

## エラーハンドリング戦略

該当なし(文書とテストの変更)。

## テスト戦略

### ユニットテスト
- `tests/procedures/` の契約テスト(上記)。**追加テストは変更前の文書で失敗することを確認してから文書を変える**
- 既存の `test_add_feature_ordering.py` / `test_lightweight_path_criteria.py` / steering lint のテストが引き続き通ること(中立手順書とアダプタのステップ順序・フェーズ構造を壊していないことの確認)

### 統合テスト
- `uv run python3 scripts/local_quality_gate.py --steering 20261113-link-version-bump-to-add-feature`

## 依存ライブラリ

なし。

## ディレクトリ構造

```
docs/procedures/templates/tasklist.md
docs/procedures/add-feature.md
.claude/commands/add-feature.md          (本文のみ。frontmatter・ファイル名・配置は不変 → G3 不要)
AGENTS.md
docs/development-guidelines.md
pyproject.toml
uv.lock
tests/procedures/test_add_feature_ordering.py (追記)
```

## 実装の順序

1. 契約テストを書き、現状の文書で失敗することを確認する
2. テンプレート・中立手順書・アダプタ・AGENTS.md・development-guidelines.md を更新する
3. バージョンを 0.12.2 に上げ、`uv lock` する

## セキュリティ考慮事項

該当なし。

## パフォーマンス考慮事項

該当なし。

## 将来の拡張性

- バージョン更新の入れ忘れが続くなら、PR 前の機械的な検査(lint)を別 Issue で検討する

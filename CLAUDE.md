# プロジェクトメモリ（Claude Code アダプタ）

SDDプロセスの正典は AGENTS.md にある(下記でインポート)。本ファイルは **Claude Code 固有の運用差分のみ**を定義するハーネスアダプタである(換装の構想と経緯は `docs/ideas/harness-swap.md` を参照)。

@AGENTS.md

---

# Claude Code 固有の運用

## 承認確認

AGENTS.md の承認フロー(ドキュメント作成時)は **AskUserQuestionツール**(選択肢: 承認して次へ/修正を指示する/スキップ)で実施する。AskUserQuestionが使えない場合は、AGENTS.md 正文のテキスト方式で明確に伝えて待機する。計画承認(add-featureワークフローの承認ゲート)はプランモード(ExitPlanMode)を優先し、フォールバックはAskUserQuestion(定義は `.claude/commands/add-feature.md`)。

## steering / distill の呼び出し

AGENTS.md の「steering 手順」の実体は `steering` スキルである:

- **作業計画時**: `Skill('steering')`でモード1(ステアリングファイル作成)
- **実装時**: `Skill('steering')`でモード2(実装とtasklist.md更新管理)
- **検証時**: `Skill('steering')`でモード3(振り返り)

手順の正は `docs/procedures/steering.md`(スキルはそれを参照する薄いラッパ)。蒸留(`/distill`)は `distill` スキル(正は `docs/procedures/distill.md`)を使用する。

## 記憶層

AGENTS.md の記憶層の運用は、**Claude Codeのネイティブ永続メモリ**で実施する(書くべきもの/書かないものの基準はAGENTS.mdに従う)。

## MCP サーバー設定（`.mcp.json`）

MCP サーバーは LLM の「ツール層」として、外部システムへのアクセスを提供する。2層構造で管理する：

- **プラットフォーム層**: ユーザー設定（全プロジェクト共通）に配置。GitHub、ファイルシステム等。
- **プロジェクト固有層**: `.mcp.json`（リポジトリ直下）に配置。プロジェクトの技術スタックに応じて選択。

詳細は `docs/ideas/harness-engineering.md` のツール層セクションを参照。

## 機構による担保（参考）

以下はプロンプトではなく機構で強制される(詳細は `.claude/README.md`):

- **フック**: Stopフックは使わず、実装編集が続いた際のtasklist更新リマインド(PostToolUseフック)だけを非強制で使う
- **状態遷移**: 明示的な中断・再開・完了は`python3 scripts/steering_state.py pause / resume / complete`で記録する
- **パーミッション**: 読み取り・検証系のみ自動、書き込み系は都度確認(settings.json)

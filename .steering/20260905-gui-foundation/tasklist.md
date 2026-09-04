# タスクリスト

## 作業状態

- **状態**: complete
- **状態更新日時**: 2026-09-05T08:52:21+09:00
- **使用ハーネス**: Claude Code

## 作業履歴

_記録なし_

## タスク管理の原則

- `active`: 作業系列が継続中。未完了を許容する
- `paused`: 意図的な中断。有効な中断記録がある場合に未完了を許容する
- `complete`: 全タスクと振り返りが完了。未完了を許容しない
- 完了・技術的スキップは実態に合わせて即時記録する
- 「今日はここまで」はスキップではなく`scripts/steering_state.py pause`で記録する
- 最終品質ゲート、コミット、G3受け入れ記録、push、PRはチェックボックスにしない

### フェーズとadd-featureステップ

| フェーズ | 消化するステップ |
|---|---|
| フェーズ1〜5（実装フェーズ） | ステップ5 |
| フェーズ6: 4段検証 | ステップ6 |
| フェーズ7: 振り返りとドキュメント更新 | ステップ7 |
| `complete`遷移・最終品質ゲート・PR | ステップ7終端・ステップ8（手順管理） |

---

## フェーズ1: 完了日時の記録（実装フェーズ / ステップ5）

- [x] `models/task.py` に `completed_at: datetime | None = None` を追加
- [x] `services/task_manager.py` に `_apply_status_change()` を導入し、`start_task` / `complete_task` / `archive_task` を経由させる
  - [x] 完了へ入るとき `completed_at` を設定
  - [x] 完了から出るとき `completed_at` をクリア（遷移経路自体は追加しない）
  - [x] archive では `completed_at` を変更しない
- [x] `cli/renderer.py` の `render_task_detail()` に完了日時の行を追加（`None` は「—（記録なし）」。ラベルは既存の9桁カラムに収めるため `Done`）
- [x] `task_mcp/server.py` の `_fmt_task()` に完了日時を追加
- [x] `cli/commands/migrate.py` の `_convert_tasks()` に `completedAt` の防御的マッピングを追加
- [x] テスト追加: `test_models.py`（デフォルト・旧dict互換）/ `test_storage.py`（ラウンドトリップ・キー欠落YAML）/ `test_usecases.py`（set・archive保持・open→archiveでNone・編集後も保持・完了から出るとクリア）/ `test_migrate.py`（`completedAt` 有無両方）/ `test_mcp_server.py`（`_fmt_task` 3ケース）

## フェーズ2: `$EDITOR` 連携（実装フェーズ / ステップ5）

- [x] `cli/editor.py` を新規作成し `open_editor()` を実装
  - [x] `click.edit()` の戻り値 `str | bytes | bytearray | None` を `isinstance` で絞り込む
  - [x] 末尾改行を `.rstrip("\n")` で正規化する
  - [x] `click.UsageError` / `OSError` を `AppError` に変換する（remedy に `EDITOR="code --wait"` の例）
- [x] `cli/commands/edit.py` を変更
  - [x] 引数なしガードを「TTY ならエディタ起動 / 非TTY なら現行の `AppError`」に置換
  - [x] `--editor` / `-e` フラグを追加
  - [x] キャンセル・無変更（`None`）は「変更はありませんでした」で exit 0
  - [x] `renderer.py` に `render_info()` を追加（エラーでも成功でもない通知用）
- [x] テスト追加: `test_editor.py`（文字列 / None / bytes / bytearray / 末尾改行 / 例外変換 / 引数の受け渡し）と、非TTY分岐のテスト

## フェーズ3: 作業セッションのモデルと手動記録（実装フェーズ / ステップ5）

- [x] `duration.py` を新規作成し `parse_duration` / `format_clock` / `format_duration` を移設（`cli/commands/time.py` から再exportして `tests/test_time.py` の既存importを無変更で維持）
- [x] `models/time.py` を新規作成し `WorkSession` を定義
- [x] `models/task.py` に `work_sessions` と `total_worked_seconds` プロパティを追加
- [x] `services/task_manager.py` に `append_work_session()` を追加（`updated_at` を触らない専用経路）
- [x] `cli/renderer.py` / `task_mcp/server.py::_fmt_task` に合計作業時間の表示を追加
- [x] テスト追加: `test_models.py`（デフォルト空・旧dict互換・合計・非永続化）/ `test_storage.py`（ネストしたリストのラウンドトリップ・キー欠落YAML）/ `test_usecases.py`（**`updated_at` が変化しないこと**・move で追随すること）/ `test_duration.py`（新規）/ `test_mcp_server.py`

## フェーズ4: タイマーの永続化とタスク接続（実装フェーズ / ステップ5）

- [x] `models/time.py` に `TimerKind` / `TimerState` / `TimerFile` を追加
- [x] `storage/timer_storage.py` を新規作成（`~/.task-py/timer.yaml`、`RoutineStorage` と同型、壊れたYAML・スキーマ不一致は空として扱う）
- [x] `services/timer_service.py` を新規作成
  - [x] `get_active` / `start` / `clear`
  - [x] `elapsed_seconds` / `remaining_seconds` / `is_expired` / `describe`（`now` を注入可能に）
  - [x] 二重起動で `AppError`、`force` で置換
- [x] `usecases/time_tracking_usecase.py` を新規作成
  - [x] `start_timer`（タスク存在検証・**開始時のプロジェクトを state に焼き込む**）
  - [x] `stop_timer`（**`state.project` でパス解決する**。現在のアクティブプロジェクトを使わない）
  - [x] `cancel_timer` / `status` / `log_work` / `clear_timer_for_task`
  - [x] 記録先タスクが削除済みの場合は例外にせず state をクリアして呼び出し側へ伝える（`StopResult`）
- [x] `cli/deps.py` に `get_timer_service()` / `get_time_tracking_use_case()` を追加
- [x] `cli/commands/time.py` を書き換え
  - [x] `start [duration] [--task/-t] [--detach/-d] [--force]`（duration 省略でストップウォッチ）
  - [x] 表示ループを `remaining_seconds()` の都度計算に置換（カウントダウン変数を廃止）
  - [x] `Ctrl+C` で経過分を記録して終了
  - [x] `status` / `stop` / `cancel` / `log <task_id> <duration>` を追加
  - [x] `--task` 未指定時に「`--task <id>` を付けると作業時間が記録されます」とヒント表示
- [x] `task_mcp/server.py` にタイマー系ツール5件を追加（`@mcp.tool()` + `@track`、起動は常に detach 相当）
- [x] テスト追加: `test_timer_service.py` / `test_time_tracking_usecase.py`（**プロジェクト切替後の記録先**の回帰テストを含む）/ `test_time.py`（`--task` なし・duration 位置引数の非破壊）/ `test_mcp_server.py`（`EXPECTED_TOOLS` とスキーマ）
- [x] 別インスタンス（別プロセス相当）から `get_active()` が読めることのテスト

## フェーズ5: ライフサイクル結合（実装フェーズ / ステップ5）

- [x] `usecases/task_crud_usecase.py` に `TimeTrackingUseCase` を注入（本番の組み立ては `cli/deps.py` の `get_use_case()` に集約）
  - [x] 未注入時は後始末を行わない。既定でタイマーストレージを暗黙生成すると、単体テストが実ホームの `~/.task-py/timer.yaml` を読み書きしてしまうため
- [x] `complete_task` / `archive_task` で、対象タスクの実行中タイマーを記録して停止
- [x] `delete_task` で、対象タスクの実行中タイマーを記録せずに停止（記録先ごと消えるため）
- [x] テスト追加: `test_time_tracking_usecase.py::TestTaskLifecycleReleasesTimer`（complete/archive でセッション記録＋active クリア / delete で active クリアのみ / 別タスクのタイマーは触らない / 完了失敗時の整合）

## フェーズ6: 4段検証（ステップ6）

- [x] 段1: 静的検証
  - [x] `uv run pytest`（472 passed）
  - [x] `uv run ruff check .`
  - [x] `uv run basedpyright`（0 errors）
- [x] 段2: 実挙動検証（隔離 HOME で `task-py` を別プロセス起動して観察）
  - [x] `time start --detach` で書かれた `~/.task-py/timer.yaml` を確認し、**別プロセス**の `time status` が同じ残り時間を返すことを観察。二重起動が `AppError` になることも確認
  - [x] 擬似端末（pty）を割り当てて `$EDITOR` の往復を観察。改行を含む長文の保存、無変更時の「変更はありませんでした」（exit 0）、`-p high -e` の併用、非対話パイプでの従来どおりのエラーを確認
  - [x] `task-py done` → `task-py show` で `Done` と `Worked` が出ること、完了後に `edit -t` しても `Done` が変わらないことを観察
  - [x] `task-py time start 2s`（`--task` なし）が従来どおり動くことを観察
  - [x] **段2で欠陥を1件検出し修正**: `click.edit()` の起動失敗は `UsageError` ではなく `ClickException` で飛ぶため、`AppError` への変換を取りこぼして click 自身のエラーパネルが出ていた（原因・対処が表示されない）。`click.ClickException` を捕捉するよう修正し、回帰テストを追加
- [x] 段3: コードレビューと指摘対応（`Skill('code-review')` high）
  - 8件の指摘すべてに対応。いずれも今回書いたコードの実欠陥だった。設計判断として残すべきものは design.md「判断6〜10」に追記済み
  1. **`move` が実行中タイマーを孤児にする**（記録が黙って落ち、移動元で ID が再利用されると別タスクに記録される）→ `retarget_timer_for_task` で移動先へ付け替え
  2. **カウントダウンの超過分を無制限に記録**（25分タイマーの一晩放置が10時間の作業になる）→ `duration_seconds` で打ち切り、超過分は `overrun_seconds` で明示
  3. **遷移に失敗する `done` / `archive` でもタイマーが止まる**（ユーザーにはエラーしか見えない）→ 遷移可否を先に確認してから畳む
  4. **`--force` が置き換え前の実測を破棄**→ 記録してから差し替え、CLI・MCP で報告
  5. **フォアグラウンド表示が別プロセスの張り替えたタイマーを止める**→ `expected_started_at` で自分のものだけ止める
  6. **記録前に解除するため保存失敗で作業時間を失う**→ 記録成功後に解除
  7. **MCP `start_timer` が `duration=""` を無限ストップウォッチとして受け流す**→ `is not None` で判定
  8. **`-d` と `-e` 併用でエディタ内の取り消しが無視される**→ `_description_after_edit` に切り出して修正
  - 増分再検証: pytest 492 passed / ruff / basedpyright すべて緑。指摘1〜4は実機（隔離 HOME・別プロセス）でも修正を確認
- [x] 段4: スペック準拠検証と指摘対応
  - `implementation-validator` の判定は「準拠」。受け入れ条件 22/22 充足、設計判断との乖離なし、スコープ外6項目への逸脱なし
  - 指摘ではないが、`_is_interactive()` が design.md 記載の `stdin` 単独ではなく `stdin`/`stdout` 両方を見ている差異が報告されたため、実装に合わせて design.md を修正した（挙動を弱める差異ではない）

## フェーズ7: 振り返りとドキュメント更新（ステップ7）

- [x] 永続ドキュメントの更新要否を判断し、必要な更新とレビューを完了
  - [x] `docs/product-requirements.md`（「13. 作業時間の記録」の優先度・リリース計画・スコープ外のGUI方針・6番への `$EDITOR` 受け入れ条件）
  - [x] `docs/functional-design.md`（対象バージョン表・P2スコープ宣言・タイマー/作業時間の節・完了日時・`$EDITOR` 連携）
  - [x] `docs/architecture.md`（永続化ストレージ表に `timer.yaml`・作業セッションの配置理由・プロセス間共有の設計）
  - [x] `docs/repository-structure.md`（新規モジュールと `models/` の主要クラス表）
  - [x] `docs/glossary.md`（作業セッション・タイマー状態・完了日時の3項目と索引）
  - [x] `doc-reviewer` のレビューと指摘対応（総合4.0/5。記述と実装の一致は指摘ゼロ）
    - **問題1（最優先）**: PRD の「スコープ外: Web UI（CLI 専用）」が、同じ差分で書いた「GUI 導入の土台」と矛盾していた → 2026-09-05 のユーザー決定に合わせ、スコープ外を「モバイルアプリ・SaaS 型 Web サービス」に改め、決定の経緯と「CLI は引き続き第一級」を注記。プロダクトコンセプト節の「ブラウザや GUI ツールに切り替えることなく」も同趣旨に修正
    - 問題2: `task edit` が2つの表に重複 → P1 表の行から v1.2 節への参照を追記
    - 問題3: 実装済みの13番が「将来的な機能」見出しの下に残る → 節冒頭に注記
    - 問題4: `$EDITOR` 連携が PRD の機能一覧に無い → 6番「タスクの編集」の受け入れ条件に追加
    - 提案1: ロードマップ表の日付列に「実装済み」の語 → 日付を入れる形に修正
    - 提案2: `models/` 主要クラス表のファイル注記が不統一 → ファイル列を追加して統一
- [x] README類の更新要否を判断し、必要なら更新（コマンド例・データ保存先ツリー・MCPツール一覧）
- [x] 実装後の振り返りを記録
- [x] 全テスト通過、lintエラーなし、リリース判断を記録（0.8.3 → 0.9.0 に更新済み）

> 上の全チェック完了後、`python3 scripts/steering_state.py complete --harness "Claude Code"`で`complete`へ遷移する。その後、add-featureステップ8で最終品質ゲートを1回実行する。

---

## 実装後の振り返り

### 実装完了日

2026-09-05

### 計画と実績の差分

**計画と異なった点**:

- **`StopResult` / `StartResult` の導入**: 計画では `stop_timer` がタプルを返す想定だったが、停止結果に「実際の経過」「実績に含めなかった超過分」「記録できたセッション」の3つを載せる必要が出たため dataclass にした。`start_timer` も `--force` で置き換えた側の停止結果を返す必要が生じ、同様に `StartResult` を導入した。
- **`duration.py` の切り出し先**: 計画では `cli/formatting.py` を候補にしていたが、MCP からも `parse_duration` を使うため `cli/` に置くと MCP → CLI の依存になり層構造が壊れる。`exceptions.py` と同じくパッケージ直下の leaf モジュールにした。`cli/commands/time.py` から再 export したので `tests/test_time.py` の既存 import は無変更のまま緑を保っている（非破壊の証明になった）。
- **`TaskCrudUseCase` へのタイマー注入を「暗黙生成しない」方針に変更**: 当初は未注入時に既定の `TimerService` を遅延生成する実装にしたが、それだと既存の単体テストが**実ホームの `~/.task-py/timer.yaml` を読み書きしてしまう**ことに気づき、未注入なら後始末を行わない方式へ変えた。本番の組み立ては `cli/deps.py` の `get_use_case()` に集約されている。
- **`_is_interactive()` の判定**: design.md では `stdin` のみだったが、実装では `stdout` も見るようにした（design.md 側を実装に合わせて修正済み）。
- **カウントダウンの実績を設定時間で打ち切る仕様を追加**: 計画には無かった。段3のレビューで「25分のタイマーを一晩放置すると10時間の作業として記録される」と指摘され、この機能の目的（正確な実績）が壊れるため仕様として追加した。

**新たに必要になったタスク**:

- 段3のコードレビュー指摘8件への対応。うち5件（`move` でのタイマー孤児化、超過分の無制限記録、遷移失敗時の巻き添え停止、`--force` での実績破棄、フォアグラウンドからの他タイマー停止）は**設計判断の追加**を伴ったため design.md に「判断6〜10」として追記した。

**技術的理由でスキップしたタスク**:

- 該当なし。

### 学んだこと

**技術的な学び**:

- **「動く状態」を足すと、周囲のイベントとの取り合いを全部決めなければならない**。今回の欠陥8件のうち5件（`move` / `done` 失敗 / `--force` / 別プロセスの張り替え / 保存失敗）は、すべて「タイマーが走っている最中に別のことが起きたらどうするか」を決めていなかったことに由来する。`completed_at` のような静的なフィールド追加とは質の違う設計コストがあり、**ライフサイクル上のイベントを列挙してから実装に入るべきだった**。計画では `done` / `archive` / `delete` の3つしか列挙しておらず、`move` が漏れた。
- **`click.edit()` の起動失敗は `UsageError` ではなく `ClickException` で飛ぶ**。`UsageError` はその一部でしかない。取りこぼすと click 自身のエラーパネルが出て、`AppError` の「原因・対処」が表示されない。
- **タスク ID がストレージローカルであることが、周辺機能の設計を決める**。`move_task` が移動先で採番し直すため、タスクに紐づくデータを外部ファイルに `(project, task_id)` で持つと move / 改名 / 削除のすべてに整合処理が要る。作業セッションをタスク自身に内包する判断はここから来ており、同じ理由でタイマーの向き先の付け替えも必要になった。

**プロセス上の改善点**:

- **段2（実挙動検証）が段1では絶対に見つからない欠陥を出した**。`click.ClickException` の取りこぼしは、テストで `UsageError` をモックしていたため 472 件のテストが全部緑のまま素通りしていた。「自分がモックした前提そのものが間違っている」類の誤りは、実際に動かす以外に検出手段がない。
- **非対話環境の制約が段2の設計を変えた**。シェルから `HOME` を差し替えられなかったため、Python から `subprocess` で環境変数を渡す方式にした。結果として「別プロセスから同じタイマーが見える」という**土台要件そのものを実プロセスで検証できた**ので、制約がむしろ良い検証を生んだ。`$EDITOR` の経路は `pty` を割り当てないと TTY ガードで弾かれる点も同様。
- **段3を high で回した価値があった**。8件中5件は設計レベルの見落としで、テストが緑でも残っていた欠陥だった。

### 次回への改善提案

- **状態を持つ機能を設計するときは、「その状態が生きている間に起こりうる他の操作」を列挙する節を design.md に設けるとよい**。今回は判断1〜5（どこに置くか・何を意味するか）は詰められていたが、判断6〜10（他の操作との取り合い）が段3まで出てこなかった。前者は静的な設計、後者は動的な設計であり、テンプレートが前者に寄っている。
- `docs/repository-structure.md` に今回と無関係な陳腐化が残っている（実在しないファイル構成、実装済み機能への「未実装」注記、テスト件数の古い数値）。`docs/development-guidelines.md` の陳腐化は Issue #28 で追跡されているが、`repository-structure.md` は未起票。**起票の要否をユーザーに確認したい**。

### リリース判断

| 観点 | 評価 |
|---|---|
| ユーザー価値のあるまとまりか | Yes |
| 未解決の重大バグ | なし |
| 適切なバージョン種別 | MINOR（0.8.3 → 0.9.0） |

**提案**:

リリースを提案する。CLI に `time status` / `stop` / `cancel` / `log` が増え、`edit` が `$EDITOR` に対応し、完了日時と作業時間が記録されるようになった。既存データは後方互換（フィールド追加のみ）で、`task-py time start 20m` などの既存コマンドラインも無変更で動く。

**利用者に伝えるべき変化**:

- `task-py edit <id>` をオプションなしで実行したときの挙動が変わる（従来はエラー終了 → 対話端末では `$EDITOR` が開く）。非対話環境は従来どおり。
- 次回保存時から `tasks.yaml` に `completed_at: null` と `work_sessions: []` が書き込まれる（無害だが差分が大きく見える）。
- 新しいバージョンで保存した YAML を古いバージョンで読むことは問題ないが、古いバージョンで保存し直すと新フィールドが失われる。

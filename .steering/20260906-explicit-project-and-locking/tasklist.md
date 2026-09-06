# タスクリスト

## 作業状態

- **状態**: complete
- **状態更新日時**: 2026-09-06T09:27:51+09:00
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
| 実装フェーズ（フェーズ1〜5） | ステップ5 |
| 4段検証 | ステップ6 |
| 振り返りとドキュメント更新 | ステップ7 |
| `complete`遷移・最終品質ゲート・PR | ステップ7終端・ステップ8（手順管理） |

技術的理由でタスクが不要になった場合だけ、取り消し線と具体的理由を付けて完了扱いにする。時間や難易度を理由に使わない。

---

## フェーズ1: `storage/atomic.py`（実装フェーズ / ステップ5）

- [x] `write_atomic(path, dump)` を実装する
  - [x] 同一ディレクトリの一時ファイルへ書き、`flush` + `os.fsync` の後 `os.replace()` する
  - [x] 置き換え前に、既存ファイルのパーミッションへ合わせる（無い場合は既定のまま）
  - [x] 例外時は一時ファイルを削除して re-raise し、元ファイルに触れない
- [x] `locked(*paths)` を実装する
  - [x] `<path>.lock` に対する `fcntl.flock(LOCK_EX)`
  - [x] `threading.local()` による同一プロセス内の再入許可
  - [x] 複数パスを `resolve()` で正規化しソート順に取得（デッドロック回避）
  - [x] `fcntl` が import できない環境では何もしないコンテキストマネージャに縮退
- [x] `tests/test_atomic.py` を作成する（design.md「ユニットテスト」の6項目）

## フェーズ2: 5ストレージへのアトミック置換適用（実装フェーズ / ステップ5）

- [x] `FileStorage.save()` を `write_atomic` 経由にする（`.bak` の作成・削除・復元は現行のまま）
- [x] `GlobalConfigStorage.save()` を `write_atomic` 経由にする
- [x] `RoutineStorage.save()` を `write_atomic` 経由にする
- [x] `DailyLogStorage._write()` を `write_atomic` 経由にする
- [x] `TimerStorage.save()` を `write_atomic` 経由にする
- [x] `tests/test_storage.py` に「書き込み例外時に元ファイルが 0 バイトにならない」を5ストレージ分追加する
- [x] 既存の `test_backup_created_during_save` / `test_backup_restored_on_write_failure` が**無変更で通る**ことを確認する

## フェーズ3: トランザクション境界（実装フェーズ / ステップ5）

- [x] `FileStorage.transaction()` と `GlobalConfigStorage.transaction()` を追加し、`save()` 内部も `locked()` で覆う
- [x] `TaskManager` の `create_task` / `update_task` / `append_work_session` / `delete_task` を `transaction()` で覆う
- [x] `ProjectService` の `create_project` / `use_project` / `remove_project` / `rename_project` を `transaction()` で覆う（rename はディレクトリ移動まで境界に含める）
- [x] `TaskCrudUseCase.move_task` の2ストレージ跨ぎを1つのトランザクションで覆う

## フェーズ4: プロジェクトの明示指定（実装フェーズ / ステップ5）

- [x] `usecases/project_target.py` を作成する（`_ActiveProject` / `ACTIVE_PROJECT` / `ProjectTarget`）
- [x] `TaskCrudUseCase` に `_resolve()` を追加し、`_get_manager(project)` を明示指定対応にする
- [x] 公開メソッドすべてに `project: ProjectTarget = ACTIVE_PROJECT` を末尾キーワード引数として追加する
- [x] `_release_timer` が解決後のプロジェクト名を `clear_timer_for_task` に渡すよう修正する
- [x] `move_task` の移動元を `project` で解決し、`retarget_timer_for_task` にも解決後の名前を渡す
- [x] `TimeTrackingUseCase.log_work` に `project: ProjectTarget = ACTIVE_PROJECT` を通す
- [x] `TimeTrackingUseCase.start_timer` にも `project` を通す（実装中に追加。明示指定でタスクを操作しても `state.project` はアクティブが焼き付き、停止時の作業セッションが別プロジェクトへ記録される。①と同じ欠陥クラスなので同じ作業単位で閉じる）
- [x] `tests/test_usecases.py` に明示指定のテストを追加する（アクティブ無視 / Inbox 指定）
- [x] `tests/test_time_tracking_usecase.py` に明示指定時のタイマー後始末テストを追加する
- [x] 既存の CLI・MCP・テストの呼び出しが**1行も変わっていない**ことを `git diff` で確認する

## フェーズ5: 別プロセス統合テスト（実装フェーズ / ステップ5）

- [x] `tests/test_concurrency.py` を作成する
  - [x] 別プロセス2本の同時 `add_task` で両方のタスクが残る
  - [x] 別プロセス2本の同時 `project create` で `last_project_id` が重複しない
  - [x] 対照実験（ロック無効化）で実際にデータが失われることを確認し、仕掛けが競合を作れている証拠にする（実装中に追加）

## フェーズ6: 4段検証（ステップ6）

- [x] 段1: 静的検証
  - [x] `uv run pytest`（521 passed）
  - [x] `uv run ruff check`（All checks passed）
  - [x] `uv run basedpyright`（0 errors）
- [x] 段2: 実挙動検証
  - [x] 別 HOME で実 `task-py` プロセスを8本同時起動し、8件すべてが残り id が重複しないことを観測
  - [x] 実 `task-py project create` を6本同時起動し、`last_project_id` が 1..6 で重複しないことを観測
  - [x] `task-py add` の体感が 100ms 要件を超えていないことを観測（`fsync` の追加コストは中央値 +0.35ms / 7.18ms→7.53ms、最大 8.96ms）
  - [x] 明示指定した書き込みがアクティブプロジェクトに影響されないことを実プロセスで観測
  - [x] 一時ファイルの残骸がないこと・YAML のパーミッションが 600 であることを観測
  - [x] 段3の修正後に増分で再検証: タイマーの往復（start → status → 二重起動拒否 → stop → show の作業時間）/ daily の往復（add → done → stats → reset）/ **段3 指摘1 の再現シナリオ**（削除済みプロジェクトのディレクトリが残った状態での rename が、トレースバックではなく分かるエラーで止まり、設定もデータも無傷）/ 正常な rename でディレクトリごと移動すること
- [x] 段3: コードレビューと指摘対応（`Skill('code-review')`。8件すべて実コードで再現・確認し、8件すべて対応）
  - [x] 指摘1(HIGH) `rename_project` が設定を先に保存してからディレクトリを移動しており、移動失敗時に戻せない食い違いが残る。`remove_project` がディレクトリを消さないため実際に起こる（`Directory not empty`）→ **移動先の事前検査 → ディレクトリ移動 → 設定保存**の順に変更。保存失敗時はディレクトリを戻す。`OSError` は `AppError` に変換。回帰テスト2件追加
  - [x] 指摘2(MED) `rename_project` は `tasks.yaml` のロックを取らないため、並走する書き込みが取り残される → **design.md に「意図的に残す窓」として記載済みの内容**。決定は据え置き、`ensure_directory()` による孤児ディレクトリ再生成の詳細を design.md に追記
  - [x] 指摘3(MED) `TimerStorage` にロックが無く `time start` / `stop` が競合する → **設計の前提が誤りだった**（「`TimerFile` の全置換だから不可分性だけで足りる」と書いたが、`TimerService.start()` は `get_active()` → `save()` の check-then-act）。`transaction()` を追加し、`start` / `clear` / `stop_timer` / `cancel_timer` / `clear_timer_for_task` / `retarget_timer_for_task` を排他区間に入れた
  - [x] 指摘4(MED) `DailyService.add_routine` に `create_project` と同じ ID 衝突がある → `RoutineStorage.transaction()` を追加し `add_routine` / `resume_all` / `delete` / `_update_paused` を覆った
  - [x] 指摘5(MED) `DailyLogStorage.save()` の read-modify-write が無防備 → `transaction()` を追加し `save` / `mark_done` / `reset_today` / `_ensure_today_log` を覆った
  - [x] 指摘6(LOW) `move_task` が検証前に両プロジェクトのディレクトリを作る → ロックの外で存在確認を先に行うよう変更。回帰テスト追加
  - [x] 指摘7(LOW) 親ディレクトリを fsync しておらず `os.replace` 自体が永続化されない → `_fsync_directory()` を追加
  - [x] 指摘8(LOW) 対照実験がプロセス起動のばらつきに依存して flaky → 時計ではなく**合図ファイル**での同期に変更。3回連続で安定を確認
  - [x] 自己指摘: `_ActiveProject` をモジュールをまたいでアンダースコア付きで import していた → `ActiveProject` に改名（`isinstance` 分岐に必要なため公開名にする理由を docstring に記載）
- [x] 段4: スペック準拠検証と指摘対応（`implementation-validator`: 準拠。受け入れ条件 12/12 充足、指摘なし。乖離は `start_timer` への `project` 追加1件のみで tasklist に記録済み。`doc-reviewer` は docs 更新後のステップ7で実施する）

## フェーズ7: 振り返りとドキュメント更新（ステップ7）

- [x] 永続ドキュメントの更新要否を判断し、必要な更新とレビューを完了
  - [x] `docs/architecture.md`（「バックアップ戦略」を「書き込み戦略」「バックアップ戦略」「排他制御」「ファイルパーミッション」に再構成）
  - [x] `docs/glossary.md`（`FileStorage` の定義を Python 版へ現行化、新規3用語「不可分な置き換え」「排他区間（transaction）」「操作対象プロジェクト（ProjectTarget）」を追加、索引も更新）
  - [x] `docs/repository-structure.md`（`atomic.py` / `project_target.py` の追加、storage・usecases 節の説明追記）
  - [x] `docs/functional-design.md`（`FileStorage` 節・エラー処理表・パフォーマンス設計のうち書き込み方式に関わる箇所のみ現行化。**残る TypeScript 版時代の記述は本作業のスコープ外とし Issue #43 に起票**）
  - [x] `doc-reviewer` を更新差分に対して実行し、必須1件・推奨3件・提案2件すべてに対応
    - 必須: `glossary.md` の壊れたアンカー（`#タイマー状態` → `#タイマー状態-timer-state`）
    - 推奨: 「排他区間の境界を決めるのはservice層」が `move_task`（usecase層で `locked()` を直接使う）と矛盾していた／「1コマンドあたりロック取得1回」が `move`・`time stop` と矛盾していた／索引「さ行」の五十音順
    - 提案: 「（将来の）ローカル Web GUI」の限定表現を既存記述に統一／**`.bak` 復元経路は「原理的に到達しない」ではなく「到達しても実質何もしない」が正しい**（`write_atomic` 失敗時に `except` 節は実行される）。`file_storage.py` のコードコメントも同じ誤りだったので直した
- [x] README類の更新要否を判断し、必要なら更新（README に書き込み方式・排他制御の記述はないため更新不要）
- [x] 実装後の振り返りを記録
- [x] 全テスト通過、lintエラーなし、リリース判断を記録

> 上の全チェック完了後、`python3 scripts/steering_state.py complete --harness "Claude Code"`で`complete`へ遷移する。その後、add-featureステップ8で最終品質ゲートを1回実行する。

---

## 実装後の振り返り

### 実装完了日

2026-09-06

### 計画と実績の差分

**計画と異なった点**:

- **ロックの適用範囲を5ストレージ全部に広げた（計画では2つ）。** 計画では `RoutineStorage` / `DailyLogStorage` / `TimerStorage` を「アトミック置換のみ、ロックは作業単位D」とし、特に `TimerStorage` は「RMW ではなく `TimerFile` の全置換なので不可分性だけで足りる」と書いた。**この根拠が誤りだった**。`TimerService.start()` は `get_active()` で確認してから `save()` する check-then-act であり、まさに read-modify-write である。段3のコードレビューで指摘され、実コードで確認して全面適用に変更した。`RoutineStorage`（`add_routine` の `max(id)+1` 採番）と `DailyLogStorage`（`save()` 自体が RMW）も同様で、`ProjectService.create_project()` に対して直したのと**同じ欠陥クラスの片方だけを残す**ことになるため、まとめて閉じた。
- **`TimeTrackingUseCase.start_timer` にも `project` を通した（計画では `log_work` のみ）。** 明示指定でタスクを操作しても `state.project` にはアクティブが焼き付き、停止時の作業セッションが別プロジェクトへ記録される。①と同じ欠陥クラスなので同じ作業単位で閉じた。
- **`rename_project` の順序を変えた（計画ではロックを掛けるだけ）。** 段3で「設定を先に保存してからディレクトリを移動する」既存の順序が実際に壊れることが示された（`remove_project` はディレクトリを消さないため、削除済みプロジェクトのディレクトリが残っていると移動先が既に存在し `Directory not empty` で失敗し、そのとき設定は既に確定している）。「移動先の事前検査 → ディレクトリ移動 → 設定保存」に変更し、`OSError` を `AppError` に変換した。
- **`_ActiveProject` を公開名 `ActiveProject` にした。** モジュールをまたいでアンダースコア付きの名前を import していたため。

**新たに必要になったタスク**:

- 対照実験（ロック無効化）のテスト。「テストが通ったのは競合が起きていないからではないか」を潰すために追加した。結果的にこれが最も価値のある検証になった
- `write_atomic` の親ディレクトリ fsync（段3 指摘7）。`os.replace()` が書き換えるのは親ディレクトリのエントリなので、そこを永続化しないと元の docstring の主張が成立していなかった
- `move_task` の事前存在確認（段3 指摘6）。ロックファイルを置くために `ensure_directory()` が要るが、それを検証より前に無条件で行うと、失敗しただけで見えないゴミディレクトリが残る
- Issue #43 の起票（`functional-design.md` の TypeScript 版時代の記述）

**技術的理由でスキップしたタスク**:

- 該当なし

### 学んだこと

**技術的な学び**:

- **「全置換だから排他は要らない」は、書き込みだけを見た判断だった。** 実際に見るべきは「その値を決めるのに直前の値を読んだか」である。`TimerService.start()` は `TimerFile` を丸ごと置き換えるが、置き換えてよいかの判断に直前の状態を使っている。read-modify-write かどうかは `save()` の形ではなく **`load()` から `save()` までの依存関係**で決まる。
- **ロックには取得順の規約が要る。** 単一ファイルなら考えなくてよいが、`move`（2つの `tasks.yaml`）と `stop`（`timer.yaml` → `tasks.yaml`）が入った時点で必要になった。前者はパスをソートして、後者は「timer → tasks の一方向」と決めて対処した。`move_task` がタイマーの付け替えをタスクのロック区間の**外**でやっているのは、この規約を守るためである。
- **`flock` はプロセス死で OS が解放するので、残骸の後始末を書かなくてよい。** Issue #38 でタイマーの `pid` を「表示用のみ、生死判定に使わない」と決めたのと同じ問題（PID 再利用は信用できない）に、ここでは OS が答えを持っていた。
- `os.replace()` の不可分性は同一ファイルシステム内に限る。中身の `fsync` だけでは足りず、親ディレクトリの `fsync` まで要る。

**プロセス上の改善点**:

- **対照実験を置くと、テストの意味が桁違いに強くなる。** 並行性のテストは「通った」だけでは何も言えない（競合が起きていなかっただけかもしれない）。子プロセス側で `atomic._flock = None` にする対照を並べたことで、「この仕掛けは確かに競合を作れており、その競合をロックが防いでいる」まで言えるようになった。最初は時計（`sleep`）で同期していてレビューで flaky と指摘され、合図ファイルに変えて決定論的にした。
- **設計の前提が誤っていたときに、段1・段2はまったく警告しなかった。** 521テストが緑、実プロセスの観察も期待どおりで、それでも `TimerStorage` に穴が空いていた。前回（Issue #38）は「段2・段3が実欠陥9件」で、今回は「段3が8件」。**設計判断の誤りを見つけるのは段3である**というのが2回続けて確認された。
- **同じ欠陥クラスの片方だけを直さない。** 「GUI が触るのは作業単位D だから後回し」は一見きれいなスコープの切り方だったが、`create_project` の ID 衝突を直しながら `add_routine` の同じ衝突を残すことになっていた。スコープを切る線は「機能」ではなく「欠陥のクラス」で引くほうが正しい場面がある。

### 次回への改善提案

- **並行性・状態を扱う作業では、design.md に「read-modify-write の棚卸し」節を置く。** 今回は「動く状態の生存中に起こりうる操作」の表（Issue #38 の教訓から導入）は書いたが、そこに載せたのは「ロック」という新しい状態についてだけで、**既存コードのどこが RMW かの一覧**は作らなかった。作っていれば `TimerService.start()` の check-then-act に設計時点で気づけた。次は「`load()` を呼んでから `save()` を呼ぶ箇所」を機械的に列挙してから境界を決める。
- 段3のレビューには「自分が書いた設計コメントが主張していることを、実装が本当に満たしているか」を明示的に見てもらうとよい。今回 `rename_project` のコメント（「食い違う窓を残さない」）が実装より強い主張をしていたのを指摘され、そこから HIGH の欠陥が出た。

### リリース判断

| 観点 | 評価 |
|---|---|
| ユーザー価値のあるまとまりか | Yes |
| 未解決の重大バグ | なし |
| 適切なバージョン種別 | MINOR（v0.10.0） |

**提案**:

v0.10.0 としてリリースする。利用者から見た機能追加はないが、**データ損失の修正**が複数含まれる（並行更新でのロストアップデート、書き込み中断による全損、`project rename` 失敗時の設定とデータの食い違い、`daily add` の ID 衝突、タイマーの二重起動・二重記録）。PATCH ではなく MINOR とするのは、`usecases` の公開シグネチャに `project` 引数が増える後方互換な API 追加を含むため。

GUI 本体（作業単位B）に進む前にリリースしておくと、GUI 側で問題が出たときに切り分けやすい。

# 要求内容

## 概要

GUI（ローカル Web）本体に着手する前に、「別プロセスが同じ `~/.task-py/` を触る」ときに壊れる箇所を2件解消する。① 書き込み経路をプロジェクト明示指定にする ② YAML ストレージに排他制御とアトミックな置き換えを入れる。

- **関連Issue**: https://github.com/kanan4gh/dev-tasks2-py/issues/42
- **使用ハーネス**: Claude Code
- **軽量パス**: 非適用

## パス判定（**通常パス・軽量パスのどちらでも必ず記載する**。基準の正は add-feature 手順のステップ4）

- [ ] 1. 既存パターンの踏襲のみで、新しいアーキテクチャ要素・新規依存を導入しない
- [ ] 2. 変更対象が3ファイル以下(テスト除く)
- [ ] 3. 対象文書の更新が不要
- [x] 4. データ形式・API契約の破壊的変更がない

**判定理由**:

- 基準1: **満たさない**。ファイルロック（`fcntl.flock`）とアトミック置換（`os.replace`）という機構をリポジトリに初めて持ち込む。`fcntl` / `tempfile` / `os.replace` は現状リポジトリ全体で未使用。あわせて「アクティブ追従」を表す番兵型（`ProjectTarget`）という新しい型の語彙を usecase 層に導入する。**新規の外部依存はゼロ**（すべて Python 標準ライブラリ）。
- 基準2: **満たさない**。新規2・変更9の計11ファイル（テスト除く）。内訳は下記「実装対象の機能」を参照。
- 基準3: **満たさない**。`docs/architecture.md` の「バックアップ戦略」節は現行の書き込みフロー（`.bak` へコピー → 直接上書き → 成功なら削除）そのものを記述しており、この記述の書き換えが変更の実体の一部である。加えて `docs/glossary.md` の `FileStorage` 定義の書き込みフロー、`docs/repository-structure.md` のファイル一覧も更新する。**記録例外には該当しない**（一覧への項目追加にとどまらず、方針の記述そのものが変わるため）。
- 基準4: **満たす**。YAML のスキーマは不変。CLI のコマンドライン・MCP のツール契約も不変。usecase の各メソッドに追加する `project` 引数は既定値つきキーワード引数であり、既存の呼び出し（CLI 12ファイル・MCP 12箇所・テスト多数）は無改修で挙動が変わらない。`.bak` の生成・削除タイミングも現行どおり保つ（`tests/test_storage.py` の既存2テストを変更せずに通すことで担保する）。

4項目すべてにチェックが付かないため**通常パス**。基準側の問題で不要に通常パスへ落ちているケースではない。

## G3 受け入れの要否

**不要**。`.claude/skills/` `.claude/agents/` `.claude/commands/` の frontmatter・ファイル名・配置、`.claude/settings.json` の権限、`.claude/hooks/` の定義・登録のいずれも変更しない。製品コードと `docs/` のみの変更。

## 背景

2026-09-05 に GUI の形態を**ローカル Web（サーバ + ブラウザ）**に決定し、v0.9.0（Issue #38）で形態非依存の土台4件を解消した。本作業はその続きで、残る2件を片付ける。どちらも「単一プロセスなら顕在化しないが、GUI という常時起動の別プロセスが加わると壊れる」という共通の性質を持つ。

### ① 書き込み経路がグローバルのアクティブプロジェクトに依存している

`TaskCrudUseCase._get_manager()` がグローバル設定の `activeProject` からストレージパスを解決し、`get_task` / `start_task` / `complete_task` / `archive_task` / `delete_task` / `edit_task` / `set_scheduled_date` / `search_tasks` / `move_task` / `list_tasks` がすべてこれを通る。読み取りのうち `list_all_projects()` / `list_inbox_tasks()` だけがプロジェクト明示に対応している。

GUI は全プロジェクトを一画面に出す面である。したがって「読めるが書き込み先を選べない」状態になる。画面上の `foo` のタスク #3 で「完了」を押したとき、並走する CLI が `project use bar` していれば `bar` の #3 が完了する。タスク ID はストレージローカルなので #3 は両方に存在しうる。エラーも出ず、別のタスクが静かに書き換わる。

これは Issue #38 で見つけた「move × タイマー」欠陥と同じ形（静かに別のものを書き換える）である。GUI を載せてから直すと、初期実装が「アクティブプロジェクト依存」の形で固まったあとで剥がすことになる。

### ② YAML ストレージに排他制御とアトミック置換がない

調査で判明した現状:

- ロック機構は皆無。`fcntl` / `tempfile` / `os.replace` はリポジトリ全体で未使用
- すべての更新が `load()` → リストを書き換え → `save()` の read-modify-write（`TaskManager` の `create_task` / `update_task` / `append_work_session` / `delete_task`、`ProjectService` の全変更メソッド）
- `.bak` によるロールバックがあるのは `FileStorage` だけ。`GlobalConfigStorage` / `RoutineStorage` / `DailyLogStorage` / `TimerStorage` の4つは `open("w")` で直接上書きしており、**書き込み中に落ちるとファイル全体を失う**

実害は3つ:

1. **ロストアップデート**: 2プロセスが同じファイルを更新すると、後から `save()` した側が「自分が読んだ時点のリスト全体」を書き戻すため、もう一方の変更が丸ごと消える。`ProjectService.create_project()` の `config.last_project_id += 1` は同時実行で同じ ID を採番する
2. **`.bak` の相互破壊**: `.bak` のパスは `tasks.yaml.bak` 固定で共有される。A が退避 → B が退避（A の退避を上書き）→ A が書き込み成功して `.bak` を削除 → B が失敗しても復元元が無い、という順序が成立する。バックアップ機構自体が並行時に無効化される
3. **書き込み中断による全損**: `.bak` の無い4ストレージは、`open("w")` の時点でファイルが 0 バイトに切り詰められる。ここで落ちるとデータが残らない

## ユースケースの軸

**呼び出し側（GUI・MCP・CLI）が「どのプロジェクトのタスクを操作するか」を明示でき、複数のプロセスが同時に同じ YAML を更新しても、どちらの変更も失われず、書きかけのファイルが観測されない。**

## 実装対象の機能

### 1. プロジェクトの明示指定（`ProjectTarget`）

- usecase 層に「操作対象プロジェクト」を表す型 `ProjectTarget = str | None | _ActiveProject` と番兵 `ACTIVE_PROJECT` を導入する
- `None` は Inbox という**実在の保存先**を意味するため、`None` を「未指定」に流用しない。両者を型で区別する
- `TaskCrudUseCase` の各メソッドに `project: ProjectTarget = ACTIVE_PROJECT` を追加する。既定値のままなら現行どおりアクティブプロジェクトを使う
- `TimeTrackingUseCase.log_work()` にも同じ引数を通す（現状 `self._active_project()` で解決している）
- タイマー後始末（`_release_timer` / `move_task` の `retarget_timer_for_task`）は、グローバルのアクティブではなく**解決後のプロジェクト名**を使う

**新規ファイル**: `src/task_cli/usecases/project_target.py`
**変更ファイル**: `src/task_cli/usecases/task_crud_usecase.py` / `src/task_cli/usecases/time_tracking_usecase.py`

### 2. アトミックな書き込みとファイルロック

- `src/task_cli/storage/atomic.py` に2つの機構を置く
  - `write_atomic(path, dump)`: 同一ディレクトリの一時ファイルへ書く → `flush` + `fsync` → `os.replace()` で置き換える。読み手は常に完全なファイルだけを見る
  - `locked(*paths)`: `<path>.lock` に対する `fcntl.flock(LOCK_EX)`。同一プロセス内での再入を許す。複数パスは正規化してソート順に取得する（デッドロック回避）
- ロックは **`load()` → 変更 → `save()` の全体**を覆う。`save()` だけを守ってもロストアップデートは防げない
- **アトミック置換は5ストレージすべてに適用**する（3行の変更で全損モードが消えるため）
- **ロック（トランザクション境界）は `FileStorage`（tasks.yaml）と `GlobalConfigStorage`（config.yaml）に適用**する。GUI が作業単位B・Cで触るのはこの2つ
- `.bak` の意味論は変えない。`FileStorage` のみが持ち、書き込み前に作成し成功後に削除する

**新規ファイル**: `src/task_cli/storage/atomic.py`
**変更ファイル**: `storage/file_storage.py` / `storage/global_config_storage.py` / `storage/routine_storage.py` / `storage/daily_log_storage.py` / `storage/timer_storage.py` / `services/task_manager.py` / `services/project_service.py`

## 受け入れ条件

### プロジェクトの明示指定

- [ ] `project=` を渡さない既存の呼び出し（CLI・MCP・既存テスト）が**1行も変更せずに**現行どおり動く
- [ ] `uc.complete_task(3, project="foo")` が、グローバルのアクティブプロジェクトが `bar` であっても `foo` の #3 を完了にする
- [ ] `uc.add_task("x", project=None)` が、アクティブプロジェクトが設定されていても Inbox に追加する
- [ ] `project="foo"` を指定した `complete_task` / `archive_task` / `delete_task` が、`foo` のタスクに紐づくタイマーだけを畳む（`bar` の同 ID のタイマーは触らない）
- [ ] `move_task(id, "dst", project="src")` が `src` から読み `dst` へ書き、タイマーの向き先も `src` 基準で付け替える
- [ ] basedpyright が `ProjectTarget` の絞り込みを通す（`str | None` への変換に型エラーが出ない）

### アトミックな書き込みとファイルロック

- [ ] 2つの**別プロセス**が同じ `tasks.yaml` に同時に `add_task` しても、両方のタスクが残る（ロストアップデートが起きない）
- [ ] 2つの別プロセスが同時に `project create` しても、`last_project_id` が重複せず両方のプロジェクトが残る
- [ ] 書き込みの途中で例外が起きても、既存ファイルは 0 バイトにならず元の内容が読める（5ストレージすべて）
- [ ] `tests/test_storage.py` の `test_backup_created_during_save` と `test_backup_restored_on_write_failure` が**無変更で通る**（`.bak` の意味論を変えていないことの証明）
- [ ] `move_task` が2ファイルにロックを取っても、逆向きの同時 move でデッドロックしない
- [ ] `fcntl` が無いプラットフォームでは例外にならず、ロックなし（現行の挙動）に縮退する

## 成功指標

- 段2 の実挙動検証で、別 OS プロセスを2本同時に走らせてロストアップデートが起きないことを観測する（Issue #38 で「別プロセスからタイマーが見える」を実プロセスで確認したのと同じやり方）
- CLI・MCP の既存テストが1件も変更を必要としない

## スコープ外

以下はこのフェーズでは実装しません:

- GUI 本体（作業単位B以降）
- undo / 操作履歴（GUI の書き込み面を作る作業単位で要否を再判定する）
- `RoutineStorage` / `DailyLogStorage` / `TimerStorage` への**ロック**適用（アトミック置換のみ行う。GUI がこれらを触るのは作業単位D。`atomic.py` は汎用に作るため、その時点で3行ずつ足せる）
- `.bak` の保持世代の変更（Issue #32 の領分）
- 楽観的並行制御（バージョン番号や ETag による衝突検出）。単一利用者・単一ホスト前提ではロックで足りる
- Windows での動作保証（`fcntl` が無い環境ではロックなしに縮退する。現行と同じ強度であり後退しない）

## 参照ドキュメント

- `docs/product-requirements.md` - プロダクト要求定義書
- `docs/functional-design.md` - 機能設計書
- `docs/architecture.md` - アーキテクチャ設計書
- `docs/repository-structure.md` - リポジトリ構造定義書
- `docs/glossary.md` - ユビキタス言語定義

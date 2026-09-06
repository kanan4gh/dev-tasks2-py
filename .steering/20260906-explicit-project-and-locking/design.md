# 設計書

## アーキテクチャ概要

既存の4層（`cli/` → `usecases/` → `services/` → `storage/`、すべて → `models/`）はそのまま。追加するのは2つの直交した関心である。

```
usecases/                         storage/
  project_target.py  ← 新規         atomic.py  ← 新規
    ACTIVE_PROJECT                    write_atomic()   … 書き込みの不可分性
    ProjectTarget                     locked()         … 更新の排他

  task_crud_usecase.py            file_storage.py          ┐
    project= を全メソッドへ        global_config_storage.py │ 5つとも
  time_tracking_usecase.py        routine_storage.py       │ write_atomic +
    log_work / start_timer に      daily_log_storage.py     │ transaction()
    project=                      timer_storage.py         ┘
services/
  task_manager.py       … load→save を transaction() で覆う
  project_service.py    … 同上
  daily_service.py      … 同上
  timer_service.py      … check-then-act を transaction() で覆う
```

**貫く原則**: 「操作対象は呼び出し側が決める。プロセス外の状態（アクティブプロジェクト）を暗黙の引数にしない」「ファイルは常に完全な状態でしか観測されない」。前者が ① を、後者が ② を成立させる。

## コンポーネント設計

### 1. `usecases/project_target.py`（新規）

**責務**:
- 「操作対象のプロジェクト」を表す語彙を1箇所で定義する
- 「Inbox（`None`）」と「アクティブに従う（未指定）」を型で区別する

**実装の要点**:

```python
class ActiveProject:
    """「グローバル設定のアクティブプロジェクトに従う」ことを表す番兵。"""
    __slots__ = ()
    def __repr__(self) -> str:
        return "ACTIVE_PROJECT"

ACTIVE_PROJECT = ActiveProject()
ProjectTarget = str | None | ActiveProject
```

- **`usecases/` に置く**。「アクティブプロジェクトに追従する」という概念は usecase 層にしか存在しない（`services/` 以下は常に具体的なパスを受け取る）
- `task_crud_usecase.py` に同居させず独立モジュールにするのは、`time_tracking_usecase.py` も使うため。`task_crud` ↔ `time_tracking` は既に `TYPE_CHECKING` 越しの片方向依存になっており、実行時の相互 import を増やしたくない

### 2. `TaskCrudUseCase` の明示指定化

**責務**: 受け取った `ProjectTarget` を具体的なプロジェクト名（`str | None`）に解決し、そのパスの `TaskManager` を作る。

**実装の要点**:

```python
def _resolve(self, project: ProjectTarget) -> str | None:
    if isinstance(project, ActiveProject):
        return self._global_config_service.get_active_project()
    return project

def _get_manager(self, project: ProjectTarget = ACTIVE_PROJECT) -> TaskManager:
    return TaskManager(self._storage_factory(resolve_storage_path(self._resolve(project))))
```

- 公開メソッドはすべて `project: ProjectTarget = ACTIVE_PROJECT` を**末尾のキーワード引数**として受け取る。位置引数を増やさないので既存の呼び出しは無改修
- `list_inbox_tasks()` / `list_all_projects()` は既に明示的なので変更しない
- `_release_timer(id, record, project)` は解決後の名前を `clear_timer_for_task` に渡す（現状はグローバルのアクティブを渡している）
- `move_task(id, target_project, project=ACTIVE_PROJECT)`: 移動元は `project`、移動先は従来どおり `target_project`（こちらは元から明示）。`retarget_timer_for_task` の第1引数も解決後の移動元名にする

### 3. `storage/atomic.py`（新規）

**責務**: 「書きかけのファイルを観測させない」と「read-modify-write を直列化する」の2つを提供する。

**実装の要点**:

```python
def write_atomic(path: Path, dump: Callable[[TextIO], object]) -> None:
    """同一ディレクトリの一時ファイルへ書いてから os.replace() で置き換える。"""
```

- 一時ファイルは**同一ディレクトリ**に作る。`os.replace()` が不可分なのは同一ファイルシステム内だけで、`/tmp` 経由では保証が消える
- `flush()` + `os.fsync()` してから `os.replace()`。fsync を省くと、置き換えは成功したのに中身が空、という状態がクラッシュ時に残りうる
- 例外時は一時ファイルを削除して re-raise する。**元のファイルには一切触れていない**
- 置き換え後に**親ディレクトリも fsync する**（段3 指摘7）。中身を fsync しても、`os.replace()` が書き換えるのは親ディレクトリのエントリであり、そちらが永続化されなければ電源断で置き換え前の inode を指したままになりうる。ディレクトリの fsync を許さない環境では握りつぶす（そこでは元々この保証が得られない）

```python
@contextmanager
def locked(*paths: Path) -> Iterator[None]:
    """<path>.lock に対する排他ロック。同一プロセス内で再入可能。"""
```

- `fcntl.flock(fd, LOCK_EX)`。**プロセスが死ねば OS がロックを解放する**ので、タイマーで避けた「残骸の後始末」問題が発生しない（PID を信用する必要がない）
- **再入可能にする**。`move_task` は移動元と移動先の2つのストレージを跨いだトランザクションを開き、その内側で `TaskManager.delete_task()` → `storage.save()` が同じパスのロックを取りに行く。`flock` は同一プロセスでも別 fd なら待つため、素直に実装するとここで自己デッドロックする。`threading.local()` に保持中のパス集合を持ち、既に握っているパスは素通しする
- **複数パスは `Path.resolve()` で正規化してソート順に取得する**。`move_task` を A→B と B→A で同時に走らせたときのデッドロックを、取得順を一意にすることで防ぐ
- ロックファイルは `<path>.lock`。ロック対象の本体を直接 flock しないのは、`os.replace()` で inode が入れ替わるとロックが別のファイルに付いてしまうため
- `fcntl` の import に失敗した場合（Windows）は、`locked()` を何もしないコンテキストマネージャに縮退させる。現行と同じ強度であり後退はしない

### 4. ストレージ各クラス

| クラス | `write_atomic` | `transaction()` | 備考 |
|---|---|---|---|
| `FileStorage` | ✅ | ✅ | `.bak` の作成・削除・復元は現行のまま残す |
| `GlobalConfigStorage` | ✅ | ✅ | `ProjectService` が全メソッドで RMW している |
| `RoutineStorage` | ✅ | ✅ | `add_routine` の `max(id) + 1` 採番 |
| `DailyLogStorage` | ✅ | ✅ | `save()` 自体が RMW |
| `TimerStorage` | ✅ | ✅ | `start()` が check-then-act |

> **段3のコードレビューを受けて変更（2026-09-06）。** 当初は下3つを「ロック不要」と
> していたが、その根拠が誤りだった。`TimerStorage` は「`TimerFile` の全置換だから
> 不可分性だけで足りる」と書いたが、`TimerService.start()` は `get_active()` で
> 確認してから `save()` する **check-then-act** であり、まさに read-modify-write
> である。`RoutineStorage` は `DailyService.add_routine()` が `max(id) + 1` で
> 採番しており、`ProjectService.create_project()` に対して直したのと同じ ID 衝突を
> 持つ。`DailyLogStorage` は `save()` 自体が `load_all()` → 差し替え → `_write()`。
> 「GUI が触るのは作業単位D だから後回し」という切り方は、**同じ欠陥クラスの片方
> だけを直して片方を残す**ことになるので採らない。

### ロックの取得順（デッドロック回避の規約）

**timer.yaml → tasks.yaml の順に取る。** `stop_timer` はタイマーを読んでから作業
セッションをタスク側へ書くため、この向きに入れ子になる。逆向き（タスク側のロックを
握ったままタイマーを触る）を作らないこと。`move_task` がタイマーの付け替えをタスクの
ロック区間の**外**で行っているのはそのためである。`TimerService.transaction()` の
docstring にも同じことを書いてある。

`transaction()` は `locked(self._path)` を返すだけの薄いメソッド。`save()` の内部も `locked()` で覆うため、トランザクション外の単独 `save()` も守られる（再入可能なので二重取得にならない）。

### 5. サービス層のトランザクション境界

- `TaskManager`: `create_task` / `update_task` / `append_work_session` / `delete_task` の load→save を `with self._storage.transaction():` で覆う
- `ProjectService`: `create_project` / `use_project` / `remove_project` / `rename_project` を同様に覆う
- **`rename_project` は「移動先の事前検査 → ディレクトリ移動 → 設定保存」の順で行う**（段3 指摘1）。当初は現行の順序（設定を先に保存してからディレクトリを移動）のままロックだけを掛けたが、これは実際に壊れる: `remove_project()` はディレクトリを消さないので、削除済みプロジェクトのディレクトリが残っていると移動先が既に存在し `Directory not empty` で失敗する。そのとき設定は既に確定しており、「設定は new・データは old」という戻せない食い違いが残る。設定の保存に失敗した場合はディレクトリを戻す。`OSError` は `AppError` に変換して CLI にトレースバックを出さない
- `DailyService`: `add_routine` / `mark_done` / `reset_today` / `_ensure_today_log` / `resume_all` / `delete` / `_update_paused` を覆う

## データフロー

### GUI が別プロジェクトのタスクを完了する
```
1. GUI が uc.complete_task(3, project="foo") を呼ぶ
2. _resolve(ProjectTarget) → "foo"（グローバルのアクティブは読まない）
3. _release_timer(3, record=True, project="foo")
   → timer.yaml の active が (project="foo", task_id=3) のときだけ畳む
4. TaskManager(~/.task-py/projects/foo/tasks.yaml).complete_task(3)
   → with transaction():  # foo/tasks.yaml.lock を握る
       load() → completed へ遷移 → write_atomic()
```

### 2プロセスが同時に add_task する
```
P1: transaction 取得 → load([A]) → [A,B] → write_atomic → 解放
P2:                    （ここで待つ）
P2: transaction 取得 → load([A,B]) → [A,B,C] → write_atomic → 解放
                                 ↑ P1 の結果が見えている
```

## この「動く状態」の生存中に起こりうる操作

> Issue #38 の振り返りで得た教訓（「動く状態」を足すと周囲のイベントとの取り合いを全部決めなければならない。前回は `move` の列挙が漏れて最悪の欠陥がそこに出た）に従い、本作業が導入する生存期間のある状態について、その間に起こりうることを網羅的に列挙する。

本作業が導入する「動く状態」は**保持中のロック**である。生存期間は `transaction()` の内側だけで、プロセスをまたいで残らない。

| その間に起こりうること | 決定 |
|---|---|
| 同一プロセスが同じパスのロックを再度取る | 再入として素通しする（`move_task` → `delete_task` が実際にこの経路） |
| 別プロセスが同じパスのロックを取る | ブロックして待つ。タイムアウトは設けない（単一利用者の CLI 操作は数ミリ秒で終わる） |
| ロック保持中にプロセスが強制終了する | OS が `flock` を解放する。`.lock` ファイルは残るが中身は空で無害。**残骸の検出処理を書かない** |
| ロック保持中に例外が送出される | `contextmanager` の `finally` で解放。書き込みは一時ファイル段階なので本体は無傷 |
| `move_task` が2パスのロックを取る | `resolve()` してソート順に取得。逆向きの同時 move でも取得順が一致するのでデッドロックしない |
| ロック対象ファイルが `os.replace()` で入れ替わる | ロックは本体ではなく `<path>.lock` に対して取っているので影響しない |
| `rename_project` がディレクトリごと移動する | `config.yaml` のロックの内側で、**ディレクトリ移動 → 設定保存**の順に行う。`tasks.yaml` 側のロックは取らない（移動前後で `.lock` のパスが変わり、取っても意味を持たないため）。この窓は残る（後述） |
| タイマーのロックを握ったままタスク側を書く | 許可する（`stop_timer` の経路）。逆向きは作らない。取得順の規約は上記「ロックの取得順」を参照 |
| `~/.task-py/` がまだ存在しない | `locked()` は `ensure_directory()` の後に呼ぶ。ロックファイルの親が無いと `open` に失敗するため |
| テストが `tmp_path` を使う | ロックファイルも `tmp_path` 配下にできる。テスト間で共有されないので直列化の影響を受けない |

**残す窓（意図的）**: `rename_project` の実行中に、別プロセスが旧プロジェクト名の `tasks.yaml` を開いて書き込むと、その書き込みは rename されたあとの旧ディレクトリに取り残される。段3のレビューで具体的な経路が示された: 書き込み側は `projects/old/tasks.yaml.lock` を握っており、これは `config.yaml.lock` とは別のロックなので排他されない。しかも `FileStorage.save()` → `transaction()` → `ensure_directory()` が `mkdir(parents=True, exist_ok=True)` で**旧ディレクトリを作り直す**ため、書き込み自体は成功したうえで誰も読まない場所に残る。これを閉じるにはプロジェクト単位の上位ロックが要り、単一利用者の想定に対して機構が重い。GUI がプロジェクト改名の面を持つのは作業単位D なので、そこで再判定する。requirements のスコープ外に含めない代わりにここへ明示的に残す。

## エラーハンドリング戦略

新しいエラークラスは作らない。

- ロック取得は無期限ブロックのため、専用のエラーが要らない
- `write_atomic` の失敗はこれまでどおり元の例外（`OSError` 等）をそのまま re-raise する。`FileStorage` の呼び出し側で `.bak` からの復元を試みる現行の構造も維持する
- `ProjectTarget` に不正な値が入ることは型で防ぐ（実行時チェックを足さない）

## テスト戦略

### ユニットテスト

**新規 `tests/test_atomic.py`**
- `write_atomic` が成功後に一時ファイルを残さない
- `dump` が例外を投げたとき、既存ファイルの内容が保たれ、一時ファイルも残らない
- `write_atomic` の途中で他プロセス相当の読み手が見るのは「置き換え前の完全な内容」だけである
- `locked` が同一プロセス内で再入できる
- `locked(a, b)` と `locked(b, a)` が同じ順序でロックを取る
- `fcntl` が無い環境をシミュレートしたとき例外にならない

**既存 `tests/test_storage.py`**
- `test_backup_created_during_save` / `test_backup_restored_on_write_failure` を**変更せずに通す**
- 各ストレージについて「書き込み例外時に元ファイルが 0 バイトにならない」を追加

**既存 `tests/test_usecases.py`**
- `project=` を渡さない既存テストが無変更で通る
- `project="foo"` 指定時にアクティブ（`bar`）を無視して `foo` を操作する
- `project=None` 指定時に Inbox を操作する

**既存 `tests/test_time_tracking_usecase.py`**
- `project="foo"` の `complete_task` が `bar` の同 ID のタイマーを畳まない
- `move_task(id, "dst", project="src")` のタイマー付け替え

### 統合テスト

- **別プロセス2本での同時 `add_task`**: `subprocess.run(env={**os.environ, "HOME": fake})` で2本を同時起動し、両方のタスクが残ることを確認する（Issue #38 で「別プロセスからタイマーが見える」を確認したのと同じ枠組み）
- **別プロセス2本での同時 `project create`**: `last_project_id` が重複しないことを確認する

## 依存ライブラリ

**新規の依存はゼロ**。`fcntl` / `tempfile` / `os` / `contextlib` / `threading` はすべて Python 標準ライブラリ。

## ディレクトリ構造

```
src/task_cli/
├── storage/
│   ├── atomic.py                 ← 新規（write_atomic / locked）
│   ├── file_storage.py           ← 変更（transaction + write_atomic）
│   ├── global_config_storage.py  ← 変更（transaction + write_atomic）
│   ├── routine_storage.py        ← 変更（write_atomic）
│   ├── daily_log_storage.py      ← 変更（write_atomic）
│   └── timer_storage.py          ← 変更（write_atomic）
├── services/
│   ├── task_manager.py           ← 変更（transaction 境界）
│   └── project_service.py        ← 変更（transaction 境界）
└── usecases/
    ├── project_target.py         ← 新規（ACTIVE_PROJECT / ProjectTarget）
    ├── task_crud_usecase.py      ← 変更（project= を全メソッドへ）
    └── time_tracking_usecase.py  ← 変更（log_work に project=）

tests/
├── test_atomic.py                ← 新規
├── test_storage.py               ← 変更（追加のみ）
├── test_usecases.py              ← 変更（追加のみ）
├── test_time_tracking_usecase.py ← 変更（追加のみ）
└── test_concurrency.py           ← 新規（別プロセス2本）
```

## 実装の順序

1. **`storage/atomic.py`**（他に依存しない。単体でテストできる）
2. **5ストレージへの `write_atomic` 適用**（②の前半。既存テストが緑のまま通ることを確認）
3. **`FileStorage` / `GlobalConfigStorage` の `transaction()` とサービス層の境界**（②の後半）
4. **`usecases/project_target.py` と `TaskCrudUseCase` の明示指定化**（①。②と独立しているので順序は入れ替え可能だが、②を先にすると①のテストが並行の心配をせずに書ける）
5. **`TimeTrackingUseCase.log_work` の `project=`**
6. **別プロセス統合テスト**

## セキュリティ考慮事項

- `.lock` ファイルは `~/.task-py/` 配下（`700`）に作られるため、既存のパーミッション方針の内側に収まる
- 一時ファイルも同一ディレクトリに作るので同じ。`tempfile.NamedTemporaryFile` の既定パーミッション（`600`）は本体（`644`）より狭いため、`os.replace()` の前に本体の元パーミッションへ合わせる

## パフォーマンス考慮事項

- ロック取得は非競合時にはファイル1つの `open` + `flock` で、`~/.task-py/` がローカルディスクである限りマイクロ秒オーダー。`docs/architecture.md` の「ローカル操作全般 100ms 以内」に影響しない
- `fsync()` は数ミリ秒かかりうる。1操作あたり1回なので同上の要件内に収まるが、段2 で `task-py add` の体感を確認する

## 作業単位B・C（GUI）への申し送り

- **`None` と `ACTIVE_PROJECT` を取り違えないこと。** HTTP のクエリや MCP のオプションが
  未指定のときに `None` をそのまま `project=` へ渡すと、「アクティブプロジェクト」では
  なく**Inbox** を指す。未指定は `ACTIVE_PROJECT`（既定値）であって `None` ではない。
  CLI・MCP を明示指定に対応させるときの最初の落とし穴になる（段3レビューの指摘）
- 現時点で `project=` を渡す呼び出し元は存在しない。GUI がこの引数の最初の利用者になる

## 将来の拡張性

- `atomic.py` を汎用に作るため、作業単位D で `RoutineStorage` / `DailyLogStorage` にロックを足すのは各3行で済む
- `ProjectTarget` は GUI（作業単位B・C）がそのまま使う語彙になる。HTTP のパスパラメータ（`/api/projects/{name}/tasks/{id}`）から `str | None` を作って渡すだけでよい
- ロックを楽観的並行制御へ置き換える必要が出た場合（ネットワークファイルシステム上の `~/.task-py/` 等）、境界が `transaction()` に集約されているので差し替え先が1箇所で済む

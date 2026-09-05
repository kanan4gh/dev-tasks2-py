# 設計書

## アーキテクチャ概要

貫く原則は **「CLI は表示と対話だけ、状態はすべて YAML に、経過時間は wall-clock から導出」** である。これが「別プロセス（将来のローカル Web サーバ）が同じ YAML を読めば同じ状態が見える」という土台要件をそのまま満たす。

現行の `cli/commands/time.py` は `while remaining > 0: time.sleep(1); remaining -= 1` でカウントダウン変数を持つため、(a) 別プロセスから値が見えない、(b) プロセスが落ちると状態が消える、(c) ラップトップのスリープでズレる、の3点すべてに失敗している。**残り時間を `started_at + duration - now` から都度計算する**ことで3点が同時に解消する。

既存の Clean Architecture 4層（`docs/architecture.md`）をそのまま踏襲し、タイマー／作業時間という新しいドメインを4層すべてに通す。

```
┌──────────────────────────────────────────────────────────────┐
│ CLI レイヤー   cli/commands/time.py  cli/commands/edit.py     │
│               cli/editor.py (click.edit ラッパ)               │
│               cli/renderer.py  cli/deps.py                    │
├──────────────────────────────────────────────────────────────┤
│ ユースケース層 usecases/time_tracking_usecase.py  ★新規        │
│               usecases/task_crud_usecase.py（タイマー整理）    │
├──────────────────────────────────────────────────────────────┤
│ サービス層     services/timer_service.py  ★新規                │
│               services/task_manager.py（状態変更の絞り口）     │
├──────────────────────────────────────────────────────────────┤
│ ストレージ層   storage/timer_storage.py  ★新規                 │
│               storage/file_storage.py（変更なし）              │
└──────────────────────────────────────────────────────────────┘
              ↓
  ~/.task-py/timer.yaml          … 実行中タイマー（グローバル・同時1本）
  ~/.task-py/{inbox,projects/*}/tasks.yaml … Task に work_sessions を内包
```

`click.edit()` の呼び出しは **CLI 層のみ**に閉じる（`services` / `usecases` に持ち込まない）。GUI は同じ usecase を別 UI から叩く。

---

## 主要な設計判断

### 判断1: 作業セッションの記録先 → `Task` モデル内に持つ

`Task.work_sessions: list[WorkSession]` として `tasks.yaml` に内包する。

**決め手はタスク ID がストレージローカルで、グローバルに一意でないこと。** `usecases/task_crud_usecase.py:104-105` の `move_task()` は移動先で `next_id()` を採番して **ID を振り直す**。

| 方式 | move | project rename | delete | 横断集計 |
|---|---|---|---|---|
| **A. Task 内に埋め込み（採用）** | `model_copy` で自動追随 | 影響なし | 自動削除 | `list_all_projects()` で走査 |
| B. `~/.task-py/time/sessions.yaml`（`project` + `task_id` キー） | 要書き換え（ID が変わる） | 要書き換え | 孤児化 | 1ファイルで済む |
| C. `projects/<name>/time_sessions.yaml` | 要移送 | ディレクトリごと移動で可 | 孤児化 | 全ファイル走査 |

B / C は「タスクのライフサイクルイベント3種（move / rename / delete）すべてに整合処理を追加する」義務を負う。しかも `ProjectService.rename_project()` は sessions ファイルの存在を知らないので、整合を忘れた瞬間に静かに壊れる。A はその義務がゼロ。

**受容するトレードオフ**: `tasks.yaml` が肥大し、セッション追記のたびに全件書き戻す。ただし既存のあらゆる編集が同じコストなので新規の劣化ではない。lost update の余地は Issue #38 でスコープ外と判断済み。

**付随する設計**: セッション追記で `updated_at` を更新してはいけない。`completed_at` を追加する動機（「`updated_at` は編集で潰れる」）とまったく同じ理由で、時間記録は「内容の編集」ではない。`TaskManager.update_task()`（`services/task_manager.py:66-80`）は常に `updated_at` を更新するため、**それとは別経路の `append_work_session()` を置く**。

### 判断2: タイマー状態の永続化先 → `~/.task-py/timer.yaml` に同時1本

- **グローバル（プロジェクト配下でない）理由**: 「今どのタイマーが動いているか」はプロジェクトを跨いだ唯一の答えであってほしい。プロジェクト配下に置くと、GUI が「実行中タイマーがあるか」を知るのに全プロジェクトを走査する羽目になる。`config.yaml` と同じ階層が素直。
- **同時1本の理由**: 本ツールの思想（`overview` の「今とりかかるべきタスク」）が単一フォーカス前提。複数本にすると CLI にタイマー ID の概念が要り（`time stop <timer_id>`）、表面積が跳ね上がる。将来広げられるよう、**ファイルのトップレベルはオブジェクト**にして `active` を包んでおく。

**プロセス落ち・クラッシュ後の扱い（明確なルール）**:

- 状態は**宣言的**に読む。「T 時刻に D 秒のタイマーが開始された」という事実のみを保存し、**プロセスの生死を判定に使わない**（PID 再利用や別ホストで信用できないため。`pid` は表示・デバッグ用に留める）
- `time status` は `elapsed = now - started_at` を計算する。`duration` 超過なら「時間切れ（未記録）」と表示し、`time stop` で記録するよう促す
- `time start` 実行時に `active` が残っていれば `AppError`（remedy: `time stop` か `time cancel`）。`--force` で置き換え可。**これが「ゴミが残り続ける」ことへの唯一必要な対処**で、ハートビートやロックは不要
- フォアグラウンド実行中の `Ctrl+C` は経過分をセッションとして記録して終了する（現行の「キャンセルしました」だけの挙動からの改善。記録したことを明示表示する）

### 判断3: `completed_at` の意味論

| 事象 | `completed_at` |
|---|---|
| `complete_task()`（→ completed） | `now(UTC)` を設定 |
| `archive_task()`（completed → archived） | **保持**（クリアしない） |
| `archive_task()`（open → archived） | `None` のまま（archive は完了ではない） |
| 完了から出る遷移（将来） | `None` にクリア |
| 既存データ（completed だが値なし） | **バックフィルしない。`None` のまま** |

- **archive で保持する理由**: `completed_at` は「いつ終わったか」に答えるフィールドで、archive は直交する「片付け」操作。archive で消すと「先月完了して今月アーカイブしたタスク」の完了日が失われ、`updated_at` 頼りに逆戻りする。アーカイブ日時が要るなら将来 `archived_at` を別に足す（スコープ外）
- **バックフィルしない理由**: 埋める材料が `updated_at` しかないが、それが信用できないというのが本作業の出発点。誤った日時を**永続化**すると、後から嘘か本当か区別できなくなる。代わりに**表示時フォールバック**に留める（「—（記録なし）」と出す）
- **状態変更の絞り口**: 現行の `can_transition_to()`（`models/task.py:44-52`）に completed → open の経路は**存在しない**が、`edit_fields()` / `update_task(status=...)` はバリデータを迂回できる。`TaskManager` 内に `_apply_status_change()` を作り、完了への出入りのルールをそこ一箇所に実装する。遷移そのものは追加しないが、追加された瞬間に正しく動く

### 判断4: タイマーの `task_id` は任意（既存挙動を壊さない）

- `task-py time start 20m` は現行どおり動く。`--task` / `-t` を**追加オプション**として足すだけで、既存コマンドライン・`tests/test_time.py`・シェル補完はすべて無傷
- `--task` 未指定時は作業セッションを記録しない（タイマーは動く）。判断1 で「セッションは Task の中に住む」と決めた以上、タスク無しセッションには置き場所が無い。現行が「何も記録しない」なので機能後退にはならない。CLI でヒントを出す
- `task start` からのタイマー自動起動は**しない**。`task start` は MCP からも呼ばれ（`start_task` ツール）、そこにブロッキング処理や暗黙の副作用が入るのは事故のもと
- **逆方向の結合は必要**: `done` / `archive` / `delete` の際、そのタスクに紐づく実行中タイマーが残ると孤児になる。`TaskCrudUseCase` に `TimerService` を注入し、対象タスクのタイマーが動いていれば処理する。**CLI 側ではなく usecase 層に一箇所だけ置く**（CLI に書くと MCP 側と必ずズレる）
- 追加として `task-py time start --task 12`（duration 省略）で**ストップウォッチ**を許可する。GUI での「作業中」表現に直結する

### 判断5: `$EDITOR` 連携の CLI 表面 → 引数なし `edit <id>` をエディタ起動にする

現行の「引数なしはエラー（exit 1）」（`cli/commands/edit.py:22-28`）は**機能ではなく no-op へのガード**であり、`git commit` / `crontab -e` / `gh issue edit` と同じ慣習に置き換えるのが素直である。フラグ駆動の経路は一切変更しないので、自動化・MCP は完全に無影響。ただし**観測可能な挙動が変わるため、requirements.md のパス判定では破壊的変更として扱う**。

安全弁を2つ付ける:

1. **TTY ガード**: `sys.stdin.isatty()` と `sys.stdout.isatty()` の**どちらかが偽**（CI・パイプ・リダイレクト・非対話）のときは現行と同じ `AppError` を出して exit 1。エディタで無限ハングする事故を防ぐ
2. **`--editor` / `-e` フラグも併設**: 他のフラグと併用したいとき（`edit 1 -p high -e`）に意図を明示できる

**編集対象は description だけ（プレーンテキスト）**にする。YAML front-matter で title / priority / due をまとめて編集する案は、**パース失敗という新しい失敗モードを持ち込む**（インデント崩れ、日本語タイトルのクォート、description 中の `---`）。今回の課題は「改行を含む長文 description が入らない」であり、プレーンテキストで完全に解決する。全項目の一括編集は GUI のフォームがやるほうが明確に優れているので、そちらに譲る。

### 判断6〜10（段3のコードレビューを受けて実装中に追加）

計画段階では詰めていなかったが、レビューで実害が示されたため決めた事項。いずれも「タイマーは動く状態を持つので、周囲のイベントとの取り合いを明示的に決めないと黙って壊れる」という同じ根に由来する。

| 論点 | 決定 | 理由 |
|---|---|---|
| **`move` と実行中タイマー** | タイマーの向き先を移動後のタスクへ**付け替える**（`retarget_timer_for_task`） | `move_task` は移動先で採番し直すため、付け替えないとタイマーが存在しない ID を指す。停止時に記録が黙って落ちるだけでなく、`_next_id` が `max(id)+1` なので**移動元で ID が再利用されると別のタスクに記録される**。止めて記録する案もあるが、ユーザーはまだ同じ作業を続けているので、追随させるほうが意図に合う |
| **カウントダウンの超過分** | 実績は `duration_seconds` を上限に**打ち切る**。超過分は `StopResult.overrun_seconds` で返し、CLI・MCP が明示する | 25分のタイマーを掛けたまま一晩放置した結果が「10時間の作業」になると、この機能の目的（正確な実績）そのものが壊れる。カウントダウンは宣言した時間が作業の枠である。実際に働いていた分は `time log` で足せる（過少は後から直せるが、誤った長時間の記録は後から嘘か本当か区別できない） |
| **`--force` による置き換え** | 置き換えられる側を**記録してから**差し替える | エラーの remedy が `stop` / `cancel` と並べて `--force` を案内している以上、`--force` だけ実測が消えるのは一貫しない。ユーザーから見て `stop` → `start` と同じ結果になる |
| **遷移に失敗する `done` / `archive`** | 遷移可否を**先に確かめてから**タイマーを畳む | 先に畳むと、失敗時にユーザーへはエラーしか見えず、裏でタイマーが止まって作業時間が確定していることに気づけない |
| **フォアグラウンド表示からの停止** | 自分が開始したタイマーだけを止める（`stop_timer(expected_started_at=...)`） | `_finish` は状態を読み直すため、別プロセスが `stop` / `--force` していると、他人のタイマーを取り違えて記録してしまう |

あわせて `stop_timer` は**記録が成功してから**タイマーを解除する。先に解除すると、保存が失敗（ディスク不足・権限等）したときに実測した作業時間を取り戻せない。

---

## コンポーネント設計

### 1. `models/time.py`（新規）

**責務**: 作業セッションとタイマー状態のデータ表現。

```python
class WorkSession(BaseModel):
    started_at: datetime
    ended_at: datetime
    seconds: int
    source: Literal["timer", "manual"] = "timer"

class TimerKind(str, Enum):
    COUNTDOWN = "countdown"
    STOPWATCH = "stopwatch"

class TimerState(BaseModel):
    kind: TimerKind = TimerKind.COUNTDOWN
    project: str | None = None      # 開始時のアクティブプロジェクト（None = Inbox）
    task_id: int | None = None
    task_title: str | None = None   # 表示用の非正規化コピー
    duration_seconds: int | None = None  # stopwatch なら None
    started_at: datetime
    pid: int | None = None          # 参考情報。生死判定には使わない

class TimerFile(BaseModel):
    active: TimerState | None = None  # 将来の複数化・履歴のためのラッパ
```

**実装の要点**:
- `models/daily.py` と同じく `models/task.py` とは別ファイルに分離する既存慣習に従う
- `models/time.py` は `models/task.py` を import しない（循環回避。`Task` 側が import する）
- `task_title` を非正規化コピーで持つ理由: GUI が `tasks.yaml` を開かずに「何のタイマーか」を表示できるため。正本は Task 側であり、ズレても表示が古くなるだけで実害がない

### 2. `models/task.py`（変更）

**責務**: 既存の Task エンティティに完了日時と作業セッションを追加。

```python
completed_at: datetime | None = None
work_sessions: list[WorkSession] = Field(default_factory=list)

@property
def total_worked_seconds(self) -> int:  # 計算のみ。永続化しない
    return sum(s.seconds for s in self.work_sessions)
```

**実装の要点**:
- どちらもデフォルト付きなので旧 YAML をそのまま読める
- `total_worked_seconds` は `@property` にして `model_dump()` に出さない（保存すると二重の真実になる）

### 3. `services/timer_service.py`（新規）

**責務**: タイマー状態の遷移と時刻計算。純ロジックで、タスクストレージを知らない。

```python
class TimerService:
    def __init__(self, storage: TimerStorage) -> None: ...
    def get_active(self) -> TimerState | None: ...
    def start(self, state: TimerState, force: bool = False) -> TimerState: ...
    def clear(self) -> TimerState | None: ...
    @staticmethod
    def elapsed_seconds(state: TimerState, now: datetime | None = None) -> int: ...
    @staticmethod
    def remaining_seconds(state: TimerState, now: datetime | None = None) -> int | None: ...
```

**実装の要点**:
- **`now: datetime | None = None` で時刻を注入可能にする**。`tests/test_daily_service.py` は `_today_str` を monkeypatch しているが、タイマーは時刻計算そのものが本質なので明示注入のほうが素直で堅い
- 二重起動は `AppError`（message: 「既にタイマーが実行中です。」/ cause: 実行中タイマーの内容 / remedy: `task-py time stop` か `task-py time cancel`、または `--force`）
- `remaining_seconds` は countdown のとき負値を返しうる（時間切れ）。stopwatch では `None`

### 4. `usecases/time_tracking_usecase.py`（新規）

**責務**: タイマーとタスクストレージの調整役。`TaskCrudUseCase` と同じ `resolve_storage_path()` + `storage_factory` DI パターンを踏襲する。

```python
class TimeTrackingUseCase:
    def start_timer(self, duration_seconds: int | None, task_id: int | None, force: bool) -> TimerState
    def stop_timer(self, now: datetime | None = None) -> tuple[TimerState, WorkSession | None]
    def cancel_timer(self) -> TimerState | None
    def status(self, now: datetime | None = None) -> TimerState | None
    def log_work(self, task_id: int, seconds: int) -> Task
```

**実装の要点（実装時に最も間違えやすい箇所）**:
- `start_timer` は `task_id` 指定時にタスクの存在を検証し、**開始時のアクティブプロジェクト名を `TimerState.project` に焼き込む**
- `stop_timer` は **`state.project` でパス解決する。現在のアクティブプロジェクトを使ってはいけない** — タイマー実行中に `project use` で切り替えられる可能性がある。ここは回帰テストを必ず置く
- `stop_timer` は `task_id` が `None` ならセッションを作らずに state をクリアするだけ

### 5. `storage/timer_storage.py`（新規）

**責務**: `~/.task-py/timer.yaml` の load / save。

**実装の要点**:
- `RoutineStorage`（`storage/routine_storage.py:11-32`）と同じ load / save パターン。`.bak` バックアップ機構は付けない（揮発的な状態であり、失うコストが低いため過剰）
- `ensure_directory()` で `chmod 0o700`（既存ストレージと同じ）
- デフォルトパス `~/.task-py/timer.yaml`、コンストラクタで差し替え可能（テスト用）
- 壊れた YAML を読んだときは空の `TimerFile()` を返す（タイマーは揮発的な状態なので、読めなければ「動いていない」で正しい）

### 6. `cli/editor.py`（新規）

**責務**: `click.edit()` のラッパ。型の絞り込み・末尾改行の正規化・例外変換を1ファイルに閉じ込める。

```python
def open_editor(initial: str, extension: str = ".md") -> str | None:
    """エディタを開いて編集後の文字列を返す。キャンセル・無変更なら None。"""
```

**実装の要点**:
- `click.edit()` の戻り型は `str | bytes | bytearray | None`。`isinstance(result, str)` で明示的に絞り込まないと basedpyright（standard）が通らない。**この面倒をこの1ファイルに閉じ込めるのが分離の目的**
- 末尾改行はエディタが必ず付けるので `.rstrip("\n")` で正規化する（しないと毎回差分が出る）
- エディタ起動失敗（`click.UsageError` / `OSError`）は `AppError` に変換する（cause: `$EDITOR` の値、remedy: `EDITOR="code --wait"` の設定例）
- `click` は `typer` の推移的依存として既にインストール済み（8.4.0 で確認）。`click._termui_impl.Editor.get_editor` が `VISUAL` → `EDITOR` の順に見て、`edit_files` が `shlex.split(editor)` してから `subprocess.Popen` するため、`EDITOR="code --wait"` の引数付き指定がそのまま通る

### 7. `duration.py`（新規・パッケージルート）

**責務**: 時間文字列のパースと整形。CLI・MCP の両方から使う。

現在 `parse_duration` / `_format_time` は `cli/commands/time.py` のプライベート関数だが、MCP の `start_timer` ツールと `renderer` も同じ整形を必要とする。`cli/` に置くと MCP → CLI の依存になり層構造を壊すため、`exceptions.py` と同じくパッケージルートの leaf モジュールに置く。

**実装の要点**:
- `cli/commands/time.py` は `from task_cli.duration import parse_duration` で再 export する形にし、`tests/test_time.py` の既存 import（`from task_cli.cli.commands.time import parse_duration`）を**変更せずに緑のままにする**。これが非破壊の証明になる

---

## データフロー

### タイマーを回して作業時間を記録する

```
1. task-py time start 20m --task 1
2. CLI: parse_duration("20m") → 1200
3. TimeTrackingUseCase.start_timer(1200, task_id=1, force=False)
   3-1. アクティブプロジェクトを解決 → "myproj"
   3-2. TaskManager.get_task(1) でタスクの存在を検証（無ければ AppError）
   3-3. TimerService.start(TimerState(project="myproj", task_id=1,
        task_title="...", duration_seconds=1200, started_at=now, pid=os.getpid()))
        → 既に active があれば AppError（force で置換）
   3-4. TimerStorage.save() → ~/.task-py/timer.yaml
4. CLI: rich.Live で 1 秒ごとに TimerService.remaining_seconds(state) を再計算して描画
   （※ カウントダウン変数を持たない。ここが現行との本質的な違い）
5. 時間切れ or Ctrl+C
6. TimeTrackingUseCase.stop_timer()
   6-1. state.project でストレージパスを解決（現在のアクティブプロジェクトではない）
   6-2. WorkSession(started_at, ended_at=now, seconds=elapsed, source="timer") を構築
   6-3. TaskManager.append_work_session(1, session) → updated_at は触らない
   6-4. TimerStorage.save(TimerFile(active=None))
7. CLI: 「タスク #1 に 20m 00s を記録しました」
```

### 別プロセス（将来の GUI / 現時点では MCP）から実行中タイマーを見る

```
1. MCP: get_timer_status()
2. TimeTrackingUseCase.status()
3. TimerStorage.load() → ~/.task-py/timer.yaml
4. TimerService.remaining_seconds(state, now) を計算して返す
   → CLI プロセスと同じ値になる（同じ started_at から同じ式で導出しているため）
```

### `$EDITOR` でタスクの説明を編集する

```
1. task-py edit 1        （オプションなし）
2. CLI: sys.stdin.isatty() と sys.stdout.isatty() を確認
   → どちらかが偽なら現行どおり AppError で exit 1
3. TaskCrudUseCase.get_task(1) で現在の description を取得
4. cli/editor.open_editor(task.description, extension=".md")
   → click.edit() が $EDITOR（例: code --wait）を起動
5. 戻り値が None（キャンセル・無変更）→「変更はありませんでした」で exit 0
6. 文字列 → TaskCrudUseCase.edit_task(1, description=編集後) → render_success
```

---

## エラーハンドリング戦略

既存パターン（`exceptions.py:1-6` の `AppError` を `message` / `cause` / `remedy` の3点セットで送出し、CLI・MCP 層で catch して整形表示）をそのまま踏襲する。新規に定義する例外クラスはない。

| 状況 | 送出層 | remedy |
|---|---|---|
| タイマー二重起動 | `TimerService` | `task-py time stop` / `time cancel` / `--force` |
| `stop` / `cancel` したが実行中タイマーなし | `TimeTrackingUseCase` | `task-py time start <duration>` |
| `--task` に存在しないタスク ID | `TimeTrackingUseCase` | `task-py list` で確認 |
| タイマー停止時、記録先タスクが既に削除済み | `TimeTrackingUseCase` | state をクリアした上で警告表示（例外にしない） |
| エディタ起動失敗 | `cli/editor.py` | `EDITOR="code --wait"` の設定例を示す |
| 非対話端末で `edit <id>`（引数なし） | `cli/commands/edit.py` | 現行と同じメッセージ（フラグを指定せよ） |
| `time log` の duration が不正 | `duration.parse_duration` | 現行と同じ（`20m`, `1h`, `30s`） |

---

## テスト戦略

既存方針（`CliRunner` は使わない、ロジックは services / usecases でカバー、`tmp_path` で実ファイル I/O、`class Test<対象>` → `def test_<ケース>`）を踏襲する。

### ユニットテスト

- **`tests/test_models.py`（変更）**: `completed_at` / `work_sessions` のデフォルト、**フィールドを持たない旧 dict を `Task.model_validate()` できること**（後方互換の核心）、`total_worked_seconds` の合計
- **`tests/test_storage.py`（変更）**: `completed_at` / `work_sessions` の save / load ラウンドトリップ、両キーを欠いた YAML を直に書いて `load()` が通ること
- **`tests/test_usecases.py`（変更）**: `complete_task` で `completed_at` が set、`archive_task`（completed → archived）で**保持**、open → archive で `None` のまま、`append_work_session` が **`updated_at` を変えない**こと（最も回帰しやすい重要アサーション）
- **`tests/test_migrate.py`（変更）**: `completedAt` 有り / 無しの両方の TypeScript 版 JSON が変換できること
- **`tests/test_timer_service.py`（新規）**: `now` を明示注入して経過・残り・超過（負値）を検証、二重 start で `AppError`、`force` で置換、`clear` で state が空になること
- **`tests/test_time_tracking_usecase.py`（新規）**: **タイマー実行中にアクティブプロジェクトを切り替えても、セッションが開始時のプロジェクトのタスクに記録されること**（設計判断4の実装事故ポイントの回帰テスト）、存在しない `task_id` で start すると `AppError`、`cancel` ではセッションが記録されないこと
- **`tests/test_editor.py`（新規）**: `click.edit` を `unittest.mock.patch` で差し替え、(a) 文字列が返る、(b) `None`（キャンセル）、(c) `bytes` が返った場合の絞り込み、(d) 末尾改行の正規化、(e) 例外 → `AppError` 変換。**実際にエディタを起動するテストは書かない**
- **`tests/test_time.py`（変更）**: 既存の `parse_duration` テストを**import 文ごとそのまま緑に保つ**（非破壊の証明）
- **`tests/test_mcp_server.py`（変更）**: `EXPECTED_TOOLS` にタイマー系ツールを追加、`start_timer` の `task_id` が required でないこと

### 統合テスト

- **別プロセス相当の検証（土台要件の直接検証）**: `TimerStorage` インスタンス A で start → **同一パスの別インスタンス B** で `get_active()` が読める。`tests/test_usecases.py` が別インスタンスで永続化を確認しているのと同じ手法
- **実挙動検証（4段検証の段2）**: 実際に `task-py time start` を別シェルで走らせ、もう一方のシェルの `task-py time status` に同じ残り時間が出ることを観察する。`EDITOR` を非対話的なスクリプト（例: `EDITOR="sed -i '' 's/^/edited: /'"`）にして `task-py edit <id>` の往復も観察する

---

## 依存ライブラリ

**新規に追加する本番依存はない。** `click` は `typer` の推移的依存として既にインストール済み（8.4.0）。

```toml
# pyproject.toml の [project] dependencies は変更なし
```

---

## ディレクトリ構造

```
src/task_cli/
├── duration.py                       ★新規  時間文字列のパース・整形（leaf）
├── models/
│   ├── task.py                       変更   completed_at / work_sessions
│   └── time.py                       ★新規  WorkSession / TimerState / TimerFile
├── storage/
│   └── timer_storage.py              ★新規  timer.yaml の load/save
├── services/
│   ├── task_manager.py               変更   _apply_status_change / append_work_session
│   └── timer_service.py              ★新規  タイマー状態遷移・時刻計算
├── usecases/
│   ├── task_crud_usecase.py          変更   done/archive/delete でのタイマー整理
│   └── time_tracking_usecase.py      ★新規  タイマー × タスクの調整
└── cli/
    ├── deps.py                       変更   timer 系の DI を追加
    ├── editor.py                     ★新規  click.edit ラッパ
    ├── renderer.py                   変更   Completed / Worked 行
    └── commands/
        ├── edit.py                   変更   エディタ起動 + TTY ガード
        ├── time.py                   変更   全面書き換え（start/status/stop/cancel/log）
        └── migrate.py                変更   completedAt の防御的マッピング

src/task_mcp/
└── server.py                         変更   _fmt_task 拡張 + タイマー系ツール

tests/
├── test_editor.py                    ★新規
├── test_timer_service.py             ★新規
├── test_time_tracking_usecase.py     ★新規
└── test_models.py / test_storage.py / test_usecases.py /
    test_migrate.py / test_mcp_server.py / test_time.py   変更
```

---

## 実装の順序

フェーズ1・2は互いに独立でそれぞれ単独でコミットできる。フェーズ3はフェーズ4の土台になる（タイマーは「セッションを保存できる」仕組みの消費者にすぎない）。

1. **フェーズ1: `completed_at`** — 最小・独立。`scheduled_date` 追加の前例どおり8箇所を踏む
2. **フェーズ2: `$EDITOR` 連携** — CLI 層のみで完結。独立
3. **フェーズ3: 作業セッションのモデルと手動記録** — `WorkSession` / `append_work_session` / 表示。タイマー抜きで完結させる
4. **フェーズ4: タイマーの永続化とタスク接続** — フェーズ3 の上に載せる本丸
5. **フェーズ5: ライフサイクル結合とドキュメント更新** — done / archive / delete とタイマーの整合、永続ドキュメント更新

---

## セキュリティ考慮事項

- `~/.task-py/timer.yaml` は既存ストレージと同じく `ensure_directory()` の `chmod 0o700` 配下に置く。ファイル自体に機密情報は入らない（タスクタイトルの非正規化コピーは `tasks.yaml` に既にある情報）
- `click.edit()` は `$EDITOR` を `shlex.split` して `subprocess.Popen` に渡す。シェルを経由しない（`shell=True` ではない）ため、`$EDITOR` の値によるコマンドインジェクションの経路にはならない。`$EDITOR` はユーザー自身の環境変数であり、信頼境界の内側

---

## パフォーマンス考慮事項

- 作業セッションを `tasks.yaml` に内包するため、セッション追記のたびに全タスクを書き戻す。ただし既存のあらゆる編集（`edit` / `done` / `start`）が同じコストであり、新規の劣化ではない。`docs/architecture.md` の性能要件（1,000件で1秒以内）に対して十分な余裕がある
- タイマーのフォアグラウンド表示は 1 秒ごとに `remaining_seconds()` を再計算するが、これはメモリ上の減算のみで YAML の再読み込みは行わない（開始時に読んだ `TimerState` を保持する）

---

## 将来の拡張性

- **ローカル Web GUI（次の作業単位）**: `timer.yaml` と `tasks.yaml` を読むだけで、実行中タイマーと作業実績を表示できる。CLI プロセスに依存しない。GUI から `TimeTrackingUseCase` を直接呼べば操作もできる
- **複数タイマー**: `TimerFile.active` を `list` に広げられるようトップレベルをオブジェクトにしてある
- **`archived_at`**: `completed_at` と同じパターンで追加できる（`_apply_status_change` に1行）
- **タイマー完了通知**: `--detach` はデーモン化しないため通知できない。通知は常駐する GUI 側の責務として先送りする
- **リッチな一括編集**: description 以外の一括編集は GUI のフォームに譲る（YAML front-matter 方式を採らない理由は判断5 を参照）

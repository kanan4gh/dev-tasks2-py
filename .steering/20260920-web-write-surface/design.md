# 設計書

## アーキテクチャ概要

`task_web` は読み取り面（#46）と同じ構造のまま、書き込み経路を足す。層の規則は変えない。

```
ブラウザ ──POST/PATCH/DELETE──→ task_web/api.py ──→ usecases/ ──→ services/ ──→ storage/
                                  │                                  ↑
                                  ├─ csrf.py    … 書き込みだけを検査   │
                                  └─ versions.py … If-Match の照合    │
                                                                      │
                          ここで直す: update_task の再バリデーション ──┘
                                      move_task の移動先検証
```

**貫く原則**（#46 から継続）: 「サーバは `usecases` の薄いラッパ」「真実は YAML、サーバは状態を溜めない」。
本作業で足す原則: **「成功を報告したなら、利用者が見える場所にそれが残っている」**。欠陥 A・B はどちらもこれを破っていた。

## コンポーネント設計

### 1. 書き込み経路の安全化（`services/task_manager.py` / `usecases/task_crud_usecase.py`）

#### A. `update_task` の再バリデーション

```python
def update_task(self, id: int, **kwargs: object) -> Task:
    ...
    updated = task.model_copy(update={**kwargs, "updated_at": ...})
    updated = self._revalidate(updated)   # ← 追加
```

- **`model_copy(update=...)` は pydantic v2 では再バリデーションしない。** そのため `due_date` の
  `field_validator` が編集経路で一切効いておらず、`due_date: bogus` が YAML に書かれていた。
  書かれたあとは `load()` の `Task.model_validate` が落ちるため、**そのプロジェクトのタスクが
  全部読めなくなる**（`list` も `add` も落ちる）
- 保存の直前に `Task.model_validate(updated.model_dump())` を通し、`ValidationError` は
  `AppError` に写す。**保存前に弾く**のが肝で、保存後に気づいても手で YAML を直すしかない
- `append_work_session` と `move_task` の `model_copy` は対象外。前者は検証済みの
  `WorkSession`、後者は自前で採番した `int` しか差し替えないため

#### B. `move_task` の移動先検証

```python
if target_project is not None and target_project not in {p.name for p in config.projects}:
    raise AppError("移動先のプロジェクトが見つかりません。", ...)
```

- 検証は**ディレクトリを作る前**に行う。#42 で移動元について同じことをした（失敗しただけで
  空のディレクトリが残らないように）のと同じ理由
- `None`（Inbox）は常に有効

#### C. `ValidationError` → `AppError`

- 写す場所は **`TaskManager`**（`create_task` と `update_task`）。ここに置けば CLI・MCP・Web の
  3入口すべてが同時に直る。入口ごとに `except ValidationError` を書くと必ずどこかで漏れる
- メッセージは pydantic の生の英文ではなく、どのフィールドが何を期待しているかを日本語で出す

### 2. `task_web/csrf.py`（新規）

**責務**: 書き込みリクエストがこのサーバ自身の画面から来たことを確かめる。

**実装の要点**:

- **`Host` 検証（#46）では CSRF は防げない。** あれは DNS リバインディング対策であり、
  攻撃者のページから `fetch("http://127.0.0.1:8765/...", {method:"POST"})` を投げられた場合、
  `Host` はこちらの正しい値になる
- 3層で塞ぐ:

| 検査 | 不一致のとき | 効く理由 |
|---|---|---|
| `Content-Type: application/json` を必須 | 415 | クロスオリジンで JSON を送るとブラウザが**プリフライト**を投げる。`OPTIONS` を登録していないので 405 になり、本番のリクエストは飛ばない |
| `Sec-Fetch-Site` があれば `same-origin` のみ | 403 | 現行ブラウザは必ず送り、**ページ側から偽装できない** |
| `Origin` があればホストが許可リスト内 | 403 | `Sec-Fetch-Site` を送らない古いブラウザ向けの保険 |

- **ヘッダが無い場合は通す。** curl やテストのため。ブラウザは必ず送るので、ブラウザ経由の
  CSRF は塞がる。「送られてこないなら攻撃ではない」ではなく「**攻撃者はブラウザ越しにしか
  来られず、ブラウザは必ず送る**」という理屈である
- トークン方式を採らない。サーバが状態を持たないという原則を崩さずに済み、単一利用者の
  ローカル面には十分

### 3. `task_web/versions.py`（新規）

**責務**: 画面が見ていた版と、いま保存されている版を照合する。

**実装の要点**:

- 版として `Task.updated_at` の ISO 文字列を使う。`serializers` は一覧・詳細の両方で
  すでに返しているため、画面は追加の取得なしに送れる
- 運び方は **`If-Match` ヘッダ**。`DELETE` にも付けられ、本文の形に依存しない。HTTP の
  意味論そのまま
- 無ければ **428**（前提条件が必要）。「省略したら上書き」にしない。省略が黙って
  危険側に倒れる既定値は作らない
- 食い違えば **409** + 現在のタスクを本文に載せる。画面が最新を出し直せる
- **`append_work_session` は `updated_at` を動かさない**ので、タイマーの停止で作業セッションが
  足されても 409 にならない。これは偶然ではなく #38 で意図して決めた性質で、
  「編集と競合していないものを競合と呼ばない」という正しい挙動になっている

### 4. `task_web/api.py` の書き込みエンドポイント

**実装の要点**:

- **書き込みは `async def` にする。** 本文を読むのに `await request.json()` が要るため。
  ただし #46 の段3 指摘5（同期処理をイベントループで走らせない）を壊さないよう、
  **ドメインの処理は `starlette.concurrency.run_in_threadpool` に逃がす**:

  ```python
  async def wrapper(request):
      payload = await _json_body(request)          # ループ上（速い）
      return await run_in_threadpool(fn, request, payload)   # YAML と flock はここ
  ```
- 既存の `_handle`（読み取り用・同期のまま）とは別に、書き込み用のデコレータファクトリ
  `_writer(allowed_hosts)` を作る。読み取り側の性質を変えない
- エラーの写し方を拡張する。現行は `BadRequest` → 400、その他 `AppError` → 404 の2分岐。
  書き込みでは「見つからない」と「値が不正」と「遷移できない」が混ざるため、
  **例外のクラスで分ける**（`NotFound` / `BadRequest` / `Conflict` / `PreconditionRequired`）
- 移動先の検証は **usecase 層の `TaskCrudUseCase._require_known_project`** が行う
  （上記セクション1B）。web 層に同じ判断を二重に置かない。パスのプロジェクト名の
  検証だけが `api.py` の `_require_project` である

### 5. 画面（`static/js/`）

- `api.js` に `request(path, {method, body, ifMatch})` を足し、`get()` もそこへ寄せる
- 書き込み後は**楽観的更新をしない**。サーバの応答で置き換えるか、リビジョンの変化を
  待って取り直す。楽観的更新は「画面とファイルが食い違う」状態を作るため、
  「真実は YAML」という原則と相性が悪い
- 409 は専用の見せ方をする（「別の場所で変更されました」＋最新の内容）。ほかのエラーと
  同じ赤い箱に流し込むと、利用者は自分の入力が悪かったと誤解する
- 削除は確認を置く（CLI の `delete` が `typer.confirm` を出しているのと揃える）

## データフロー

### 画面からタスクを完了する
```
1. 一覧の行の「完了」を押す（行は updated_at を持っている）
2. POST /api/projects/foo/tasks/3/done
   Content-Type: application/json
   If-Match: "2026-09-20T01:23:45.678901Z"
3. csrf 検査 → versions 照合（現在の updated_at と一致するか）
4. run_in_threadpool: uc.complete_task(3, project="foo")
5. 200 + 更新後のタスク。SSE でリビジョンも変わり、他のタブも追随する
```

### 途中で CLI が同じタスクを編集していた
```
3'. 照合で食い違い → 409 + 現在のタスク
4'. 画面が「別の場所で変更されました」と出し、最新を表示する
```

## この「動く状態」の生存中に起こりうる操作

> #38・#42・#46 と同じく列挙する。本作業が足す「動く状態」は**画面に開いたままの編集フォーム**である。

| その間に起こりうること | 決定 |
|---|---|
| CLI が同じタスクを編集する | `If-Match` の照合で 409。黙って上書きしない |
| CLI がタイマーを止めて作業セッションが足される | **409 にしない**。`append_work_session` は `updated_at` を動かさない |
| CLI がそのタスクを削除する | 保存時に 404。画面は一覧へ戻す |
| CLI がそのタスクを move する（ID が変わる） | 旧 ID は 404。SSE の取り直しで消える |
| CLI がそのプロジェクトを rename / remove する | パスが 404。同上 |
| フォームを開いたまま SSE でリビジョンが変わる | **入力中の内容を勝手に捨てない**。一覧は更新するが、開いているフォームはそのまま。保存時に 409 で気づく |
| 同じタスクを2つのタブで編集する | 後から保存したほうが 409。先勝ち |
| 追加の最中に別プロセスが同名を作る | タスクに一意制約は無いので衝突しない。ID は保存時に採番される |
| 削除の確認中にタスクが変わる | `If-Match` を確認時点の値で送るので 409 になる |

## エラーハンドリング戦略

新しいエラークラスは `api.py` の内部にだけ作る（`AppError` のサブクラス）。ドメイン層には持ち込まない。

| クラス | HTTP | 使う場面 |
|---|---|---|
| `BadRequest` | 400 | クエリ・本文の値が不正 |
| `NotFound` | 404 | タスク・プロジェクトが無い |
| `Forbidden` | 403 | CSRF 検査に落ちた |
| `UnsupportedMedia` | 415 | `Content-Type` が JSON でない |
| `PreconditionRequired` | 428 | `If-Match` が無い |
| `Conflict` | 409 | `If-Match` が食い違う。本文に現在のタスクを載せる |

ドメイン側（`TaskManager` / usecase）が投げる `AppError` は従来どおり 404 に写す。ただし
`update_task` の再バリデーション由来のものは値の問題なので 400 に写す必要がある。
**例外クラスで区別する**ため、`TaskManager` は検証失敗に専用のサブクラス（`InvalidTaskData`）を使う。

## テスト戦略

### ユニットテスト

**`tests/test_usecases.py` / `tests/test_models.py`（追加）**
- `update_task` が不正な `due_date` を**保存前に**弾く
- 弾いたあとストレージの内容が変わっていない（次の `load()` が通る）
- `move_task` が存在しない移動先を弾き、ディレクトリを作らない
- 正常系は無変更で通る

**`tests/test_web_write.py`（新規）**
- 追加・編集・状態変更・移動・削除がそれぞれ `~/.task-py/` に反映される
- アクティブプロジェクトに影響されない（パスで明示した先に書かれる）
- `If-Match` 一致 → 成功 / 不一致 → 409 + 現在のタスク / 無し → 428
- **作業セッションの追記では 409 にならない**
- CSRF: JSON でない → 415 / `Sec-Fetch-Site: cross-site` → 403 / 他オリジンの `Origin` → 403 / ヘッダ無し → 通る
- 読み取りは CSRF 検査を受けない
- 不正な値 → 400（原因と対処つき）

### 統合テスト

- `tests/test_web_server.py` に、実プロセスへ `POST` して反映を確かめる経路を足す
- **欠陥 A・B の回帰**: 実 CLI で再現手順をなぞり、修正後は失敗して**データが読める**ことを確認する

## 依存ライブラリ

**追加なし。** `starlette.concurrency.run_in_threadpool` は導入済みの starlette に含まれる。

## ディレクトリ構造

```
src/task_web/
├── api.py          ← 変更（書き込みエンドポイントと _handle_write）
├── csrf.py         ← 新規
├── versions.py     ← 新規
└── static/js/
    ├── api.js      ← 変更（request() へ寄せる）
    ├── ui.js       ← 変更（フォーム・確認・409 の見せ方）
    └── main.js     ← 変更（書き込みの状態遷移）

src/task_cli/
├── services/task_manager.py        ← 変更（再バリデーション・InvalidTaskData）
└── usecases/task_crud_usecase.py   ← 変更（move_task の移動先検証）

tests/
├── test_web_write.py               ← 新規
├── test_web_server.py              ← 変更（追加のみ）
├── test_usecases.py                ← 変更（追加のみ）
└── test_web_api.py                 ← 変更（追加のみ）
```

## 実装の順序

1. **書き込み経路の安全化**（欠陥 A・B・C）。他に依存せず、先に直さないと GUI がその上に載る
2. **`csrf.py` と `versions.py`**（単体でテストできる）
3. **書き込みエンドポイント**と `tests/test_web_write.py`
4. **画面**（フォーム・確認・409 の見せ方）
5. **統合テスト**（実プロセス・欠陥 A/B の回帰）

## セキュリティ考慮事項

- CSRF は上記3層。**`Host` 検証（#46）とは別の問題**であることを混同しない
- 書き込みが増えても待ち受けは `127.0.0.1` のまま。`--host` は引き続き用意しない
- 削除は物理削除で、undo は持たない（スコープ外の判断）。そのぶん画面で確認を置く

## パフォーマンス考慮事項

- 書き込みは `run_in_threadpool` へ逃がすので、`flock` の待ちが他のリクエストと SSE を止めない
- `If-Match` の照合のために保存前にもう一度読むが、同じ排他区間の内側で行うので追加の
  ロック取得は発生しない（再入可能。#42 の設計）

## 将来の拡張性

- 一括操作を入れるときは、この `If-Match` を「対象それぞれの版のリスト」に広げるか、
  一括専用の経路を作るかを決める必要がある。**undo の要否もそこで再判定する**
- 作業単位D（project 管理・daily・タイマー）も同じ `csrf` と `versions` を使える

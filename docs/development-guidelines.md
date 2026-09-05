# 開発ガイドライン (Development Guidelines)

## 本書の役割

本書は、TaskCLIを開発するための環境準備、Pythonコーディング規約、テスト、品質保証、Git・PR・リリースの実務を定める。

仕様とプロセスの正典は次の文書に置き、本書では日常作業に必要な入口だけを示す。

- SDDプロセスと技術スタック: `AGENTS.md`
- 作業計画・状態遷移・振り返り: `docs/procedures/steering.md`
- アーキテクチャ: `docs/architecture.md`
- ファイル配置と依存方向: `docs/repository-structure.md`
- 外部自動化の利用境界: `docs/external-automation-policy.md`
- 利用者向けのインストール・操作方法: `README.md`

---

## 開発環境セットアップ

### 必要なツール

| ツール | 要件 | 用途 |
|---|---|---|
| Python | 3.12以上 | アプリケーションと開発スクリプトの実行 |
| uv | 安定版 | 依存関係、仮想環境、コマンド実行の管理 |
| Git | 利用環境の安定版 | ブランチ・履歴管理 |
| GitHub CLI | PR・Issue・Releaseを操作する場合 | `gh` コマンド |
| Docker / VS Code Dev Containers | 任意 | 再現可能なコンテナ開発環境 |

devcontainerは任意である。ローカルにPython 3.12とuvがあれば、コンテナを使わずに同じ品質ゲートを実行できる。

### セットアップ手順

```bash
git clone https://github.com/kanan4gh/dev-tasks2-py.git
cd dev-tasks2-py
```

ここで実行環境を選ぶ。

- Dev Containerを使う場合: VS Codeで「Reopen in Container」を選ぶ
- ローカル環境を使う場合: `python3 --version` と `uv --version` で要件を確認する

選択した環境内で依存関係を同期し、CLIを確認する。

```bash
uv sync
uv run task-py --help
```

Dev Containerでは `.devcontainer/postCreate.sh` がuvと開発ツールを準備する。

`uv sync` は `pyproject.toml` と `uv.lock` に従って環境を同期する。依存関係を変更した場合は、両ファイルの差分を確認してコミットする。

---

## 日常の開発フロー

1. 関連するGitHub Issueを確認し、なければ先に作成する
2. `main` の最新状態から `feature/<task-name>` ブランチを作る
3. `.steering/YYYYMMDD-<task-name>/` に要求・設計・タスクリストを記録する
4. 関連文書と類似実装を読んでから変更する
5. 完了した項目を直後に `tasklist.md` へ反映する
6. 変更種別に応じた検証とレビューを行う
7. tasklistを `complete` に遷移してから、明示対象のローカル品質ゲートを通す
8. Conventional Commits形式でコミットし、フィーチャーブランチからPRを作成する

機能実装コードを `main` に直接コミット・プッシュしない。計画、実装、検証、振り返りの詳細と `active / paused / complete` の遷移規則は `docs/procedures/steering.md` に従う。

通常の応答終了は作業の中断ではない。意図的に中断・再開・完了する場合だけ、次のスクリプトを使う。

```bash
uv run python3 scripts/steering_state.py pause --help
uv run python3 scripts/steering_state.py resume --help
uv run python3 scripts/steering_state.py complete --help
```

---

## Pythonコーディング規約

### 命名

| 対象 | 規則 | 例 |
|---|---|---|
| モジュール・関数・変数 | `snake_case` | `task_manager.py`, `list_tasks` |
| クラス・列挙型 | `PascalCase` | `TaskManager`, `TaskStatus` |
| 定数 | `UPPER_SNAKE_CASE` | `_PRIORITY_ORDER` |
| 真偽値 | 意味が分かる述語 | `is_active`, `has_tasks`, `can_transition` |
| テスト | `test_<期待する振る舞い>` | `test_missing_task_raises_app_error` |

省略名よりドメイン用語を優先する。用語の意味は `docs/glossary.md`、ファイルの配置は `docs/repository-structure.md` に合わせる。

### 型とデータモデル

- 公開する関数・メソッドの引数と戻り値には型注釈を付ける
- 「値がない」を許す場合は `T | None` を明示する
- 固定した文字列集合は `Enum` または `Literal` で表す
- 永続化するエンティティと入力検証にはpydantic `BaseModel` を使う
- 内部処理だけの小さな値オブジェクトには `dataclass` を使ってよい
- 型検査を避けるための無根拠な `Any` や `# type: ignore` を追加しない

```python
from dataclasses import dataclass
from typing import Literal

from task_cli.models.task import Priority, TaskStatus


@dataclass
class TaskFilter:
    status: TaskStatus | list[TaskStatus] | None = None
    priority: Priority | None = None
    sort: Literal["id", "priority", "due_date", "created_at"] = "id"
```

basedpyrightは `pyproject.toml` の設定を正とし、Python 3.12、`typeCheckingMode = "standard"` で実行する。

### フォーマットとimport

- 行の最大長は100文字とする
- インデントはスペース4つとする
- importは標準ライブラリ、外部ライブラリ、プロジェクト内の順に分ける
- 未使用import、未定義名、構文上の問題はruffで検出する
- 自動整形だけを前提にせず、既存ファイルの書式へ合わせる

ruffの有効ルールと対象Pythonバージョンは `pyproject.toml` を正とする。現設定は行長違反をlint対象に含めないため、100文字以内かは差分レビューでも確認する。

### 関数と責務

- 1つの関数・メソッドには1つの主要な責務を持たせる
- CLIとMCPは入力変換と出力整形に集中し、ドメイン判断をusecaseまたはserviceへ委譲する
- 通常のタスク・設定・日次・タイマーYAMLの読み書きと復元方針はstorageへ閉じ込める
- 移行、全体リセット、観測ログ、プロジェクトディレクトリのライフサイクルなど通常永続化と異なる境界処理は、責務と例外理由が明確な専用モジュールへ置く
- 複数のserviceやstorageを調整する処理はusecaseへ置く
- 共有ドメイン層の外部状態依存は、原則としてコンストラクタや引数で渡し、テストで差し替えられるようにする。現状の `ProjectService` にあるディレクトリ操作は境界処理の例外であり、再利用や独立テストが必要になった時点でstorageへの抽出を検討する
- 同じ分岐が複数の入口に現れたら、共有層へ集約できないか検討する

```python
from task_cli.exceptions import AppError
from task_cli.models.task import Task
from task_cli.storage.file_storage import FileStorage


class TaskManager:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def get_task(self, task_id: int) -> Task:
        for task in self._storage.load():
            if task.id == task_id:
                return task
        raise AppError(
            "タスクが見つかりません。",
            cause=f"ID={task_id} のタスクは存在しません。",
            remedy="task list で有効なIDを確認してください。",
        )
```

### エラーハンドリング

利用者が対処できるエラーは `task_cli.exceptions.AppError` で表し、次の3要素を渡す。

- `message`: 何が失敗したか
- `cause`: なぜ失敗したか
- `remedy`: 利用者が次に何をすればよいか

予期しない例外を握りつぶさない。復旧可能な境界で別の例外を捕捉する場合も、元の原因を失わない説明または例外チェーンを残す。CLI固有の終了コードと表示はCLIレイヤー、MCP向けの変換はMCPレイヤーで扱う。

### コメントとdocstring

- コードから明らかな「何をしているか」ではなく、判断理由や制約を書く
- 後方互換、時刻、永続化、依存方向など、誤って単純化されやすい理由を優先する
- docstringは公開API、複雑な振る舞い、呼び出し側が知るべき副作用に付ける
- 一時的なTODOには追跡先のIssueを添える
- コメントアウトしたコードやデバッグ出力を残さない

---

## テスト戦略

### 基本方針

- pytestを使用する
- 正常系だけでなく、入力境界、状態遷移、欠損データ、I/O失敗を確認する
- ファイルI/Oはpytestの `tmp_path` で隔離し、実際の利用者データへ触れない
- 時刻、ホームディレクトリ、ネットワークなどの外部境界だけをfixtureやmonkeypatchで制御する
- serviceとusecaseのドメイン判断は、可能な限り実装を通して検証する
- バグ修正では、修正前に失敗する回帰テストを追加する
- テスト件数や固定比率ではなく、要求とリスクに対する網羅性で判断する

```python
from pathlib import Path

import pytest

from task_cli.exceptions import AppError
from task_cli.services.task_manager import TaskManager
from task_cli.storage.file_storage import FileStorage


def test_missing_task_raises_app_error(tmp_path: Path) -> None:
    manager = TaskManager(FileStorage(tmp_path / "tasks.yaml"))

    with pytest.raises(AppError):
        manager.get_task(999)
```

### 配置

- プロダクト機能のテスト: `tests/test_<対象>.py`
- ハーネス・規律・スクリプトのテスト: `tests/<分類>/test_<対象>.py`

詳細な分類は `docs/repository-structure.md` を参照する。

### 個別検証コマンド

```bash
uv run pytest
uv run ruff check .
uv run basedpyright
uv run python3 scripts/steering_lint.py
uv run python3 scripts/metered_automation_lint.py
```

対象を絞って反復する場合は、たとえば `uv run pytest tests/test_models.py` のように実行する。PR前は個別コマンドの寄せ集めではなく、次節の単一ゲートを使う。

---

## 品質保証

### 必須のローカル品質ゲート

PR前の品質保証の正は次のコマンドである。

```bash
uv run python3 scripts/local_quality_gate.py --steering YYYYMMDD-<task-name>
```

このゲートはpytest、ruff、basedpyright、steering lint、外部有料自動化lintを固定順で実行する。ネットワークやLLMを呼び出さない。対象steeringのタスク・振り返りを完了し、`complete` へ遷移した後に実行する。

### GitHub Actions

`.github/workflows/steering-lint.yml` は、利用権限と予算がある場合だけ明示的に起動する任意の手動ミラーである。PR、push、scheduleでは自動起動せず、その成功をPR完了の必須証拠にしない。

### 対話型実機受け入れ

ハーネスの構成・権限・フックを変更した場合は `docs/procedures/harness-acceptance.md` に従う。利用許可済みのIDEまたは対話型CLIを使い、従量課金型LLMの非対話実行を標準受け入れに使わない。

純ドキュメント変更は実行時の観察対象がないため、実挙動検証をスキップし、変更差分と文書品質をレビューする。

---

## Git・PR運用

### ブランチ

`main` を安定ブランチとし、作業ごとに最新の `main` からフィーチャーブランチを作る。

```text
main
└── feature/<task-name>
```

- 機能、修正、ドキュメントのいずれもPR経由で `main` へ統合する
- ブランチ名と `.steering/YYYYMMDD-<task-name>/` のタスク名を揃える
- ユーザーの既存変更を無断で破棄・上書きしない
- GitHub Actionsを自動実行しないプロジェクト方針を維持する

### コミット

Conventional Commits形式を使う。

```text
<type>(<scope>): <subject>

<変更理由と重要な判断>

Closes #<Issue番号>
```

主なtypeは `feat`、`fix`、`docs`、`refactor`、`test`、`chore` とする。1つのコミットには、レビュー可能な1つの目的を持たせる。

### PR

`.github/pull_request_template.md` に従い、次を記録する。

- 変更概要・理由・内容
- 実行したローカル品質ゲート、日時、結果
- 対話型実機受け入れの要否と理由
- 関連Issueを閉じる `Closes #<番号>`

PRは `gh pr create` で作成できる。マージはプロジェクトオーナーが判断する。

---

## バージョニングとリリース

[Semantic Versioning 2.0.0](https://semver.org/lang/ja/) に従う。

| 種別 | 条件 |
|---|---|
| MAJOR | 移行手段のないデータ形式変更、公開契約の非互換変更 |
| MINOR | 後方互換な機能追加 |
| PATCH | 後方互換なバグ修正・軽微な改善 |

リリースする場合は次の順序で進める。

1. `pyproject.toml` の `version` を更新する
2. ローカル品質ゲートを通し、PRで `main` へマージする
3. 関連GitHub Issuesが閉じていることを確認し、未完了ならリリース前に閉じる
4. マージ済みコミットからGitHub Releaseを作成する

```bash
gh issue close <issue-number>
gh release create v<version> --title "v<version>" --notes "<変更内容>"
```

純ドキュメント更新は通常、単独リリースを行わず次回リリースへ含める。最終判断はステアリングの振り返りで記録する。

---

## README.mdの管理

READMEは利用者向けマニュアルである。次の場合は同じ作業で更新する。

- コマンドやオプションを追加・変更・削除した
- インストール・アンインストール方法を変更した
- 利用者が見るステータス遷移や保存形式を変更した
- MCPツールの公開契約や設定方法を変更した

内部リファクタリング、開発専用手順、利用者の操作に影響しない修正では原則として更新しない。

---

## 実装前・PR前チェックリスト

### 実装前

- [ ] `AGENTS.md` と使用ハーネスのアダプタを確認した
- [ ] 関連Issueと永続ドキュメントを確認した
- [ ] 既存の類似実装と配置規則を確認した
- [ ] steeringの要求・設計・タスクリストが作業内容と一致している

### PR前

- [ ] tasklistの実装・検証・振り返りが完了している
- [ ] 変更に対応するテストと文書を更新した
- [ ] `AppError`、型注釈、レイヤー依存の規則を守っている
- [ ] 不要なデバッグ出力、コメントアウト、秘密情報が残っていない
- [ ] 対象steeringを明示したローカル品質ゲートが成功している
- [ ] PR本文に検証結果、受け入れ判定、関連Issueを記載した

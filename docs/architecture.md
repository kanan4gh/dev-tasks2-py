# 技術仕様書 (Architecture Design Document)

## テクノロジースタック

### 言語・ランタイム

| 技術 | バージョン |
|------|-----------|
| Node.js | v18以上（開発環境: v24.11.0） |
| TypeScript | 5.x |
| npm | 11.x |

**選定理由**:

- **Node.js v20以上** — v18 は EOL のため v20 LTS 以上を動作保証最小バージョンとする（開発環境: v24.11.0）。非同期 I/O に優れ、Git・ファイルシステム操作を伴う CLI に適する。v18 以上では標準 `fetch` API が使用可能なため、追加 HTTP ライブラリ不要。
- **TypeScript 5.x** — 静的型付けによりコンパイル時にバグを検出。`Task` / `Config` 等の型定義を複数コンポーネント間で共有でき、保守性が高い。IDE 補完による開発効率向上。
- **npm 11.x** — Node.js v24.11.0 に標準搭載。`package-lock.json` による依存関係の厳密な管理が可能。

---

### フレームワーク・ライブラリ（本番依存）

| 技術 | バージョン | 用途 | 選定理由 |
|------|-----------|------|----------|
| commander | ^12.0.0 | CLI フレームワーク | 学習コストが低く、サブコマンド・オプション解析が十分。Commander.js はデファクトスタンダード。 |
| simple-git | ^3.0.0 | Git 操作 | Node.js から Git コマンドを安全に呼び出せる抽象化ライブラリ。シェルコマンド文字列結合を避けることでインジェクションリスクを排除。 |
| chalk | ^5.0.0 | ターミナルカラー出力 | ステータス・優先度の色分けに使用。ES Modules 対応の v5 系を採用。 |
| cli-table3 | ^0.6.0 | テーブル表示 | `task list` のボーダー付きテーブルを簡潔に実装できる。 |
| inquirer | ^9.0.0 | 対話型プロンプト | 削除確認・フックインストール確認などの `y/N` プロンプトに使用。 |
| (標準 fetch) | — | GitHub API 通信 | Node.js v20 以上で標準搭載。`node-fetch` は追加しない。 |

### 開発ツール

| 技術 | バージョン | 用途 | 選定理由 |
|------|-----------|------|----------|
| Vitest | ^2.0.0 | テストフレームワーク | TypeScript ネイティブ対応で設定が少ない。Jest 互換 API でエコシステムが活用できる。 |
| ESLint | ^9.0.0 | 静的解析 | プロジェクト標準のリンター。コードスタイルとバグの早期検出。 |
| Prettier | ^3.2.0 | フォーマッター | 自動整形によりコードスタイルを統一。 |
| husky | ^9.0.0 | Git フック管理 | コミット前のリント・テスト実行を強制。プロジェクトに既存導入済み。 |
| lint-staged | ^15.2.0 | ステージ済みファイルへのリント適用 | husky と連携し、差分ファイルのみを高速にリント。 |

---

## アーキテクチャパターン

### Clean Architecture とは

Robert C. Martin（Uncle Bob）が提唱したソフトウェア設計の考え方。**「変わりやすいもの」と「変わりにくいもの」を分離し、依存の方向を制御する**ことを核心とする。

```
         外側（変わりやすい）
  ┌─────────────────────┐
  │  UI / Framework     │
  │  ┌───────────────┐  │
  │  │  Use Cases    │  │
  │  │  ┌─────────┐  │  │
  │  │  │ Domain  │  │  │  ← 内側（変わりにくい）
  │  │  └─────────┘  │  │
  │  └───────────────┘  │
  └─────────────────────┘
```

**依存は必ず外→内の方向のみ。内側は外側を知らない。**

| 変わりやすい（外側） | 変わりにくい（内側） |
|---|---|
| ファイル保存 → SQLite 移行 | タスクのステータス遷移ルール |
| CLI → Web UI への変更 | 「in_progress は completed になれる」 |
| GitHub → GitLab 移行 | タスクの優先度の概念 |

#### なぜ Clean Architecture を採用するか

- **テスタビリティ**: 内側のロジックは外側（ファイルシステム・CLI）に依存しないため、単体テストが書きやすい
- **差し替え容易性**: `FileStorage` を `SQLiteStorage` に変えても、内側のビジネスロジックは無変更
- **変更の局所化**: UI や永続化手段が変わっても、ドメインロジックへの影響がない

#### 依存性逆転の原則（DIP）

具体的な実装ではなく**インターフェースに依存する**ことで、依存の方向を逆転させる。

```typescript
// ❌ Use Case が具体実装に依存（変更に弱い）
class OnboardUseCase {
  execute() {
    const storage = new FileStorage(path); // ← 具体実装を直接知っている
  }
}

// ✅ Use Case はインターフェースにのみ依存（差し替え自由）
interface IStorage {
  load(): Task[];
  save(tasks: Task[]): void;
}

class OnboardUseCase {
  constructor(private storage: IStorage) {} // ← 抽象に依存
}

// 外側から具体実装を注入する
new OnboardUseCase(new FileStorage(path));
new OnboardUseCase(new SQLiteStorage(db));  // 差し替え自由
```

本プロジェクトでは `IStorage` インターフェースを `src/types/index.ts` に定義済み。将来の SQLite 移行・テスト時のモック差し替えを意識した設計。

---

### ドメイン駆動設計（DDD）と Clean Architecture の関係

DDD と Clean Architecture は**補完関係**にあり、競合しない。

| | DDD | Clean Architecture |
|---|---|---|
| **提唱者** | Eric Evans（2003年） | Robert C. Martin（2012年） |
| **問う問い** | 「何を作るか」 | 「どう構造化するか」 |
| **関心事** | ビジネスの複雑さをコードで表現する | 依存の方向を制御して変更に強くする |

DDD が「内側の世界（ドメイン）」を豊かにし、Clean Architecture が「層の境界と依存の方向」を定める。

#### DDD の核心概念

**ユビキタス言語** — ビジネス専門家と開発者が同じ言葉を使う。TaskCLI では `docs/glossary.md` がこれに相当する。

**境界づけられたコンテキスト（Bounded Context）** — ドメインを意味的な境界で分割する。

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ タスク管理   │  │ 毎日やること │  │ Git 連携    │
│ TaskManager │  │ DailyManager│  │ GitService  │
└─────────────┘  └─────────────┘  └─────────────┘
```

**エンティティと値オブジェクト** — ドメインモデルの分類。

| 種類 | 特徴 | TaskCLI の例 |
|---|---|---|
| エンティティ | ID で同一性を判断する | `Task`（id で識別） |
| 値オブジェクト | 値で同一性を判断する | `TaskStatus`、`TaskPriority` |

#### Clean Architecture の層に DDD を当てはめると

```
┌─────────────────────────────────────┐
│  CLI 層（Interface Adapter）         │
├─────────────────────────────────────┤
│  ユースケース層（Application Service）│ ← DDD の「アプリケーション層」
├─────────────────────────────────────┤
│  サービス層（Domain Service）         │ ← DDD の「ドメイン層」
│  TaskManager / DailyManager         │   エンティティ・ビジネスルールが住む
├─────────────────────────────────────┤
│  ストレージ層（Infrastructure）       │ ← DDD の「インフラ層」
└─────────────────────────────────────┘
```

#### TaskCLI における DDD の実践状況

| DDD の概念 | 実践状況 |
|---|---|
| ユビキタス言語 | `docs/glossary.md` で定義済み ✅ |
| 境界づけられたコンテキスト | `TaskManager` / `DailyManager` で分離済み ✅ |
| エンティティ | `Task` 型で定義済み ✅ |
| 値オブジェクト | `TaskStatus` 等は型のみ、独立したクラスではない △ |
| ドメインイベント・集約ルート | 未実装（現規模では不要） — |

ドメインイベントや集約ルートは大規模システム向けの概念であり、TaskCLI の現規模では導入しない。

---

### Clean Architecture に基づくレイヤー構成

本プロジェクトは Clean Architecture の考え方に基づき、以下の4層で構成する。

```
┌───────────────────────────────┐
│   CLI レイヤー                 │ ← 入力受付・バリデーション・結果表示
│   src/cli/                    │   Commander.js + Renderer
│   （Interface Adapter）        │
├───────────────────────────────┤
│   ユースケース層                │ ← ユースケース主導の複数サービス調整
│   src/usecases/               │   （オーケストレーター）
│   （Application Service）      │
├───────────────────────────────┤
│   サービスレイヤー               │ ← 個別ドメインロジック
│   src/services/               │   TaskManager / GlobalConfigService
│   （Domain Service）           │   DailyManager 等
├───────────────────────────────┤
│   ストレージレイヤー             │ ← データ永続化
│   src/storage/                │   FileStorage / GlobalConfigStorage
│   （Infrastructure）           │   DailyStorage 等
└───────────────────────────────┘
         ↓ 外部依存
┌──────────────────┬──────────────────────┐
│ ~/.task/ (FS)    │ GitHub REST API（P1） │
└──────────────────┴──────────────────────┘
```

#### ユースケース層とサービスレイヤーの違い

| | ユースケース層 | サービスレイヤー |
|---|---|---|
| 役割 | ユーザーの意図を実現するための複数サービスの調整 | 個別ドメインの CRUD・状態管理 |
| 依存 | サービスレイヤーを横断的に呼び出す | ストレージレイヤーのみ |
| 例 | `OnboardUseCase`（タスク・ルーティーン・設定を集約） | `TaskManager`、`DailyManager` |

ユースケース層はレイヤの「段階的な抽象化」ではなく、ユースケースごとのオーケストレーターとして機能する。

#### CLIレイヤー（`src/cli/`）
- **責務**: コマンド解析・引数バリデーション・整形表示
- **許可される操作**: ユースケース層またはサービスレイヤーの呼び出し
- **禁止される操作**: ストレージレイヤーへの直接アクセス・ビジネスロジックの実装

#### ユースケース層（`src/usecases/`）
- **責務**: 複数のサービスを組み合わせてユースケースを実現する
- **許可される操作**: サービスレイヤーの呼び出し・ストレージ生成の委譲
- **禁止される操作**: ターミナル出力・CLIレイヤーへの依存
- **対象**: 複数サービスを横断する読み取り集約・複合ビジネスフロー

#### サービスレイヤー（`src/services/`）
- **責務**: 個別ドメインのビジネスロジック・Git/GitHub 連携・設定管理
- **許可される操作**: ストレージレイヤーの呼び出し・外部 API の呼び出し
- **禁止される操作**: CLIレイヤーへの依存・ターミナル出力

#### ストレージレイヤー（`src/storage/`）
- **責務**: ファイルシステムへのデータ読み書き・バックアップ
- **許可される操作**: ファイルシステム操作
- **禁止される操作**: ビジネスロジックの実装

### ディレクトリ構造

```
src/
├── cli/
│   ├── index.ts               # エントリーポイント・Commander.js セットアップ
│   ├── commands/              # サブコマンド定義（add.ts / list.ts / project.ts ...）
│   └── Renderer.ts            # ターミナル表示（テーブル・カラー）
├── usecases/                  # ユースケース層（複数サービス横断の調整）
├── services/
│   ├── TaskManager.ts         # タスク CRUD・ステータス管理
│   ├── GlobalConfigService.ts # グローバル設定管理（activeProject 等）
│   ├── DailyManager.ts        # ルーティーン管理・統計計算
│   ├── GitService.ts          # ブランチ操作・コミットフック（P1）
│   ├── GitHubService.ts       # Issues 同期・PR 作成（P1）
│   └── ConfigService.ts       # プロジェクト別設定の読み書き・バリデーション（P1）
├── storage/
│   ├── FileStorage.ts         # tasks.json の読み書き・バックアップ
│   ├── GlobalConfigStorage.ts # ~/.task/config.json の読み書き
│   ├── DailyStorage.ts        # routines.json / log.json の読み書き
│   └── ConfigStorage.ts       # projects/<name>/config.json の読み書き（P1）
├── types/
│   └── index.ts               # Task / GlobalConfig / AppError 等の型定義
└── utils/
    └── slug.ts                # ブランチ名スラッグ変換ユーティリティ（P1）
```

---

## データ永続化戦略

### ストレージ方式

| データ種別 | ストレージ | フォーマット | 理由 |
|-----------|----------|-------------|------|
| グローバル設定 | `~/.task/config.json` | JSON オブジェクト | どのディレクトリからでも参照できるグローバル配置。activeProject の管理に使用 |
| タスクデータ | `~/.task/projects/<name>/tasks.json` または `~/.task/inbox/tasks.json` | JSON 配列 | 特別なソフトウェア不要・MVP では十分なパフォーマンス |
| ルーティーン定義 | `~/.task/daily/routines.json` | JSON 配列 | プロジェクト非依存のグローバルルーティーン管理 |
| ルーティーン実績ログ | `~/.task/daily/log.json` | JSON 配列（DailyLog[]） | 直近30日分の日別 done/pending 実績。30日超の古いログは自動削除 |
| プロジェクト別設定（P1） | `~/.task/projects/<name>/config.json` | JSON オブジェクト | パーミッション `600` で GitHub Token を保護 |
| 作業中タスク ID（P1） | Git リポジトリルートの `.taskcli-current` | プレーンテキスト | Git フック（シェルスクリプト）から読み取るため最小形式。`task start` で書き込み、`task done` で削除 |

**保存パス**:
```
~/.task/
├── config.json                    # グローバル設定（パーミッション: 644）
├── daily/
│   ├── routines.json              # ルーティーン定義（パーミッション: 644）
│   └── log.json                   # 日別 done/pending 実績（最大30日分、パーミッション: 644）
├── inbox/
│   ├── tasks.json                 # Inbox タスクデータ（パーミッション: 644）
│   └── tasks.json.bak             # 書き込み中のみ存在するバックアップ
└── projects/
    └── <name>/
        ├── tasks.json             # タスクデータ（パーミッション: 644）
        ├── tasks.json.bak         # 書き込み中のみ存在するバックアップ
        └── config.json            # プロジェクト別設定（パーミッション: 600、P1）

<Git リポジトリルート>/
└── .taskcli-current               # 作業中タスク ID（P1、.gitignore 追加推奨）
```

### バックアップ戦略

- **タイミング**: `FileStorage.save()` を呼ぶたびに書き込み前に `.bak` を作成
- **保存先**: 対象 `tasks.json` と同じディレクトリの `tasks.json.bak`
- **世代管理**: 最新 1 世代のみ保持（常に直前の状態に復元可能）
- **復元フロー**: 書き込み失敗時は `.bak` を `tasks.json` にリネームして自動復元

### 将来の移行パス（SQLite）

タスク数が 10,000 件を超えパフォーマンス問題が発生した場合、`FileStorage` の実装を `SQLiteStorage` に差し替える。`TaskManager` はストレージの実装詳細に依存しないため、インターフェースを維持したまま移行が可能。

移行可能性の根拠として、以下の `IStorage` インターフェースを `src/types/index.ts` に定義する:

```typescript
// IStorage インターフェース（src/types/index.ts に定義）
interface IStorage {
  load(): Task[];
  save(tasks: Task[]): void;
  ensureDirectory(): void;
}
// FileStorage および将来の SQLiteStorage は IStorage を実装する
```

---

## パフォーマンス要件

### レスポンスタイム

| 操作 | 目標時間 | 測定環境 |
|------|---------|---------|
| ローカル操作全般（add / list / start 等） | 100ms 以内 | RAM 8GB・SSD・タスク 100 件以下 |
| `task list`（1,000 件） | 1 秒以内 | 同上 |
| GitHub API を含む操作（sync / done --pr） | タイムアウト 5 秒 | ネットワーク接続あり |

**測定方法**: `console.time` で CLI 起動から結果表示まで計測。CI で 1,000 件のダミーデータを使ったベンチマークテストを実行。

### リソース使用量

| リソース | 上限 | 理由 |
|---------|------|------|
| メモリ | 128MB | JSON 全件読み込みでも 10,000 件 ≈ 10MB 程度。Node.js ベースラインを含めて余裕を持たせる |
| 起動 CPU | バースト可（制限なし） | CLI は単発起動のため常時 CPU を消費しない |
| ディスク（~/.task/） | 50MB 以内 | 10,000 件 × 平均 1KB ≈ 10MB。.bak を含めても十分な余裕 |

---

## セキュリティアーキテクチャ

### データ保護

- **暗号化**: GitHub Token はファイルパーミッション `600` で保護。暗号化は行わない（OS のユーザー分離に委ねる）
- **アクセス制御**:
  - `~/.task/` ディレクトリ → `chmod 700`（オーナーのみアクセス可）
  - `~/.task/inbox/` および `~/.task/projects/<name>/` → `chmod 700`（親ディレクトリと同等）
  - `~/.task/config.json` → `chmod 644`（グローバル設定。機密情報を含まないため読み取り可）
  - `~/.task/projects/<name>/config.json` → `chmod 600`（GitHub Token を含むため、オーナーのみ読み書き、P1）
  - `tasks.json`（プロジェクト・Inbox 共通）→ `chmod 644`（オーナー読み書き、他は読み取り可）
- **機密情報管理**: GitHub Token はコード・Git 履歴に含まれない。データはグローバルストレージ（`~/.task/`）に保存するため、プロジェクトの `.gitignore` 設定は不要（P1 の `.taskcli-current` ファイルのみ `.gitignore` への追記を案内）。

### 入力検証

- **バリデーション対象**: タスクタイトル（長さ・空文字）、優先度・ステータスの enum 値、`dueDate` の日付フォーマット、設定キーの値（`githubOwner` のユーザー名規則等）
- **サニタイゼーション**: ブランチ名は `slug.ts` で英数字+ハイフンに正規化（非 ASCII 除去）。GitHub API パラメータは URL エンコード。
- **エラーハンドリング**: エラーメッセージには内部パスやスタックトレースを含めない。ユーザー向けに「原因」と「対処」のみ表示。

### コマンドインジェクション防止

`simple-git` の API（文字列ではなく配列でコマンド引数を渡す）を使用し、シェルへの文字列連結を行わない。

---

## スケーラビリティ設計

### データ増加への対応

- **想定データ量**: MVP では最大 10,000 件。`Array.prototype.filter` による全件操作でも数ミリ秒以内。
- **パフォーマンス劣化対策**: タスク数が増加した場合は `task archive` で完了済みタスクを `archived` ステータスに遷移し、`task list` のデフォルト表示から除外する。
- **アーカイブ戦略**: `archived` タスクは `tasks.json` 内に残存。将来的には `tasks.archive.json` への分離を検討。
- **SQLite 移行**: `FileStorage` のインターフェースを維持したまま `SQLiteStorage` に差し替え可能な設計。

### 機能拡張性

- **サービスの追加**: GitLab / Bitbucket 連携は `GitLabService` として `GitHubService` と同インターフェースで追加できる。
- **ストレージの切り替え**: `FileStorage` を `SQLiteStorage` に置き換えても `TaskManager` 側の変更は不要（インターフェースを厳守）。
- **設定のカスタマイズ**: `config.json` の `defaultBranch` で PR のベースブランチを変更可能。将来はブランチ命名規則のカスタマイズも `config.json` で対応。

---

## テスト戦略

### ユニットテスト

- **フレームワーク**: Vitest
- **対象**: `TaskManager`（CRUD・ステータス遷移）、`GlobalConfigService`（activeProject の取得・切り替え）、`GlobalConfigStorage`（config.json の読み書き・デフォルト値初期化）、`GitService`（`formatBranchName` スラッグ変換、P1）、`ConfigService`（バリデーションロジック、P1）、`Renderer`（テーブル・トリミング・カラー）、`FileStorage`（バックアップ・リストアロジック）
- **カバレッジ目標**: 全体 80% 以上・`src/services/` は 90% 以上（`vitest --coverage`）
- **モック方針**: `FileStorage` は `vi.mock` でモック化。`simple-git` は `vi.mock` でモック化。GitHub API は `fetch` のモックで代替。

### 統合テスト

- **方法**: 実ファイルシステムの一時ディレクトリを使用（`os.tmpdir()`）
- **対象**: `task add` → `task start` → `task done` の一連フロー。`FileStorage` のバックアップ復元（書き込み中断シミュレート）。

### E2Eテスト（手動）

**P0（v1.0 MVP）**:
- **環境**: 任意のディレクトリ（Git 不要）
- **シナリオ**: `task add` → `task start`（ステータス変更のみ）→ `task done` の一連フロー。Inbox/プロジェクト切り替え（`task project use` / `task inbox`）と `task move` の動作確認

**P1（v1.1）**:
- **環境**: ローカル Git リポジトリあり・なしの両環境
- **シナリオ**: `task start` でブランチ自動作成 → `git commit` でタグ自動付与 → `task done --pr` で PR 作成（テスト用 GitHub リポジトリ使用）

---

## 技術的制約

### 環境要件

- **OS**: macOS 12以上・Linux (Ubuntu 22.04以上)・Windows 10以上（Git Bash 環境）
- **最小メモリ**: 512MB（Node.js 起動に必要な最低限）
- **必要ディスク容量**: 50MB（本体 + データ）
- **必要な外部依存**:
  - Node.js v20 以上（開発環境: v24.11.0）
  - Git 2.20 以上（simple-git の動作要件）
  - インターネット接続（GitHub 連携機能のみ）

### パフォーマンス制約

- GitHub API のレートリミット: 認証済みリクエストは 5,000 req/時（`task sync` の実行頻度に注意）
- `tasks.json` の全件ロード: 10,000 件を超えると読み込みに数十ミリ秒かかる可能性。100ms 制限を超える場合は SQLite 移行を検討。

### セキュリティ制約

- GitHub Token の最小スコープ: `repo`（Issues・PR 操作に必要な最低限）
- Token のログ出力禁止: エラーメッセージ・デバッグ出力に Token 値を含めない

---

## 依存関係管理

| ライブラリ | 用途 | バージョン管理方針 |
|-----------|------|-------------------|
| commander | CLI フレームワーク | `^12.0.0`（マイナーまで自動） |
| simple-git | Git 操作 | `^3.0.0`（マイナーまで自動） |
| chalk | カラー出力 | `^5.0.0`（マイナーまで自動） |
| cli-table3 | テーブル表示 | `^0.6.0`（マイナーまで自動） |
| inquirer | 対話型プロンプト | `^9.0.0`（マイナーまで自動） |
| typescript | TypeScript コンパイラ | `~5.3.0`（パッチのみ自動） |
| vitest | テストフレームワーク | `^2.0.0`（マイナーまで自動） |
| eslint | 静的解析 | `^9.0.0`（マイナーまで自動） |
| prettier | フォーマッター | `^3.2.0`（マイナーまで自動） |
| husky | Git フック管理 | `^9.0.0`（マイナーまで自動） |
| lint-staged | ステージファイルへのリント | `^15.2.0`（マイナーまで自動） |

**方針**:
- 本番依存はマイナーバージョンまで自動（`^`）。メジャーバージョンアップは手動で検証してから適用。
- `typescript` はパッチのみ自動（`~`）。コンパイラの変更はビルドに影響するため慎重に。
- `package-lock.json` を Git 管理し、CI では `npm ci` で厳密に再現可能なビルドを保証。

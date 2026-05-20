# 開発ガイドライン (Development Guidelines)

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | インストール方法 |
|--------|-----------|-----------------|
| Node.js | v18以上（開発環境: v24.11.0） | devcontainer で自動セットアップ |
| npm | 11.x | Node.js に同梱 |
| Git | 2.20 以上 | OS 標準または `apt install git` |
| Docker | 最新安定版 | Dev Container 利用時に必要 |

### セットアップ手順

```bash
# 1. リポジトリのクローン
git clone <リポジトリURL> dev-tasks2
cd dev-tasks2

# 2. Dev Container で開く（推奨）
# VS Code で「Reopen in Container」を選択
# → Node.js のインストール・npm install・Claude Code のインストールが自動実行される

# 3. 手動セットアップの場合
npm install            # 依存関係のインストール（husky も自動セットアップ）

# 4. 動作確認
npm run typecheck      # TypeScript 型チェック
npm test               # テスト実行
npm run build          # ビルド確認
```

### npm スクリプト一覧

| コマンド | 用途 |
|---------|------|
| `npm run build` | TypeScript をコンパイルして `dist/` に出力 |
| `npm run dev` | ウォッチモードでビルド |
| `npm run lint` | ESLint でコード検査 |
| `npm run format` | Prettier でコード整形 |
| `npm run typecheck` | 型チェックのみ（ビルドなし） |
| `npm test` | テストを一度だけ実行 |
| `npm run test:watch` | テストをウォッチモードで実行 |
| `npm run test:coverage` | カバレッジレポートを生成 |

---

## コーディング規約

### 命名規則

#### 変数・関数

```typescript
// ✅ 良い例
const taskList = await taskManager.listTasks();
function formatBranchName(taskId: number, title: string): string { }
const isGitRepository = await gitService.isGitRepository();

// ❌ 悪い例
const data = await tm.list();
function fmt(id: number, t: string): string { }
const flag = await gs.isGit();
```

**原則**:
- 変数: `camelCase`、名詞または名詞句
- 関数: `camelCase`、動詞で始める
- 定数: `UPPER_SNAKE_CASE`
- Boolean: `is`, `has`, `should`, `can` で始める

#### クラス・インターフェース

```typescript
// クラス: PascalCase + 役割接尾辞
class TaskManager { }
class GitService { }
class FileStorage { }
class Renderer { }

// インターフェース: PascalCase（I 接頭辞なし）
interface Task { }
interface Config { }
interface TaskFilter { }

// 型エイリアス: PascalCase
type TaskStatus = 'open' | 'in_progress' | 'completed' | 'archived';
type TaskPriority = 'high' | 'medium' | 'low';
```

#### ファイル・ディレクトリ

```
// クラスファイル: PascalCase
TaskManager.ts / GitService.ts / FileStorage.ts

// コマンドファイル: camelCase（コマンド名と一致）
add.ts / list.ts / done.ts

// ユーティリティ関数ファイル: camelCase
slug.ts

// テストファイル: tests/unit/<レイヤー>/[対象名].test.ts
tests/unit/services/TaskManager.test.ts
tests/unit/utils/slug.test.ts
```

---

### 型定義

**原則: `any` の使用禁止**

```typescript
// ✅ 良い例: 明示的な型を定義
function loadTasks(): Task[] { }
function saveConfig(config: Config): void { }

// ❌ 悪い例: any を使用
function loadTasks(): any { }
function saveConfig(config: any): void { }
```

**インターフェース vs 型エイリアス**:
- `interface`: 拡張可能なオブジェクト型（`Task`, `Config` 等）
- `type`: ユニオン型・プリミティブ型（`TaskStatus`, `TaskPriority` 等）

**型は `src/types/index.ts` に集約する**:
```typescript
// ✅ 良い例: types/index.ts に集約して import
import type { Task, TaskFilter } from '../types';

// ❌ 悪い例: 各ファイルで重複定義
// services/TaskManager.ts で独自に type Task = { ... } を定義
```

---

### コードフォーマット

**フォーマット設定**（`.prettierrc` で管理）:
- **インデント**: 2 スペース
- **行の最大長**: 100 文字
- **セミコロン**: あり
- **クォート**: シングルクォート

フォーマットは Prettier に任せる。コミット前に `lint-staged` が自動実行する。設定を変更する場合は `.prettierrc` を編集し、チームで合意を取ること。

---

### 関数設計

**単一責務の原則**（1 関数 = 1 つの処理）:

```typescript
// ✅ 良い例: 責務を分離
function validateTaskTitle(title: string): void {
  if (!title || title.length === 0) {
    throw new AppError('タイトルは必須です', 'タイトルが空です', '1文字以上入力してください');
  }
  if (title.length > 200) {
    throw new AppError('タイトルが長すぎます', `${title.length}文字が入力されました`, '200文字以内で入力してください');
  }
}

function createTask(input: CreateTaskInput): Task {
  validateTaskTitle(input.title);  // バリデーションは委譲
  return { id: this.nextId(), ...input, status: 'open', createdAt: new Date().toISOString() };
}

// ❌ 悪い例: 1 関数に複数の責務
function createTask(input: CreateTaskInput): Task {
  if (!input.title) throw new Error('invalid');  // バリデーションと生成が混在
  const id = tasks.reduce((max, t) => Math.max(max, t.id), 0) + 1;
  const task = { id, ...input };
  fs.writeFileSync('.task/tasks.json', JSON.stringify(tasks));  // 永続化まで担当
  return task;
}
```

**関数の長さの目安**:
- 20 行以内: 推奨
- 50 行以内: 許容範囲
- 50 行超: リファクタリングを検討

**パラメータが 4 つ以上になる場合はオブジェクト化する**:
```typescript
// ✅ 良い例
interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: TaskPriority;
  dueDate?: string;
}
function createTask(input: CreateTaskInput): Task { }

// ❌ 悪い例
function createTask(title: string, description: string, priority: string, dueDate: string): Task { }
```

---

### エラーハンドリング

**プロジェクト共通の `AppError` クラスを使用する**（`src/types/index.ts` 定義）:

```typescript
class AppError extends Error {
  constructor(
    message: string,           // エラー概要
    public readonly cause: string,   // 原因
    public readonly remedy: string   // 対処法
  ) {
    super(message);
  }
}
```

**表示フォーマット（Renderer が担当）**:
```
[Error] <message>
  原因: <cause>
  対処: <remedy>
```

**エラーハンドリングの原則**:

```typescript
// ✅ 良い例: 予期されるエラーは AppError でラップ
function getTask(id: number): Task {
  const task = tasks.find(t => t.id === id);
  if (!task) {
    throw new AppError(
      'タスクが見つかりません',
      `ID=${id} のタスクは存在しません`,
      'task list で有効な ID を確認してください'
    );
  }
  return task;
}

// ✅ 良い例: 予期しないエラーは上位に伝播
async function push(branch: string): Promise<void> {
  try {
    await git.push('origin', branch);
  } catch (error) {
    throw new AppError(
      'プッシュに失敗しました',
      error instanceof Error ? error.message : String(error),
      'git status を確認し、認証情報を見直してください'
    );
  }
}

// ❌ 悪い例: エラーを無視する
function getTask(id: number): Task | null {
  try {
    return tasks.find(t => t.id === id) ?? null;
  } catch {
    return null;  // エラー情報が消える
  }
}
```

---

### 非同期処理

`async/await` を使用し、Promise チェーンは使わない:

```typescript
// ✅ 良い例
async function syncWithGitHub(): Promise<SyncResult> {
  const issues = await githubService.fetchIssues();
  const localTasks = fileStorage.load();
  const result = await applyDiff(issues, localTasks);
  fileStorage.save(result.updatedTasks);
  return result.summary;
}

// ❌ 悪い例: Promise チェーン
function syncWithGitHub(): Promise<SyncResult> {
  return githubService.fetchIssues()
    .then(issues => applyDiff(issues, fileStorage.load()))
    .then(result => { fileStorage.save(result.updatedTasks); return result.summary; });
}
```

**並列実行には `Promise.all` を使用する**:

```typescript
// ✅ 良い例: 並列実行
const [tasks, config] = await Promise.all([fileStorage.load(), configStorage.load()]);

// ✅ 許容: コールバック API の Promise 化（promisify の代替）
function readFileAsync(path: string): Promise<string> {
  return new Promise((resolve, reject) => {
    fs.readFile(path, 'utf-8', (err, data) => (err ? reject(err) : resolve(data)));
  });
}
```

---

### コメント規約

**「なぜそうするか」を書く。「何をしているか」はコードから読める**:

```typescript
// ✅ 良い例: 理由を説明
// 書き込み前にバックアップを作成し、失敗時に自動復元できるようにする
fs.copyFileSync(tasksPath, backupPath);

// ✅ 良い例: 複雑なロジックを説明
// スラッグが空になる（タイトルが全角文字のみ等）場合は ID のみとする
const slug = toSlug(title);
return slug ? `feature/task-${id}-${slug}` : `feature/task-${id}`;

// ❌ 悪い例: コードの繰り返し
// バックアップパスにコピーする
fs.copyFileSync(tasksPath, backupPath);
```

**公開クラス・メソッドには TSDoc コメントを付ける**:

```typescript
/**
 * タスクを開始状態に遷移させ、Git ブランチを自動作成する
 *
 * @param id - 対象タスクの ID
 * @returns 更新後の Task オブジェクト
 * @throws {AppError} タスクが存在しない場合
 * @throws {AppError} 遷移不可能なステータスの場合（archived など）
 */
async startTask(id: number): Promise<Task> { }
```

---

## Git 運用ルール

### ブランチ戦略

**TaskCLI 開発用ブランチ構成**（シンプルな Git Flow）:

```
main（リリース済みの安定版）
└── develop（次期リリース向けの統合ブランチ）
    ├── feature/task-<id>-<slug>  ← task start で自動作成
    ├── fix/<内容>
    └── refactor/<対象>
```

**ルール**:
- `main` と `develop` への直接コミットは禁止。PR 経由でマージする
- 機能ブランチは `task start <id>` コマンドで自動作成する（手動作成も可）
- feature → develop: squash merge を推奨
- develop → main: merge commit を使用（リリース時）

---

### コミットメッセージ規約

**Conventional Commits 形式を採用**:

```
<type>(<scope>): <subject>

<body>（任意）

<footer>（任意）
```

**Type 一覧**:

| type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメント |
| `style` | フォーマット変更（動作に影響なし） |
| `refactor` | リファクタリング |
| `test` | テスト追加・修正 |
| `chore` | ビルド・依存関係・設定変更 |

**TaskCLI の自動タグ付け**:

`task start <id>` 実行後は `.git/hooks/prepare-commit-msg` フックが自動インストールされ、コミットメッセージ末尾に `[Task #<id>]` が自動付与される。

```bash
# 入力（開発者が書くメッセージ）
feat(task): タスク一覧のソート機能を追加

# コミット後の実際のメッセージ（フックが自動付与）
feat(task): タスク一覧のソート機能を追加

[Task #5]
```

**良いコミットメッセージの例**:

```
feat(cli): task list に --sort オプションを追加

--sort priority / --sort dueDate / --sort id に対応。
デフォルトは id 昇順のまま変更なし。

Closes #8
[Task #5]
```

---

### プルリクエストの作成

**PR テンプレート**（`.github/pull_request_template.md`）:

```markdown
## 変更の種類
- [ ] 新機能 (feat)
- [ ] バグ修正 (fix)
- [ ] リファクタリング (refactor)
- [ ] ドキュメント (docs)
- [ ] その他 (chore)

## 何を変更したか
[簡潔な説明]

## なぜ変更したか
[背景・理由]

## 変更内容
- [変更点1]
- [変更点2]

## テスト
- [ ] ユニットテスト追加・更新
- [ ] 統合テスト追加・更新
- [ ] 手動テスト実施
- [ ] `npm test` がパスする
- [ ] `npm run typecheck` がパスする

## 関連タスク / Issue
Closes #[番号]
```

**PR 作成前のセルフチェック**:
- [ ] `npm test` がパスする
- [ ] `npm run typecheck` がパスする
- [ ] `npm run lint` にエラーがない
- [ ] 変更ファイル数 10 以内・変更行数 300 行以内
- [ ] 不要なコメントアウトコードがない

---

## テスト戦略

### テストピラミッド

```
       /\
      /E2E\        少（手動・テスト用 GitHub リポジトリ使用）
     /------\
    / 統合   \      中（実ファイルシステムで完全フローを検証）
   /----------\
  / ユニット   \    多（モックを活用して高速実行）
 /--------------\
```

**目標比率**: ユニット 70% / 統合 20% / E2E 10%

---

### ユニットテスト

**フレームワーク**: Vitest
**カバレッジ目標**: 全体 80% 以上、`src/services/` は 90% 以上

**カバレッジの自動強制**: `vitest.config.ts` に閾値を設定し、未達時にテストを失敗させる:

```typescript
coverage: {
  thresholds: {
    global: { lines: 80 },
    'src/services/': { lines: 90 },
  }
}
```

**テスト構造（Given-When-Then パターン）**:

```typescript
describe('TaskManager', () => {
  describe('startTask', () => {
    it('open のタスクを in_progress に遷移できる', () => {
      // Given: open のタスクが存在する
      const storage = new MockFileStorage([
        { id: 1, title: 'テスト', status: 'open', ... }
      ]);
      const manager = new TaskManager(storage);

      // When: startTask を呼ぶ
      const result = manager.startTask(1);

      // Then: ステータスが in_progress になる
      expect(result.status).toBe('in_progress');
    });

    it('archived のタスクは開始できず AppError をスローする', () => {
      // Given: archived のタスクが存在する
      const storage = new MockFileStorage([
        { id: 2, title: 'アーカイブ済み', status: 'archived', ... }
      ]);
      const manager = new TaskManager(storage);

      // When/Then: startTask を呼ぶと AppError がスローされる
      expect(() => manager.startTask(2)).toThrow(AppError);
    });
  });
});
```

**モック方針**:
- `FileStorage` / `ConfigStorage` は `vi.mock` でモック化
- `simple-git` は `vi.mock` でモック化
- GitHub `fetch` は `vi.stubGlobal('fetch', ...)` でモック化
- ビジネスロジック（`TaskManager`, `GitService` 等）は実装を使用

```typescript
// モックの例
const mockStorage = {
  load: vi.fn(() => []),
  save: vi.fn(),
  ensureDirectory: vi.fn(),
};
```

---

### 統合テスト

実際の一時ディレクトリ（`os.tmpdir()`）でファイル I/O を含むフローを検証する:

```typescript
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';

describe('task-workflow', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(`${tmpdir()}/taskcli-test-`);
    process.chdir(tmpDir);
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true });
  });

  it('add → start → done の一連フローが正常に動作する', () => {
    const manager = new TaskManager(new FileStorage(tmpDir));

    const task = manager.createTask({ title: 'テストタスク' });
    expect(task.status).toBe('open');

    const started = manager.startTask(task.id);
    expect(started.status).toBe('in_progress');

    const done = manager.completeTask(task.id);
    expect(done.status).toBe('completed');
  });
});
```

---

### E2Eテスト（手動）

以下のシナリオを手動で確認する:

| シナリオ | 実行コマンド | 確認コマンド | 期待される結果 |
|---------|------------|------------|--------------|
| Git リポジトリありの環境で `task start` | `task start 1` | `git branch --show-current` | `feature/task-1-<slug>` が表示される |
| Git リポジトリなしの環境で `task start` | `cd /tmp/no-git && task start 1` | 標準出力を目視確認 | `[Warning] Gitリポジトリが見つかりません。` が表示され終了コード 0 |
| `git commit` 後（フックインストール済み） | `git commit -m "feat: テスト"` | `git log --oneline -1` | コミットメッセージ末尾に `[Task #<id>]` が付与されている |
| `task done --pr` | `task done 1 --pr` | GitHub リポジトリの PR 一覧 | テスト用リポジトリに PR が正しく作成される |

---

## コードレビュー基準

### レビューのポイント

**機能性**:
- [ ] 機能設計書の受け入れ条件を満たしているか
- [ ] ステータス遷移ルールが守られているか
- [ ] エッジケース（ID 不存在・不正ステータス遷移等）が考慮されているか

**可読性**:
- [ ] 命名がガイドラインに沿っているか
- [ ] 複雑なロジックにコメントがあるか
- [ ] 関数が単一責務を持っているか

**レイヤー規約**:
- [ ] CLI レイヤーがビジネスロジックを持っていないか
- [ ] Storage レイヤーがサービスに依存していないか
- [ ] 循環依存が発生していないか

**セキュリティ**:
- [ ] 機密情報（Token 等）がログに出力されていないか
- [ ] 入力バリデーションが実装されているか
- [ ] simple-git の API を通じて Git 操作しているか（シェル文字列結合なし）

**テスト**:
- [ ] ユニットテストが追加されているか
- [ ] 異常系（AppError）のテストがあるか

### レビューコメントの書き方

優先度を明示して、建設的なフィードバックを行う:

```markdown
[必須] この実装だと archived → in_progress に遷移できてしまいます。
       ステータス遷移ルール（functional-design.md 参照）に合わせて
       遷移前チェックを追加してください。

[推奨] `tasks.find()` を毎回呼ぶのではなく、`getTask()` を使うと
       「タスクが見つからない」エラーハンドリングを一元化できます。

[提案] この関数は 60 行を超えているので、バリデーション部分を
       別関数に抽出するとテストしやすくなります。

[質問] `.current-task` ファイルを削除するタイミングはここで良いですか？
       `task archive` の場合も削除が必要では？
```

---

## 品質自動化（CI/CD）

### Pre-commit フック（Husky + lint-staged）

コミット前に自動で以下が実行される（プロジェクトに既設定）:

```bash
# .husky/pre-commit
npx lint-staged
npm run typecheck
```

```json
// package.json（lint-staged の設定）
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

### GitHub Actions（必須）

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
```

---

## バージョニング規則

[Semantic Versioning 2.0.0](https://semver.org/lang/ja/) に従う。バージョン形式は `MAJOR.MINOR.PATCH`。

### バージョンの上げ方

| 種別 | 条件 | 例 |
|------|------|-----|
| `MAJOR` | 後方互換性のない破壊的変更（コマンド廃止・データ形式の非互換変更など） | `1.0.0` → `2.0.0` |
| `MINOR` | 後方互換性を保った新機能追加 | `1.0.0` → `1.1.0` |
| `PATCH` | 後方互換性を保ったバグ修正・軽微な改善 | `1.0.0` → `1.0.1` |

### 具体例

```
# PATCH: バグ修正
task delete のエラーメッセージが表示されない → 1.0.0 → 1.0.1

# MINOR: 新機能追加
task list --all を追加             → 1.0.0 → 1.1.0
task --version にアップデート通知  → 1.1.0 → 1.2.0

# MAJOR: 破壊的変更
~/.task/ のデータ形式を変更（移行ツールなし） → 1.x.x → 2.0.0
```

### リリース判断基準

**判断主体**: プロジェクトオーナー。ステアリングの振り返り時に Claude が検討・提案し、オーナーが最終決定する。

#### 通常フロー（MINOR / MAJOR）

ステアリングの振り返りフェーズで以下を評価し、リリース可否を判断する:

| 評価項目 | 内容 |
|---|---|
| 全テスト通過 | `npm test` がパスしている |
| ビルド成功 | `npm run build` が成功している |
| 変更内容の記載準備 | リリースノートに記載すべき変更内容が整理されている |

上記をすべて満たしており、かつ今回の変更がユーザーにとって価値のあるまとまりになっていればリリースを提案する。

#### 例外フロー（PATCH: 重大バグ修正）

データ破損・コマンドのクラッシュなど重大なバグが発見された場合は、ステアリングの振り返りを待たず即時リリースを判断する。

軽度なバグ（表示ずれ・エラーメッセージの誤りなど）は MINOR リリースのバッチに含めて対応する。

#### リリース後のユーザーへの周知

`task --version` 実行時に GitHub Releases API から最新バージョンを取得し、新しいバージョンが存在する場合はアップデート通知を自動表示する機能が実装済みである。リリース後の個別周知は不要で、ユーザーが次回コマンド実行時に自然に通知を受け取る。

### リリース手順

**マージ前:**

1. README.md がリリース内容を反映していることを確認する
2. `package.json` の `version` を更新する
3. `src/cli/index.ts` の `.version()` を同じバージョンに更新する
4. `main` ブランチにマージする

**マージ後（必須）:**

5. 関連する GitHub Issues がクローズされていることを確認する
   - クローズされていない場合は `gh issue close <番号> --comment "<理由>"` でクローズする
6. GitHub Releases でタグ（例: `v1.1.0`）を作成し、変更内容を記載する
   - `gh release create v1.1.0 --title "v1.1.0" --notes "<変更内容>"` で作成する

---

## README.md の管理

README.md はユーザーマニュアルとして位置づける（詳細は `repository-structure.md` を参照）。

### 更新が必要なタイミング

| 変更内容 | README.md 更新 |
|---|---|
| コマンドの追加・削除 | **必須** |
| オプションの追加・変更・削除 | **必須** |
| インストール手順の変更 | **必須** |
| ステータス遷移・データ構造の変更 | **必須** |
| 内部実装の変更（ユーザー操作に影響しない） | 不要 |
| バグ修正（コマンドの動作は変わらない） | 不要 |

### 更新のタイミング

ステアリングの実装フェーズ中に行う（リリース前に完了させること）。

リリース手順の実行前に「README.md がリリース内容を反映しているか」を確認する。

---

## 実装前チェックリスト

新機能・修正を実装する前に確認する:

- [ ] 関連する PRD の受け入れ条件を確認した
- [ ] 機能設計書のシーケンス図・エラー仕様を確認した
- [ ] 既存の類似実装を検索した（`grep` で重複を避ける）
- [ ] レイヤーの依存ルールを把握した

実装後・PR 作成前に確認する:

- [ ] `npm run typecheck` がパスする
- [ ] `npm test` がパスする（カバレッジ 80% 以上）
- [ ] `npm run lint` にエラーがない
- [ ] `AppError` を使ったエラーハンドリングが実装されている
- [ ] ストレージ直接アクセスが CLI レイヤーにないこと
- [ ] コメントアウトコード・デバッグ用 `console.log` が残っていないこと

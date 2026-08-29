# AI-DLC Workflows 2.0とuroborosの対比

_2026-07-24 壁打ちのまとめ_

## この文書の位置づけ

AI-DLC Workflows 2.0の記事を起点に、uroborosのSDDプロセスとAI-DLCを同じ粒度・文脈で比較した議論を整理する。

現時点では仕様や実装方針を確定する文書ではない。確認済みの事実、現時点の仮説、今後議論すべき論点を記録する。

## 参照

- [AI-DLC Workflows 2.0とは何か、そしてどう実装されているか](https://zenn.dev/aws_japan/articles/aidlc-workflows-v2-harness-engineering)
- [awslabs/aidlc-workflows v2: 5フェーズのステージ仕様](https://github.com/awslabs/aidlc-workflows/tree/v2/docs/reference/04-stages)
- [platform-harness PR #25: SDD軽量パスと4段検証の増分化](https://github.com/kanan4gh/platform-harness/pull/25)
- [platform-harness PR #27: tasklistのC3循環回避](https://github.com/kanan4gh/platform-harness/pull/27)
- `docs/procedures/add-feature.md`
- `docs/procedures/steering.md`

---

## AI-DLC Workflows 2.0の概要

AI-DLC Workflows 2.0は、AIによるソフトウェア開発を5フェーズ32ステージとして定義している。

1. Initialization: 3ステージ
2. Ideation: 7ステージ
3. Inception: 8ステージ
4. Construction: 7ステージ
5. Operation: 7ステージ

重要なのは32という数ではなく、以下の制御モデルである。

- Intentの種類に応じて実行するステージを選択する
- scope、depth、test strategyによって実行の深さを変える
- 次に実行するステージは決定論的なエンジンが判断する
- LLMはエンジンのdirectiveに従ってステージを実行する
- 人間は承認ゲートで重要な判断を行う
- ステージや成果物の依存関係をグラフとして管理する

## GreenfieldとBrownfield

### Greenfield

既存のコードや仕様に縛られず、更地から新しく作る開発。

例:

- 新しいリポジトリでサービスを作る
- 技術スタックやアーキテクチャも新しく決める
- 新規プロダクトのMVPを作る

着想整理、要求定義、技術選定、アーキテクチャ設計が必要になる一方、既存コードのReverse Engineeringは不要である。

### Brownfield

既存のシステム、コード、仕様、運用制約の上で改修・増築する開発。

例:

- 既存機能の変更
- バグ修正
- 既存サービスへのAPI追加
- レガシーシステムの段階的モダナイズ

実装前に、既存コード、依存関係、テスト、設計判断、運用制約を理解する必要がある。

uroborosの現在の開発は、既存の正典、手順、アダプタ、テスト、品質ゲートとの整合が必要なため、基本的にBrownfieldである。ただし、既存プロジェクト内に独立した新規コンポーネントを作る場合など、部分的にGreenfieldとなることはある。

適応型プロセスを考える際は、Greenfield/Brownfieldの二択だけでなく、変更の性質を次のように捉える方が実用的である。

- 新規独立
- 既存拡張
- 既存変更
- 修復
- 移行

---

## 5フェーズ32ステージとuroborosの対応

対応の強さ:

- `◎`: 直接対応する
- `○`: 概ね対応する
- `△`: 一部のみ対応する
- `—`: 標準フローに存在しない

### 0. Initialization

| AI-DLC | uroborosで近いもの | 対応 |
|---|---|---:|
| 0.1 Workspace Scaffold | Issue確認、feature branch、`.steering/`ディレクトリ作成 | ○ |
| 0.2 Workspace Detection | `AGENTS.md`、永続docs、既存コードの調査 | ○ |
| 0.3 State Initialization | `requirements.md`、`design.md`、`tasklist.md`の作成 | △ |

AI-DLCでは、初期化は決定論的ツールによって行われ、greenfield/brownfield、scope、depth、実行対象ステージが状態ファイルに設定される。

uroborosではtasklistが作業状態を表すが、「今回どのプロセスを通るか」を表す機械可読なステージグラフはない。エージェントが固定された`add-feature`手順を読み、内容を解釈して進める。

### 1. Ideation

| AI-DLC | uroborosで近いもの | 対応 |
|---|---|---:|
| 1.1 Intent Capture & Framing | ユーザー依頼、Issue、requirementsの背景・ユースケース軸 | ◎ |
| 1.2 Market Research | `docs/ideas/`での任意調査 | — |
| 1.3 Feasibility & Constraints | 既存パターン調査、designの制約・リスク検討 | △ |
| 1.4 Scope Definition | requirementsの実装対象、受け入れ条件、スコープ外 | ◎ |
| 1.5 Team Formation | エージェント委譲、使用ハーネスの選択 | △ |
| 1.6 Rough Mockups | 標準手順なし | — |
| 1.7 Approval & Handoff | `add-feature`ステップ4.5の計画承認 | ◎ |

uroborosは通常、ユーザーから機能追加や変更の依頼を受けた時点から始まる。Ideation前半を外部で済ませたものとして扱っている。

不足している可能性がある要素:

- 市場・競合調査
- build / buy / partner判断
- リスク、前提、課題、依存関係の明示
- ラフモックによる早期の価値検証
- 人間チームの編成・キャパシティ設計

一方、スコープ固定と計画承認は強く実装されている。

### 2. Inception

| AI-DLC | uroborosで近いもの | 対応 |
|---|---|---:|
| 2.1 Reverse Engineering | プロジェクト理解、既存パターン調査 | ◎ |
| 2.2 Practices Discovery | AGENTS、development-guidelines、既存規約の確認 | ◎ |
| 2.3 Requirements Analysis | `requirements.md` | ◎ |
| 2.4 User Stories | requirementsのユースケース軸・機能要件 | ○ |
| 2.5 Refined Mockups | 標準手順なし | — |
| 2.6 Application Design | `design.md`のアーキテクチャ、コンポーネント、データフロー | ◎ |
| 2.7 Units Generation | `tasklist.md`への実装単位分解 | ◎ |
| 2.8 Delivery Planning | タスク順序、検証方針、ブランチ・PR計画 | ◎ |

ここが最も一致している。

AI-DLCのInception成果物を、uroborosでは主に3ファイルへ縮約している。

- `requirements.md`: Requirements AnalysisとUser Stories
- `design.md`: Application Design
- `tasklist.md`: Units GenerationとDelivery Planning

さらに、Reverse EngineeringとPractices Discoveryが作成前の必須調査として存在する。

したがって、uroborosのステアリングは「AI-DLC Inceptionの軽量な三文書版」と見ることができる。

主な違い:

- AI-DLCは各ステージを独立した成果物と承認ゲートで管理する
- uroborosは三文書をまとめて作成し、計画全体を1回承認する
- AI-DLCはユーザーストーリーやモックを独立した設計入力として扱う
- uroborosのユースケースは要求の軸であり、詳細なストーリー分解までは必須ではない

### 3. Construction

| AI-DLC | uroborosで近いもの | 対応 |
|---|---|---:|
| 3.1 Functional Design | `design.md`、必要に応じた`docs/functional-design.md`更新 | ○ |
| 3.2 NFR Requirements | 成功指標、セキュリティ・性能要件 | △ |
| 3.3 NFR Design | designのセキュリティ・性能・エラー処理 | △ |
| 3.4 Infrastructure Design | designのアーキテクチャ、CDK/SAM関連タスク | ○ |
| 3.5 Code Generation | tasklist完全消化ループ、steeringモード2 | ◎ |
| 3.6 Build and Test | 4段検証 | ◎ |
| 3.7 CI Pipeline | ローカル品質ゲート、任意のGitHub Actions | △ |

実装と検証も強く対応している。

uroborosの4段検証:

1. 静的検証
2. 実挙動検証
3. コードレビュー
4. スペック準拠検証

AI-DLCのBuild and Testがビルド・テスト実行と失敗診断を中心とするのに対し、uroborosは実際の振る舞い、レビューの独立性、要求・設計との整合まで明示している。

一方、NFRは独立した要求・設計ステージではなく、designテンプレートのセキュリティ・性能欄に集約されている。大規模な変更では検討が浅くなる可能性がある。

また、uroborosはFunctional Designを実装前の`design.md`に寄せる。AI-DLCはUnit of Workごとに、必要な場合だけConstruction中に深掘りする。

### 4. Operation

| AI-DLC | uroborosで近いもの | 対応 |
|---|---|---:|
| 4.1 Deployment Pipeline | 標準フローなし | — |
| 4.2 Environment Provisioning | CDK/SAMを使う個別タスクとしては実施可能 | — |
| 4.3 Deployment Execution | PR後のリリース手順 | △ |
| 4.4 Observability Setup | 標準フローなし | — |
| 4.5 Incident Response | 標準フローなし | — |
| 4.6 Performance Validation | 4段検証で明示した場合のみ | △ |
| 4.7 Feedback & Optimization | 振り返り、distill、platform-harnessへの環流 | △ |

uroborosはPR作成を完了地点とし、マージはユーザー判断、リリースは別操作として扱う。デプロイ後の監視、SLO、インシデント対応、コスト最適化、ドリフト検査までを一つの作業単位として追跡しない。

ただし、Feedback & Optimizationに対しては独自の強みがある。

- 作業ごとの振り返り
- 複数作業からの`distill`
- プロジェクト知見と正典候補の分類
- platform-harnessへの環流
- release済み正典の派生プロジェクトへの再同期

AI-DLCはプロダクトの運用データを次のIdeationへ戻す。uroborosは開発プロセスの学びを正典へ戻す。両者は異なるフィードバックループである。

---

## 現時点の位置づけ

uroborosは、AI-DLCの5フェーズ全体に対応する仕組みではない。

> InceptionとConstructionに特化し、GitHub運用、強い検証、正典への環流を加えた固定型の軽量AI-DLCハーネス

と捉えるのが近い。

| 観点 | AI-DLC | uroboros |
|---|---|---|
| 対象範囲 | 着想から本番運用まで | 要求がある変更からPRまで |
| プロセス | 32ステージから適応的に選択 | 固定されたステップ0〜8 |
| 適応方法 | scope、depth、条件でステージを選ぶ | tasklistの中身を案件ごとに変える |
| 状態 | コンパイルされたステージグラフと状態ファイル | Markdownのtasklist |
| 承認 | 原則としてステージごと | 計画承認の1回 |
| 実装後 | デプロイ・運用まで継続 | PRで一旦終了 |
| 学習 | Spaceのmemoryへ承認済みルールを蓄積 | 振り返り、distill、正典への環流 |

## 32ステージを持つべきか

議論上の合意:

- uroborosがAI-DLCと同じ32ステージを持つ必要はない
- ステージ数を増やすこと自体を目的にしない
- AI-DLCから学ぶべきなのは、案件の性質に応じて検討の種類と深さを変える考え方である

---

## 小さな変更への対応は正典で一部解決済み

platform-harnessの直近PRで、小規模変更に対するプロセス過剰は一部解決されている。

### PR #25で導入されたもの

- 軽量パス
  - `requirements.md + tasklist.md`の2ファイル
  - `design.md`を省略可能
- 軽量パスの適用条件
  - 既存パターンの踏襲のみ
  - 新しいアーキテクチャ要素・新規依存なし
  - 変更対象が3ファイル以下（テスト除く）
  - 永続docs更新不要
  - データ形式・API契約の破壊的変更なし
- 条件を外れた場合の通常パスへの昇格
- 4段検証の縮約
- 修正後の増分再検証
- 最後の実装変更後に全体品質ゲートを1回通す安全境界

### PR #27で整理されたもの

- 最終品質ゲートとtasklist C3の自己参照
- 品質ゲートの2回実行運用
- commit・PR作成をtasklistのチェックボックスにしない規則
- 正典内での軽量パス初適用

したがって、現在の課題を「小さな変更に対して一律に重い」と置くのは正確ではない。

なお、この記述はplatform-harness正典の現状を指す。派生プロジェクトuroborosへの同期状況は別途管理する。

---

## 修正後の課題設定

現在の課題感:

> 大きな変更に対して、通常パスだけでは検討ステージが足りない可能性がある。

正典は実質的に次の二段階になっている。

```text
小変更     → 軽量パス
それ以外   → 通常パス
```

問題は「それ以外」の幅が広いことである。

- 4ファイルを変更する既存パターンの拡張
- 新しいアーキテクチャ境界の導入
- 複数システムをまたぐ移行
- 認証、データモデル、運用を同時に変える変更

これらがすべて同じ通常パスに入る。

## 仮説: 通常パスから上に拡張する仕組み

現時点の仮説は三段階である。

```text
軽量パス
  小さく、既存パターンを踏襲する変更

通常パス
  設計判断はあるが、影響範囲と解決方法が見えている変更

拡張パス
  不確実性、横断性、不可逆性、運用影響が大きい変更
```

ただし、単純なファイル数やコード量だけで拡張パスを選ばない。大きな変更で問題になるのは実装量より検討漏れである。

### 拡張パスへの昇格トリガー候補

- 新しいアーキテクチャ境界や抽象化を導入する
- 複数のサブシステム、リポジトリ、チームに影響する
- API、データ形式、DBスキーマに互換性問題がある
- 認証、権限、機密情報、コンプライアンスに影響する
- 明示的な性能、可用性、コスト目標がある
- 移行、段階展開、ロールバックが必要
- デプロイ後の監視・障害対応まで設計する必要がある
- 複数の有力な設計案があり、選択根拠を残す必要がある
- 要求に曖昧さがあり、関係者間の合意形成が必要

### 拡張パスの検討モジュール候補

| 検討モジュール | 主な問い |
|---|---|
| 問題・成功定義 | 本当に解く問題は何か。成功をどう測るか |
| 代替案・実現性 | 他の方法は何か。なぜこの案を選ぶか |
| 影響範囲分析 | 既存仕様、利用者、システム、運用への影響は何か |
| NFR | セキュリティ、性能、可用性、コスト要件は何か |
| 移行・互換性 | 既存データや利用者をどう移行するか |
| 展開・ロールバック | どう安全に公開し、失敗時に戻すか |
| 運用準備 | 何を監視し、誰がどう障害対応するか |

拡張パスを一つの巨大なテンプレートにせず、必須モジュールと条件付きモジュールに分ける案がある。

```text
拡張パス
  ├─ 影響範囲分析       必須候補
  ├─ 代替案比較         必須候補
  ├─ NFR                該当時
  ├─ 移行設計           該当時
  ├─ 展開・ロールバック  該当時
  └─ 運用設計           該当時
```

すなわち、

> パス選択は三段階で単純に保ち、拡張パスの中だけをモジュール式にする。

という案である。

## 制御モデルの仮説

LLMが自由に検討ステージを省略する設計にはしない。

1. 決定論的ルールが、変更特性に応じた必須モジュールを要求する
2. AIが追加モジュールと検討の深さを提案する
3. 人間が実装計画と一緒に、パス判定と選択モジュールを承認する

uroborosの強みである以下の境界は維持する。

- 計画は承認必須
- 承認後の実装は自動
- 最終品質ゲートは決定論的

適応させる対象は安全規律ではなく、調査・設計・検証の深さである。

### 実装中の昇格

軽量パスから通常パスへの昇格と、通常パスから拡張パスへの昇格は同じ扱いにしない可能性がある。

- 軽量から通常: `design.md`を追加し、4段検証をフル実施する
- 通常から拡張: アーキテクチャ、移行、運用責任などの重要な前提が変わる場合、計画承認へ戻す

大きな設計判断まで、承認済み計画の範囲として自動的に吸収させないためである。

---

## 次に議論する論点

1. 「拡張パス」という第3パスを設けるか
2. 通常パスと拡張パスの境界を何で判定するか
3. 昇格トリガーをどこまで決定論的にできるか
4. 拡張パスで必須にする検討モジュールは何か
5. 条件付きモジュールの選択を誰がどの時点で承認するか
6. `requirements.md` / `design.md`へ統合するか、独立した成果物を追加するか
7. 実装中に拡張パスへ昇格した場合、どこまで計画承認へ戻すか
8. Operation領域をuroborosの責務に含めるか、別手順として分離するか

現時点の中心的な問題設定:

> 大きな変更で「何を追加検討すべきか」を検出し、承認前に設計へ強制的に載せる仕組みを、uroborosへどう組み込むか。

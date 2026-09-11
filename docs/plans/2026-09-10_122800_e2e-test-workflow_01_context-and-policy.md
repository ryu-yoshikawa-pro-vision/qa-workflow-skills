# テスト設計からE2E実装・実行・結果分析・報告まで拡張するPlan

## 目的

現在の`qa-workflow-skills`は、仕様分析から詳細テストケース、カバレッジ分析、反証レビューまでを主対象としています。本変更では、既存のテスト分析・設計フローを維持したまま、要求に応じてPlaywrightによるE2Eテストの対象調査、実装、指定されたテスト環境URLへのローカル実行、結果分析、結果報告までを`qa-workflow`で扱えるようにします。

`qa-workflow`自身はコード実装、ブラウザ操作、Playwright実行、原因分析を行いません。開始点、既存成果物の再利用、Skillルーティング、状態、ブロック、変更伝播、再開、完了判定だけを担当します。

Playwright固有の知識と実行規則は新規E2E Skill側へ閉じ、既存の汎用QA Skillへ必要以上に拡散させません。

ブラウザ操作や実対象調査に利用する具体的な手段は固定しません。対象リポジトリ、ワークスペース、利用可能な実行環境に従います。

## 対象ブランチ

`feat/e2e-test-workflow`

## 現状

`main`では次の9 Skillを扱っています。

- `qa-workflow`
- `spec-analysis`
- `question-analysis`
- `test-analysis`
- `test-requirement-design`
- `test-condition-design`
- `test-case-design`
- `coverage-analysis`
- `adversarial-review`

現在の`qa-workflow`の既定経路は`adversarial-review`までで、Playwright実装、テスト実行、結果分析、報告は責務外です。

`test-analysis`はプロダクトリスク、テスト重点、テストレベル、観測方法、適用技法を扱います。E2E自動化を要求する場合の候補範囲や判断基準は現状の明示的な契約に含まれていません。

`coverage-analysis`は現在有効な仕様根拠から詳細テストケースまでの意味上の追跡・閉鎖性を扱います。TCとPlaywright E2E実装の対応は現状の責務外です。

`adversarial-review`はQA設計成果物を独立レビューしますが、Playwright E2Eテスト成果物は現状のレビュー対象に含まれていません。

`skills/qa-workflow/assets/project-context-template.md`にはテスト環境等の項目がありますが、E2E実行に必要なテスト環境URL、認証情報の取得方法、副作用の許可範囲、証跡の取扱い、テスト対象version等は十分に分離されていません。

### 現在の状態モデルとの不整合

現行の`workflow-state-template.md`と`skills/qa-workflow/evals/deterministic/validator.py`は、1 Skillにつき1状態行を前提としています。`WF-D012`はSkill名の重複を不許可にしています。

本変更では`adversarial-review`を「テスト設計成果物」と「E2E実装」、`coverage-analysis`を「テスト設計」と「TC → E2E実装」へ別々に適用するため、Skill名だけでは状態を識別できません。

また`WF-D014`等、Skill名を辞書キーにして状態を比較する実装も同じ問題を持ちます。`WF-D012`だけを直すのではなく、Skill名単独キーを前提とする状態・fixture・validatorをまとめて見直す必要があります。

### 現在の評価基盤との不整合

現行評価基盤には9 Skill前提が複数箇所にあります。少なくとも次を実装時の明示的な確認対象とします。

- `.github/workflows/validate-skills.yml`
  - 9 Skill一覧
  - Skill件数
  - 発火評価180件
- `.github/workflows/deterministic-output-evals.yml`
  - 対象Skill一覧
  - 最低評価ケース数
- `scripts/skills/evals/deterministic/common.py`
  - `CANONICAL_SKILLS`
  - 既存ID / 追跡グラフ処理
- `tests/skills/evals/semantic/test_repository_structure.py`
  - Skill一覧
- `tests/skills/evals/semantic/test_semantic_datasets.py`
  - Skill一覧とケース数契約
- `skills/qa-workflow/evals/deterministic/validator.py`
  - `WF-D012`、`WF-D014`等のSkill名単独キー依存
- `tests/skills/evals/deterministic/test_false_pass_regressions.py`
  - Skill重複を不正とする既存回帰テスト
- `skills/coverage-analysis/evals/deterministic/validator.py`
  - 現在の追跡グラフ前提
- `scripts/skills/evals/deterministic/ASSERTIONS.md`
  - assertion契約の説明

変更前にリポジトリ全体を再検索し、上記以外の固定箇所も確認します。Skillを動的発見しており変更不要なruntimeへ、Skill追加だけを理由に変更を広げません。

### `E2E`という用語の既存利用

`EVALS.md`の「ワークフローE2E評価」はブラウザE2Eテストとは別の意味で使われています。また`skills/coverage-analysis/references/guidance.md`にも「現在有効な仕様根拠 → テストケースのE2E追跡」という表現があります。

ブラウザE2Eを正式に扱う本変更では混同を避けるため、これらは「ワークフロー統合評価」「現在有効な仕様根拠からテストケースまでの全体追跡」等、意味が明確な既存日本語へ変更します。

## 固定する方針

### 追加するSkill

次の5 Skillを追加します。

1. `e2e-test-inspection`
2. `e2e-test-implementation`
3. `e2e-test-execution`
4. `e2e-test-result-analysis`
5. `e2e-test-reporting`

追加後のSkill総数は14です。

5 Skillは次の異なる責務を持つため、現時点では統合しません。

- `e2e-test-inspection`: コードを書かず、実装前の事実・実装可能性・安全条件を確認する
- `e2e-test-implementation`: Playwrightコードを変更し、実装として成立していることを静的・軽量検証する
- `e2e-test-execution`: 外部状態へ副作用を起こし得る実行を行い、事実を構造化して収集する
- `e2e-test-result-analysis`: 実行事実から原因を推論し、必要な責任工程を判断する
- `e2e-test-reporting`: 確定済みの実行・分析結果を再解釈せず報告する

`e2e-test-inspection`は「E2E化できるか調べて」という単独依頼を扱えること、コード変更前の事実確認境界として利用できることから独立させます。

`e2e-test-reporting`は「分析済み結果から報告だけ作る」という途中開始を扱い、原因再判定を禁止する境界として独立させます。

E2E専用レビューSkillやE2E専用カバレッジSkillは追加せず、既存の`adversarial-review`と`coverage-analysis`を対象別に再利用します。

### 同一リポジトリに置く

Playwright固有Skillは現時点では別リポジトリへ分離しません。

理由:

- 今回の要求がテスト設計からPlaywright実装・実行までを1つの`qa-workflow`で扱うこと
- 同一リポジトリでも各`skills/<skill-name>/`は独立Skillとして利用できること
- 別リポジトリ化するとversion整合、同時配置、評価、`qa-workflow`との対応関係の管理が増えること
- Selenium、Cypress、Appium等への対応要求は現時点で存在せず、将来frameworkを理由に抽象化する必要がないこと

Playwright固有規則は新規E2E Skillの`SKILL.md`と`references/`へ閉じます。

### 今回追加しないもの

次は本変更の対象外です。

- 対象プロダクトのCI上でのE2E実行
- GitHub Actions向けの対象プロダクトE2E実行基盤
- shard、matrix、runner性能調整等のE2E実行高速化
- 変更差分からE2E実行対象を選択する仕組み
- 特定のブラウザ操作方式の固定
- 共通Page Object frameworkの新設
- 共通fixture frameworkの新設
- locator方式の一律強制
- Selenium、Cypress、Appium等の将来用adapter
- 独自Playwright runner
- 独自retry framework
- 独自reporter
- 汎用ネットワークallowlist framework
- 巨大なE2E / RUN / ANALYSIS等の共通ID体系
- 汎用workflow engine / 独自state machine
- E2E基盤構築専用Skill
- E2Eレビュー専用Skill
- E2Eカバレッジ専用Skill
- 案件固有ナレッジの自動永続化
- 実行結果によるSkill判断基準の自己更新
- 不具合管理システムへの自動登録・外部通知
- 実Agentクライアント上で14 Skillを連続実行する汎用統合評価harness

このリポジトリ自身のSkill評価用GitHub Actions更新は、対象プロダクトのE2E実行基盤とは別であり、本変更の対象に含めます。

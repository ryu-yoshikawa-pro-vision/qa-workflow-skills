# workflow state / Project Context 文書整合Plan

この文書は、`docs/plans/2026-09-27_163600_main-document-consistency.md`のうち、単純な件数・表記同期では判断できない3件を扱います。

対象は文書整合だけです。runtime、validator、fixture、dataset、CI、production helperの実装変更は行いません。

## 対象

8. `skills/qa-workflow/assets/workflow-state-template.md`のpersisted state項目と、PR #13で確定したworkflow state契約の不整合
9. `skills/qa-workflow/references/guidance.md`の「全体ワークフロー完了条件」と、Regression / Exploration / QA Knowledgeを含む現在のworkflow入口の不整合
10. Project Contextから発見するhistory / shared resource関連入口について、PR #13 Planと現在テンプレート・各Skill文書の関係を明確にする

## 判断原則

この3件では、過去Planの文言を機械的に現在文書へコピーしません。

次の順で現在の正本を確認します。

1. merge済みのproduction実装と現在のSkill契約
2. PR #13の最終実装・検証記録
3. PR #13の実装順序・完了条件
4. PR #13の詳細Plan
5. 過去時点の中間案

同じPR #13内で詳細Planと最終実装が食い違う場合は、まず実装時に意図的に狭めたのか、単なる文書反映漏れなのかを確認します。

確認できないまま、新しいfield、root、state schemaを文書だけで追加しません。

## 8. workflow-state-template.mdのpersisted state項目

### 現在の不整合

PR #13の詳細Planでは、workflow stateへ最低限次を保持するとしています。

- `workflow_ref`
- workflow objective / requested outcome
- workflow scope
- started source refs / revisions
- used knowledge refs / revisions
- project context ref / revision
- currentness判定に使ったProject Context stable key / content identity / affected scope / operation
- used environment / shared resource refs
- produced artifact / Activity / Session refs
- optional related workflow refs
- state revision / content identity

現在の`skills/qa-workflow/assets/workflow-state-template.md`のpersisted recordは、少なくとも次を持っています。

- `workflow_ref`
- `state_revision`
- `overall_state`
- `started_source_refs`
- `knowledge_entry_refs`
- `project_context_ref`
- `project_context_revision`
- `used_project_context_fields`
- `source_dependencies`
- `resource_conditions`
- `mutable_operation_claims`
- `unresolved`

一方、次は明示されていません。

- workflow objective / requested outcome
- workflow scope
- produced artifact / Activity / Session refs
- optional related workflow refs
- state content identity
- started source / knowledge refsのrevisionをどのfieldで保持するか

### 実装前に確認すること

次を確認して、現在の実装契約を確定します。

- `skills/qa-workflow/scripts/artifact_graph.py`の`create_workflow_state` / `read_workflow_state`
- workflow stateを生成・保存・resumeする現在の呼び出し経路
- `workflow-state-template.md`を利用するSkill契約
- PR #13実装・検証記録
- workflow stateに関するdeterministic test
- PR #13の`_04d_continuous-qa-knowledge-and-concurrency.md`、`_05_skill-integration.md`、`_06_evaluation-ci-implementation-order.md`

### 修正方針

確認結果に応じて、次のどちらかへ揃えます。

#### A. 現在も必須項目である場合

`workflow-state-template.md`のpersisted recordへ不足fieldを追加し、Planで要求された最小stateを表現できるようにします。

ただし、field名は既存実装・既存文書で使われている名称を優先します。新しい命名を作らないでください。

単に例を増やすのではなく、次が読み取れる形にします。

- workflowが何を達成しようとしているか
- どのscopeを管理しているか
- 何を入力として開始したか
- どのknowledge / resourceを使ったか
- 何を生成したか
- 関連Activity / Session / workflowは何か
- どのrevision / content identityを現在stateとして扱うか

#### B. 実装時に意図的に不要となった場合

現在のtemplateへ不要fieldを追加しません。

その場合は、現在文書のどこを正本とするかを明確にし、必要であれば`workflow-state-template.md`または`qa-workflow/references/guidance.md`へ、現在保持するstate項目と保持しない項目の境界を短く明記します。

過去Plan自体は履歴なので書き換えません。

### 禁止

- persisted stateのためだけに新しいruntime schema validatorを追加する
- current implementationにないfieldを将来用途だけで追加する
- workflow stateをproject-wide registryへ拡張する
- relation indexやcentral manifestを追加する

## 9. qa-workflowの全体完了条件

### 現在の不整合

`skills/qa-workflow/references/guidance.md`は現在、正式なworkflow入口として次を扱います。

- 新規・改修
- Regression
- Exploration / Investigation
- QA Knowledge
- 修正確認を含む複合workflow

一方、「全体ワークフロー完了条件」は、対象workflowに関係なく次を要求するように読めます。

- `spec-analysis`の仕様根拠
- Product Risk / TR / TCN / Coverage Item
- 詳細テストケース
- coverage analysis
- adversarial review

このままでは、例えば次の単独要求でも設計チェーンを必須と解釈できます。

- Regression履歴参照
- Regression baseline / membership
- Explorationだけ
- QA Knowledge triage / lookup

同じguidance前半のrouting契約と後半の完了条件が一致していません。

### 修正方針

「全体ワークフロー完了条件」を、要求されたworkflow / 成果物に応じて適用する条件へ修正します。

共通条件は次に限定します。

- 要求された成果物 / workflowの担当Skillが、そのSkill自身の完了条件を満たしている
- 対象scopeに未解決の`ブロック中` / `要再検証`が残っていない
- 必要な追跡性が閉じている
- 実操作を含む場合は必要なcleanup / unresolved stateが閉じている
- 必要なcurrentness確認が完了している

そのうえで、条件付きの完了条件を明示します。

- 新規・改修のテスト設計を要求する場合だけ、仕様根拠 / Risk / TR / TCN / TC / coverage等の該当契約を要求する
- E2Eを要求する場合だけ、E2E実行・分析・報告・cleanupの該当契約を要求する
- Regressionは`regression-testing`の完了条件を正本とし、`qa-workflow`へdomain完了条件を複製しない
- Exploration / Investigationは`exploratory-testing`のSession完了条件を正本とする
- QA Knowledgeは`qa-knowledge`のtriage / lifecycle / lookup契約を正本とする

### 変更しないもの

- 各domain Skillの完了条件
- routing
- state語彙
- E2E固有契約
- Regression Activity判定
- Exploration Session lifecycle
- QA Knowledge lifecycle

## 10. Project Contextのhistory / resource入口

### 現在の状態

PR #13の詳細Planには、Project Contextから少なくとも次を発見できるようにする記述があります。

- fixed knowledge root
- fixed workflow state root
- workflow history root
- Activity / Session history root
- shared environment / resource policy

現在の`skills/qa-workflow/assets/project-context-template.md`のstable keyは次です。

- `qa.regression_scope`
- `qa.regression_policy`
- `qa.knowledge_root`
- `qa.workflow_state_root`
- `qa.reservation_root`
- `qa.auxiliary_testware_refs`

一方、PR #13の最終実装順序では、

- fixed knowledge root
- fixed workflow state root
- started source refs / revisions
- shared environment / resource policy入口
- reservation

は明示されていますが、workflow history root / Activity / Session history rootを独立stable keyとして必須化する記述は弱くなっています。

そのため、過去Planのroot名をそのまま新しいstable keyとして追加してはいけません。

### 実装前に確認すること

次を確認します。

- Regression historyを`regression-testing`がどのinput / rootから発見する契約か
- Exploration Session historyの発見経路
- workflow state historyを`qa.workflow_state_root`で扱うのか、別rootを必要とするのか
- `qa.reservation_root`とProject Contextの環境・test user・test data・cleanup欄でshared resource policyを十分表現できるか
- `既存QA成果物`表がhistory artifactの参照入口として意図されているか
- fixed-root scanを要求する各Skillでrootの出所が文書化されているか

### 修正方針

確認結果に応じて、現在の文書だけを同期します。

#### 既存欄・既存rootで解決できる場合

新しいstable keyを増やしません。

各Skill guidanceまたはProject Context templateへ、

- どの既存欄 / rootからhistoryを発見するか
- shared resource policyをどこに記録するか

を明示し、rootの出所が曖昧な状態だけを解消します。

#### 独立rootが現在の契約上必須である場合

現在の既存実装・契約で必要性を確認できたrootだけ、Project Contextのstable keyとして追加します。

追加する場合は`artifact_graph.py`の既存stable key parserで扱える既存field typeを使います。新しいparserやfield typeは追加しません。

### 禁止

- 過去Planに名前があることだけを理由にstable keyを追加する
- workflow / Activity / Sessionをまとめるgeneric history registryを追加する
- relation indexやcentral artifact registryを追加する
- history discoveryのためだけにproduction codeを変更する

## 変更対象候補

確認結果に応じて、文書変更は次の範囲に限定します。

- `skills/qa-workflow/assets/workflow-state-template.md`
- `skills/qa-workflow/assets/project-context-template.md`
- `skills/qa-workflow/references/guidance.md`
- 必要な場合だけ
  - `skills/regression-testing/references/guidance.md`
  - `skills/exploratory-testing/references/guidance.md`

`qa-knowledge`のfixed rootは現在`qa.knowledge_root`で明示済みなので、この確認だけを理由に変更しません。

## 検証

### 文書契約の確認

次を確認します。

- workflow state templateのpersisted recordが、現在のworkflow state契約で必須の情報を表現できる
- `qa-workflow`の完了条件が、単独Regression / Exploration / QA Knowledgeを設計chain必須にしない
- 各domain完了条件を`qa-workflow`へ複製していない
- historyを固定root scanするSkillについて、rootの出所が文書から一意に分かる
- Project Contextへ不要なstable keyを増やしていない
- shared resource policyの記録場所が現在文書から特定できる

### 既存評価

文書変更後は親Plan記載の検証に加えて、少なくとも次を確認します。

```bash
python -m unittest discover -s tests/skills/evals/deterministic -p 'test_qa_artifact_graph_skills.py' -v
python -m unittest discover -s tests/skills/evals/trigger -v
git diff --check
```

`SKILL.md`のfrontmatterをこの補助Planでは変更しません。

## 完了条件

- workflow stateの現在契約と`workflow-state-template.md`のpersisted recordが一致している
- workflow objective / scope / produced refs等を追加するか追加しないかが、現在実装に基づいて確定している
- `qa-workflow`の全体完了条件が全workflowへ旧テスト設計chainを強制しない
- Regression / Exploration / QA Knowledgeの完了条件は各owner Skillを正本として参照する
- Regression / Exploration / workflow historyの発見入口が現在文書から追える
- Project Contextへ不要なroot / stable keyを追加していない
- shared resource policyの記録場所が明確である
- runtime / validator / dataset / CIを変更していない

# main文書整合修正Plan

このPlanは、PR #13 merge後の`main`で確認した現行文書の不整合を修正するための実装計画です。

対象は、現在のリポジトリ状態を説明する文書に残ったSkill数・評価件数・責務・workflow state / Project Context・正規artifact契約のずれです。過去時点のPlan、history、実装・検証記録は履歴として保持し、現在値へ書き換えません。

## 対象ブランチ

`docs/main-document-consistency`

## 基準

- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- 基準branch: `main`
- 基準commit: `1a13958180877971d77ba92ee7b13872bccb26b8`
- 基準時点の正規Skill数: 19
- trigger dataset: 428 query
- deterministic output dataset: 38 case
- semantic dataset: 72 case
- `qa-workflow` routing fixture: 61件

基準値は、`skills/`の19 Skill、GitHub Actions、`EVALS.md`、`tests/skills/evals/semantic/test_semantic_datasets.py`、`skills/qa-workflow/evals/deterministic/routing_cases.json`で確認済みです。

## 目的

PR #13 merge後の実装を正本として、現在状態を説明する文書同士の不整合を解消します。

今回修正するのは次の12件です。

1. `skills/qa-workflow/references/guidance.md`に残る「全16 Skill」を19 Skillへ合わせる
2. `EVALS.md`のsemantic case内訳「その他13 Skill」を実データに合わせて「その他10 Skill」へ修正する
3. `docs/PROJECT_CONTEXT.md`をPR #11時点の評価・実装一覧から、PR #12 / #13 merge後の現在状態へ同期する
4. `README.md`の「工程固有ロジックの正本」表を、現在の19 Skill構成と責務境界へ同期する
5. `skills/qa-workflow/assets/workflow-state-template.md`のSkill状態表へ`qa-workflow`行を追加し、19 Skill構成と揃える
6. `README.md`冒頭説明と`skills/qa-workflow/SKILL.md` frontmatter `description`を、Regression / Exploration / QA knowledgeを含む現在の責務範囲へ同期する
7. `EVALS.md`に残るmerge前提の「本Plan」「今回14件」等を、`main`上で参照先が明確な表現へ修正する
8. `workflow-state-template.md`のpersisted state項目と、現在のworkflow state契約を照合して文書上の不一致を解消する
9. `qa-workflow/references/guidance.md`の全体完了条件を、Regression / Exploration / QA Knowledgeを含む現在のworkflow入口へ同期する
10. Project Contextのhistory / shared resource関連入口について、現在の実装契約と文書の関係を明確にする
11. `regression-testing`のBaseline / Run / Activity正規出力契約を、現在のvalidator / fixture / production helperと一致させる
12. `qa-knowledge`の`entry_revision`をentry body必須fieldではなくstorage metadataとして統一する

8〜10は単純な文言置換ではありません。詳細は[`workflow state / Project Context 文書整合Plan`](./2026-09-27_163600_main-document-consistency_workflow-contract-sync.md)を正本とします。

11〜12の詳細は[`Skill artifact contract 文書整合Plan`](./2026-09-27_163600_main-document-consistency_skill-artifact-contract-sync.md)を正本とします。

新しいSkill、runtime、評価方式、CI、文書生成機構は追加しません。

## 確認済みの不整合

### 1. qa-workflow guidanceのSkill数

`skills/qa-workflow/references/guidance.md`は「ランタイム前提」で19 Skillを正しく列挙しています。

一方、同じファイルの「E2E要求時の分岐」に、

```text
全16 Skillを固定順に実行しません。
```

が残っています。

同一文書内で矛盾しているため、現在の19 Skill構成へ修正します。ルーティング内容そのものは変更しません。

### 2. EVALS.mdのsemantic case内訳

`EVALS.md`はsemantic datasetを合計72 caseとしています。この合計値は現在のrepository testと一致しています。

個別件数が明示されているSkillは次の9 Skillです。

- `test-analysis=7`
- `test-condition-design=14`
- `adversarial-review=8`
- `qa-workflow=3`
- `test-target-inspection=2`
- `test-execution=2`
- `regression-testing=6`
- `exploratory-testing=4`
- `qa-knowledge=6`

正規Skillは19個なので、既定2 caseを使う残りは10 Skillです。

`tests/skills/evals/semantic/test_semantic_datasets.py`も、上記9 Skillだけを`EXPECTED_CASE_COUNTS`へ定義し、その他Skillを2 caseとして合計72を検証しています。

したがって、

```text
その他13 Skillは各2
```

を、

```text
その他10 Skillは各2
```

へ修正します。case数そのものは変更しません。

### 3. PROJECT_CONTEXT.mdの現在値

`docs/PROJECT_CONTEXT.md`の「評価・検証」は現在もPR #11時点の値を現在値として記述しています。

現状:

- 14 Skill
- trigger 328件
- semantic 51件
- runtime CIは7 Skillのcompile

PR #13 merge後の現在状態とは一致しません。

現在の実装では次を確認済みです。

- 19 Skill
- trigger 428件
- deterministic output 38件
- semantic 72件
- `deterministic-output-evals.yml`は`spec-analysis`、PR #11 runtime対象Skill、`regression-testing`、`exploratory-testing`、`qa-knowledge`のscriptをcompileする
- PR #12で`test-target-inspection` / `test-execution`が追加済み
- PR #13で`regression-testing` / `exploratory-testing` / `qa-knowledge`と`qa-workflow/scripts/artifact_graph.py`が追加済み

`PROJECT_CONTEXT.md`は現在状態を説明する文書なので、現在値と主要実装面を同期します。

PR #11固有のruntime契約や、PR #11実装時に24/24 PASSだった実Judge結果は履歴上の事実として残して構いません。ただし、現在の全repository評価件数と混同しない位置・表現へ整理します。

### 4. READMEの責務表

`README.md`冒頭のSkill構成表は19 Skillを正しく列挙しています。

一方、「工程固有ロジックの正本」の表には、現在の責務表から次が欠落しています。

- `test-target-inspection`
- `test-execution`
- `e2e-test-inspection`
- `e2e-test-implementation`
- `e2e-test-execution`
- `e2e-test-result-analysis`
- `e2e-test-reporting`
- `regression-testing`
- `exploratory-testing`
- `qa-knowledge`

正本は`skills/qa-workflow/references/guidance.md`の「工程固有ロジックの正本」とし、READMEの表を同じ責務境界へ合わせます。

README側で詳細アルゴリズムを増やさず、担当Skillの一覧と責務だけを同期します。


### 5. workflow-state-template.mdのSkill状態表

`skills/qa-workflow/assets/workflow-state-template.md`のSkill状態表は、`spec-analysis`から`qa-knowledge`まで18 Skillを列挙していますが、`qa-workflow`自身の行がありません。

現在の正規Skillは19個で、READMEは`qa-workflow`も1 Skillとして扱うと明記しています。また、`skills/qa-workflow/evals/deterministic/routing_cases.json`では複合workflowの開始Skillとして`qa-workflow`自身を利用するcaseがあります。

テンプレート側に`qa-workflow`だけを除外する契約はないため、単一用途Skillとして対象 / 実行範囲を空欄にした状態行を追加します。

新しい状態値や対象値は追加しません。

### 6. README / qa-workflow descriptionの現在スコープ

README冒頭と`skills/qa-workflow/SKILL.md` frontmatterの`description`は、新規・変更機能のテスト設計からE2E実装・実行までを中心に説明しています。

一方、同じREADME / Skill本文では現在、

- Regression baseline / membership / Run / Activity
- Charterに沿ったExploration / Investigation
- QA knowledgeのtriage / lifecycle / lookup

まで扱う19 Skill構成になっています。

冒頭説明だけPR #13以前の範囲に留まっているため、既に本文で定義済みの現在責務へ同期します。

`SKILL.md`のfrontmatter `description`はSkill選択へ影響するため、責務を新しく追加する表現は使いません。本文と`references/guidance.md`に存在する現在の入口だけを簡潔に反映し、既存trigger datasetの回帰確認を必須にします。

### 7. EVALS.mdのmerge前提表現

`EVALS.md`には現在も次の表現があります。

```text
本Planで追加した意味責務とcase対応は次のとおりです。
```

```text
PR #11 / #12後の47件に今回14件を加えた61件
```

`EVALS.md`は現在の評価契約を説明する文書であり、「本Plan」「今回」が指す対象を文書単体では確定できません。

case数やrouting fixture数は変更せず、例えば「現在の追加・拡張責務」「PR #13で14件を追加した61件」のように、`main`で読んでも参照先が明確な表現へ修正します。

同じ節に残る「新規Skill」「新3 Skill」も対象を明示します。`regression-testing` / `exploratory-testing` / `qa-knowledge`を指す場合は、その3 Skill名または「PR #13で追加した3 Skill」と書き、文書単体で参照先が分かる状態へ揃えます。


### 11. regression-testingの正規出力契約

`skills/regression-testing/assets/output-template.md`は正規machine artifactを説明していますが、詳細fieldを「Plan記載の全field」として過去Planへ依存しています。

また、baselineは`assets/baseline-template.json`を使うとしていますが、現在のdeterministic validator / fixtureが使う`artifact_type`、`completeness_evidence`等とtemplateの記載に差があります。

`skills/regression-testing/SKILL.md`のResourcesも「baselineとActivityのmachine input」としており、参照先`references/data-contract.md`が扱うRunが説明から欠落しています。

現在のproduction helper / validator / fixtureを正本として、過去PlanなしでBaseline / Run / Activityの正規契約を追える文書へ同期します。

詳細は[`Skill artifact contract 文書整合Plan`](./2026-09-27_163600_main-document-consistency_skill-artifact-contract-sync.md)に分離します。

### 12. qa-knowledgeのentry_revision

`skills/qa-knowledge/references/guidance.md`は`entry_revision`をentryの必須項目として列挙しています。

一方、`references/data-contract.md`と現在のproduction helperは、`entry_revision`をentry bodyへ書かないstorage metadataとして扱っています。`assets/entry-template.md` / `assets/entry-template.json`にも`entry_revision`はありません。

現在のdata contract / runtimeを正本として、entry bodyの必須fieldとstorage metadataを分離して説明します。

`entry_revision`をentry templateへ追加しません。

詳細は[`Skill artifact contract 文書整合Plan`](./2026-09-27_163600_main-document-consistency_skill-artifact-contract-sync.md)に分離します。

## 追加の契約整合確認

8〜10の3件は、過去Planの文言をそのまま現在文書へコピーせず、merge済み実装と現在のSkill契約を確認してから同期します。

- workflow state persisted recordの必須項目
- `qa-workflow`全体完了条件の適用範囲
- Project Contextから発見するhistory / shared resource関連入口

詳細な確認順序、変更候補、禁止事項、完了条件は[`2026-09-27_163600_main-document-consistency_workflow-contract-sync.md`](./2026-09-27_163600_main-document-consistency_workflow-contract-sync.md)に分離します。

この3件の確認結果だけを理由にruntime / validator / dataset / CIを変更しません。現在実装にないfieldやrootを将来用途で追加しません。

## 変更対象

### `skills/qa-workflow/references/guidance.md`

変更:

- 「全16 Skill」を「全19 Skill」へ修正

変更しないもの:

- E2E routing
- 各Skillの責務
- workflow状態
- production helper checkpoint

### `EVALS.md`

変更:

- semantic case内訳の「その他13 Skill」を「その他10 Skill」へ修正
- 「本Planで追加した意味責務」を、現在の評価文書として参照先が明確な表現へ修正する
- routing fixtureの「今回14件」を「PR #13で14件」のようにmerge後も意味が確定する表現へ修正する
- 「新規Skill」「新3 Skill」を、対象Skill名または「PR #13で追加した3 Skill」のように参照先が確定する表現へ修正する

変更しないもの:

- semantic case数
- rubric
- Judge契約
- deterministic / semantic評価方式
- routing fixture自体

routing fixtureの「今回」の表現は事実誤りではないため、可読性改善として同じ変更内で直す場合も意味を変えない文言修正に限定します。

### `docs/PROJECT_CONTEXT.md`

現在状態を説明する部分だけを更新します。

#### 維持する内容

- PR #11 runtimeの基本契約
- Skill-local `runtime_contract.py`の責務
- PR #11実装時の検証事実
- 既知の環境差

#### 更新する内容

「主な実装面」に、現在存在する次の主要経路を追記します。

- `skills/test-target-inspection/`
- `skills/test-execution/`
- `skills/regression-testing/`
- `skills/exploratory-testing/`
- `skills/qa-knowledge/`
- `skills/qa-workflow/scripts/artifact_graph.py`

「評価・検証」の現在値を次へ更新します。

- 19 Skill
- trigger 428件
- deterministic output 38件
- semantic 72件
- current CIで実行している主要検証

PR #11の24/24実Judgeやruntime smoke等、過去の実行結果は「PR #11実装時の検証」と分かる表現で残します。

現在値と過去時点の実績を同じ文で「固定する」と表現しません。

### `README.md`

「工程固有ロジックの正本」表を`skills/qa-workflow/references/guidance.md`へ同期します。

追加する責務は現在のguidanceに存在するものだけとします。

READMEへ新しい責務を定義せず、guidanceとの差異をなくします。

冒頭のタイトル・説明も、Regression / Exploration / QA knowledgeを含む現在のSkill群の対象範囲が分かる表現へ更新します。ただし、README冒頭で個別Skillの詳細責務を再定義しません。

### `skills/qa-workflow/assets/workflow-state-template.md`

Skill状態表へ`qa-workflow`行を追加します。

- 対象 / 実行範囲は空欄
- 状態の許可値は既存行と同一
- 新しいworkflow stateやfieldは追加しない

persisted workflow state recordやCAS / claim / reservation契約は変更しません。

### `skills/qa-workflow/SKILL.md`

frontmatter `description`だけを、本文で既に定義済みの現在のオーケストレーション範囲へ同期します。

含める対象は、既存の新規・変更機能のQA workflowに加えて、既に本文が担当として持つRegression / Exploration / QA knowledgeの接続です。

変更しないもの:

- 実行契約
- 工程固有ロジックの担当表
- runtime統合
- production helper checkpoint
- 入出力契約

frontmatter変更後はtrigger datasetの回帰確認を実行します。

### workflow state / Project Context契約

8〜10の変更対象候補は次です。

- `skills/qa-workflow/assets/workflow-state-template.md`
- `skills/qa-workflow/assets/project-context-template.md`
- `skills/qa-workflow/references/guidance.md`
- 必要な場合だけ
  - `skills/regression-testing/references/guidance.md`
  - `skills/exploratory-testing/references/guidance.md`

実際に変更するファイルは、補助Planの確認手順で現在の契約を確定してから決めます。


### Regression / QA Knowledge artifact契約

11〜12の変更対象候補は次です。

- `skills/regression-testing/SKILL.md`
- `skills/regression-testing/references/data-contract.md`
- `skills/regression-testing/assets/output-template.md`
- 必要な場合だけ `skills/regression-testing/assets/baseline-template.json`
- `skills/qa-knowledge/references/guidance.md`
- 必要な場合だけ
  - `skills/qa-knowledge/references/data-contract.md`
  - `skills/qa-knowledge/assets/output-template.md`

`qa-knowledge/assets/entry-template.md` / `entry-template.json`は現在のruntime / data contractと整合しているため、`entry_revision`を追加しません。

実際の変更範囲と確認手順は[`2026-09-27_163600_main-document-consistency_skill-artifact-contract-sync.md`](./2026-09-27_163600_main-document-consistency_skill-artifact-contract-sync.md)を正本とします。

## 対象外

次は変更しません。

- `docs/plans/`に残る14 Skill / 16 Skill等の過去時点の基準値
- `docs/history/`の過去検証値
- `docs/reports/`の実装・検証時点の記録
- 各Skillのdomain責務・実行意味の変更
- runtime実装
- validator
- fixture / dataset
- GitHub Actions
- test code
- PR #11 / #12 / #13の履歴

過去Plan・history・reportの数値を現在値へ一括置換しません。これらは当時の基準・実績を残す文書であり、更新すると履歴の意味を壊します。

## 実装順序

1. 最新`main`との差分がないことを確認する
2. `skills/qa-workflow/references/guidance.md`のSkill数を19へ修正する
3. `EVALS.md`のsemantic case内訳とmerge前提表現を現在の評価文書へ同期する
4. `docs/PROJECT_CONTEXT.md`の現在状態をPR #12 / #13 merge後へ同期する
5. `README.md`の責務表と冒頭説明を現在の19 Skill構成へ同期する
6. `skills/qa-workflow/assets/workflow-state-template.md`へ`qa-workflow`状態行を追加する
7. `skills/qa-workflow/SKILL.md`のfrontmatter `description`を本文の現在責務へ同期する
8. 補助Planに従ってworkflow state persisted recordの現在契約を確認し、templateとの不一致だけを修正する
9. `qa-workflow`の全体完了条件を、要求されたworkflow / 成果物に応じた条件へ整理する
10. Project Contextのhistory / shared resource関連入口を確認し、既存欄・既存rootで解決できる場合はその経路を文書化する。独立rootが現在契約上必須と確認できた場合だけstable key追加を検討する
11. Skill artifact contract補助Planに従い、`regression-testing`のBaseline / Run / Activity契約を現在のvalidator / fixture / helperへ同期する
12. 同補助Planに従い、`qa-knowledge`のentry bodyと`entry_revision` storage metadataの境界を文書で統一する
13. 現行文書に古い現在値・参照先不明のmerge前提表現・過去Plan依存・契約上の孤立項目が残っていないか検索する
14. 既存の文書・評価契約検証を実行する

## 検証

### 文書横断確認

少なくとも次を確認します。

```bash
git grep -nE '全?16 Skill|全?14 Skill|368クエリ|328件|その他13 Skill|本Plan|今回14件|新3 Skill|新規Skill|Plan記載|entry_revision' -- \
  README.md \
  EVALS.md \
  docs/PROJECT_CONTEXT.md \
  skills/*/SKILL.md \
  skills/*/references/*.md \
  skills/*/assets/*.md
```

過去文書である`docs/plans/`、`docs/history/`、`docs/reports/`はこの現在値確認から除外します。

検索結果が存在する場合は、その文脈が現在値か過去値かを確認し、現在値として残っているものだけを修正します。

### 現行値との照合

次を確認します。

- `skills/`の正規Skillが19個
- trigger datasetが428 query
- deterministic output datasetが38 case
- semantic datasetが72 case
- routing fixtureが61件
- READMEと`qa-workflow` guidanceの責務表に担当Skillの欠落がない
- `workflow-state-template.md`のSkill状態表が現在の19 Skill構成と整合する
- README / `qa-workflow` descriptionの対象範囲が本文の現在責務と矛盾しない
- workflow state persisted recordが現在のworkflow state契約と一致する
- `qa-workflow`の完了条件が単独Regression / Exploration / QA Knowledgeへ旧テスト設計chainを強制しない
- historyをfixed-root scanするSkillについて、rootまたは既存成果物入口の出所が文書から追える
- shared resource policyの記録場所が現在文書から特定できる
- `regression-testing`のBaseline / Run / Activity正規契約を過去Planなしで追える
- `regression-testing/assets/baseline-template.json`とcurrent validator / fixtureの必須fieldに説明不能な差がない
- `qa-knowledge`でentry bodyのfieldと`entry_revision` storage metadataが混同されていない

### 既存検証

文書修正だけですが、現在の正本と矛盾していないことを確認するため、少なくとも次を実行します。

```bash
python -m unittest discover -s tests/skills/evals/deterministic -v
python scripts/skills/evals/semantic/validate.py
python -m unittest discover -s tests/skills/evals/semantic -v
python -m unittest discover -s tests/skills/evals/trigger -v
git diff --check
```

`README.md` / `EVALS.md`のSkill一覧を検査する`Validate Agent Skills`相当のrepository eval structure検証も実行します。

`skills/qa-workflow/SKILL.md`のfrontmatter `description`を変更するため、trigger dataset validationを必須とします。今回は既存責務の記述同期であり、trigger dataset自体は変更しません。既存trigger testが失敗した場合は、description変更が既存選択境界を変えていないかを確認し、文書同期の範囲で修正します。

8〜10の契約文書同期では、既存の`tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`も実行し、現在のProject Context / workflow state / claim / reservation契約と矛盾しないことを確認します。

11〜12では、同テストに加えてrepository deterministic test全体を実行し、現在のRegression / QA Knowledge contractと文書同期が矛盾しないことを確認します。validator / fixture / datasetは変更しません。

コード・dataset・runtimeを変更しないため、実Agent candidate / 実Judgeの再評価は行いません。

## 完了条件

次をすべて満たしたら完了です。

- `qa-workflow` guidanceの現在Skill数が19で統一されている
- `EVALS.md`のsemantic case内訳が実datasetと算術的に一致する
- `PROJECT_CONTEXT.md`の現在値が19 Skill / 428 trigger / 38 deterministic / 72 semanticと一致する
- `PROJECT_CONTEXT.md`にPR #12 / #13で追加された主要実装面が反映されている
- READMEの「工程固有ロジックの正本」が現在のqa-workflow guidanceと責務上矛盾しない
- `workflow-state-template.md`のSkill状態表に`qa-workflow`を含む19 Skillが反映されている
- README冒頭と`qa-workflow` frontmatter `description`がRegression / Exploration / QA knowledgeを含む本文の現在責務と矛盾しない
- `EVALS.md`に参照先不明の「本Plan」「今回14件」「新規Skill」「新3 Skill」が残っていない
- workflow state persisted recordと現在のworkflow state契約に説明不能な差が残っていない
- `qa-workflow`の全体完了条件が、要求していないspec / design / E2E工程を全workflowへ必須化していない
- Regression / Exploration / workflow historyの発見入口が現在文書から追える
- Project Contextへ、現在実装で必要性を確認できないhistory root / stable keyを追加していない
- shared resource policyの記録場所が明確である
- `regression-testing/assets/output-template.md`に「Plan記載の全field」のような過去Plan依存が残っていない
- `regression-testing`のBaseline / Run / Activity正規契約と現在のvalidator / fixtureに説明不能な差が残っていない
- `regression-testing/SKILL.md`のResources説明からRunだけが欠落していない
- `qa-knowledge`のentry body必須fieldから`entry_revision`が分離され、storage metadataとして説明されている
- `qa-knowledge` entry templateへ`entry_revision`を追加していない
- 過去Plan / history / reportを現在値へ書き換えていない
- 文書横断検索で、現行文書に14 / 16 Skill等の旧現在値が残っていない
- semantic dataset validation、repository semantic test、trigger test、repository eval structure検証がpassする
- `git diff --check`がpassする

## 実装時に追加しないもの

この不整合修正だけを理由に、次は追加しません。

- 文書生成script
- Skill数を埋め込む新しい設定ファイル
- 文書専用lint framework
- 新しいCI job
- README / EVALS / PROJECT_CONTEXTの自動生成
- 過去Planの一括修正
- generic history registry
- relation index / central artifact registry
- workflow state専用の新規runtime schema framework
- 文書整合だけを理由にしたproduction code変更
- `entry_revision`のentry bodyへの追加
- `regression-testing`のvalidator / fixtureを文書へ合わせる変更

同種の文書driftが今後も繰り返し発生し、既存CIでは防げないことが実測された場合に、その時点で必要な最小の自動検証を検討します。

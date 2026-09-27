# Skill artifact contract 文書整合Plan

この文書は、`docs/plans/2026-09-27_163600_main-document-consistency.md`のうち、新規Skillの正規出力・storage metadataに関する文書不整合を扱います。

原則は文書整合です。ただし、Plan 11の実装時に既存Baseline contractの不整合が見つかり、Plan本文の例外を適用します。

## 対象

11. `regression-testing`の正規出力契約を、現在のvalidator / fixture / production helperと一致させる
12. `qa-knowledge`の`entry_revision`を、entry bodyではなくstorage metadataとして統一する

## 判断原則

この2件では、過去Planを現在の正本として参照させません。

現在の正本は次の順で確認します。

1. merge済みproduction helper
2. deterministic validator
3. 現在のdeterministic fixture
4. 現在のSkill / guidance / data contract / asset template
5. 実装・検証記録
6. 過去Plan

### Plan 11の実装例外: Regression Baseline contractの既存不整合

Plan 11の実装時、`memberships`にcurrentな`member`があり`complete=true`でも、`member_tc_refs`欠落をdeterministic validatorが受理し、`plan_run()`が欠落を空集合としてfull Runを0件で`ready`にできることが分かりました。文書だけを現在fixtureへ合わせると、production helperが使うBaseline projectionとRun planning契約を壊します。

この不整合を解消する範囲に限り、既存Baseline fieldを使った最小限のRegression runtime、deterministic validator、deterministic fixture、Regression runtime testの変更を許可します。Regression以外のruntime / validator / fixture / dataset / test、Regression dataset、CIは対象外のままです。新しいfieldやschemaは追加しません。

現在の実装と文書が一致している箇所は変更しません。文書整合だけを理由にvalidatorやfixtureを現在文書へ合わせて変更しません。

## 11. regression-testingの正規出力契約

### 現在の不整合

`EVALS.md`は、各Skillの`assets/output-template.md`を正規出力の基準としています。

しかし`skills/regression-testing/assets/output-template.md`は、baseline / Run / Activityの詳細fieldについて、

```text
選んだkindに必要なPlan記載の全fieldを含めます。
```

としています。

merge後のSkill packageが過去Planを暗黙の正本として参照する状態になっており、現行文書だけでは正規artifactを確定できません。

また、baselineについて`assets/baseline-template.json`のfieldを使うとしていますが、現在のdeterministic validator / fixtureでは少なくとも次を利用しています。

- `artifact_type`
- `completeness_evidence.root_listing_complete`
- `completeness_evidence.source_revisions_complete`
- `completeness_evidence.lifecycle_resolved`
- `completeness_evidence.membership_decisions_complete`

現在の`assets/baseline-template.json`にはこれらの一部がありません。

さらに`skills/regression-testing/SKILL.md`のResourcesでは、

```text
baselineとActivityのmachine input
```

と説明していますが、参照先`references/data-contract.md`はBaseline / Run / Activityを扱っています。

### 確認対象

- `skills/regression-testing/scripts/regression_runtime.py`
- `skills/regression-testing/evals/deterministic/validator.py`
- `skills/regression-testing/evals/output/cases/`
- `skills/regression-testing/references/data-contract.md`
- `skills/regression-testing/assets/output-template.md`
- `skills/regression-testing/assets/baseline-template.json`
- `skills/regression-testing/SKILL.md`

### 修正方針

正規artifact契約を現在のSkill package内だけで追えるようにします。

#### output-template.md

「Plan記載の全field」のような過去Plan依存を削除します。

Baseline / Run / Activityそれぞれについて、正規fieldの参照先を現在のSkill package内へ閉じます。

重複を避けるため、すべてのfield説明を`output-template.md`へ複製する必要はありません。例えば次のように役割を分けます。

- machine input / projection契約: `references/data-contract.md`
- 正規出力のartifact種別と必須構造: `assets/output-template.md`
- baselineの初期形: `assets/baseline-template.json`

ただし、どの文書を読めばBaseline / Run / Activityの正規fieldが確定するかを曖昧にしません。

#### baseline-template.json

現在のvalidator / fixtureでbaseline正規artifactに必要とされるfieldを確認し、templateが不足している場合だけ同期します。

新しいfieldは追加しません。validator / fixture / production helperが現在使用しているfieldだけを反映します。

`completeness_evidence`を追加する場合は、現在のvalidatorが使う4項目と一致させます。

#### SKILL.md

Resourcesの説明を、実際の`references/data-contract.md`の範囲へ合わせます。

```text
baseline / Run / Activityのmachine input / data contract
```

のように、Runを欠落させない表現へ修正します。

### 変更しないもの

- baseline completenessの意味
- membership semantics
- Run selection
- required route
- Activity actual start / result finalization
- Plan 11の例外で許可したBaseline contract修正以外のvalidator criterion
- Plan 11の例外で許可したBaseline fixture以外のfixture
- Regression dataset、Regression以外のruntime / validator / fixture / test、CI
- production helper

## 12. qa-knowledgeのentry_revision

### 現在の不整合

`skills/qa-knowledge/references/guidance.md`はentryの必須項目として`entry_revision`を列挙しています。

一方、現在の`skills/qa-knowledge/references/data-contract.md`は、

```text
entry_revision is storage metadata kept in the calling workflow / Activity, not written into the entry body.
```

という契約です。

現在の実装もこのdata contractと一致しています。

- `assets/entry-template.md`のentry bodyに`entry_revision`はない
- `assets/entry-template.json`のentry bodyに`entry_revision`はない
- `knowledge_runtime.validate_entry(..., entry_revision=...)`はstorage revisionを外部引数として受け取る
- update / revalidationではexpected revisionをstorage conditionとして扱う

したがって、guidanceの「entry body必須項目」と「storage metadata」の説明が混在しています。

### 確認対象

- `skills/qa-knowledge/scripts/knowledge_runtime.py`
- `skills/qa-knowledge/references/guidance.md`
- `skills/qa-knowledge/references/data-contract.md`
- `skills/qa-knowledge/assets/entry-template.md`
- `skills/qa-knowledge/assets/entry-template.json`
- `skills/qa-knowledge/assets/output-template.md`
- `skills/qa-knowledge/evals/deterministic/validator.py`

### 修正方針

`guidance.md`のEntry lifecycleを、次の2つに分けて説明します。

#### entry bodyの必須項目

現在のtemplate / runtime contractにあるfieldだけを列挙します。

少なくとも次を現在契約として照合します。

- `entry_ref`
- `identity`
- `kind`
- `content`
- `scope_refs`
- `applicability`
- `provenance`
- `currentness_dependencies`
- `last_verified`
- `state`
- `replacement_ref`
- `related_qa_refs`

#### storage metadata

`entry_revision`はentry bodyへ書かず、保存先が返したstorage revisionとしてcaller側で保持すると明記します。

update / revalidation / historical readで必要な場合は、そのstorage revisionをexpected revision / historical revisionとして使用します。

### 禁止

- `entry-template.md`へ`entry_revision`を追加する
- `entry-template.json`へ`entry_revision`を追加する
- entry identityへstorage revisionを含める
- local file digestをatomic conditional write tokenとして扱う
- revision管理のために新しいstorage abstractionを追加する

## 変更対象候補

### regression-testing

- `skills/regression-testing/SKILL.md`
- `skills/regression-testing/references/data-contract.md`
- `skills/regression-testing/assets/output-template.md`
- 必要な場合だけ `skills/regression-testing/assets/baseline-template.json`
- Plan 11の例外で許可する最小範囲に限り
  - `skills/regression-testing/scripts/regression_runtime.py`
  - `skills/regression-testing/evals/deterministic/validator.py`
  - `skills/regression-testing/evals/output/cases/reg-out-001/output.md`
  - `tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`
- Assertion契約を追加する場合は `scripts/skills/evals/deterministic/ASSERTIONS.md`

### qa-knowledge

- `skills/qa-knowledge/references/guidance.md`
- 必要な場合だけ、説明の参照関係を明確にするため
  - `skills/qa-knowledge/references/data-contract.md`
  - `skills/qa-knowledge/assets/output-template.md`

`entry-template.md` / `entry-template.json`は現在実装と整合しているため、今回の確認だけを理由に変更しません。

## 検証

### 文書契約

次を確認します。

- `regression-testing`の正規Baseline / Run / Activity契約が過去Planなしで追える
- `baseline-template.json`とcurrent validator / fixtureの必須fieldが矛盾しない
- `member_tc_refs`欠落や不正なscope identityのBaselineがvalidator / runtimeでfull Runとして受理されず、正規Baselineではmembership projectionとRun planningが一致する
- `regression-testing/SKILL.md`のResources説明がdata contractの実際の範囲と一致する
- `qa-knowledge`のentry bodyとstorage metadataが明確に分離されている
- `entry_revision`をentry body必須fieldとして説明している現行文書が残っていない

### 既存評価

親Planの検証に加え、少なくとも次を確認します。

```bash
python -m unittest discover -s tests/skills/evals/deterministic -p 'test_qa_artifact_graph_skills.py' -v
python -m unittest discover -s tests/skills/evals/deterministic -v
git diff --check
```

コード、validator、fixtureを変更しないため、deterministic datasetの期待値変更は行いません。

## 完了条件

- `regression-testing`の現行文書だけでBaseline / Run / Activityの正規契約を追える
- `output-template.md`に「Plan記載の全field」のような過去Plan依存が残っていない
- baseline templateと現在のdeterministic contractに説明不能な差が残っていない
- `regression-testing/SKILL.md`でRunだけがResources説明から欠落していない
- `qa-knowledge`のentry body必須fieldから`entry_revision`が除外されている
- `entry_revision`がstorage metadataとしてcaller側で保持されることが明記されている
- Plan 11の例外で列挙したRegression runtime / validator / fixture / testだけを必要最小限変更し、Regression datasetおよびRegression以外のruntime / validator / fixture / test / CIは変更していない

# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、formalなWCAG conformance evaluationを担当する `wcag-conformance-evaluation` の責務、Input / Function / Output、WCAG-EM 2.0の実行境界を固定します。

対象はWebだけです。WCAG-EM 2.0自体は他のdigital productにも適用できますが、本Skillではnative app、document、kiosk等をlive評価対象へ広げません。

## 1. 目的

`wcag-conformance-evaluation` は、live Web targetに対してWCAG-EM 2.0のmethodologyを用い、代表sampleに対するWCAG conformance evaluationを実施して評価結果を報告します。

`usability-inspection` のgeneral accessibility inspectionとは分離します。

- general accessibility inspection → 対象UIへapplicableなaccessibility concernを確認する
- WCAG conformance evaluation → WCAG version / level / product scopeを固定し、WCAG-EM 2.0の全non-optional methodology requirementを実施する

本Skillは「WCAG適合しているか」のようなformal evaluation要求のownerです。

## 2. 必須Input

評価開始前に次を確定します。

- live Web target / entry point
- evaluation commissioner。self-evaluationの場合はself-evaluationであることと責任主体
- target WCAG version。初期実装のsupported valueは `2.2`
- target conformance level: A / AA / AAA
- digital product scope
- product enclosure。評価対象として定義したself-enclosedなWeb productの全view / state / functionalityを含むこと
- scope boundaryの外側とした領域がある場合は、その領域が定義したproduct enclosure外である根拠
- accessibility support baseline
- browser / assistive technology / other user agentのbaseline
- role / permission / environment条件
- side-effect / cleanup scope
- evaluation期間または開始時点
- project Authority / release gateとの関係（存在する場合）

target WCAG version、level、self-enclosedなdigital product scope、accessibility support baselineを確定できない場合は推測せず `unresolved` とし、formal evaluationを開始しません。初期実装でsupportedとするversionはWCAG 2.2だけです。2.0 / 2.1等、supported subset外のversionが明示された場合はsupport statusを `unsupported` としてformal evaluationを開始せず、version自体が不明・未指定の場合の `unresolved` と混同しません。product内の特定page / componentを任意に除外してscopeを狭めません。

追加評価要件は任意Inputです。

## 3. Function

### Step 1: evaluation scope

WCAG-EM 2.0 Step 1へ対応付けます。

- digital product scope
- conformance target
- accessibility support baseline
- additional evaluation requirements（存在する場合）

を成果物へ固定します。

### Step 2: target exploration

少なくとも次を探索し、結果を成果物へ記録します。

- common views
- essential functionality
- variety of sample types
- technologies relied upon
- accessibilityに特に関係するその他sample

探索結果からstructured sampleの候補を意味判断します。target scopeを有限に列挙できる場合は、currentなtarget inventoryとそのprovenance / completenessを別に固定します。このfinite inventoryはrandom samplingのcandidate集合をscriptが導出するmachine inputであり、LLMがrandom candidate refsを都合よく手作成しません。

### Step 3: representative sample set

Step 3開始時に、sampling procedureを使うか、製品全体をselected sample setとしてsamplingをskipするかを確定します。

samplingをskipできるのは、currentなtarget inventoryまたは同等のauthoritative sourceからin-scope sample全体を列挙でき、semantic layerが「製品全体を評価可能」と判断できる場合です。scriptは次をmaterializeします。

- sampling procedure: skipped
- sampling skip rationale
- completeなin-scope inventory / provenance
- selected sample set = 全in-scope sample refs
- structured sample / random sample / Step 4.3 = not-applicable

samplingをskipしてもcomplete processの識別とStep 4.2評価は省略しません。inventory completenessを確認できない場合はsampling skipを選びません。

それ以外はsampling procedureを使用し、以下のstructured / random sample contractへ進みます。

#### structured sample

Step 2で識別した、

- common views
- essential functionality
- sample types
- technologies relied upon
- other relevant samples

を反映するstructured sample setを作ります。

#### random sample

structured sample setとは別に、target scope全体からrandom sample setを選びます。

WCAG-EM 2.0の10%要件を満たすため、本Planの整数化規則は次とします。

```text
random_sample_target_count = ceil(structured_sample_count * 0.10)
```

このceilingは「10%未満へ切り捨てない」ための実装規則であり、WCAG-EM本文が丸め方を規定しているとは表現しません。

random sampleは、

- structured sampleと重複しない
- 同一sampleを重複選択しない
- target scope全体から選択可能な方法を使う
- 個々の選択がpredictable patternに従わない
- selection methodを記録する

ことを必須にします。

target scopeをfinite inventoryとして列挙できる場合、`sampling.py` がcurrent inventoryからscope内candidateを導出し、duplicate除去とstructured sample除外を行ってからrandom selectionします。Agent / LLMが `candidate sample refs` を手で列挙しません。

target全体を有限列挙できない場合も、LLMが個々のsample identityをrandom sampleとして選びません。manual list、crawler / server log / search等から有限なcandidate listを得られる場合はそのlistをscriptへ渡してrandom selectionします。外部tool自体がrandom selectionを行う場合は、tool / method / candidate scope / provenance / selected sampleを記録し、scriptがcount / duplicate / overlap / methodを検証します。LLMはmethodの適用性を判断できますが、selected sample identityを手選択しません。

選択方法が既存sampleを選び、別のunique sampleが存在する場合は再選択します。新しいunique sampleが存在しない場合は、その事実と候補母集団を記録してStep 3.2を完了できます。

random selectionそのものを固定seedで決定論化しません。

#### complete process

structured / random sampleにcomplete processが含まれる場合、

- starting point
- default sequence
- commonly accessed / critical branch sequence

はsemantic layerが意味上のsequenceとして識別します。sequence内のsample union、duplicate除去、`process-added` sampleの追加、process membership、countはscriptがmaterializeし、LLMが同じsample集合を別途手組みしません。

### Step 4: evaluation

`assets/wcag-2.2-requirements.json` のversioned static catalogからtarget levelに必要なSuccess Criteria / conformance requirementsをscriptが導出し、selected sample setをその期待集合に対して評価します。formal初期実装ではWCAG 2.2だけを扱います。

- complete process外のinitial sample
- complete process
- structured / random sample comparison

を分離して記録します。

各sampleの評価ではtarget levelのSuccess Criteriaだけでなく、WCAG 2のconformance requirementsを確認します。

### Step 4.3: structured / random comparison

semantic layerは各sample / findingについて、今回のevaluation artifact内で比較に使うnormalized content type key / finding group keyを意味判断として確定します。global identityにはしません。

scriptはstructured / randomのkey集合差分から、

- new content type detected
- new finding detected
- new content / finding refs
- `closed / return-to-step-2-3`

を導出します。LLMがbooleanや次actionを手入力しません。

差分がある場合、semantic layerが追加すべきstructured sampleを選びます。scriptはその追加を新しいstructured sample revisionへmaterializeし、次を順に実行します。

1. 新structured countから `ceil(count * 0.10)` でrandom targetを再計算する
2. 新structured setへ移った旧random sampleをrandom setから除外する
3. structuredと重複せずcurrentな旧random sampleは保持する
4. target countへ不足する件数だけ、現在のcandidate scope / provenanceに従って追加random selectionする
5. 追加random sampleにcomplete processが含まれる場合はprocess-added sampleを再materializeする
6. 新たに追加されたsample / processだけを未評価としてhandoff / evaluationへ送る。既存current resultは再利用できる
7. 新structured / random revisionで次のcomparison iterationを作る

このloopは、集合差分がなく、structured sampleが十分representativeであるというsemantic確認も成立するまで閉じません。

### Step 5: report

Step 1〜4のoutcomeをreportへ記録します。

evaluation statementはWCAG-EM 2.0の条件を満たす場合だけ任意で作成できます。

product-wide WCAG conformance claimは、WCAG-EMのrepresentative sampleがtargetを満たしたことだけでは作成しません。

aggregated accessibility scoreは生成しません。

## 4. browser observationのhandoff

`wcag-conformance-evaluation` はWCAG-EM methodology、sample set、evaluation closure、reportのownerですが、browser / session ownerにはしません。

live Web observationが必要なsample / complete processでは、次のnormalized handoffを作ります。

- handoff draft key
- originating evaluation artifact ref / revision
- workflow_ref（qa-workflow管理下の場合）
- resume operation: Step 4.1 sample / Step 4.2 process
- sample ref
- process ref（存在する場合）
- required requirement / Success Criterion refs
- required state / action / sequence
- browser / environment / role / permission条件
- accessibility support baselineから必要なuser agent / assistive technology条件
- side-effect / cleanup条件
- required evidence kind
- evidence safety constraint

複数Skillが必要なworkflowでは `qa-workflow` がこのhandoffを受け、`usability-inspection` をbrowser ownerとして直列実行し、immutableなinspection artifact / evidence refsを戻します。

formal要求から `wcag-conformance-evaluation` が直接発火した場合も、live observationが必要になり同一Agent環境で `qa-workflow` が利用可能なら、formal Skillはhandoff requirementを `qa-workflow` へ返します。`qa-workflow` はoriginating evaluation / revision、handoff ref、resume operation、expected sample / process / requirement refsをworkflow stateへ保持し、currentかつvalidなreturned inspection artifact / evidence集合が期待handoff集合を満たした場合だけ同じevaluationをresumeします。ユーザーへ別依頼として再入力させず、formal Skill自身がbrowser ownerへ変形もしません。

`wcag-conformance-evaluation` はsibling Skillの `scripts/` を直接import / 実行しません。

`qa-workflow` を利用できない真のstandalone環境では、

- callerから必要なcurrent observation / evidence artifactをInputとして受け取る
- live observationが不足する場合はrequired handoffをOutputし、formal evaluationを `blocked` のまま終了する

のどちらかとします。不足evidenceを推測して評価を完了しません。

既存の `test-target-inspection` / `test-execution` evidenceが今回のsample / conditionと一致しcurrentである場合はread-only evidenceとして再利用できます。

## 5. Output

成果物は少なくとも次を持ちます。

### evaluation header

- evaluation ref / revision
- evaluation type: wcag-em-2-evaluation
- evaluator
- evaluation commissioner / self-evaluation
- evaluation date / period
- target WCAG title / version / URI
- target conformance level
- digital product scope
- product enclosure / scope boundary
- out-of-product boundary / reason（存在する場合）
- accessibility support baseline
- additional requirements
- limitations

### exploration

- common views
- essential functionality
- variety of sample types
- technologies relied upon
- other relevant samples

### observation handoff

live observationが必要な場合:

- handoff ref
- sample / process ref
- required requirement refs
- required state / action / sequence
- execution conditions
- evidence safety / cleanup conditions
- returned inspection artifact / evidence refs
- status: satisfied / blocked

### sample set

- structured samples
- random samples
- random sample target count
- random selection method
- random selection candidate scope / limitation
- complete processes
- default / critical branch sequences

### evaluation results

- sample ref
- sample kind: structured / random / process-added
- requirement / Success Criterion ref
- result
- evidence refs
- test rule result refs（存在する場合）
- limitation

### structured / random comparison

- iteration
- new content type detected: true / false
- new finding detected: true / false
- added structured sample refs
- Step 2 / Step 3 revision refs
- closure status

### report

- Step 1 outcome
- Step 2 outcome
- Step 3 outcome
- Step 4.1 outcome
- Step 4.2 outcome
- Step 4.3 outcome
- unmet requirement / Success Criterion examples
- Finding refs
- evaluation statement（条件を満たし作成した場合だけ）
- conformance claim（WCAG側のclaim条件を別途満たした場合だけ）

## 6. human expertiseの境界

WCAG-EM 2.0はWCAG、accessible design、assistive technology、障害のある利用者がdigital productを使う方法についての専門知識を前提にします。

本Skillは、Agentが未観測のassistive technology behavior、人間の利用結果、障害当事者の経験を捏造しません。

必要なexpert judgmentまたはassistive technology環境を利用できずformal evaluationを閉じられない場合は `blocked / undetermined` として残します。

## 7. 対象外

- native app / document / kiosk等のlive conformance evaluation
- WCAG 3 evaluation
- 法令適合の法的判断
- accessibility certification
- product ownerに代わるpublic statement発行責任
- human participant study
- aggregated accessibility score

## 8. 完了条件

- general accessibility inspectionと責務が分離されている
- target WCAG version / level / scope / accessibility support baselineを創作しない
- WCAG-EM 2.0 Step 1〜5へ成果物を追跡できる
- sampling procedure used / skippedを一意に閉じられる
- sampling skippedではcompleteな全体inventoryからselected sample setをmaterializeし、structured / random / Step 4.3をnot-applicableとして閉じる
- sampling usedではstructured sampleをStep 2探索結果へ追跡できる
- random sample countがPlanの10%整数化規則を満たす
- random sampleの重複 / structured sampleとの重複を検証できる
- random selection methodを記録する
- predictable fixed-seed selectionを必須化していない
- complete processを閉じる
- Step 4.3で新content / findingが出た場合、structured revision更新後のrandom target再計算、overlap除外、current random保持、不足分top-up、process再materializeまでscriptで閉じる
- Step 5.1の必須outcomeをreportできる
- evaluation statementの生成条件を満たさない場合は作成しない
- representative sampleだけからproduct-wide WCAG conformance claimを作らない
- aggregated accessibility scoreを作らない
- browser / sessionを本Skillが直接所有せず、複数Skill実行はqa-workflowが直列オーケストレーションする
- standalone packageがsibling Skillのscriptsへruntime依存しない
- 必要なexpertise / environment不足を成功扱いしない

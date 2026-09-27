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
- target WCAG version。supported valueは `2.0 / 2.1 / 2.2`
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
- previous evaluation ref / revision（再評価の場合）

target WCAG version、level、self-enclosedなdigital product scope、accessibility support baselineを確定できない場合は推測せず `unresolved` とし、formal evaluationを開始しません。WCAG 2.0 / 2.1 / 2.2はsupportedです。指定versionを別versionへ暗黙変換しません。version自体が不明・未指定の場合は `unresolved`、現在catalogを持たない将来version等が明示された場合は `unsupported` としてformal evaluationを開始しません。product内の特定page / componentを任意に除外してscopeを狭めません。

追加評価要件は任意Inputですが、指定された場合の処理は必須です。各要件についてsemantic layerが、

- 要求内容
- requester / source
- 本Skillの目的内か
- affected WCAG-EM step / output
- semantic completion condition

を確定します。本Skillの目的内要件を `out-of-scope` へ逃がしません。目的内だが現在のevidence / environmentで実行不能なら `blocked`、本Skillの目的外であれば理由付き `out-of-scope` とします。scriptは `ADDREQ-001` からartifact-local refを採番し、status `applied / blocked / out-of-scope`、required evidence / output refs、closureをmaterializeします。無視・黙示的省略を許可しません。

## 3. Function

### Step 1: evaluation scope

WCAG-EM 2.0 Step 1へ対応付けます。

- digital product scope
- conformance target
- accessibility support baseline
- additional evaluation requirements（存在する場合）

を成果物へ固定します。

scopeは自由記述だけで閉じず、少なくとも次を個別に確認します。

- third-party content / services
- language versions
- responsive / device-dependent variations
- 別origin / subdomain / hosted application等にある同一product領域
- authenticated / restricted views

semantic layerは各領域が同じdigital productへ属するか、in-scopeかを判断します。scriptは確認対象row、scope ref、in-scope / out-of-product closure、reason / evidence refをmaterializeし、未確認rowを暗黙に省略しません。

additional requirementがsample追加、全occurrence報告、特定use case / user group分析、追加解決案、Step 5.2 / 5.5出力、reportに必要な追加field / section等を要求する場合は、既存Skill責務の範囲でaffected stepへ反映します。評価内容・coverageとして本Skillの目的内なら、既存の物理出力形式で表現できないことを理由に `out-of-scope` へ逃がさず、必要情報を `applied / blocked` へ閉じます。一方、未知の外部document format、任意の第三者templateへの変換、PDF / Office生成等のrenderer自体は本Skillの評価責務とは分離し、generic template engineを追加しません。human participantを使う評価等、本Planで明示的に目的外とした要求はout-of-scope理由を残します。

accessibility support baselineは初期定義後に固定不変とは扱いません。formal evidence取得で初期baseline外のOS / browser / assistive technology / other user agentを実際に使用した場合、scriptがreturned environmentをcurrent baseline setと比較し、formal resultへ採用する組合せだけをbaselineへ追加してnew baseline revisionをmaterializeします。baseline revisionが変わった場合は関連sample resultのfreshnessを再計算します。diagnostic用途だけの環境はbaselineへ自動追加しません。

### Step 2: target exploration

少なくとも次を探索し、結果を成果物へ記録します。

- common views
- essential functionality
- variety of sample types
- technologies relied upon
- accessibilityに特に関係するその他sample

探索結果からstructured sampleの候補を意味判断します。target scopeを有限に列挙できる場合は、currentなtarget inventoryとそのprovenance / completenessを別に固定します。このfinite inventoryはrandom samplingのcandidate集合をscriptが導出するmachine inputであり、LLMがrandom candidate refsを都合よく手作成しません。

sample identityはURLだけでは決めません。currentな `test-target-inspection` の対象キー / 状態キーを利用できる場合はidentity sourceとして再利用します。利用できない場合はsemantic layerが同一view/stateか別sampleかを判断し、scriptがartifact-local sample identityをmaterializeします。duplicate / structured-random overlap / sample union / process membershipはこのidentityで判定します。

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

#### repeat evaluation

previous evaluation refがある場合、再評価としてsample lineageを保持します。

- previous sample identity / revisionをcurrent targetへ解決する
- previous sampleがcurrent scope / inventoryへ存在するかをscriptが検証する
- significant changeの有無と、比較可能性のため残すstructured sample / coverage更新のため置き換えるstructured sampleはsemantic layerが判断する
- scriptが `retained / replaced / added / unavailable` をmaterializeし、同一sampleのduplicateやstale identityを拒否する
- samplingを使う場合、previous random sampleの個別置換をLLMが選ばず、current candidate populationからscriptまたは記録済み外部random mechanismで選択する
- sampling approach / sizeを変更する場合はreasonを記録する

W3Cの「typically about half」はguidanceとして保持し、50%を固定contractにはしません。significant changeにより前回sampleとの比較可能性を維持できない場合は、その意味判断を記録してcurrent explorationからsample setを再構成します。

#### complete process

structured / random sampleにcomplete processが含まれる場合、

- starting point
- default sequence
- commonly accessed / critical branch sequence

はsemantic layerが意味上のsequenceとして識別します。sequence内のsample union、duplicate除去、`process-added` sampleの追加、process membership、countはscriptがmaterializeし、LLMが同じsample集合を別途手組みしません。

### Step 4: evaluation

target WCAG versionに対応する `assets/wcag-2.0-requirements.json` / `assets/wcag-2.1-requirements.json` / `assets/wcag-2.2-requirements.json` のいずれかから、target levelに必要なSuccess Criteria / conformance requirementsをscriptが導出し、selected sample setをその期待集合に対して評価します。別versionのcatalogを合成しません。

- complete process外のinitial sample
- complete process
- structured / random sample comparison

を分離して記録します。

各sampleの評価ではtarget levelのSuccess Criteriaだけでなく、WCAG 2の5つのconformance requirementsを確認します。

固定rule部分はversioned catalog / scriptで処理します。

- Conformance Level: target levelのrequired Success Criteria集合をcatalogから導出する。Conforming Alternate Versionを使う場合は別sampleへ数えず、元contentと合わせてfull pageとして扱う
- Full Pages: sampleの一部を任意に除外せず、responsive / automatically presented variationも同じfull page conformanceへ含める
- Complete Processes: processの全sample / stepがtarget level以上でconformすることを要求する
- Only Accessibility-Supported Ways of Using Technologies: Step 1.3 baselineへ照らしてrelied-upon technology useを評価する
- Non-Interference: relied-uponでないcontentを含め、target version catalogが固定するNon-Interference Success Criteria集合を評価する

Conforming Alternate Versionの固定条件は、target level適合、同一情報 / 機能 / human language、non-conforming contentと同程度にcurrent、W3Cが認めるreachability条件のいずれかです。これらのfield / required set / reachability alternativeはscriptが生成し、同一情報 / 機能 / language / currentnessの意味妥当性だけをsemantic layerへ残します。

Step 4.2ではcomplete process中の全contentを毎step再評価しません。current identity / evidence / freshnessから同一と機械確認できるcontent/resultは再利用し、変化したcontentとinteraction / input / notification / feedbackを評価します。同一性を確認できない場合は再評価します。

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
2. current candidate scope / inventory / provenanceからcandidate population fingerprintを再計算する
3. population fingerprintが前revisionと同じ場合、new structured setへ移った旧random sampleだけを除外し、structuredと重複せずcurrentな旧random sampleは保持する
4. population fingerprintが変わった場合、旧random selectionをstaleとしてcurrent populationからrandom setを再選択する
5. population fingerprintが同じ場合はtarget countへ不足する件数だけ追加random selectionする
6. 新random sampleにcomplete processが含まれる場合はprocess-added sampleを再materializeする
7. 既存sample resultはPR #11のfreshness検証でcurrentの場合だけ再利用する。target version / level、scope、baseline、environment、sample identity、evidence identity、catalog hash、upstream dependencyの変更でstaleになったresultは再評価する
8. 新たに必要になったsample / processだけをhandoff / evaluationへ送る
9. 新structured / random revisionで次のcomparison iterationを作る

このloopは、集合差分がなく、structured sampleが十分representativeであるというsemantic確認も成立するまで閉じません。

### Step 5: report

Step 1〜4のoutcomeをreportへ記録します。

Step 5.1では、`not-satisfied` のConformance Requirement / Success Criterionごとに最低1件のexample refを必須にします。script / validatorは `not-satisfied set - example-covered set` を計算し差分0を要求します。Step 1.4で全occurrence報告が追加要件として指定された場合は、代表example coverageとは別に全occurrence closureを検証します。

human-readable evaluation report、Step 5.3 Evaluation Statement、accompanying documentationは、本Skillが所有するMarkdown等の成果物についてaccessible formatを必須にします。少なくとも見出し構造、table header、画像 / screenshot evidenceのtext description、色や画像だけに依存しない状態表現、意味の分かるlink textを満たします。別ownerがHTML / PDF等へ変換した後の形式まで本Skillが自動保証するとは扱いません。

### Step 5 output format boundary

`wcag-conformance-evaluation` が直接所有する物理出力は次に固定します。

- canonical human-readable WCAG-EM report
- target WCAG 2.2で条件を満たす場合のEvaluation Statement
- target versionの条件を満たす場合のWCAG Conformance Claim / Statement of Partial Conformance
- Step 5.5を要求する場合のEARL 1.0 JSON-LD sidecar

外部HTML / PDF / Office文書、任意の顧客template、第三者report systemへのupload / exportは、このSkillのbuilt-in rendererにはしません。

追加評価要件が「この情報をreportへ含める」「このoccurrenceを全件出す」等の評価内容を要求する場合は目的内です。canonical reportへmaterializeし、必要ならdownstream ownerが別formatへ変換できるようにfield / refを保持します。

任意templateへの変換機構を将来用途だけでgeneric plugin / template engine化しません。
Step 5.2 Evaluation Specificsは要求・合意がある場合に記録し、sample archive / evidence / path / settings / actions / tool / browser / assistive technology / software / methodを安全な参照として保持します。secretや不要PIIは保存しません。

WCAG-EM Evaluation Statementは任意ですが、現行WCAG-EM 2.0 Step 5.3のminimum fieldがWCAG 2.2を固定指定するため、target WCAG versionが2.2の場合だけ通常statement / partial conformance statementの生成条件を評価します。WCAG 2.0 / 2.1のformal evaluationはStep 5.1 reportまで生成しますが、Step 5.3準拠のEvaluation Statementとは称しません。

WCAG Conformance Claimはrepresentative sampleだけから作成しません。claim scope内の全Web page / complete processを評価した証拠、または各pageがconformance requirementsを満たすことを保証するprocess evidenceがあり、指定versionのWCAG Conformance Claim必須fieldをすべて埋められる場合だけ生成します。guideline title / version / claim URIはsource取得用URLと分離したversioned catalog fieldを使用します。third-party contentをmonitoring / repairによりfull conformanceへ含める場合は、全該当pageでnon-conforming contentを識別でき、継続monitoringが可能で、検出したnon-conforming contentを2 business days以内にremove / bring into conformanceできるevidenceを必須にします。

WCAG側のStatement of Partial ConformanceはConformance Claimと分離し、third-party contentまたはlanguageの条件を満たす場合だけ生成します。

Step 5.5 machine-readable reportを要求する場合はEARL 1.0 JSON-LD sidecarを生成し、human-readable reportとassertion coverageを一致させます。

aggregated accessibility scoreはStep 5.4の目的外機能として生成しません。

### Step 4.4: criterion evaluation plan

target WCAG version / levelからrequired Success Criterion集合を導出した後、各sample / processについて `_05h_wcag-criterion-evaluation-contract.md` の `wcag_criterion_plan.py` で全criterion rowをmaterializeします。

- required Success Criterion集合とcriterion row集合の差分をscriptで0件にする
- versioned requirements assetのevaluation metadataから必要capability / machine step / semantic-manual stepを取得する
- live observationが必要なrowだけformal handoffへ変換する
- supported ACT Ruleやmachine measurementがないcriterionもsemantic/manual / assistive technology経路を持つ
- required evidence不足を `undetermined / blocked` に閉じ、LLMの推測で `satisfied` にしない

required criterion rowに `pending / in-progress` が残る場合、sample evaluationとformal evaluationを完了扱いしません。

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
- previous evaluation ref / revision（再評価の場合）
- evaluation type: wcag-em-2-evaluation
- evaluator
- evaluation commissioner / self-evaluation
- evaluation date / period
- target WCAG title / version / URI
- target conformance level
- digital product scope
- product enclosure / scope boundary
- scope coverage rows: third-party / language / responsive-device / separately-hosted / authenticated-restricted
- out-of-product boundary / reason（存在する場合）
- accessibility support baseline / baseline revision
- additional requirement refs
- limitations

### additional evaluation requirements

存在する場合、各row:

- additional requirement ref
- requester / source
- requirement summary
- affected step / output refs
- status: applied / blocked / out-of-scope
- required evidence / output refs
- closure evidence / reason

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
- 再評価の場合のretained / replaced / added / unavailable sample lineage
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
- unmet requirement / Success Criterion examples。各not-satisfied requirement / Success Criterionを最低1件cover
- report accessibility closure
- Finding refs
- Evaluation Specifics（要求・合意があり記録した場合だけ）
- Evaluation Statement（通常 / partial。現行WCAG-EM 2.0 Step 5.3準拠はtarget WCAG 2.2だけ）
- WCAG Conformance Claim（条件を満たし作成した場合だけ）
- WCAG Statement of Partial Conformance（third-party content / language。条件を満たし作成した場合だけ）
- EARL 1.0 JSON-LD report（要求された場合だけ）

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
- third-party / language / responsive-device / separately-hosted / authenticated-restricted領域をscope coverageとして明示的に閉じる
- initial baseline外の環境をformal evidenceへ使った場合にbaseline revisionをscriptで拡張し、freshnessを再計算できる
- WCAG-EM 2.0 Step 1〜5へ成果物を追跡できる
- Step 1.4 additional evaluation requirementsをartifact-local refへ採番し、目的内要件はaffected step / outputへ反映してappliedまたはblockedへ、目的外だけを理由付きout-of-scopeへ閉じる
- sampling procedure used / skippedを一意に閉じられる
- sampling skippedではcompleteな全体inventoryからselected sample setをmaterializeし、structured / random / Step 4.3をnot-applicableとして閉じる
- sampling usedではstructured sampleをStep 2探索結果へ追跡できる
- 再評価ではprevious sampleをcurrent identityへ解決し、retained / replaced / added / unavailable lineageをmaterializeできる。50% replacementを固定規則にしない
- random sample countがPlanの10%整数化規則を満たす
- artifact-local sample identityでrandom sampleの重複 / structured sampleとの重複を検証できる
- random selection methodを記録する
- predictable fixed-seed selectionを必須化していない
- 5つのWCAG conformance requirementsをversioned catalog / semantic decisionへ分解し、Conforming Alternate Versionを別sampleにせず、Non-Interference固定SC集合をscriptで導出できる
- complete processを閉じ、Step 4.2ではcurrentで同一なcontent/resultを再利用して変化部分とinteractionを評価できる
- Step 4.3で新content / findingが出た場合、structured revision更新後のrandom target再計算、candidate population fingerprint再計算、population同一時のoverlap除外 / current random保持 / 不足分top-up、population変更時のrandom再選択、process再materializeまでscriptで閉じる
- 既存sample resultはPR #11のfreshness判定がcurrentの場合だけ再利用する
- Step 5.1の必須outcomeをreportでき、各not-satisfied Conformance Requirement / Success Criterionを最低1exampleへ対応付けられる
- Step 1.4で全occurrence報告が要求された場合は代表exampleとは別に全occurrence closureを検証できる
- human-readable report / Evaluation Statement / accompanying documentationを本Skill所有形式ではaccessible output contractへ閉じられる
- Step 5.2 Evaluation Specificsを要求時に安全に記録でき、secret / unnecessary PIIを複製しない
- 現行WCAG-EM 2.0 Step 5.3 Evaluation Statementはtarget WCAG 2.2だけで通常 / partial生成条件を閉じ、WCAG 2.0 / 2.1ではStep 5.3 statementを生成しない
- representative sampleだけからWCAG Conformance Claimを作らない
- WCAG Conformance ClaimとWCAG Statement of Partial Conformanceの必須 / optional field / generation guardを分離して検証する
- claim guideline URIをsource URLと分離し、third-party monitoring / repair経路では2 business days条件と全該当pageでの識別可能性をmachine guardで検証する
- Step 5.5 EARL 1.0 JSON-LD reportを要求時に生成し、human-readable reportと一致検証できる
- Step 5.4 aggregated accessibility scoreは目的外として作らない
- browser / sessionを本Skillが直接所有せず、複数Skill実行はqa-workflowが直列オーケストレーションする
- standalone packageがsibling Skillのscriptsへruntime依存しない
- 必要なexpertise / environment不足を成功扱いしない

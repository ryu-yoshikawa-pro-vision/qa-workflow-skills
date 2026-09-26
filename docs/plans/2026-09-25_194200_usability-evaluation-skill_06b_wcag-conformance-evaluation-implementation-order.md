# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` の実装順と完了条件を固定します。

## 1. 実装開始条件

- PR #11 merge済みcurrent runtime確認
- PR #12はmainへmerge済みでcurrent実装を確認済み
- PR #13 main merge済み
- usability-inspectionのgeneral accessibility / browser observation contract成立
- WCAG-EM 2.0 / WCAG 2.2 current official source確認
- repository標準eval / CI確認

## 2. Step 0: baseline

latest mainで、

- Skill一覧
- Activity / artifact identity
- browser ownership
- evidence safety
- side-effect / cleanup
- Finding
- qa-workflow routing
- Playwright execution path

を再確認します。

## 3. Step 1: package / source

`_05f_wcag-conformance-evaluation-package-and-runtime.md` のpackageを作ります。

source-catalogへ少なくとも、

- WCAG 2.2
- WCAG-EM 2.0
- WCAG-EM Report Tool。WAI Overview上の公式resourceとして保持するが、WCAG-EM 2.0本文と同一の成果物schemaを提供することは前提にせず、WCAG-EM 2 schema Authorityにはしない
- ACT Rules Format 1.1 / All ACT Rules
- Understanding Accessibility Support

をcurrent URL / status / checked_at付きで登録します。

## 4. Step 2: output contract

browser操作前にoutput-templateとvalidator最小schemaを実装します。

WCAG-EM 2のoutput contractはReport ToolのschemaではなくWCAG-EM 2.0本文を正本にします。Step 5.1のStep 1〜4 outcome closureと、Step 5.3のoptional evaluation statement minimum fieldsを別々に固定します。

先に次をfixtureで固定します。

- required Input
- supported WCAG version = 2.2 / unsupported version rejection
- static requirement catalog / target level expected set
- evaluation header
- accessibility support baseline
- exploration
- structured / random sample
- complete process
- sample result
- Step 4.3 comparison
- Step 5.1 report outcome closure
- Step 5.3 evaluation statement minimum fields / generation guard
- conformance claim guard

## 5. Step 3: production helper

`wcag_requirements.py`、`sampling.py`、`wcag_em_structure.py` を実装します。

### requirements

- supported WCAG versionを2.2へ固定
- `assets/wcag-2.2-requirements.json` からA / AA / AAAごとのrequired Success Criteria集合を導出
- 5つのconformance requirement集合を別に導出
- 2.0 / 2.1等はunsupported / unresolved
- actual result coverageをLLM supplied listではなくstatic expected setと比較

### sampling

- 10% count計算。WCAG-EM本文の丸め規則ではなく本Planの `ceil` 規則として扱い、structured count 1 / 9 / 10 / 11の境界fixtureを持つ
- finite inventoryからrandom candidate集合を導出し、structured sampleを除外
- target全体を有限列挙できない場合はrecorded method / candidate scope / provenanceを検証
- duplicate / overlap検証
- optional random select
- fixed seed禁止
- complete process sequenceからsample union / process-added sampleを導出
- normalized content type / Finding group keyの集合差分からStep 4.3 boolean / actionを導出
- selection method記録
- no-new-sample completion

### structure

- semantic decisionからfixed machine rowをmaterialize
- draft ref採番
- cross-reference
- Step closure
- static expected requirement coverage
- handoff expected / returned closure
- comparison iteration chain
- machine-owned Markdown render
- summary

production helperとdeterministic validatorは別実装にします。

## 6. Step 4: methodology vertical slice

小さいWeb targetで、

1. scope
2. exploration
3. structured sample
4. random sample
5. complete process
6. sample evaluation
7. comparison
8. report

を1本通します。

この時点では全repo integrationへ広げません。

## 7. Step 5: qa-workflow observation handoff

selected sampleごとにlive accessibility observationが必要なcaseで、

- wcag-conformance-evaluationがsample / requirement scope、originating evaluation / revision、resume operationを固定してnormalized handoffを出す
- qa-workflowがhandoffとexpected sample / process / requirement refsをworkflow stateへ記録する
- usability-inspectionがbrowser ownerとして直列実行する
- immutable evidence / inspection artifact refをhandoff ref付きでqa-workflowへ返す
- qa-workflow helperがexpected handoff集合とcurrent valid returned result集合を照合する
- 全expected handoffが閉じた場合だけqa-workflowが元evaluation / revision / resume operationへresultをhandoffする
- wcag-conformance-evaluationが同じevaluationをresumeしてaggregationする

ことを確認します。

sample selectionをusability-inspectionへ移しません。formal Skillからsibling Skillのscriptsを直接import / 実行しません。

formal Skillが直接発火した場合も、同一Agent環境で `qa-workflow` が利用可能ならhandoff requirementをworkflowへ返し、`usability-inspection` の結果を受けてformal evaluationをresumeします。`qa-workflow` を利用できない真のstandalone環境でcurrent evidenceがInputに不足する場合だけ、handoff requirementを出してblockedへ閉じます。

## 8. Step 6: random sampling

W3C WCAG-EM 2.0 Step 3.2へ合わせて確認します。

- target count = ceil(structured * 0.10)
- unique
- structured sampleと非重複
- finite inventoryがある場合はcurrent inventoryからcandidate集合をscript導出し、LLMがcandidate refsを手列挙しない
- finite inventoryがない場合はcandidate scope / provenance付きの別random methodを記録する
- target scope全体をselection scopeとする
- predictable fixed patternを使わない
- selection method記録
- unique candidate exhaustion

selection結果そのものをdeterministic fixtureへ固定して「random性」を証明しません。

## 9. Step 7: complete process

default sequenceとcommonly accessed / critical branch sequenceはsemantic layerがsequenceとして識別し、`sampling.py materialize-process` がsample union、duplicate除去、process-added分類、membershipを生成します。LLMがsequenceとsample setを二重管理しません。

全interactionをStep 4.2契約へ結び付けます。

## 10. Step 8: Step 4.3 loop

random sampleに新content type / findingがないcaseと、あるcaseを実装します。

semantic layerはcontent type / Findingのartifact-local grouping keyだけを確定し、`sampling.py compare` がstructured / random集合差分、detected boolean、new refs、`closed / return-to-step-2-3` を導出します。

差分がある場合:

- exploration update
- semantic layerによる追加structured sample選定
- scriptによるsample set / revision更新
- new random / process condition確認
- re-evaluation
- comparison iteration chain

を閉じます。

## 11. Step 9: report / statement

Step 5.1に従い、Step 1〜4のrequired outcomeをreportへ記録します。

evaluation statementは条件成立case / 不成立caseを分け、成立caseでは `_05f_wcag-conformance-evaluation-package-and-runtime.md` のStep 5.3 minimum fieldsをすべて保持します。

product-wide claimは通常のsample評価では生成しません。

aggregated scoreは生成しません。

## 12. Step 10: repository integration

latest mainを基準に、

- CANONICAL_SKILLS
- MULTI_USE_SKILL_TARGETSへの影響
- qa-workflow
- README
- EVALS
- ASSERTIONS
- validation workflow
- dataset counts

を同期します。

件数をPlanの古い値で固定しません。

## 13. eval

### trigger

formal WCAG要求 / general accessibility要求の境界を含めます。

### deterministic

- schema
- supported WCAG version / static requirement catalog
- target level expected Success Criteria / conformance requirement set
- observation handoff origin / resume identity / expected-returned closure
- ref
- sample count
- finite inventory candidate derivation / recorded method provenance
- duplicate / overlap
- process sequence → process-added sample materialization
- Step 4.3 set difference → boolean / action derivation
- machine-owned structured section materialization
- closure
- report
- statement / claim guard

### semantic

`_05f` Case A〜Kをすべて実Judgeで確認します。

### real Agent / browser

`_06c_canonical-live-validation.md` のrepository-controlled canonical fixtureで、formal direct trigger → observation handoff → qa-workflow → usability-inspection → formal Skill resume → reportまでのWCAG-EM E2Eを実行します。

外部実対象・実アカウント・特定assistive technologyを必要とするacceptanceは別ゲートです。それらが提供されていないことだけでrepository implementationを未完了にしません。

## 14. 完了条件

- Skill責務がusability-inspectionと分離
- qa-workflowがmulti-Skill observation handoffを直列オーケストレーション
- standalone packageがsibling Skill scriptsへruntime依存しない
- WCAG-EM Step 1〜5 traceability
- WCAG-EM 2 output schemaがReport Toolへ依存せず、WCAG-EM 2.0本文を正本としている
- accessibility support baseline必須
- WCAG 2.2だけをsupported versionとし、target levelからrequired Success Criteria / conformance requirement集合をstatic catalogで独立導出
- Step 2 exploration closure
- Step 3.1 structured sample
- Step 3.2 random sample。finite inventory時のcandidate集合はscript導出、非finite時はmethod / provenanceを保持
- Step 3.3 complete process。sequenceからprocess-added sample / membershipをscript導出
- Step 4.1 / 4.2評価
- Step 4.3 retry loop。semantic grouping keyから集合差分 / boolean / actionをscript導出
- Step 5.1のStep 1〜4 required outcome closure
- Step 5.3 optional evaluation statement minimum fields / generation guard
- product-wide claim guard
- requirements / sampling / structure helperでmachine-owned fieldをmaterializeし、Agentがfinal refs / expected集合 / derived status / countを手作成しない
- independent deterministic validator
- trigger / deterministic / semantic PASS
- `_06c_canonical-live-validation.md` のrepository-controlled canonical Web E2E PASS
- repository-controlled validationのblocked 0。外部acceptance未実施は別statusとして記録し、このblocked件数へ含めない

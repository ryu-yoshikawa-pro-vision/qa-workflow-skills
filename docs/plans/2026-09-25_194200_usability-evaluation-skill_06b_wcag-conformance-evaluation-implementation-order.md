# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` の実装順と完了条件を固定します。

## 1. 実装開始条件

- PR #11 merge済みcurrent runtime確認
- PR #12 / #13 main merge済み
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
- WCAG-EM Report Tool
- ACT Rules Format 1.1 / All ACT Rules
- Understanding Accessibility Support

をcurrent URL / status / checked_at付きで登録します。

## 4. Step 2: output contract

browser操作前にoutput-templateとvalidator最小schemaを実装します。

先に次をfixtureで固定します。

- required Input
- evaluation header
- accessibility support baseline
- exploration
- structured / random sample
- complete process
- sample result
- Step 4.3 comparison
- report
- statement / claim guard

## 5. Step 3: production helper

`sampling.py` と `wcag_em_structure.py` を実装します。

### sampling

- 10% count計算
- duplicate / overlap検証
- optional random select
- fixed seed禁止
- selection method記録
- no-new-sample completion

### structure

- draft ref採番
- cross-reference
- Step closure
- result coverage
- comparison iteration chain
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

- wcag-conformance-evaluationがsample / requirement scopeを固定してnormalized handoffを出す
- qa-workflowがhandoffをworkflow stateへ記録する
- usability-inspectionがbrowser ownerとして直列実行する
- immutable evidence / inspection artifact refをqa-workflowへ返す
- qa-workflowがformal Skillへresultをhandoffする
- wcag-conformance-evaluationがaggregationする

ことを確認します。

sample selectionをusability-inspectionへ移しません。formal Skillからsibling Skillのscriptsを直接import / 実行しません。

standalone formal Skillではcurrent evidenceがInputに不足する場合、handoff requirementを出してblockedへ閉じます。

## 8. Step 6: random sampling

W3C WCAG-EM 2.0 Step 3.2へ合わせて確認します。

- target count = ceil(structured * 0.10)
- unique
- structured sampleと非重複
- target scope全体をselection scopeとする
- predictable fixed patternを使わない
- selection method記録
- unique candidate exhaustion

selection結果そのものをdeterministic fixtureへ固定して「random性」を証明しません。

## 9. Step 7: complete process

default sequenceとcommonly accessed / critical branch sequenceをsample setへ含めます。

全interactionをStep 4.2契約へ結び付けます。

## 10. Step 8: Step 4.3 loop

random sampleに新content type / findingがないcaseと、あるcaseを実装します。

ある場合:

- exploration update
- structured sample update
- new random / process condition確認
- re-evaluation
- comparison iteration chain

を閉じます。

## 11. Step 9: report / statement

Step 5.1 required outcomeをreportへ記録します。

evaluation statementは条件成立case / 不成立caseを分けます。

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
- observation handoff schema / closure
- ref
- sample count
- duplicate / overlap
- closure
- report
- statement / claim guard

### semantic

`_05f` Case A〜Kをすべて実Judgeで確認します。

### real Agent / browser

canonical live Web targetでWCAG-EM E2Eを実行します。

実行環境・必要expertise・必要assistive technologyを利用できず必須caseを閉じられない場合はblockedであり、実装完了にはしません。

## 14. 完了条件

- Skill責務がusability-inspectionと分離
- qa-workflowがmulti-Skill observation handoffを直列オーケストレーション
- standalone packageがsibling Skill scriptsへruntime依存しない
- WCAG-EM Step 1〜5 traceability
- accessibility support baseline必須
- Step 2 exploration closure
- Step 3.1 structured sample
- Step 3.2 random sample
- Step 3.3 complete process
- Step 4.1 / 4.2評価
- Step 4.3 retry loop
- Step 5.1 report
- optional statement guard
- product-wide claim guard
- sampling helper / structure helper
- independent deterministic validator
- trigger / deterministic / semantic PASS
- canonical real Web E2E PASS
- blocked 0

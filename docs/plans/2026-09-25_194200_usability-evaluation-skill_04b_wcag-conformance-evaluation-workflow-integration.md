# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` と既存workflow / Skillのroutingとbrowser ownershipを固定します。

## 1. direct trigger

次は `wcag-conformance-evaluation` へroutingします。

- WCAG 2.2 AAに適合しているか評価
- WCAG conformance evaluationを実施
- WCAG-EM 2.0で評価
- WCAG適合評価reportを作成

「accessibilityを確認」「keyboard / focusを確認」のようなformal conformanceを要求しない依頼は `usability-inspection` のgeneral accessibility inspectionです。

## 2. usability-inspection

`wcag-conformance-evaluation` はsample selection / WCAG-EM methodology / evaluation closure / reportを所有します。

個別sampleでlive Web observationが必要な場合だけ、required sample / required requirement setを明示して `usability-inspection` を直列利用します。

`qa-workflow` からhandoffされた `usability-inspection` は、

- sampleを独自追加 / 除外しない
- target WCAG levelを変更しない
- product-wide conformanceを判断しない
- WCAG-EM Step 4.3 comparisonを担当しない

ことを必須にします。

## 3. usability-evaluation

general UI / UX expert evaluationはformal WCAG reportの正本にしません。

WCAG evaluation中にUI / UX上の別懸念を評価する明示要求がある場合だけ、immutable evidenceを `usability-evaluation` へ渡します。

WCAG requirement resultをheuristic評価で上書きしません。

## 4. test-target-inspection / test-execution

既存のcurrent evidenceが、

- 同じtarget / state / role
- 同じviewport / browser条件
- 必要なWCAG requirementの観測に十分
- currentnessを確認可能

な場合はread-only evidenceとして再利用できます。

不足分はformal evaluation側がobservation handoffとして要求し、`qa-workflow` が必要な `usability-inspection` を直列実行します。

既存TC PASS / FAILをWCAG conformance resultへ変換しません。

## 5. qa-workflow

複合要求ではqa-workflowがroutingします。

例:

```text
release前のWCAG 2.2 AA評価
→ wcag-conformance-evaluation
→ selected sampleごとに必要なら usability-inspection
→ WCAG-EM report
```

```text
WCAG評価とUI / UX専門評価
→ wcag-conformance-evaluation
→ required live observation
→ WCAG-EM report
→ 明示されたUI / UX scopeだけ usability-evaluation
```

## 6. Finding

WCAG evaluationで後続QA活動が必要なnon-conformance / unresolved itemはPR #13のFindingへroutingできます。

Findingを作ってもWCAG-EM report内のrequirement resultを置き換えません。

## 7. browser / session

同じbrowser / sessionを複数Skillが同時操作しません。

sample observationが必要な場合:

1. wcag-conformance-evaluationがsample / requirement scopeを固定してhandoffを出す
2. qa-workflowがhandoffをworkflow stateへ記録する
3. usability-inspectionがbrowser ownerとして操作する
4. immutable evidence / resultをqa-workflowへ返す
5. qa-workflowがresult refをwcag-conformance-evaluationへhandoffする
6. wcag-conformance-evaluationが集約する

を直列に行います。

standalone `wcag-conformance-evaluation` はsibling Skillのscriptsを直接実行しません。必要evidenceがInputにない場合はhandoff requirementを出してblockedになります。

## 8. 完了条件

- formal WCAG要求がusability-inspectionへ誤routingされない
- general accessibility要求がformal evaluationへ誤routingされない
- sample selection ownerがwcag-conformance-evaluationへ一意
- browser ownerが同時に複数存在しない
- multi-Skill executionをqa-workflowがownerし、formal Skillがsibling scriptsへruntime依存しない
- TC result / expert evaluation / WCAG resultを混同しない
- Findingがreportの正本を置き換えない

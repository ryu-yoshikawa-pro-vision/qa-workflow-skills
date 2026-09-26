# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` と既存workflow / Skillのroutingとbrowser ownershipを固定します。

## 1. direct trigger

次は `wcag-conformance-evaluation` をformal methodology ownerとして最初に選びます。

- WCAG 2.2 AAに適合しているか評価
- WCAG conformance evaluationを実施
- WCAG-EM 2.0で評価
- WCAG適合評価reportを作成

直接発火は「formal Skillだけで最後まで実行する」という意味ではありません。sample / complete processでcurrent live observationが必要になった場合は、同一Agent環境で `qa-workflow` が利用可能なら次の経路へ遷移します。

```text
formal request
→ wcag-conformance-evaluation
→ observation handoff requirement
→ qa-workflow
→ usability-inspection
→ immutable observation / evidence
→ qa-workflow
→ wcag-conformance-evaluation resume
→ WCAG-EM report
```

この遷移でユーザーへ別依頼として再入力させません。`wcag-conformance-evaluation` がbrowser ownerへ変形したり、sibling Skillのscriptを直接実行したりもしません。handoffはoriginating evaluation / revision、handoff ref、resume operation、expected sample / process / requirement refsを持ち、別evaluationへ誤って戻らないようにします。

`qa-workflow` を利用できない真のstandalone環境では、必要なcurrent evidenceがInputにない場合だけhandoff requirementを出して `blocked` へ閉じます。

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

1. wcag-conformance-evaluationがsample / requirement scopeを固定し、originating evaluation / revisionとresume operationを含むhandoffを出す
2. qa-workflowがhandoffとexpected sample / process / requirement refsをworkflow stateへ記録する
3. usability-inspectionがbrowser ownerとして操作する
4. immutable evidence / resultをhandoff ref付きでqa-workflowへ返す
5. qa-workflowのproduction helperがexpected handoff集合とcurrent valid returned result集合を照合する
6. 全expected handoffが閉じた場合だけqa-workflowが元のwcag-conformance-evaluation / revision / resume operationへresult refsを返す
7. wcag-conformance-evaluationが同じevaluationをresumeして集約する

を直列に行います。

`wcag-conformance-evaluation` はsibling Skillのscriptsを直接実行しません。同一Agent環境で `qa-workflow` が利用可能ならhandoffをworkflowへ返してresumeします。`qa-workflow` を利用できない真のstandalone環境で必要evidenceがInputにない場合だけ、handoff requirementを出してblockedになります。

## 8. 完了条件

- formal WCAG要求がusability-inspectionへ誤routingされない
- general accessibility要求がformal evaluationへ誤routingされない
- sample selection ownerがwcag-conformance-evaluationへ一意
- browser ownerが同時に複数存在しない
- formal direct triggerからlive observationが必要になった場合にoriginating evaluation / revision / resume operationを保持してqa-workflow → usability-inspection → formal Skill resumeへ一意に遷移できる
- expected handoff集合とcurrent valid returned result集合のclosureをproduction helperで検証し、LLMの手判断でresumeしない
- multi-Skill executionをqa-workflowがownerし、formal Skillがsibling scriptsへruntime依存しない
- TC result / expert evaluation / WCAG resultを混同しない
- Findingがreportの正本を置き換えない

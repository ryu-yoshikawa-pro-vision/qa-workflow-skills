# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは、`usability-evaluation`、`usability-inspection`、`wcag-conformance-evaluation` の実装完了判定に使うcanonical Agent / browser E2Eと、外部実対象でのacceptanceを分離します。

目的は、実装完了条件を外部URL、実アカウント、secret、特定の顧客環境、利用可否が不定なassistive technologyへ依存させず、同時に「実browser経路を未検証のまま完成」ともしないことです。

## 1. 完了状態を分離する

### repository implementation

repository内で再現可能なfixtureと既存のAgent / browser実行基盤を使い、今回追加するSkill contractとmulti-Skill routingを端から端まで検証します。

repository implementationの完了には本ファイル§2〜§6をPASSする必要があります。

### external acceptance

実案件のURL、実アカウント、実データ、特定browser / assistive technology、顧客固有Authority等が提供された場合に、その環境で追加確認します。

external acceptanceが要求されていない、または必要入力が提供されていないことだけでrepository implementationを未完了にしません。

一方、ユーザー要求またはrelease gateが特定の外部実対象での検証を明示している場合、その要求はexternal acceptanceのblockedとして残し、repository fixtureのPASSで代替しません。

## 2. canonical fixtureの要件

実装時にrepository内へ、またはrepositoryから固定手順で起動できるWeb fixtureを1つ定義します。既存fixtureで要件を満たせる場合は新設しません。canonical validationのためだけに新しいbackend、database、authentication system、browser frameworkを追加せず、必要なら最小のstatic HTML / JavaScript fixtureで成立させます。

fixtureは少なくとも次を満たします。

- start commandまたは固定起動手順をrepositoryから特定できる
- entry pointを固定できる
- 外部認証、実secret、個人データを必須にしない
- test role / permissionを固定できる。認証不要ならその事実を明記する
- 初期dataとreset / cleanup手順を固定できる
- side effectがfixture内で閉じる
- browser / viewport / input methodを固定できる
- 複数viewまたはstateを持ち、samplingを使うstructured sample / random sample / complete processの経路検証ができる
- 同一URLで異なるstateと、同一stateへ別経路で到達するcaseを持ち、sample identity canonicalizationをbrowser evidence付きで検証できる
- complete process内に、共通header等のunchanged contentとinteraction後に変化するcontentを持ち、Step 4.2のcurrent-result reuse境界を検証できる
- 必要なら同一static fixture内の別pathでConforming Alternate Version候補を表現できる。新しいserver / originはこのためだけに追加しない
- 同じfixture server内に、製品全体を列挙できる小さいself-enclosed product scopeを持ち、sampling procedure skip経路を追加serverなしで検証できる
- keyboard / focus、visual / responsive、general accessibility observationを少なくとも1件ずつ実行できる
- `_05g` のviewport / geometry / document location / rendered text / control value / selected value / accessibility semantics / responsive-boundaries / interaction-timing fixed probeをfixture上で検証できる
- responsive boundary取得ではreadable sourceと、意図的にcomplete扱いできないunreadable-source contract caseをdeterministic fixtureで再現できる
- taskなしpage inspectionと、明示task / flow inspectionの両方を実行できる
- intentional issueを使う場合はfixture contractとして期待状態を固定し、実製品の仕様と混同しない

performance値そのものを安定した製品SLOとしてfixtureへ持ち込みません。measurement経路を検証する必要がある場合は、start / end eventとclock domainを固定できるfixture挙動を使います。

## 3. canonical environment contract

実装時にfixtureと一緒に次を固定します。

- fixture identifier / path
- start command
- base URL / entry point
- browser engine
- desktop viewport
- responsive viewport
- touch / mobile profileを使う場合のdevice profile
- input method
- localeが結果へ影響する場合のlocale
- role / permission
- initial data
- allowed side effects
- cleanup / reset
- timeoutはrepository既存基準があればそれを使用する
- evidence保存境界

current Playwright versionやPR #12 / #13 merge後のbrowser contractが変わった場合はcurrent implementationを正本にしてこの値を確定します。Plan内で存在しないAPIや固定versionを創作しません。

## 4. Skill別canonical E2E

### usability-evaluation

少なくとも次を確認します。

1. 保存済みfixture evidenceをread-only入力として評価できる
2. live Web targetを `usability-inspection` が観測したimmutable evidenceを評価できる
3. reference entry / source item / evidence / evaluation refを追跡できる
4. browser / sessionを `usability-evaluation` 自身が操作しない
5. 固定上位観点に直接名前がない複合的な懸念を、宣言済みscope内のevidenceから追加evaluationとして保持できる
6. 直接適用できるpublic referenceがないevidence-semantic評価を、fakeなreferenceなしでreference不使用理由 / 判断理由 / evidence付きで保持できる。一方でbest practice / standard主張はsource item refなしで成立させない
7. user / business goal / success condition / business outcomeがAuthority付きで与えられたcaseでflow全体の意味的整合を評価できるが、business logicの仕様上のPASS / FAILを再定義しない

### usability-inspection

少なくとも次を確認します。

1. taskなしpage inspection
2. task / flowありinspection
3. safe interaction
4. keyboard / focus
5. visual / responsive evidence
6. applicable general accessibility check
7. `inspection_structure.py` がgeneral / scoped / formal-handoffのscope rowをmaterializeすること
8. `observation_contract.py` が5種resolver payload、exact matching、parent scope、population revision / fingerprint、session currentnessとrequired probe requestをmaterializeし、browser resultをschema / unit / capability検証してnormalizeすること
9. responsive boundaryのmedia `px / em / rem`、条件付きcontainer `px / em / rem`、complete+boundaryなし、unreadable・unsupported、normalizedだがnot-executableによるincomplete各case
10. fixed interaction timingで8種predicateごとのpayload、same-page clock、preexisting end state、timeout、unknown attribute / ARIA state rejectを扱えること
11. measurement経路
12. cleanup
13. semantic layerがcanonical observation field / fixed predicate keyを選び、`observation_contract.py` が requester kind / state basis refs / current document identity / `OBSREQ-...` / request identity / evidence fingerprint / fixed probeへmaterializeして追加evidenceを取得し再評価できること。general accessibilityのsemantic requirementでは `inspection-requirement` requesterを使えること
14. canonical observation field inventory全15 keyがexactly-one probeへ解決し、scriptが自由記述からprobeを推論せず、unknown observation fieldをunsupportedへ閉じること
15. 同一request identity + 同一input evidence fingerprintを再実行せずno-progressを返し、state descriptionの言い換えだけでguardを回避できないこと
16. business outcome / Authority refsがあるflowで `page.url()` / `locator.innerText()` / `locator.inputValue()` / selectedOptions `{value,label}` 等のmachine observationとobserved end state / outcomeを保持し、usability-evaluationへ渡せること
17. `usability-evaluation` へのread-only handoff
18. 同一sessionを別Skillが並行操作しない

### wcag-conformance-evaluation

fixtureは製品の実WCAG適合性を証明するためではなく、methodology / orchestration contractを検証するために使います。

少なくとも次を確認します。

```text
formal request
→ wcag-conformance-evaluation
→ scope / exploration / sample
→ observation handoff
→ qa-workflow
→ usability-inspection
→ immutable result
→ qa-workflow
→ wcag-conformance-evaluation resume
→ Step 4.3 closure
→ Step 5 report
```

さらに、

- sampling procedure usedのcase
- structured sample
- random sample target-met。canonical Random Sample sectionへ `selection_status=target-met` を保存
- `_05i` のversion別Success Criterion集合 2.0=61 / 2.1=78 / 2.2=86、2.2の4.1.1除外、machine / manual / AT / external割当と全SCの `s-wcag-<SC>` 生成規則から導出したexpected procedure集合がrequirements assetと完全一致
- finite procedure catalogの全key解決 / machine dispatch / approved hash。inventoryにないkey / catalogにないkey / unused keyを許可しない
- sample × required presentation variation × required Success Criterionのcriterion plan coverage
- current criterion evaluation refからだけSample Evaluation Resultsを生成し、LLM supplied result listをreject
- semantic procedureが追加evidenceを必要とするcaseで、required criterion / procedure集合を変更せずfixed observation requestを追加し、new handoffが必要なら `_04c` lineageで再観測して同じprocedureを再評価する
- fixed observation contractで表現できない、または同一requestがno-progressとなるcaseではad hoc probeを作らずundetermined / blockedへ閉じる
- semantic判断で別のusability / business flow concernを発見してもWCAG resultへ混ぜず別routingする
- complete candidate exhaustionによる `exhausted-no-new-view`。exhaustion evidence / provenanceをcanonical Random Sample sectionへ保存
- candidate取得不完全による `blocked`。blocked reasonをcanonical Random Sample sectionへ保存し、no-new-sample completionへ誤変換しない
- complete process
- Step 4.3で再samplingなしのcase
- semantic / fixtureでStep 4.3再samplingありのcase。structured追加後のcandidate populationが同じcaseでrandom target再計算、overlap除外、retained random、不足分top-up、process再materializeを確認する
- sampling procedure skippedのcase。completeなin-scope inventory全件がselected sample setとなり、structured / random / Step 4.3がnot-applicableでもcomplete process / Step 4.2評価が続くこと
- 同一URLの異なるstateを別sample、同じstateへの別経路を同一sampleとして扱えること
- production helperのouter envelopeと `state.handoffs` physical schema、storage-provided state revisionを区別できること
- 同じ `HANDOFF-001` でもorigin artifact / revisionが異なれば別operation refになること
- same handoff identityのCAS retry / exact immutable result再適用は同じoperation refのidempotent処理でbrowserを再開始しないこと
- browser開始済みhandoffのstale / evidence不足再観測は `HANDOFF-002` 等のnew handoff + `retry_of_handoff_ref` + new operation refになること
- handoffをworkflow stateへ `pending` CAS保存するまでbrowser ownerを開始しないこと
- mutable operation claim / canonical-order resource reservation後に `in-progress` CASを保存できた場合だけbrowser actionを開始すること
- resource取得途中失敗 / in-progress CAS conflictではbrowser未開始のままreservation逆順releaseとsafe claim recoveryを行うこと
- partial return、stale origin、conflicting current return、cleanup未完了、reservation未releaseではresumeしないこと
- normal completionでreservationを逆順releaseし、release失敗 / revision conflictではcloseしないこと
- close-ready → closed CAS → state再読込 → may-resumeの順序を満たすこと
- exact duplicate returnはidempotentに扱い、明示supersedes lineageでのみcurrent resultを置き換えること
- observation結果がPR #11 freshness契約でcurrentな場合だけformal evaluationへ再利用されること
- selected sampleにautomatically presented responsive variationが複数あるcaseで `VAR-...` をmaterializeし、1 variation未評価ではFull Pagesをsatisfiedにしないこと
- unreadable / unsupported / not-executable responsive conditionでvariation completenessを閉じられない場合にFull Pagesをundetermined / blockedへ残すこと
- Step 4.2でunchangedかつcurrentなcontent resultは再利用し、interaction後にchanged / unknownとなったcontentだけを再評価すること
- Conforming Alternate Version候補を別sampleへ数えず、primary contentと同じfull-page evaluationへ紐付けること
- Step 1.4 additional evaluation requirementとして「代表sampleに加えてfixtureの特定viewを追加評価し、Step 5.5 reportも出力する」を指定し、`ADDREQ-001` 等のref、sample追加、output closureまで同一evaluationで追跡できること
- Step 5.1 outcome closure
- not-satisfied requirement / Success Criterionごとのexample coverageと、all-occurrence追加要件がある場合の追加coverage
- report materialization / accessible output contract
- Step 5.2 Evaluation Specificsを有効化したcaseで、browser / tool metadataとsafe evidence refがreportへ戻ること。secret値は保持しない
- Step 5.5を有効化したcaseで、browser observation由来のformal resultがEARL assertionへ対応しhuman-readable reportと一致すること

を確認します。

repository fixtureだけを根拠に「実製品がWCAGへ適合した」とは報告しません。

## 5. assistive technology / expertise

WCAG-EMで必要なexpert judgmentやassistive technologyの利用可否は、formal evaluationの実案件条件として重要です。

canonical repository E2Eでは、

- accessibility support baseline field
- assistive technology条件のhandoff
- 利用不能時の `undetermined / blocked`
- evidence / limitationの保持

という処理経路を検証できます。

一方、特定のscreen reader等を実際に利用した結果が必要な要求はexternal acceptanceです。実環境がない場合に成功を仮定せず、そのexternal acceptanceだけをblockedにします。

## 6. 完了条件

repository implementationの完了条件:

- canonical fixtureと起動条件がrepositoryから一意に特定できる
- fixtureの初期化 / cleanupが再現可能
- external secret / user dataを必須にしない
- 3 Skillの対象canonical E2EがPASS
- formal direct triggerからoriginating evaluation / revision / resume operationを保持して `qa-workflow → usability-inspection → formal Skill resume` をPASS
- `_04c` handoff stateをnative CASで更新し、composite operation identity、claim / reservation lifecycle、expected observation集合とcurrent valid returned result集合、origin revision / cleanup / lineage / releaseがcurrentになり、closed CAS後の再読込まで完了するまでresumeしないことをPASS
- `_05g` fixed probe request / normalize契約をbrowser E2EでPASSし、Agentのad hoc JavaScript / raw値手計算を必要としない
- fixed coverage外の複合的懸念、semantic追加観測、Authority付きbusiness outcomeの3ケースをsemantic / browser E2EでPASSし、機械化がLLMのscope内意味判断を抑制しないことを確認する
- evidence safety / side-effect / browser ownershipをPASS
- repository標準のdeterministic / semantic / routing / Skill validationをPASS
- WCAG 2.0 / 2.1 / 2.2 requirement catalogのcanonical hash再計算と承認済みhash contract testをdeterministic validationでPASS
- version切替、unsupported / unresolved / out-of-scope分離、scope coverage row、presentation variation / Full Pages closure、baseline extension、finite procedure catalog、criterion plan→final result linkage、applicable population none guard、repeat-evaluation retained / replaced / added lineage、random `target-met / exhausted-no-new-view / blocked` 分離、non-finite random selection guard、candidate population変更時のreselection、Conforming Alternate Version条件、Non-Interference固定SC集合、Step 5.1 example coverage / accessible output、Step 5.3 Evaluation Statementの2.2-only guard、version別Claim URI / third-party 2-business-day guard、EARL全mappingはdeterministic / semantic evalでPASS
- browser E2EではStep 1.4 additional requirementのsample / report反映、sampling used / skipped、sample identity、Conforming Alternate Versionのfull-page grouping、Step 4.2 unchanged-result reuse、same-population Step 4.3再sampling、freshness付きobservation handoff / resume、safe Evaluation Specifics handoff、EARL assertionとのresult一致をPASS
- canonical fixtureで未解決blockedが0

external acceptance:

- ユーザー要求またはproject gateで必要な場合だけ別途実施する
- 対象URL / account / role / data / Authority / allowed side effect / cleanup / browser / assistive technology等の必要入力を固定する
- 入力不足はexternal acceptanceのblockedとして記録する
- repository fixtureの結果で外部targetの成功を代替しない

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
- 複数viewまたはstateを持ち、structured sample / random sample / complete processの経路検証ができる
- keyboard / focus、visual / responsive、general accessibility observationを少なくとも1件ずつ実行できる
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

### usability-inspection

少なくとも次を確認します。

1. taskなしpage inspection
2. task / flowありinspection
3. safe interaction
4. keyboard / focus
5. visual / responsive evidence
6. applicable general accessibility check
7. measurement経路
8. cleanup
9. `usability-evaluation` へのread-only handoff
10. 同一sessionを別Skillが並行操作しない

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

- structured sample
- random sample
- complete process
- Step 4.3で再samplingなしのcase
- semantic / fixtureでStep 4.3再samplingありのcase
- Step 5.1 outcome closure
- evaluation statement生成条件成立 / 不成立
- product-wide conformance claim guard

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
- expected handoff集合とcurrent valid returned result集合が一致するまでresumeしないことをPASS
- evidence safety / side-effect / browser ownershipをPASS
- repository標準のdeterministic / semantic / routing / Skill validationをPASS
- canonical fixtureで未解決blockedが0

external acceptance:

- ユーザー要求またはproject gateで必要な場合だけ別途実施する
- 対象URL / account / role / data / Authority / allowed side effect / cleanup / browser / assistive technology等の必要入力を固定する
- 入力不足はexternal acceptanceのblockedとして記録する
- repository fixtureの結果で外部targetの成功を代替しない

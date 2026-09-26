# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 本ファイルの対象

本ファイルは `usability-inspection` で決定論的に処理できる部分をSkill runtime scriptへ分離する契約です。

目的は、LLMへ次を任せないことです。

- fixed inspection scope row skeletonの生成
- ref採番
- scope closureの構造検査
- selected supported ruleからrequired observation field集合の導出
- 数値計算
- threshold比較
- 同じ入力から同じ結果を導けるaccessibility test rule
- status + follow_up_requiredからのFinding作成要否導出
- artifact内の参照整合
- machine-owned structured sectionのmaterialize
- machine-readableな集計

一方、次はscriptへ押し込みません。

- どのUI patternが適用されるか
- advisory guidanceの意味判断
- subjectiveなvisual / UX評価
- 人間の使いやすさの推測
- machine evidenceだけで決められないcriterion applicability / exception
- screenshotの意味解釈

## 2. 既存runtimeとの関係

PR #11 merge後のcurrent runtime contractを再利用します。

実装開始時に次のcurrent contractをすべて確認します。

- `skills/*/scripts/runtime_contract.py` のcurrent契約
- common envelope
- canonical JSON
- exact number
- input / generation fingerprint
- runtime status / result status / support status
- Machine Runtime Input / Result
- current artifact verifier
- portability / size / error contract

PR #11のcurrent実装に同じhelperが存在する場合、その契約を `usability-inspection` 用に再利用します。

別のruntime framework、plugin system、rule DSLは追加しません。

## 3. 処理境界

処理順は次で固定します。

~~~text
ユーザー要求 / project Authority / current target context
        ↓
LLM: scope applicability、criterion exception、follow-up要否等のsemantic decisionだけを返す
        ↓
Skill runtime script: fixed scope skeleton / selected rule metadataから必要な観測fieldを導出
        ↓
browser owner: live UIから要求されたmachine-readableな観測値を取得
        ↓
Skill runtime script
  - structure / machine-owned section materialization
  - exact measurement calculation
  - supported deterministic test rule
  - derived status / Finding requirement
        ↓
machine evidence
        ↓
LLM: scriptでは決められないapplicability / exception / UX意味判断
        ↓
usability-evaluation
        ↓
runtime / validatorで構造を再検査
        ↓
最終成果物
~~~

scriptは自然言語のUI、screenshot、仕様本文を直接解釈しません。

browserから取得できるDOM属性、accessibility属性、bounding box、viewport、timestamp、computed value等のmachine-readableな値だけを直接処理できます。

## 4. 追加するscript

実装構成:

~~~text
skills/usability-inspection/
├── scripts/
│   ├── runtime_contract.py
│   ├── inspection_structure.py
│   ├── measurement.py
│   └── criterion_checks.py
├── assets/
│   ├── output-template.md
│   └── test-rule-catalog.json
└── ...
~~~

### runtime_contract.py

PR #11で確定するcurrent helper contractを再利用します。

Skill固有のcriterion logicやmeasurement logicは入れません。

### inspection_structure.py

#### Input

正規化済みの次を受け取ります。

- inspection metadata
- top-level aspect decisions: aspect key / 今回確認する・対象外 / semantic reason
- browser ownerが取得したraw observation records
- measurement inputs
- selected supported test rule keys
- machine evidenceだけで確定できないrequirement applicability / exception等のsemantic decisions
- action inputs
- optional task / flow semantic result
- usability-evaluation refs
- follow_up_required / Finding本文に必要なsemantic input

inspection内で生成するsemantic input / raw recordはinvocation内で一意な `draft_key` を持ちます。`measurement.py` / `criterion_checks.py` はfinal refを生成せずdraft resultを返します。Agentは完成したscope closure row、required observation field集合、final ref、summary count、`finding_required` を入力しません。

#### Function

- unknown field拒否
- enum / required field検証
- duplicate draft key拒否
- Planで固定したtop-level aspectのscope row skeletonを全件生成し、semantic applicability decisionを適用
- selected supported test ruleについて `test-rule-catalog.json.required_observation_fields` のunionを導出し、browser observation requirementとしてmaterialize
- artifact-local refの決定論的採番
  - scope: `SCOPE-001`
  - observation: `OBS-001`
  - measurement: `MEAS-001`
  - test rule result: `RULE-001`
  - requirement check: `REQ-001`
  - action trace: `ACT-001`
- draft key → final ref解決
- draft同士のcross-reference解決
- inspection scope closure検証
- selected scopeごとのevidence / result参照検証
- statusと `follow_up_required` からFinding作成要否を固定ruleで導出
- final row order固定
- summary count導出
- unresolved / limitation整合確認
- machine-owned structured sectionをcanonical Markdownとしてrender

artifact-local refは同じ正規化済み入力から同じ順序で生成します。

既存artifactのrevisionを跨いで同じrefを維持するglobal identity契約は追加しません。

#### Output

Outputは次を必須で持ちます。

- normalized inspection header
- inspection scope closure rows
- observations
- measurements
- test rule results
- requirement check rows
- action traces
- optional task / flow result
- evaluation refs
- Finding requirement / refs
- summary counts
- rendered machine-owned structured sections
- issues

### measurement.py

#### Input

1 measurementごとに次を必須入力とします。

- draft_key
- measurement label
- start value
- end value
- value / unitを直接与えるmeasurementの場合はraw value
- measurement method
- clock domain（elapsedをstart / endから導出する場合）
- metric definition ref（既存metric名を使用する場合）
- metric source type
- external metric source ref（外部measurement sourceを受け取る場合）
- external source name / tool
- external source version（取得可能な場合）
- external source mode: field / lab / RUM / synthetic（applicableな場合）
- population / period / device class / percentile（field判定へ必要な場合）
- threshold value / operator / Authority ref（存在する場合）
- environment / viewport / device profile refs

timestamp / numeric valueはPR #11 current runtime contractのexact number表現を利用します。

#### Function

- start / endが同一clock domainであることの検証
- start / end差分の計算
- unit整合
- non-negative検証
- threshold comparison
- clock domain不一致の場合の `measurement-unavailable`
- thresholdなしの場合の `threshold-not-defined`
- metric definition ref不足時に既存metric名を確定しない
- external metric source metadataの構造検証
- field判定で必要なpopulation / period / device class / percentileのrequired field検証
- inputとderived valueのcanonicalization

LLMに引き算・大小比較をさせません。

#### Output

Outputは次を必須で持ちます。

- draft_key
- normalized label
- calculated value
- unit
- measurement method
- metric source type
- external metric source ref
- external source name / tool
- external source version
- external source mode
- population / period / device class / percentile
- threshold
- threshold Authority ref
- result: within-threshold / over-threshold / threshold-not-defined / measurement-unavailable
- issues

### criterion_checks.py

固定dispatch tableに登録したdeterministic checkだけを処理します。

genericな自然言語rule engineや式DSLは作りません。

#### Input

1 checkごとに次を必須入力とします。

- draft_key
- check_key
- source type: act-rule / project-rule
- source status: formal / proposed / project
- source rule ref
- mapped requirement ref
- target scope / target ref
- normalized machine observations
- browser / document context
- project Authority ref（project固有ruleの場合）

#### Function

machine evidenceだけで完全に判定できるsupported test ruleは `criterion_checks.py` の明示dispatchで自動判定します。supported ruleのmetadataだけを `assets/test-rule-catalog.json` に固定します。catalogは実行可能コードや式を持たず、generic rule DSL / plugin registryにはしません。

ref採番、cross-reference、scope closure、geometry、elapsed、threshold等のhelper処理はcatalogへ登録しません。

次の場合は自動PASS / FAILへ進みません。

- applicabilityがmachine evidenceだけで確定できない
- exceptionが意味判断を必要とする
- screenshotの意味解釈が必要
- user intent / purposeの判断が必要
- checkがrequirementの一部分しか評価しない
- browser evidenceが不足している

この場合はstructured issueを返し、LLM / manual evaluationへ戻します。

#### Output

check単位で次を必須出力とします。

- draft_key
- check_key
- source type
- source status
- source rule ref
- mapped requirement ref
- target ref
- applicability
- rule result
- evidence refs
- limitation
- issues

W3C ACT Ruleを完全に実装した場合は、そのruleで定義されたoutcomeを保持します。

current WAI公開ACT RulesはACT Rules Format 1.1互換として扱い、outcomeは `inapplicable / passed / failed / cantTell / untested` を使用します。

- `inapplicable`: applicabilityを評価し、test targetがないと確定した
- `passed / failed`: applicableなtest targetを評価してexpectation結果を確定した
- `cantTell`: evaluationを開始したが、applicabilityまたはexpectationを完全に判定できない
- `untested`: supported ruleが今回scopeへ選定されたが、そのtest subjectを評価していない

automatic checkが `criterion_checks.py` までdispatchされmachine evidenceを評価した場合、単なる入力不足を `untested` へ逃がしません。完全判定できなければ `cantTell` またはstructured issueへ閉じます。`untested` は、選定済みsupported ruleを実行前にskip / blockしたことを明示する非実行経路でだけ使用します。proposed ruleはsource statusを保持し、formal ruleと混同しません。

ACT Rule resultを、そのままWCAG Success Criterion全体のrequirement resultへ読み替えません。

## 5. test-rule-catalogとsupported ruleの管理

runtime scriptが任意のreference本文を解釈しないよう、supported test ruleのmetadataを `assets/test-rule-catalog.json`、automatic実装を `criterion_checks.py` の明示dispatchへ分離します。

catalogの各entry:

- check key
- source type: act-rule / project-rule
- source rule ref
- mapped requirement refs
- source status: formal / proposed / project
- ACT Rules Format version（ACT Ruleの場合）
- execution mode: automatic / manual / semiAuto
- required observation fields
- output scope
- implementation dispatch key（automaticの場合）
- checked_atまたはsource version

`source type` と `source status` を同じfieldへ混ぜません。

`criterion_checks.py` は `automatic` のsupported ruleだけをdispatchします。selected rule keyが確定した後、必要なbrowser observation fieldはcatalogからscriptが導出し、LLMがruleごとに手で列挙しません。

`manual / semiAuto` は自動resultを生成せず、必要evidence・未評価部分・semantic procedure refをhandoffとして返し、定義済みsemantic/manual経路で閉じます。

supported ACT Ruleの条件とofficial examplesによるconsistency検証は `_05d_accessibility-requirements-and-act.md` を正本とします。

artifact structure / measurement helperはcatalog対象外です。

## 6. requirement resultとの関係

### test rule result

ACT Rule等の個別test ruleを実行した結果です。

rule単位の結果と、WCAG Success Criterion等のrequirement全体の結果を分離します。

### requirement result

最終成果物の `standard / binding requirement check` です。

`not-satisfied` は、applicableなrequirement違反を証拠で確認できた場合に記録できます。

`satisfied` は、今回宣言したevaluation scopeについて必要なapplicable populationとrequired checksを閉じられた場合だけ記録します。WCAG Success Criterionでapplicable contentが存在しないことを必要なscopeで閉じた場合は、その根拠を保持して `satisfied` と扱えます。

例えば1要素だけを確認して問題がなかったことを、page全体のrequirement `satisfied` へ昇格しません。

ruleがrequirementの一部分だけを評価する場合、rule outcomeが `passed` でもrequirementを `satisfied` にしません。

必要なpopulation / exception / manual checkを閉じられない場合は `undetermined` とし、確認済みrule結果はevidenceとして残します。

## 7. W3C ACT Rulesの利用

All ACT Rulesの公式source / rule一覧はsource catalogから辿れるようにしますが、runtime coverage inventoryとして全ruleへexecution modeを割り当てません。

runtimeが扱うのは `_05d_accessibility-requirements-and-act.md` の条件を満たして `test-rule-catalog.json` へ登録したsupported ruleだけです。

supported ruleごとに確認します。

- source status
- applicability
- expectation
- assumptions
- accessibility requirements mapping
- outcome mapping
- ACT Rules Format version
- execution mode
- required observation fields
- current browser observation contractで必要入力を取得できるか

automatic ruleだけを `criterion_checks.py` がdispatchします。

manual / semiAuto supported ruleはcatalog metadataとsemantic procedureに従い、machine evidenceだけでresultを確定しません。

unsupported ACT Ruleへ、

- automatic / manual / semiAutoのexecution mode
- `untested` result
- `cantTell` result

を機械的に作りません。`untested / cantTell` はsupported ruleにだけ使用します。`untested` は選定済みruleを評価していない場合、`cantTell` は評価を開始したが完全判定できない場合です。unsupported ruleへはどちらも作りません。

formal ACT Ruleが存在しないrequirementについて、ACT互換を装う独自ruleを作りません。

project固有checkが必要な場合は `source_type=project-rule` とし、artifact helperとは分離します。

## 8. browser observationとの境界

browser操作そのものをPython runtimeへ移しません。

PR #12 merge後のcurrent browser owner / execution pathを再利用します。

browser側はcriterionやmeasurementに必要な最小限のmachine-readable observationを取得します。

例:

- viewport dimensions
- scroll position / scroll extent
- bounding box
- visible / enabled
- role / accessible name / state
- focused element
- computed styleの必要subset
- timestamp / PerformanceEntry
- document title等の対象値

full DOM dumpや全page snapshotをruntime inputとして無条件保存しません。

secret、個人データ、機密情報を含む可能性があるraw snapshot / screenshot / accessibility treeはPR #12のevidence安全契約を再利用し、必要最小限だけ取得・永続化します。

## 9. Playwrightの決定論的利用

current Playwright versionをStep 0で確認します。

現在利用可能なPlaywright APIに、action時のimplicit scrollを無効化する正式オプションがある場合は、それをvisual / pointer reachabilityを確認するapplicable caseで優先します。

利用versionにそのAPIがない場合は、

- targetのviewport内状態をaction前に取得
- off-viewport targetへlocator actionを直接実行しない
- discoverability確認ではwheel / keyboard / viewport単位のuser-facingなexplicit scroll後に再観測
- target発見後のtargeted scrollはdiscoverability evidenceへ数えない

で代替します。

Playwright version差を吸収する独自browser wrapper frameworkは作りません。

## 10. deterministic化するもの / しないもの

| 処理 | runtime script |
| --- | --- |
| fixed scope row skeleton・ref採番・row順序 | 必須 |
| schema / cross-reference | 必須 |
| selected ruleからrequired observation field集合導出 | 必須 |
| scope closure集計 | 必須 |
| elapsed計算 | 必須 |
| threshold比較 | 必須 |
| supported ACT Rule / project ruleで完全にmachine-decidableなcheck | 対応checkでは必須 |
| target size等のraw geometry取得後の数値計算 | 必須 |
| criterion applicabilityで意味判断が必要 | LLM / manual |
| WCAG exceptionで意味判断が必要 | LLM / manual |
| screenshotの表示崩れ判断 | LLM / image evaluation |
| UI pattern同定 | usability-evaluation |
| heuristic評価 | usability-evaluation |
| user impact推定 | usability-evaluation |
| follow-upが必要かの意味判断 | LLM / workflow |
| status + follow_up_requiredからFinding作成要否導出 | 必須 |
| machine-owned structured section materialize | 必須 |

## 11. runtimeとvalidatorの分離

runtime generatorとdeterministic eval validatorを同じ実装へしません。

- runtime: machine resultを生成
- validator: 成果物が契約を満たすか独立検証
- semantic eval: applicabilityや専門評価の意味品質を確認

同じhelperをgeneratorとvalidatorで共有して、同じ不具合で両方がPASSする構造を避けます。

## 12. runtime fixture

次を必須runtime fixtureとして持ちます。

- valid inspection structure
- fixed top-level aspect skeleton + semantic applicability decisionからscope row生成
- selected ruleからrequired observation field集合導出
- observation / measurement / rule / requirement / action inputからfinal ref解決
- duplicate draft key
- unresolved reference
- selected scope未closure
- exact elapsed calculation
- project threshold以内 / 超過
- thresholdなし
- negative elapsed
- supported automatic ACT Rule `passed`
- supported automatic ACT Rule `failed`
- supported ACT Rule outcome `cantTell / inapplicable`
- selected supported ACT Ruleの非実行経路 → `untested`。automatic checkを実行済みの入力不足は `untested` にしない
- status + follow_up_requiredからFinding作成要否を導出し、不整合な手入力をreject
- rendered machine-owned sectionをAgentが値単位で再構築しない
- source typeとsource statusの分離
- partial / manual ruleを自動 `passed / failed` へしない
- rule `passed` からrequirement全体を `satisfied` へ昇格しない
- insufficient evidence → `undetermined`
- clock domain一致のelapsed計算
- clock domain不一致 → `measurement-unavailable`
- off-viewport target
- secret / sensitive raw evidenceを成果物必須にしない

## 13. 完了条件

- PR #11 current runtime contractを再利用している
- 別runtime frameworkを作っていない
- 同じnormalized inputから同じmachine resultになる
- 数値計算 / threshold比較をLLMが再計算しない
- fixed scope row、required observation field集合、Finding作成要否、summary、machine-owned sectionを `inspection_structure.py` が導出 / materializeし、Agentが同じ機械処理を手作業で再構築していない
- inspection成果物内のscope / observation / measurement / test rule / requirement / action refを `inspection_structure.py` が一括採番・cross-reference解決し、Agentや個別helperがfinal refを手採番していない
- deterministic checkのdispatchが `assets/test-rule-catalog.json` のsupported automatic ruleだけへ固定され、catalogを式DSL / plugin frameworkとして実装していない
- structure / measurement helperをtest rule catalogへ混ぜていない
- source typeとsource statusを分離している
- manual / semiAuto checkを自動 `passed / failed` へ昇格しない
- ACT Rule resultとrequirement resultを分離する
- requirement `satisfied` にはscope / population closureが必要
- elapsed計算で同一clock domainを検証する
- browser操作runtimeを二重実装しない
- raw evidenceを必要以上に永続化しない
- runtime / validator / semantic evalが分離されている

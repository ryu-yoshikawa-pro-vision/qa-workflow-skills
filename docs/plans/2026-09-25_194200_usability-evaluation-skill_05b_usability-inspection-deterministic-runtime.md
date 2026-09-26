# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 1. 本ファイルの対象

本ファイルは `usability-inspection` で決定論的に処理できる部分をSkill runtime scriptへ分離する契約です。

目的は、LLMへ次を任せないことです。

- ref採番
- scope closureの構造検査
- 数値計算
- threshold比較
- 同じ入力から同じ結果を導けるaccessibility test rule
- artifact内の参照整合
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
LLM: inspection scopeと必要な観測を決定
        ↓
browser owner: live UIからmachine-readableな観測値を取得
        ↓
Skill runtime script
  - structure materialization
  - exact measurement calculation
  - supported deterministic test rule
        ↓
machine evidence
        ↓
LLM: scriptでは決められないapplicability / UX意味判断
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
- inspection scope rows
- observation drafts
- measurement result refs
- requirement check drafts
- optional task / flow result
- usability-evaluation refs
- Finding refs

draft rowはinvocation内で一意な `draft_key` を持ちます。

#### Function

- unknown field拒否
- enum / required field検証
- duplicate draft key拒否
- artifact-local refの決定論的採番
- draft key → final ref解決
- cross-reference解決
- inspection scope closure検証
- selected scopeごとのevidence / result参照検証
- final row order固定
- summary count導出
- unresolved / limitation整合確認

artifact-local refは同じ正規化済み入力から同じ順序で生成します。

既存artifactのrevisionを跨いで同じrefを維持するglobal identity契約は追加しません。

#### Output

Outputは次を必須で持ちます。

- normalized inspection header
- inspection scope closure rows
- observations
- measurements refs
- requirement check rows
- optional task / flow result
- evaluation refs
- Finding refs
- summary counts
- issues

### measurement.py

#### Input

1 measurementごとに次を必須入力とします。

- measurement_key
- measurement label
- start value
- end value
- value / unitを直接与えるmeasurementの場合はraw value
- measurement method
- clock domain（elapsedをstart / endから導出する場合）
- metric definition ref（既存metric名を使用する場合）
- metric source type
- external metric source ref（外部measurement sourceを受け取る場合）
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
- inputとderived valueのcanonicalization

LLMに引き算・大小比較をさせません。

#### Output

Outputは次を必須で持ちます。

- measurement ref用draft key
- normalized label
- calculated value
- unit
- measurement method
- metric source type
- external metric source ref
- threshold
- threshold Authority ref
- result: within-threshold / over-threshold / threshold-not-defined / measurement-unavailable
- issues

### criterion_checks.py

固定dispatch tableに登録したdeterministic checkだけを処理します。

genericな自然言語rule engineや式DSLは作りません。

#### Input

1 checkごとに次を必須入力とします。

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

current WAI公開ACT RulesはACT Rules Format 1.1互換として扱い、outcomeは `inapplicable / passed / failed / cantTell / untested` を使用します。proposed ruleはsource statusを保持し、formal ruleと混同しません。

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

`criterion_checks.py` は `automatic` のsupported ruleだけをdispatchします。

`manual / semiAuto` は自動resultを生成せず、必要evidence・未評価部分・semantic procedure refをhandoffとして返し、定義済みsemantic/manual経路で閉じます。

supported ACT Ruleの条件とofficial examplesによるconsistency検証は `_05d_accessibility-and-conformance.md` を正本とします。

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

取得時点でW3Cが公開しているformal ACT Rulesとproposed ACT Rulesを全件inventoryへ含めます。formal / proposedを別statusで保持し、proposedをWCAG / ARIAのbinding根拠へ昇格しません。

各ruleについて次をすべて確認します。

- formal / proposed等のstatus
- applicability
- expectation
- assumptions
- accessibility requirements mapping
- outcome mapping
- ACT Rules Format version
- current WAI公開ruleとして1.1互換であること
- machine evidenceだけでfully executableか
- semantic判断が必要なexpectationがあるか
- current browser observation contractで必要入力を取得できるか
- Web-only scopeでrule全体を実行できるか

全ruleを `automatic / manual / semiAuto` の実行経路へ割り当てます。Web-only scopeや必要evidence不足で実行できないruleは、その理由と必要能力をcoverageへ残し、評価を実施しなかったruleはACT Rules Format 1.1の `untested`、applicabilityまたはexpectationを完全に判断できないruleは `cantTell` として閉じます。mapped requirement全体は他のrequired checks / evidenceも含めて独立判定します。

rule本文を独自解釈して別の判定方法へ変更しません。

formal ACT Ruleが存在しないcriterionについて、ACT互換であると偽る独自ruleを作りません。

独自のmachine checkが必要な場合はsource typeをproject / inspection helperとして区別し、WCAG ACT Ruleとは呼びません。

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
| ref採番・row順序 | 必須 |
| schema / cross-reference | 必須 |
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
| Finding化の意味判断 | LLM / workflow |

## 11. runtimeとvalidatorの分離

runtime generatorとdeterministic eval validatorを同じ実装へしません。

- runtime: machine resultを生成
- validator: 成果物が契約を満たすか独立検証
- semantic eval: applicabilityや専門評価の意味品質を確認

同じhelperをgeneratorとvalidatorで共有して、同じ不具合で両方がPASSする構造を避けます。

## 12. runtime fixture

次を必須runtime fixtureとして持ちます。

- valid inspection structure
- duplicate draft key
- unresolved reference
- selected scope未closure
- exact elapsed calculation
- project threshold以内 / 超過
- thresholdなし
- negative elapsed
- supported automatic ACT Rule `passed`
- supported automatic ACT Rule `failed`
- supported ACT Rule outcome `cantTell / untested / inapplicable`
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

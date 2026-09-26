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

実装開始時に最低限次を確認します。

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

予定構成:

~~~text
skills/usability-inspection/
├── scripts/
│   ├── runtime_contract.py
│   ├── inspection_structure.py
│   ├── measurement.py
│   └── criterion_checks.py
├── assets/
│   ├── output-template.md
│   └── deterministic-check-catalog.json
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
- criterion check drafts
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

最低限:

- normalized inspection header
- inspection scope closure rows
- observations
- measurements refs
- criterion check rows
- optional task / flow result
- evaluation refs
- Finding refs
- summary counts
- issues

### measurement.py

#### Input

1 measurementごとに最低限:

- measurement_key
- measurement label
- start value
- end value
- value / unitを直接与えるmeasurementの場合はraw value
- measurement method
- metric definition ref（既存metric名を使用する場合）
- threshold value / operator / Authority ref（存在する場合）
- environment / viewport refs

timestamp / numeric valueはPR #11 current runtime contractのexact number表現を利用します。

#### Function

- start / end差分の計算
- unit整合
- non-negative検証
- threshold comparison
- thresholdなしの場合の `threshold-not-defined`
- metric definition ref不足時に既存metric名を確定しない
- inputとderived valueのcanonicalization

LLMに引き算・大小比較をさせません。

#### Output

最低限:

- measurement ref用draft key
- normalized label
- calculated value
- unit
- measurement method
- threshold
- threshold Authority ref
- result: within-threshold / over-threshold / threshold-not-defined / measurement-unavailable
- issues

### criterion_checks.py

固定dispatch tableに登録したdeterministic checkだけを処理します。

genericな自然言語rule engineや式DSLは作りません。

#### Input

1 checkごとに最低限:

- check_key
- source rule ref
- mapped requirement ref
- target scope / target ref
- normalized machine observations
- browser / document context
- project Authority ref（project固有ruleの場合）

#### Function

`deterministic-check-catalog.json` で `automation=full` とされたcheckだけを自動判定します。

次の場合は自動PASS / FAILへ進みません。

- applicabilityがmachine evidenceだけで確定できない
- exceptionが意味判断を必要とする
- screenshotの意味解釈が必要
- user intent / purposeの判断が必要
- checkがrequirementの一部分しか評価しない
- browser evidenceが不足している

この場合はstructured issueを返し、LLM / manual evaluationへ戻します。

#### Output

check単位で最低限:

- check_key
- source rule ref
- mapped requirement ref
- target ref
- applicability
- rule result
- evidence refs
- limitation
- issues

W3C ACT Ruleを完全に実装した場合は、そのruleで定義されたoutcomeを保持します。

ACT Rule resultを、そのままWCAG Success Criterion全体のPASSへ読み替えません。

## 5. deterministic-check-catalog.json

runtime scriptが任意のreference本文を解釈しないよう、実装済みcheckだけを固定catalogで管理します。

最低限のfield:

- check_key
- source type
- source rule ref
- mapped requirement refs
- source status
- automation: full / partial / manual
- runtime function key
- required observation fields
- output scope
- version / checked_at

`automation=partial / manual` は `criterion_checks.py` の自動PASS / FAIL対象外です。

W3C ACT Rulesでは、正式公開ruleとproposed / community ruleのstatusを混同しません。

ACT RulesはWCAG / ARIA conformanceそのもののnormative basisではなく、testing methodのinformative ruleとして保持します。

## 6. criterion resultとの関係

### test rule result

ACT Rule等の個別test ruleを実行した結果です。

rule単位の結果と、WCAG Success Criterion等のrequirement全体の結果を分離します。

### requirement result

最終成果物の `standard / binding criterion check` です。

FAILは、applicableなrequirement違反を証拠で確認できた場合に記録できます。

PASSは、今回宣言したevaluation scopeについて必要なapplicable populationとrequired checksを閉じられた場合だけ記録します。

例えば1要素だけを確認して問題がなかったことを、page全体のcriterion PASSへ昇格しません。

ruleがrequirementの一部分だけを評価する場合、rule PASSだけではrequirement PASSにしません。

必要なpopulation / exception / manual checkを閉じられない場合は `判定不能` とし、確認済みrule結果はevidenceとして残します。

## 7. W3C ACT Rulesの利用

W3Cが正式公開しているACT Rulesをdeterministic候補sourceとしてinventoryへ含めます。

各ruleについて最低限確認します。

- formal / proposed等のstatus
- applicability
- expectation
- assumptions
- accessibility requirements mapping
- outcome mapping
- machine evidenceだけでfully executableか
- current browser observation contractで必要入力を取得できるか

`automation=full` にできるruleだけruntime実装候補にします。

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

現在利用可能なPlaywright APIに、action時のimplicit scrollを無効化する正式オプションがある場合は、それをvisual / pointer reachabilityの代表caseで優先します。

利用versionにそのAPIがない場合は、

- targetのviewport内状態をaction前に取得
- off-viewport targetへlocator actionを直接実行しない
- explicit scroll後に再観測

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
| formal ACT Rule等、完全にmachine-decidableなcheck | 対応checkでは必須 |
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

## 12. 最低限のfixture

最低限次をruntime fixtureとして持ちます。

- valid inspection structure
- duplicate draft key
- unresolved reference
- selected scope未closure
- exact elapsed calculation
- project threshold以内 / 超過
- thresholdなし
- negative elapsed
- fully automated deterministic check PASS
- fully automated deterministic check FAIL
- partial / manual ruleを自動PASSへしない
- rule PASSからrequirement全体PASSへ昇格しない
- insufficient evidence → 判定不能
- off-viewport target
- secret / sensitive raw evidenceを成果物必須にしない

## 13. 完了条件

- PR #11 current runtime contractを再利用している
- 別runtime frameworkを作っていない
- 同じnormalized inputから同じmachine resultになる
- 数値計算 / threshold比較をLLMが再計算しない
- deterministic checkのdispatchが固定されている
- partial / manual checkを自動PASS / FAILへ昇格しない
- ACT Rule resultとrequirement resultを分離する
- requirement PASSにはscope / population closureが必要
- browser操作runtimeを二重実装しない
- raw evidenceを必要以上に永続化しない
- runtime / validator / semantic evalが分離されている

# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` がtarget WCAG version / levelから導出したrequired Success Criterionについて、各sample / presentation variation / processで「何を確認するか」「どの処理が担当するか」「何が不足すると完了できないか」を固定します。

目的は、required criterionの選択・省略、評価procedure、machine処理、semantic / manual判断、assistive technology利用、未完了判定を実装者やLLMのその場判断へ残さないことです。

WCAG-EM 2.0のsample / variation / process / report契約は `_05f_wcag-conformance-evaluation-package-and-runtime.md`、semantic追加観測は `_05g_usability-inspection-browser-observation-contract.md`、machine procedureの固定browser入力は `_05j_wcag-machine-browser-observation-contract.md`、criterion固有semantic契約は `_05k_wcag-semantic-procedure-contract.md`、general accessibility / ACT Rule semanticsは `_05d_accessibility-requirements-and-act.md`、WCAG 2.0 / 2.1 / 2.2全Success Criterionのprocedure割当は `_05i_wcag-success-criterion-procedure-inventory.md` を正本とします。

## 1. owner境界

`wcag_requirements.py` はtarget WCAG version / levelからrequired Success Criterion集合を導出します。

`wcag_criterion_plan.py` は、そのrequired集合、required presentation variation集合、versioned requirements asset、有限procedure catalogからcriterion evaluation rowを全件materializeします。

`usability-inspection` はplanが要求するlive observation、measurement、supported ACT Ruleをbrowser ownerとして実行します。

`wcag-conformance-evaluation` のsemantic layerは、machine evidenceだけで決められないapplicability、exception、purpose / meaning、manual judgment、procedure applicability、assistive technology上の評価を担当します。

`wcag_em_structure.py` はcurrentなcriterion plan outputを正本としてsample resultへmaterializeします。LLM supplied requirement result listを別経路で受け取りません。

LLMはrequired Success Criterion集合、criterion row、required procedure集合、required machine step、未完了criterion集合、summary countを手作成しません。

## 2. asset

既存のversioned requirements assetを使います。

- `assets/wcag-2.0-requirements.json`
- `assets/wcag-2.1-requirements.json`
- `assets/wcag-2.2-requirements.json`

共通の有限procedure定義を次へ置きます。

- `assets/wcag-evaluation-procedure-catalog.json`

これはgeneric rule DSLではありません。今回のWCAG 2.0 / 2.1 / 2.2 evaluationで実際に使用するprocedure keyと固定契約だけを保持します。

### 2.1 Success Criterion metadata

各Success Criterion rowは少なくとも次を持ちます。

```json
{
  "criterion_ref": "wcag22:2.4.2",
  "evaluation": {
    "procedure_keys": [
      "m-page-title",
      "s-wcag-2.4.2"
    ],
    "external_evidence_allowed": false
  }
}
```

supported WCAG 2.0 / 2.1 / 2.2の全Success Criterionで `procedure_keys` を1件以上必須にします。expected procedure集合は `_05i` の固定生成規則から導出し、requirements assetの実値と一致させます。`TBD`、空集合、未登録key、実装時のad hoc追加を許可しません。

`external_evidence_allowed=true` はcurrent scopeへ適合する既存監査結果、field data、project instrumentation等を**利用してよい**ことを示し、外部証拠の存在や利用をSuccess Criterion完了の必須条件にはしません。`false` のcriterionへexternal-evidence procedureを割り当てた場合はasset不整合としてrejectします。

3 versionのrequirements assetは既存 `static_data_versions` / approved hash契約対象で、evaluation metadataもcanonical hashへ含めます。

### 2.2 finite procedure catalog

各procedure row:

- `procedure_key`
- `execution_kind`: `machine / semantic / manual / assistive-technology / external-evidence`
- `source_item_refs`
- `applicable_criterion_refs`
- `required_capabilities`
- `required_observation_fields`。semantic/manual追加観測で `_05g` の17 canonical fieldを使う場合
- `required_machine_probe_keys`。machine procedureで `_05j` のfixed probeを使う場合
- `required_input_refs`
- `machine_dispatch_key`。execution kindがmachineの場合だけ必須
- `semantic_decision_key`。execution kindがsemanticの場合だけ必須
- `applicability_decision_key`。`applicability_mode=semantic` の場合だけ必須。それ以外は `null`
- `result_contract`
- `completion_evidence`
- `limitation_behavior`
- `applicability_mode`: `always / semantic / machine-limitation / external-evidence-available`
- `activation_source_procedure_key`。`machine-limitation` の場合だけ必須。それ以外は `null`
- `activation_limitation_codes`。`machine-limitation` の場合だけ非空。それ以外は空配列

同じprocedureを複数Success Criterionで共有できますが、任意式、JavaScript、自然言語rule本文、plugin entry pointを入れません。

実装完了時には、

- 全Success Criterionのprocedure keyがcatalogへ解決する
- catalogの全execution kind / capability / dispatch keyが許可値
- machine procedureは全件明示dispatch実装済み
- semantic / manual / AT / external-evidence procedureも必要Input / Output / evidence contractが固定
- procedure catalogに `other`、`custom`、`TBD` 等の逃げ道がない

ことをvalidatorで確認します。

## 3. procedure分類

### 3.1 machine

固定Inputから意味判断なしで結果を導出できる処理です。

ACT / measurementの既存dispatchに加え、`_05i` §3のmachine procedureを全件実装します。少なくとも既存の次のdispatchもそのmachine procedureから再利用します。

- `act:2779a5`
- `act:97a4e1`
- `act:23a2a8`
- `measurement:target-size`
- `measurement:contrast-ratio`
- `measurement:viewport-overflow`
- `measurement:elapsed`

新しいmachine procedureを実装対象へ追加する場合もcatalogへkeyを追加し、明示dispatch / fixture / validatorを同時に追加します。「その他のmachine step」というcatch-allは作りません。

各Success Criterionのprocedure設計時、fixed browser observation / measurementだけで確定できる処理をsemantic / manualへ逃がしません。procedure catalog semantic reviewで、数値計算、集合演算、固定enum、string / attribute / stateの機械比較、既存supported ACT Ruleで閉じる部分がmachineへ分類されていることを確認します。

### 3.2 semantic

applicability、exception、purpose、meaning、content equivalence等、意味判断が必要な処理です。

`semantic_decision_key` ごとの契約は `_05k_wcag-semantic-procedure-contract.md` を正本とします。各supported version / Success Criterionにversioned semantic contract rowを必須とし、normative clause / definition / exception refs、必須semantic evaluation point、procedureから導出したrequired evidence role、不足時の `undetermined / blocked`、machine resultから自動昇格してはいけない条件をapproved static dataへ固定します。実装者やruntime LLMがcriterionごとに新しい評価手順を作りません。

### 3.3 manual

人間またはAgentがevidenceを確認する必要があるが、特定assistive technologyの実使用を前提にしないprocedureです。必要な観測対象、操作、expected evidenceをcatalogへ固定します。

### 3.4 assistive technology

AT利用はSuccess Criterionごとの静的booleanにしません。

procedure catalogで `required_capabilities` に `assistive-technology` を含むprocedureを定義し、current content / technology / accessibility support baselineに対してそのprocedureがapplicableかを**AT procedure実行前のsemantic applicability decision**で判断します。`applicability_decision_key` は `_05i` の4 AT procedureごとに固定し、対応contractは `_05k` の `procedure_applicability_contracts[]` を正本とします。

AT applicability decisionは自身のAT procedure resultやfinal `s-wcag-*` semantic resultをInputにしません。current population discovery、current machine-readable observation / machine result、technology context、accessibility support baseline、Authorityだけから `applicable / not-applicable / unknown` を返します。scriptはそのdecision refをprocedure execution rowへ投影し、`applicable` の場合だけAT executionを開始します。

必要なAT procedureがapplicableだが実施環境を用意できない場合は推測で閉じず `blocked` またはresult `undetermined` とします。

### 3.5 external evidence

既存監査結果、field data、project instrumentation等を利用できるprocedureだけをcatalogへ登録します。source / revision / environment / freshness / scope一致を必須にします。

external evidenceはoptional supporting evidenceです。外部証拠が存在しないこと自体でcriterionを `undetermined / blocked` にしません。

`applicability_mode=external-evidence-available` は `wcag_criterion_plan.py` がcurrent evaluation inputのexternal evidence candidate refsを機械検証して閉じます。

- candidate refが0件 → `not-applicable`、reason `external-evidence-not-provided`
- candidateがあるがsource / revision / environment / freshness / scopeのいずれかを満たすcurrent evidenceが0件 → `not-applicable`、reason `no-current-scope-matching-external-evidence`。candidate refsとrejection reasonをtraceabilityへ残す
- current scopeへ適合するvalid evidenceが1件以上 → `applicable`。valid refsだけをprocedure Inputへ渡す
- candidate refの不存在・stale・scope mismatchだけを理由に `unknown / blocked` へしない
- evidence ref自体が構文不正、許可されないsource kind、またはtrust boundary validationに失敗した場合は入力不正としてrejectし、外部証拠不足とは混同しない

このapplicability判定にLLMを使いません。

### 3.6 procedure applicability / fallback

全procedure execution rowはcriterion-levelの `applicable_population` と別に、procedure自身のapplicabilityを保持します。

procedure execution rowは少なくとも次を持ちます。

- procedure execution ref
- procedure key / execution kind
- applicability: `applicable / not-applicable / unknown`
- applicability basis refs / reason
- activation source procedure ref（存在する場合）
- execution status: `pending / in-progress / complete / blocked`
- procedure result。値域はcatalogの `result_contract` を正本とする
- evidence refs
- limitation code / blocker

`wcag_criterion_plan.py` がcatalogの `applicability_mode` から次を決定論的に閉じます。

- `always`: procedureは常にapplicable
- `semantic`: procedure catalogの `applicability_decision_key` に対応するfixed pre-execution semantic applicability decisionから `applicable / not-applicable / unknown` を受け、scriptがprocedure rowへ投影する。final `s-wcag-*` semantic decisionをapplicability sourceに使わず、LLMがprocedure keyを追加・削除しない
- `machine-limitation`: source machine procedureが未closureならunknown。sourceがcompleteし `activation_limitation_codes` のいずれかを返した場合だけapplicable。それ以外の正常closureではnot-applicable
- `external-evidence-available`: current evaluation inputのexternal evidence candidate refsをsource / revision / environment / freshness / scopeで機械検証し、valid current evidenceが1件以上ならapplicable、0件ならnot-applicable。LLM判断やexternal evidenceの存在待ちでunknownにしない

`not-applicable` は `execution_status=complete`、procedure resultは `null` とし、applicability basisを必須にします。required applicable procedureのclosureには数えません。

criterion-level `applicable_population` はcriterion-specific semantic procedureのpopulation discovery / applicability resultとevidenceからscriptが最終投影します。procedure applicabilityから逆算しません。

`unknown` を残したままcriterionを `satisfied / not-satisfied` にしません。必要evidenceを取得・評価したうえで意味的に確定できない場合はcriterionを `undetermined`、required capability / environment自体がなくprocedureを実施できない場合は `blocked` とします。

machine procedureが既知のmachine limitationで閉じた場合、manual fallbackがcatalogにあるならそのlimitationだけでcriterionをblockedへ短絡しません。scriptがfallback procedureをapplicableへ遷移させ、manual evidenceのclosureを待ちます。fallbackも実施不能なら初めて `blocked / undetermined` へ閉じます。

fixed probeを契約どおり実行し、machine値を完全判定できないこと自体を正しく観測できた場合、そのsource machine procedureは `execution_status=complete` とし、catalogのresult contractで定義したlimitation result + finite `limitation_code` を保持します。これはbrowser action未開始、cleanup失敗、request schema不正等の `blocked` と分離します。conditional manual fallbackはこの `complete + limitation_code` からだけ起動します。

manual fallbackはmachine値をLLM推測で補う経路ではありません。対象・状態・評価方法・測定値または観測結果・evidence refを固定契約で要求し、数値が必要なcriterionでは目視推定値を正式測定値として扱いません。

procedure catalogのmode割当は `_05i` の生成規則へ固定します。

- machine procedure: `always`
- criterion-specific `s-wcag-*`: `always`
- `_05i` の通常manual procedure: `always`
- external-evidence procedure: `external-evidence-available`
- assistive-technology procedure: `semantic`
- `_05i` のconditional manual fallback: `machine-limitation`

同じprocedure keyについて実装者が別modeを選びません。external-evidence procedureも外部証拠が存在しない通常caseでは `not-applicable` としてclosureし、manual / semantic等の他のapplicable procedureでcriterion評価を継続します。`always` procedureでも対象populationが存在しないことを確認するためのinventory / semantic closureは実行し、criterion-level `applicable_population=none` の根拠に使えます。

### 3.7 AT applicability → execution → final semantic の順序

AT procedureを持つcriterionは次の順序に固定します。

1. criterion row / 全procedure execution rowをmaterializeする。AT procedureのapplicabilityは `unknown` で開始する
2. machine / population discovery等、AT applicability decisionに必要なcurrent evidenceを取得する
3. `_05k` の `procedure_applicability_contracts[]` に従ってAT applicability decisionだけを実行する。このdecisionは `assistive-technology-result` とfinal `s-wcag-*` semantic resultをInputにしない
4. scriptがdecision refをAT procedure rowへ投影する
5. `applicable` ならAT procedureを実行、`not-applicable` ならcomplete + null result、`unknown` ならcriterionをfinal resultへ進めない
6. ATを含む全applicable sibling procedureがclosureした後で、final `s-wcag-*` semantic evaluationを実行する
7. final semantic procedureのrequired evidence roleはcurrent applicable procedure集合から導出する。`not-applicable` procedureのresult roleは要求せず、applicability basis refだけをtraceabilityへ残す

これにより `final semantic decision → AT applicability → AT result → final semantic decision` の循環を作りません。

arbitrary condition expression、procedure selector DSL、LLM supplied fallback keyは追加しません。

## 4. criterion evaluation plan

`wcag_criterion_plan.py materialize` は、sampleとrequired presentation variationの組合せごとにrequired Success Criterion全件をrow化します。

各row:

- criterion evaluation ref
- sample ref
- variation ref
- process ref（存在する場合）
- criterion ref
- target WCAG version / level
- procedure execution refs
- procedure applicability / applicability basis refs
- required capabilities
- observation request refs
- measurement refs
- supported ACT Rule result refs
- semantic / manual / AT / external evidence decision refs
- applicable population: `present / none / unknown`
- execution status: `pending / in-progress / complete / blocked`
- result: `satisfied / not-satisfied / undetermined / null`
- limitation / blocker

criterion evaluation refはartifact-localに `CRIT-001` から決定論的に採番します。

状態と判定を混ぜません。

- `pending / in-progress` → resultは `null`
- `blocked` → resultは `null`
- `complete` → resultは `satisfied / not-satisfied / undetermined` のいずれか

required criterion set × required variation setとrow setの集合差分をscriptが計算し、差分が1件でもあればsample evaluationをcomplete扱いしません。

## 5. applicable population

Success Criterionへ適用対象contentが存在するかもprocedure contractで閉じます。

`applicable_population=none` にできるのは、そのcriterionに必要なpopulation discovery / semantic applicability procedureをすべて完了し、宣言したsample / variation scopeに対象contentが存在しないことを確認した場合だけです。

`applicable_population=none` かつ必要procedure closureが完了した場合はSuccess Criterion resultを `satisfied` にできます。

単一ACT Ruleの `inapplicable`、単一element population 0件、未読source、観測失敗だけからcriterion全体のpopulation noneを導出しません。population completenessを閉じられない場合は `unknown` とし、resultを推測しません。

## 6. live observation requestへの変換

`wcag_criterion_plan.py` はselected procedureからrequired capabilityを集約します。observation requestはprocedure applicabilityが `applicable` のexecutionだけから生成します。semantic/manual/AT側の追加観測は `_05g` canonical observation field requestへ、machine procedureのbrowser入力はprocedure catalogの `required_machine_probe_keys` から `_05j` のtyped `request_kind=wcag-machine-probe` requestへmaterializeし、formal handoffへ渡します。`unknown / not-applicable` procedureからbrowser requestを先行生成しません。

同一sample / variation / stateで共有できるrequestはdeduplicateします。

formal artifact内のobservation request rowは次の2 kindだけを許可します。

`wcag-machine-probe`:

- observation request ref
- request signature
- request kind
- criterion evaluation ref
- procedure execution ref
- machine probe key
- sample / variation / process / requirement refs
- target refまたはpopulation identity input
- required browser capability
- currentness dependency

`semantic-observation`:

- observation request ref
- request signature
- request kind
- criterion evaluation ref
- procedure execution ref
- `_05g` canonical observation field key
- fixed predicate / payload（必要な場合）
- sample / variation / process / requirement refs
- target / state basis refs
- input evidence refs / fingerprint

`request_signature` はrequest kind、criterion / procedure identity、sample / variation / process / requirement、machine probe keyまたはcanonical observation field / predicate、target / population / state identityからscriptが導出します。自然言語reason、render順、artifact-local request refはsignatureへ含めません。同一signatureをdeduplicateした後にartifact-local observation request refを決定論的に採番します。machine requestへ自然言語browser instructionを保存せず、semantic requestへmachine probe keyを直接入力しません。

例:

- `dom` + supported ACT Rule → title / element population / relevant DOM fields
- `accessibility-semantics` → role / accessible name / description / state
- `viewport` → viewport-state / element-geometry
- `computed-style` →必要propertyだけ
- `visual` →必要state / viewportのscreenshot
- `timing` →fixed interaction timing request

LLMはcriterionごとにprobe keyを手列挙しません。procedure → machine probe keyの解決はformal側 `wcag_criterion_plan.py` が所有します。`usability-inspection` の `observation_contract.py` は渡されたtyped requestの `machine_probe_key` をlocal `_05j` catalogへ解決してfixed browser dispatchをmaterializeしますが、formal procedure catalogを読み直しません。

returned evidenceがstale、観測失敗、追加観測必要等でbrowser再実行が必要な場合、同じstarted handoffを再利用せず `_04c` のnew handoff lineageを使います。

## 7. scriptへ移すmachine処理

入力が揃えば決定論的に処理できるものは今回実装します。

### target geometry / spacing

`measurement.py` がnormalized bounding box / neighboring target geometryからrequired width / height / spacingを計算します。exception、equivalent target、inline target等の意味判断だけをsemantic procedureへ残します。

### contrast ratio

`measurement.py` がnormalized sRGB foreground / effective background colorからrelative luminanceとcontrast ratioを計算します。

- alpha合成後effective colorをbrowser probeで確定できる場合だけ計算
- gradient / image background / blend等で一意に取得できなければ `measurement-unavailable`
- large text、graphical object、inactive control等のapplicability / exceptionはsemantic procedure

LLMへrelative luminance計算やratio比較をさせません。

### viewport / overflow / reflow

`observation_contract.py` がcanonical viewport / geometryを返し、`measurement.py` がscroll extent / viewport overflow等を導出します。reflow exception等の意味判断はsemantic procedureです。

### elapsed / threshold

`_05e_performance-measurement.md` のcontractを再利用します。

### supported ACT Rule

`_05d` で固定した3 ruleだけ `criterion_checks.py` が明示dispatchします。

ACT Rule `failed` がmapped requirementの `not-satisfied` を直接証明できる場合はそのmappingを保持できます。`passed / inapplicable` だけでSuccess Criterion全体を `satisfied` にしません。

## 8. semantic / manual / AT処理

machineへ移せないものも実行経路を未定義にしません。

procedure catalogに基づき必要execution rowを必ずmaterializeします。semantic layerはprocedureで定義したdecisionに加えて、判断理由、uncertainty / unresolved condition、使用したevidence refs、必要な場合の追加観測要求を返せます。structured outputを求めるのはcriterion / procedure集合やstatusをLLMに手組みさせないためであり、意味判断そのものを固定enumだけへ縮退させるためではありません。

「どのcriterionを確認するか」「どのrequired procedureを省略するか」「何を未実施として隠すか」をsemantic layerへ自由入力させません。一方で、required procedureを評価する過程で複数evidenceの関係、目的、意味、例外、content equivalence等を総合判断することはsemantic layerの責務です。

追加evidenceが必要な場合は `_05g` のsemantic追加観測契約へ要求を返します。追加観測によってrequired Success Criterion集合 / procedure集合を変更せず、fixed observation contractで安全に取得できなければ `undetermined / blocked` に残します。

semantic判断からWCAG criterionとは別のユーザビリティ / business flow上の懸念を発見した場合、その懸念をWCAG resultへ混ぜません。必要なら別のusability-evaluation / Findingへroutingできます。

必要evidence不足は `undetermined`、必要環境自体がなく実施不能なら `blocked` とします。

## 9. Success Criterion result

sample / variation単位のSuccess Criterion result:

- `satisfied`
- `not-satisfied`
- `undetermined`

`not-satisfied` はapplicableなviolationを必要evidenceで確認した場合に使用できます。

`satisfied` は、

- applicable populationが `none` と完全に確認できた、または
- applicable populationが `present` でprocedure catalogが要求するapplicableなmachine / semantic / manual / AT / external evidence procedureをすべて閉じた

場合だけ使用します。

machine stepの一部PASS、単一ACT Rule PASS、単一element PASSだけから `satisfied` を生成しません。

`undetermined` がrequired criterion / variationへ残るsampleはtarget conformance levelを満たしたsampleとして扱いません。

## 10. final artifactへの接続

`wcag_criterion_plan.py` のoutputを `wcag_em_structure.py` のcanonical Inputとします。

`wcag_em_structure.py` はLLMから別の `sample requirement result decisions` を受け取りません。

final artifactは `Criterion Evaluation Plan` sectionを持ち、各rowのcriterion evaluation ref / sample ref / variation ref / criterion ref / procedure execution refs / execution status / result / evidence refsを保持します。

`Sample Evaluation Results` の各Success Criterion rowは必ず `criterion_evaluation_ref` を持ち、criterion planのcurrent `execution_status=complete` / resultからscriptがmaterializeします。

conformance requirement resultはこのcanonical Success Criterion result集合とversioned conformance requirement metadataから導出します。

## 11. deterministic validator

production `wcag_criterion_plan.py` と別実装で少なくとも次を検証します。

- target version / level required Success Criterion集合 × required variation集合とcriterion row集合が一致
- duplicate criterion rowなし
- 全criterion asset rowに1件以上のregistered procedure key
- procedure key全件がfinite procedure catalogへ解決
- unknown execution kind / capability / machine dispatch / semantic decision key reject
- machine procedure全件に明示dispatch実装
- formal procedure catalogでmachine procedure全件のrequired machine probe keyが確定し、typed requestへ一意にmaterializeされる
- formal required machine probe key集合とinspection `_05j` catalogのmissing / extra / unused 0はrepository-level contract testで検証する
- supported version / Success Criterion全件の `_05k` semantic contract rowが存在し、versioned requirement assetとsource refが一致
- required observation / measurement / ACT result / semantic / manual / AT refs解決
- applicableなexternal-evidence procedureだけexternal evidence result refを要求し、not-applicable external procedureにresult refを要求しない
- execution statusとresultの組合せ整合
- `applicable_population=none` のcompleteness evidence
- 単一ACT `inapplicable` だけでpopulation none / criterion satisfiedにしていない
- procedure applicability mode / `applicability_decision_key` / activation source / limitation code整合
- `external_evidence_allowed=false` のcriterionにexternal-evidence procedureが割り当てられていない
- `external-evidence-available` procedureがcandidateなし / current valid evidenceなしをnot-applicableへ閉じ、外部証拠不足だけでcriterionをundetermined / blockedにしていない
- `applicability_mode=semantic` procedureのapplicability decisionが自身のprocedure resultまたはfinal semantic resultへ依存していない
- final semantic required evidence roleがcurrent applicable procedure集合から導出され、not-applicable sibling resultを要求していない
- `not-applicable` procedureがbasis refなしでclosureされていない
- `machine-limitation` fallbackがsource procedure closure前にapplicable / not-applicableへ確定されていない
- `satisfied` にrequired applicable procedure未完了なし
- `not-satisfied` にviolation evidenceあり
- `undetermined` にreasonあり
- pending / in-progress / blockedが残るartifactをcompleteにしない
- ACT `passed / inapplicable` だけからSuccess Criterion `satisfied` を生成していない
- target level coverage countをLLM supplied countから採用していない
- final `Sample Evaluation Results` がcurrent criterion evaluation refsからだけ生成される
- versioned requirements asset / procedure catalog hashとapproved hash一致

## 12. fixture

少なくとも次を持ちます。

- WCAG 2.0 / A, AA, AAA
- WCAG 2.1 / A, AA, AAA
- WCAG 2.2 / A, AA, AAA
- required criterion 1件欠落 → invalid
- required variation × criterion row 1件欠落 → invalid
- duplicate criterion row → invalid
- procedure key未登録 / catalog row `TBD` → invalid
- machine procedure dispatch欠落 → invalid
- supported ACT Rule failed → mapped requirement not-satisfied可能
- supported ACT Rule passedだけ → criterion satisfied不可
- single ACT inapplicableだけ → applicable population none不可
- complete population discoveryで対象contentなし → criterion satisfied可能
- target-size machine calculation + exception semantic judgment
- contrast ratio machine calculation + gradient background unavailable
- reflow geometry + semantic exception
- external evidence candidate 0件 → external procedure not-applicable + manual / semantic経路でcriterion closure継続
- external evidence candidateあり、全件stale / scope mismatch → external procedure not-applicable + rejection traceability、criterionは外部証拠不足だけでblockedにしない
- current scope matching external evidenceあり → external procedure applicable + valid evidence refだけをresultへ使用
- `external_evidence_allowed=false` + external procedure割当 → invalid
- AT procedure applicable / environment unavailable → blocked
- machine limitationに対応するmanual fallbackがscriptでapplicable化され、machine limitationだけでcriterionをblockedへ短絡しない
- manual fallback evidence不足 → undetermined、manual実施環境 / evaluator capability自体がない場合 → blocked
- semantic procedureが追加観測を要求 → fixed observation contractで取得 → 同じprocedureを再評価
- 同一追加観測をnew evidenceなしで再要求 → no-progressとしてundetermined / blocked
- fixed observation contractで表現できない追加観測 → ad hoc probeを作らずundetermined / blocked
- semantic判断で別のusability concernを発見 → WCAG resultへ混ぜず別routing
- execution pending / blocked + result非null → invalid
- all required applicable procedure closure → satisfied可能
- stale observation → new handoffで再観測
- stale observation / measurementをcompletionへ数えない
- final sample resultがcriterion plan refを迂回 → invalid

## 13. 完了条件

- supported WCAG 2.0 / 2.1 / 2.2の全Success Criterionに1件以上のfinite procedure keyがある
- supported version / Success Criterion全件に `_05k` のsemantic contract rowがあり、normative clause / exception / evidence role coverageを実装時判断へ残さない
- procedure catalogに `TBD` / catch-all / generic DSLがなく、全machine procedureに明示dispatchがある
- machine化できる処理をsemantic / manualへ逃がしていないことをprocedure catalog semantic reviewで確認する
- target version / level × required variationからcriterion planをscriptが全件materializeする
- criterionの選択・省略・procedure集合をLLMへ任せない
- semantic procedureの判断理由・uncertainty・追加観測要求を保持でき、fixed procedure catalogをLLMが発見できる意味上の問題の上限として扱わない
- geometry / contrast / overflow / elapsed / supported ACT check等、決定論的処理をscriptへ移す
- AT利用要否をSuccess Criterion固定booleanにせず、selected procedure + current content / technology + baselineから閉じる
- applicable contentが存在しない場合のsatisfied条件をpopulation completeness付きで閉じる
- execution statusとcriterion resultを分離する
- criterion planからfinal sample resultまで一本道で、LLM supplied result listによる迂回がない
- required evidence不足を推測で埋めない
- supported ACT Ruleがないcriterionも評価対象から落とさない
- sample / variation resultとcriterion plan coverageをdeterministic validatorが独立検証する

## 14. Final closure integrity (2026-10-09)

- `close_criterion()`はcriterion行のprocedure key集合をversioned requirement asset / finite procedure catalogから再照合する。呼び出し側がmachine、manual、AT、external-evidence procedure行を削除・追加・重複してもcriterionをcompleteにできない。procedure applicability自体は既存契約どおり個別に判定する。
- `materialize_plan()`は対象version / level、canonical sample identity、variation identity、process membership、evaluation ref / revisionをbasisとして記録する。`close-report`はこのoutputを再materializeしてplan rowと結果集合を照合し、必要criterion refを呼び出し側の申告配列から導出しない。
- `materialize_sample_results()`で部分実行・再実行は維持する。全件性・currentness・sample / variation / criterion対応を必須にするのはreportをcompleteへ閉じる境界である。

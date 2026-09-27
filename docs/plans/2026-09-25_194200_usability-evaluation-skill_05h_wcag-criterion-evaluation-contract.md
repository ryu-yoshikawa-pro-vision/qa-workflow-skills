# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` がtarget WCAG version / levelから導出したrequired Success Criterionについて、各sample / presentation variation / processで「何を確認するか」「どの処理が担当するか」「何が不足すると完了できないか」を固定します。

目的は、required criterionの選択・省略、評価procedure、machine処理、semantic / manual判断、assistive technology利用、未完了判定を実装者やLLMのその場判断へ残さないことです。

WCAG-EM 2.0のsample / variation / process / report契約は `_05f_wcag-conformance-evaluation-package-and-runtime.md`、browser observationは `_05g_usability-inspection-browser-observation-contract.md`、general accessibility / ACT Rule semanticsは `_05d_accessibility-requirements-and-act.md` を正本とします。

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
      "page-title-machine-presence",
      "page-title-purpose-semantic"
    ],
    "external_evidence_allowed": false
  }
}
```

supported WCAG 2.0 / 2.1 / 2.2の全Success Criterionで `procedure_keys` を1件以上必須にします。`TBD`、空集合、未登録keyを許可しません。

3 versionのrequirements assetは既存 `static_data_versions` / approved hash契約対象で、evaluation metadataもcanonical hashへ含めます。

### 2.2 finite procedure catalog

各procedure row:

- `procedure_key`
- `execution_kind`: `machine / semantic / manual / assistive-technology / external-evidence`
- `source_item_refs`
- `applicable_criterion_refs`
- `required_capabilities`
- `required_observation_fields`
- `required_input_refs`
- `machine_dispatch_key`。execution kindがmachineの場合だけ必須
- `semantic_decision_key`。execution kindがsemanticの場合だけ必須
- `result_contract`
- `completion_evidence`
- `limitation_behavior`

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

今回少なくとも次のdispatchを固定します。

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

`semantic_decision_key` ごとに、

- 必須evidence
- 許可decision field
- 不足時の `undetermined / blocked`
- machine resultから自動昇格してはいけない条件

をreference / procedure catalogへ固定します。

### 3.3 manual

人間またはAgentがevidenceを確認する必要があるが、特定assistive technologyの実使用を前提にしないprocedureです。必要な観測対象、操作、expected evidenceをcatalogへ固定します。

### 3.4 assistive technology

AT利用はSuccess Criterionごとの静的booleanにしません。

procedure catalogで `required_capabilities` に `assistive-technology` を含むprocedureを定義し、current content / technology / accessibility support baselineに対してそのprocedureがapplicableかをsemantic layerが判断します。scriptは選択されたprocedureとbaseline / environmentを照合します。

必要なAT procedureを実施できない場合は推測で閉じず `blocked` またはresult `undetermined` とします。

### 3.5 external evidence

既存監査結果、field data、project instrumentation等を利用できるprocedureだけをcatalogへ登録します。source / revision / environment / freshness / scope一致を必須にします。

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

`wcag_criterion_plan.py` はselected procedureからrequired capability / observation fieldを集約し、formal handoffへ渡すobservation requirementを生成します。

同一sample / variation / stateで共有できるrequestはdeduplicateします。

例:

- `dom` + supported ACT Rule → title / element population / relevant DOM fields
- `accessibility-semantics` → role / accessible name / description / state
- `viewport` → viewport-state / element-geometry
- `computed-style` →必要propertyだけ
- `visual` →必要state / viewportのscreenshot
- `timing` →fixed interaction timing request

LLMはcriterionごとにprobe keyを手列挙しません。machine observationからfixed probeへの変換は `_05g` の `observation_contract.py` が所有します。

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
- required observation / measurement / ACT result / semantic / manual / AT / external evidence refs解決
- execution statusとresultの組合せ整合
- `applicable_population=none` のcompleteness evidence
- 単一ACT `inapplicable` だけでpopulation none / criterion satisfiedにしていない
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
- AT procedure applicable / environment unavailable → blocked
- manual evidence不足 → undetermined
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

# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` で、live browserからmachine-readable observationを取得する前後の契約を固定します。

目的は、target解決、bounding box、viewport、focus、accessible semantics、computed style、responsive boundary、PerformanceEntry、interaction timing等の取得方法・request schema・result schema・取得不能状態をAgentのその場判断へ残さないことです。

browser I/OそのものはPR #12のcurrent browser execution pathが所有します。今回新しいbrowser runner / wrapper / accessibility engineは作りません。決定論化できるrequest生成、fixed probe payload、target resolver、result normalization、required field / capability検証はSkill-local scriptへ移します。

## 1. 既存browser経路との関係

実装開始時はPR #12 merge後current `test-execution` の実行手段選択を再確認し、利用可能な経路をそのまま使います。

- Playwright MCP
- Playwright CLI
- 独立した今回run用Playwright Libraryコード

`usability-inspection` のために新しいrunner selection frameworkを追加しません。

browser ownerは `observation_contract.py` がmaterializeしたrequest / target resolver / fixed predicateだけを実行します。Agentが観測値の単位、enum、派生値、required field、probe result statusを手で決めません。

## 2. package追加

`skills/usability-inspection/` へ次を追加します。

```text
scripts/
├── observation_contract.py
assets/
├── browser-observation-catalog.json
```

`browser-observation-catalog.json` はmetadataだけを持ち、JavaScript式や汎用rule DSLを入れません。

catalog row:

- `probe_key`
- `execution_kind`: `playwright-native / fixed-page-evaluate / evidence-capture / external-source-read`
- `provided_observation_fields`
- required request fields
- required result fields
- result value type / unit
- clock domain（applicableな場合）
- required browser capability
- sensitive-data handling
- fixed implementation dispatch key

`observation_contract.py` は明示dispatchでrequest / fixed payload / result validationを処理します。各canonical observation field keyはcatalog内で1つのfixed probeだけがownerとなり、field → probe mappingを一意にします。任意式、任意JavaScript、plugin registryを入力として受けません。

## 3. observation lifecycle

```text
requested scope / formal handoff / selected rule / measurement kind
        ↓
inspection_structure.py
  - scope row
  - target-specific semantic applicability
        ↓
semantic / browser owner
  - user-facing discovery後のtarget draft
        ↓
observation_contract.py materialize-targets
  - TARGET-001等のtarget ref
  - resolver kind / payload
  - population / document currentness
        ↓
observation_contract.py plan
  - scope / selected rule / measurementからrequired observation field / probe key集合
  - PROBE-001等のprobe request ref
  - fixed predicate request
  - required result schema
        ↓
browser owner
  - resolverをcurrent sessionで再解決
  - fixed requestをPR #12 browser経路で直列実行
        ↓
observation_contract.py normalize
  - target resolution / schema / enum / unit / capability検証
  - responsive boundary検出結果 / 実行可能性
  - canonical machine observation
        ↓
semantic evaluation
  ├─ decision complete
  └─ additional evidence required
       ↓
     semantic layer
       - canonical observation field / fixed predicate keyを選択
       - request reason / requester / target stateを返す
       ↓
     observation_contract.py materialize-additional
       - OBSREQ-001等のobservation request ref
       - request identity / input evidence fingerprint
       - field → fixed probe mapping
       - duplicate / no-progress判定
       ↓
     browser owner → normalize → same semantic decisionを再評価
        ↓
criterion_checks.py / measurement.py / inspection_structure.py
```

LLMはraw tool resultからbounding box算術、viewport内外、elapsed、threshold、boundary変換、required field closureを再計算しません。

## 4. browser target registry

element単位のprobeは自然言語labelやPlaywright locator文字列を直接requestへ埋めません。

user-facing情報から対象を識別した後、semantic / browser ownerはtarget draftを返し、`observation_contract.py materialize-targets` がartifact-local target registryを生成します。

共通field:

- `target_ref`: `TARGET-001` から決定論的に採番
- `draft_target_key`: invocation内一意
- scope / state ref
- semantic label
- discovery basis
- resolver kind
- resolver payload
- current document / session identity
- expected match count: 1
- resolution status
- limitation

resolver kindは次だけです。

- `role-name`
- `label`
- `visible-text`
- `machine-population-index`
- `current-session-ref`

任意CSS selector、XPath、JavaScript式、source code path、test idを汎用resolver入力として受けません。

### 4.1 resolver payload

| resolver kind | 必須payload | 任意payload | 固定動作 |
| --- | --- | --- | --- |
| `role-name` | `role`, `name` | `within_target_ref` | Playwrightのrole / accessible name semanticsを使用し `exact=true`、hiddenを明示要求しない |
| `label` | `label_text` | `within_target_ref` | Playwrightのlabel semanticsを使用し `exact=true` |
| `visible-text` | `text` | `within_target_ref` | Playwrightのtext semanticsを使用し `exact=true` |
| `machine-population-index` | `population_ref`, `population_revision`, `index`, `identity_fingerprint` | なし | 同じcurrent population revision内だけで解決 |
| `current-session-ref` | `session_target_ref`, `document_identity` | なし | 同一document / session内だけ有効 |

text matchingのための独自case folding / whitespace algorithmは実装せず、選択したPlaywright locator APIのdocumented matching semanticsを使います。scriptは `exact=true` を固定し、曖昧なsubstring matchを成功扱いしません。

`within_target_ref` がある場合、parent targetを先に一意解決し、そのsubtree内でresolverを評価します。parentがmissing / ambiguous / staleならchildも成功扱いしません。

`machine-population-index` はindex単独で再解決しません。`population_revision` と `identity_fingerprint` が一致する場合だけ同じtargetとみなし、population内容や順序が変わった場合は `stale` です。

`current-session-ref` はnavigation、document replacement、session変更後に `stale` とします。永続identityとして再利用しません。

### 4.2 resolution

各element probe直前にbrowser ownerがresolverを再解決し、match count / current document identity / population revisionを返します。`observation_contract.py normalize` は次へ閉じます。

- `unique`
- `missing`
- `ambiguous`
- `stale`

`unique` 以外ではelement probeを成功扱いせず `unavailable / blocked` へ閉じます。

DOM replacement後もrole/name等のstable resolverが一意に同じ意味対象へ解決できる場合は同じ `target_ref` を継続できます。`machine-population-index` / `current-session-ref` は各currentness条件を満たす場合だけ継続できます。

target ref採番、resolver enum / payload、parent cross-reference、population revision、session currentnessはscriptが検証します。

## 5. fixed probe key

current scopeで少なくとも次を実装します。

### `viewport-state`

- viewport width / height
- scroll x / y
- document scroll width / height
- device scale factor等、current execution pathから取得できるenvironment値

### `element-geometry`

- target ref
- bounding box x / y / width / height
- box取得不能理由

viewport内外、target size、spacing、overlap候補等の数値導出はscriptが行います。

### `element-state`

- visible
- enabled / disabled
- checked / selected / expanded等、current pathでmachine-readableに取得できるstate

### `document-location`

canonical observation field:

- `document.location`

current document URLを取得します。raw URLを永続化する場合はPR #12のevidence安全契約へ従い、secret / token等を含み得るquery / fragmentを無条件に保存しません。安全に保持できない値がsemantic判断に必要な場合は、値を捏造・無断保存せず `unavailable / limitation` とします。

### `element-content`

target registryで一意に解決済みのtargetについて、requestされたfieldだけを取得します。

canonical observation field:

- `element.rendered-text`: user-facing rendered text
- `element.control-value`: input / textarea / select等のcurrent value
- `element.selected-values`: select等のcurrent selected value集合

全DOM textや全form valueを無条件取得しません。fieldごとのfixed dispatchを使い、対象element種別で取得不能なら `unavailable` とします。値の意味がbusiness outcomeと一致するかはsemantic layerが判断します。

### `accessibility-semantics`

- role
- accessible name
- accessible description（取得可能な場合）
- relevant state / property
- host element / role applicabilityに必要なmachine-readable field

値取得だけでWCAG / ARIA requirementを `satisfied` にしません。

### `focus-state`

- active/focused target identity
- focusable / focus-visible判定に必要なmachine-readable値
- before / after request ref

視覚上focus indicatorが認識可能かはvisual evidenceへ残します。

### `computed-style`

criterion / visual checkで必要と確定したpropertyだけ取得します。全computed styleを無条件保存しません。

allowlistはcurrent implemented checkからscriptが導出し、LLMが任意property集合を作りません。

### `responsive-boundaries`

current documentからwidth / height関連のmedia query / size container queryを列挙し、boundary検出結果と実行可能性を返します。

各boundary row:

- boundary ref
- source ref
- query kind: `media / container-size`
- query / container ref
- axis: `width / height / inline-size / block-size`
- comparator
- raw value / unit
- normalized boundary CSS px（導出できる場合）
- normalization method
- condition context
- detection status: `normalized / unsupported / incomplete`
- execution status: `executable / not-executable / not-needed`
- execution reason
- before / boundary / after target values（executableの場合）

#### media query

supported:

- `width / min-width / max-width / height / min-height / max-height`
- legacy min/max syntax
- Media Queries Level 4/5の単純range syntax
- `px / em / rem`
- `and` / comma-separated branch。ただし各size conditionと他conditionを保持する

`px` は直接CSS pxへ正規化します。

`em / rem` を16px等の固定値で換算しません。media queryのrelative unitはpage declarationではなくuser agent / user preferenceを含むinitial valueに基づくため、current browserでqueryを評価してeffective CSS px boundaryを導出します。

単一size thresholdまたは他conditionを固定したまま評価できるbranchでは、browser ownerがviewportを整数CSS px単位で変更し `matchMedia()` のtransitionを固定search procedureで求めます。search range、axis、他condition、取得したtransition pxをresultへ保持します。

他conditionが不安定、複数size conditionを分離できない、transitionを一意に求められない場合は `incomplete` とします。

#### container size query

supported:

- `width / height / inline-size / block-size`
- simple range / min / max
- `px`
- query containerを一意に解決でき、browserからrequired computed referenceを取得できる場合の `em / rem`

container queryのrelative unitを固定16pxで換算しません。query container / rootのcurrent computed referenceをbrowser resultとして取得し、scriptがCSS pxへ正規化します。

`var()`、`calc()`、container query length unit、style query、query containerが一意に解決できないcaseは今回のsupported subset外として `incomplete` にします。

#### boundary executable

boundaryを検出・正規化できることと、そのpresentation stateを安全に作れることを分離します。

- media width / heightでcurrent browserがviewportを設定できる → `viewport-resize`
- width + height compoundで両axisを設定し他conditionを保持できる → `viewport-resize`
- container queryは、既存のuser-facing操作またはviewport resizeでquery containerがrequired boundaryを跨ぐことを観測できる場合だけ `container-observe`
- testのためだけにDOMへstyle属性を注入したりquery container widthを直接書き換えたりしない
- required stateを安全に作れない → `not-executable`。boundary inventory自体は保持するがcoverageをcomplete扱いしない

before / boundary / afterの値はscriptがcanonicalizeし、同じCSS px boundaryをdeduplicate / sortします。

#### unsupported / incomplete

次を推測変換しません。

- `vw / vh / vmin / vmax / cqw / cqh` 等、今回のfixed resolution procedureを持たないunit
- `calc()`
- `var()`
- style query
- parse不能なnested condition
- unreadable stylesheet
- query container unresolved
- normalizedできてもpresentation stateを実現できないrequired boundary

raw CSS全文を成果物へ無条件保存せず、source ref / query kind / raw conditionの必要最小部分 / unsupported reasonを保持します。

### `navigation-timing`

Navigation Timingの必要fieldだけをcurrent page/sessionから取得します。

### `paint-timing`

Paint TimingからFCP等、Plan対象entryだけを取得します。

### `interaction-timing`

actual user-facing input eventからfixed end predicateまでを同一page `performance.now()` clockで取得します。§8を正本とします。

### `screenshot`

visual judgmentが必要なstate / viewportのevidence refを取得します。画像の意味判断はdeterministic runtimeへ押し込みません。

## 6. target discoveryとの境界

probeはUI発見shortcutになりません。

- visual / pointer inspectionでtarget発見前にtest id / hidden selector / source code情報を使わない
- user-facing情報から対象と判断した後、role / accessible name等をautomation手段として使える
- `element-geometry` 等はtarget ref確定後に使う
- off-viewport targetのdiscoverability確認はuser-facing scrollとbefore / after evidenceで行う

`observation_contract.py` は自然言語UIからtargetを選びません。targetの意味的発見はsemantic/browser owner、request schemaとmachine observation closureはscriptです。

## 6.1 semantic判断からの追加観測

固定probe集合は最低限必要なmachine observationを取得するための契約であり、semantic layerが評価途中で追加evidenceの必要性を発見することを禁止しません。

semantic layerは追加観測が必要な場合、少なくとも次のdraftを返します。

- `request_draft_key`: invocation内一意
- requester kind: `usability-evaluation / wcag-procedure`
- requester refまたはrequester draft key
- 関連scope ref
- target refまたはtarget draft key（element対象の場合）
- state draft key（特定stateが必要な場合）
- canonical observation field key
- fixed predicate key / payload（必要な場合）
- 必要な観測内容の説明
- 観測が必要な理由
- current evidence refs

canonical observation field / predicate keyの選択はsemantic layerの責務です。必要な観測内容の説明はLLMの判断理由として保持しますが、scriptがその自然言語からfield / probeを推論しません。field keyは `browser-observation-catalog.json` の ``provided_observation_fields`` に存在し、一意なprobe ownerへ解決できる必要があります。

browser ownerは宣言済みtarget / origin / role / side-effect scopeの中でuser-facing interactionを使って必要stateへ到達できます。LLMが任意CSS selector、XPath、test id、JavaScript式、hidden implementation stateを追加観測の実行方法として指定する契約にはしません。

`observation_contract.py materialize-additional` はartifact-local `OBSREQ-001` 等を採番します。request identityは requester / scope / target / state draft key / canonical observation field / canonical predicate payloadから導出し、current evidence refsはcanonical sortしてinput evidence fingerprintを導出します。ref採番、field → probe mapping、required field、schema、capability、currentnessはscriptが検証します。

同じrequest identityかつ同じinput evidence fingerprintの既存requestがある場合はbrowser操作を反復せず `no-progress` として返します。evidence fingerprintが変わった場合だけ同じsemantic decisionをnew evidence付きで再評価できます。

既存fixed contractで安全に取得できない場合は `unsupported / unavailable / blocked` とし、その結果をsemantic layerへ返します。追加観測のためだけにgeneric probe DSLやad hoc page scriptを追加しません。

formal WCAG handoffでは、追加観測は既存のrequired criterion / procedureを解くためのevidence取得に限定します。追加観測によってrequired Success Criterion集合やprocedure集合を増減しません。browser再実行が必要な場合は `_04c` のnew handoff lineageを使います。

## 7. scopeからprobe集合を導出する

`inspection_structure.py` はraw user requestから完成scope rowをLLMへ作らせません。required observation field集合とprobe集合の導出ownerは `observation_contract.py` に一元化し、`inspection_structure.py` は再計算しません。

inspection mode:

- `general`: `_05c` の固定上位観点7件
- `scoped`: semantic layerが明示要求を正規aspect keyへmappingした集合
- `formal-handoff`: handoffのrequired sample / variation / requirement / observation request集合

`task-flow` rowはtask / flowが明示された場合だけscriptが追加します。

semantic layerへ残すのはpopulationの意味的applicability / exception、visual interpretation等です。

scope rowとselected supported rule / measurement kindから必要probe key集合を `observation_contract.py plan` が導出します。

## 8. interaction timing

Playwright action呼び出しwall-clockで測りません。

### 8.1 start

- action前にfixed probeをarm
- browser page内で対象eventを観測した時点の `performance.now()`
- start / endを同じpage clockへ固定
- input event未観測 → `measurement-unavailable`

### 8.2 end predicate schema

predicate keyとpayloadを固定します。

| predicate | 必須field | 固定判定 |
| --- | --- | --- |
| `element-visible` | `target_ref` | targetがuniqueでvisible |
| `element-hidden` | `target_ref` | targetがhidden、または事前に存在したtargetがcurrent documentで消失 |
| `text-present` | `expected_text` | pageまたは `within_target_ref` 内でPlaywright text semantics + `exact=true` |
| `attribute-equals` | `target_ref`, `attribute_name`, `expected_value` | current attribute値の完全一致 |
| `aria-state-equals` | `target_ref`, `state_name`, `expected_value` | fixed ARIA state valueの一致 |
| `element-enabled` | `target_ref` | unique targetがenabled |
| `element-disabled` | `target_ref` | unique targetがdisabled |
| `url-changed` | `baseline_url` | current URLがarm時URLから変化 |

`text-present` だけ `within_target_ref` を任意fieldとして持てます。`url-changed` はelement targetを要求しません。`baseline_url` はarm時にbrowser ownerが取得し、LLM入力を正本にしません。

`attribute_name` とARIA `state_name` はallowlistをcatalogへ固定します。unknown nameを任意property accessへ変換しません。

semantic layerは「何をuser-facing feedback / ready stateとみなすか」を判断できますが、browserへ渡すのはこのfixed schemaだけです。

任意JavaScript式、CSS selector式、LLM生成predicate functionを受けません。fixed vocabularyで表現できずproject既存instrumentationもない場合は `measurement-unavailable` です。

end predicateがaction前から成立している場合は `preexisting-end-state` issueを返し、0ms成功にしません。

fixed probeはMutationObserver / animation frame等のpackage-owned dispatchを使い、end成立時の `performance.now()` を返します。timeout時はtimeout reasonを返します。

## 9. unavailable / partial result

probe result status:

- `ok`
- `unsupported`
- `unavailable`
- `incomplete`
- `blocked`

`unsupported` はcurrent browser/tool capabilityに機能がない場合、`unavailable` は対象状態や必要eventを取得できない場合、`incomplete` は一部source / boundary / population completenessを閉じられない場合です。

tool failureやprobe unavailableをproduct defect / usability issueへ自動変換しません。

## 10. sensitive data

- full DOM / accessibility tree / CSS全文を既定で保存しない
- screenshotはPR #12のevidence safety契約を再利用
- password、token、cookie、storageState、secret値をresultへ含めない
- user text / accessible nameに個人情報が含まれ得る場合は必要最小限だけ残す

## 11. deterministic fixture

- general / scoped / formal-handoff mode
- task / flow未指定でtask-flow rowなし
- selected rule / measurement → required observation field / probe集合
- unknown probe reject
- `role-name / label / visible-text` exact resolver、within scope
- machine population revision一致 / 変更時stale
- current-session-ref navigation後stale
- target unique / missing / ambiguous / stale
- viewport / element geometry schema
- `document.location` のfixed probe / sensitive URL handling
- `element.rendered-text / element.control-value / element.selected-values` のtarget-local fixed probe
- semantic additional observation draft → OBSREQ ref / field → probe mapping / request identity / evidence fingerprint
- same request identity + same evidence fingerprint → no-progress
- unknown observation field → unsupported。自然言語からprobeを推論しない
- geometry machine calculation
- media query px boundary
- media query em / rem boundaryをcurrent browser評価でCSS pxへ正規化
- media compound conditionを保持
- container px / resolvable em / rem
- unsupported relative unit / calc / var / style query
- boundary normalizedだがstateを実現できない → not-executable / incomplete
- complete boundary inventory → before / boundary / after
- accessibility semanticsをrequirement resultへ自動昇格しない
- 8種fixed end predicate schema
- predicate required field欠落 / unknown attribute or ARIA state reject
- start / end same clock
- preexisting end → measurement-unavailable
- unsupported custom predicate reject
- timeout → measurement-unavailable
- screenshotからsemantic result自動生成なし
- secret / full raw snapshotを必須resultにしない

## 12. 完了条件

- browser target registry / resolver payload / currentness / uniquenessが固定
- locator matchingをPlaywright documented semantics + exact matchingへ固定し、独自曖昧matchingを作らない
- machine-population-indexをrevision / fingerprintなしで再利用しない
- fixed probe payload / normalizationをSkill-local scriptが所有
- canonical observation field → fixed probe mappingをcatalogで一意にし、semantic layerはfield keyを選べるがscriptは自然言語からprobeを推論しない
- semantic additional observation requestをOBSREQ ref / identity / evidence fingerprint付きでmaterializeし、no-progressを機械判定する
- final artifactに `planned` requestを残さず、completed / unsupported / no-progress / blockedのいずれかへ閉じる
- document location / rendered text / control value / selected value等、business flowの意味判断に必要でmachine取得可能な値をfixed probeで取得する
- raw browser valueの算術・enum・closureをLLMへ戻さない
- general / scoped / formal-handoff scope row生成が決定論化
- rule / measurementから必要probe集合をscript導出
- arbitrary JavaScript / generic probe DSLなし
- media query `px / em / rem` と、条件付きでcontainer query `px / em / rem` を固定procedureで正規化
- boundary detectionとexecution feasibilityを分離し、実現不能stateをcomplete扱いしない
- responsive boundary completenessをunreadable / unsupported / not-executable source込みで扱う
- 8種fixed end predicateのrequest schema / required fieldが固定
- interaction timing start / end / predicate / clock domainが固定
- fixed predicateで表せないmeasurementを捏造しない
- PR #12のbrowser ownership / side-effect / cleanup / evidence safety契約を再利用
- browser runner / wrapperを二重実装しない

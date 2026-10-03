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

### 2.1 canonical observation field inventory

semantic layerが追加evidence取得のために指定できるobservation field keyは次だけです。key名は実装時に変更・追加せず、追加が必要なら先にPlanを更新します。formal WCAGのmachine procedureが必要とする固定browser取得はこの自由選択interfaceへ載せず、`_05j_wcag-machine-browser-observation-contract.md` の `machine_probe_key` を `wcag_criterion_plan.py` がprocedureから導出します。

| observation field key | owner probe | request payload | canonical result |
| --- | --- | --- | --- |
| `viewport.metrics` | `viewport-state` | なし | viewport width/height、scroll x/y、document scroll width/height、device scale factor |
| `element.geometry` | `element-geometry` | `target_ref` | x/y/width/height CSS px、取得不能理由 |
| `element.state` | `element-state` | `target_ref` | visible、enabled/disabled、checked、selected、expanded等のfixed state object |
| `document.location` | `document-location` | なし | current page URLのsafe value / limitation |
| `element.rendered-text` | `element-content` | `target_ref` | Playwright `locator.innerText()` の返却値 |
| `element.control-value` | `element-content` | `target_ref` | Playwright `locator.inputValue()` の返却値 |
| `element.selected-values` | `element-content` | `target_ref` | selected optionをDOM順で `{value,label}` 配列化した値 |
| `accessibility.semantics` | `accessibility-semantics` | `target_ref` | role / accessible name / description / relevant state-property |
| `focus.state` | `focus-state` | target / before-after context | active target identity、focusable / focus-visible machine values |
| `computed-style.properties` | `computed-style` | `target_ref`, allowlisted `property_names` | requested property name/value map |
| `responsive.conditions` | `responsive-conditions` | current document / Authority context | media / container size / style / scroll-state condition rows、source / capability / execution feasibility |
| `responsive.boundaries` | `responsive-boundaries` | `responsive.conditions` のsize condition | browser-evaluated numeric transition rows / completeness / execution feasibility |
| `navigation.timing` | `navigation-timing` | なし | allowlisted Navigation Timing fields |
| `paint.timing` | `paint-timing` | なし | allowlisted Paint Timing entries |
| `interaction.timing` | `interaction-timing` | fixed predicate payload | same-page clockのstart/end/elapsedとpredicate result |
| `screenshot.image` | `screenshot` | viewport / target / state context | evidence ref |

`browser-observation-catalog.json` の `provided_observation_fields` はこの16-key inventoryの部分集合だけを持ち、全fieldはちょうど1つのprobeへ解決します。unknown key、alias、自然言語field名を受け付けません。これら16 keyはsemantic追加観測interfaceです。WCAG machine procedure内部の固定probe inventoryとは別契約で、LLMへmachine probe keyを返させません。

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
       - request reason / requester kind / requester identity / target / state basis refsを返す
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
- scope ref
- current document / session identity
- discovery evidence refs
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

current document URLはPlaywright `page.url()` のcurrent valueを取得します。observation layerで独自URL正規化をしません。永続化前にPR #12のevidence安全契約へ従い、secret / token等を含み得るquery / fragmentを無条件に保存しません。sanitizationで意味判断に必要な部分を保持できない場合は、値を捏造・無断保存せず `unavailable / limitation` とします。

### `element-content`

target registryで一意に解決済みのtargetについて、requestされたfieldだけを取得します。

canonical observation field:

- `element.rendered-text`: Playwright `locator.innerText()` の返却値をそのままcanonical raw valueとして保持する。observation layerではtrim / case folding / whitespace collapseをしない
- `element.control-value`: Playwright `locator.inputValue()` を使い、current DOM propertyとしてのvalueを保持する。対象外elementでは `unavailable`
- `element.selected-values`: uniqueな`<select>`に対するfixed page evaluateで `HTMLSelectElement.selectedOptions` をDOM順に読み、各optionを `{value: option.value, label: option.label}` として返す。semantic判断ではuser-facing labelを優先できるが、machine resultではvalueとlabelを両方保持する

全DOM textや全form valueを無条件取得しません。fieldごとのfixed dispatchを使い、対象element種別で取得不能なら `unavailable` とします。値の比較に必要な正規化は個別machine procedureが所有し、observation layerへ汎用text normalizationを入れません。値の意味がbusiness outcomeと一致するかはsemantic layerが判断します。

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

### `responsive-conditions`

current documentで有効になり得るresponsive / conditional presentation条件をinventory化します。独自の完全CSS parserを作らず、CSSOMとbrowser自身のcondition evaluationを正本にします。

各condition row:

- condition ref
- source ref
- query kind: `media / container-size / container-style / container-scroll-state`
- raw condition textの必要最小部分
- query container name / type / identity（container queryの場合）
- axis / feature（該当する場合）
- browser capability
- evaluation method
- current match state
- execution status: `executable / not-executable / unsupported`
- execution reason
- evidence refs

既知の標準構文を、Plan側のparserが理解できないことだけを理由に `unsupported` にしません。browserがそのconditionを受理・評価できる場合はbrowser評価を使用します。browser / Playwright経路自体が必要capabilityを持たない場合だけ `unsupported` とします。

size query以外のstyle query / scroll-state queryは数値boundaryへ変換しません。presentation variation conditionとして保持し、既存user-facing interactionまたは安全なenvironment操作でrequired stateを作れる場合だけ実行します。required stateを安全に作れない場合は `not-executable` です。

### `responsive-boundaries`

`responsive.conditions` のうちsize conditionについて、browser評価で観測できるnumeric transitionをCSS pxへmaterializeします。

media size condition:

- condition text全体を `matchMedia()` へ渡し、browser parser / evaluation semanticsを正本にする
- width / heightの対象axisを固定したうえで、current browserが設定できる有限viewport rangeを整数CSS pxで探索する
- transitionが存在する場合は固定binary search + neighboring verificationで最小transitionを求める
- `px / em / rem / vw / vh / vi / vb / vmin / vmax` や `calc()` 等、browserが評価できるlength表現を独自換算しない
- query textに対して独自に `var()` を展開しない。browserがconditionを有効に評価でき、viewport変更でtransitionを観測できる場合だけ結果を採用する
- boolean combination / comma branchはraw conditionとbranch identityを保持し、transitionを一意に分離できない場合はcondition自体を失わず `incomplete` とする

container size condition:

- CSSOMとcomputed `container-name / container-type` からquery containerを一意に解決する
- `px / em / rem / viewport-relative / container-relative length / calc()` 等はbrowserのcomputed / used valueと実際のquery match変化を正本にし、固定16px等で換算しない
- `cqw / cqh / cqi / cqb / cqmin / cqmax` を既知なのに未対応として落とさない
- viewport resizeまたは既存user-facing interactionでquery container sizeを安全に変化させられる場合、condition matchとcontainer geometryを同じiterationで取得してtransition CSS pxを導出する
- testのためだけにDOM / stylesheetへstyle属性、class、custom propertyを注入しない
- current product behaviorからrequired transitionを安全に作れない場合、condition inventoryは保持して `not-executable / incomplete` とする

custom property / math function:

- `calc()` / `min()` / `max()` / `clamp()` 等のmath functionはbrowserがconditionを評価できる限り、文字列parserで拒否しない
- `var()` やstyle query custom propertyはsource textの手計算をしない。computed value / condition matchをbrowserから取得できる場合だけmachine evidenceとして使用する
- unresolved custom property、invalid at computed-value time、browser capability不足は理由付き状態へ閉じる

boundary row:

- boundary ref
- condition ref
- axis
- before / transition / after CSS px
- browser match state
- query container geometry（container sizeの場合）
- derivation method
- detection status: `normalized / incomplete / unsupported`
- execution status: `executable / not-executable`
- evidence refs

同じconditionのtransitionをcanonicalize / deduplicate / sortします。numeric transitionが存在しないstyle / scroll-state conditionをboundary 0件として消さず、`responsive.conditions` 側でclosureします。

#### unreadable / incomplete

cross-origin stylesheet等でcondition sourceを読み出せない場合、project / adopted Design System Authority、browserから取得できるCSSOM / matched condition evidenceで不足範囲を閉じます。閉じられないsourceが残る場合はinventoryをcomplete扱いしません。

`unsupported` はcurrent browser/tool capabilityが標準機能を実行できない場合に限定します。既知の標準構文を実装都合で恒久的なsupported subset外へ置きません。

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
- requester kind: `usability-evaluation / inspection-requirement / wcag-procedure`
- requester identity。kindごとのref/draft keyは `_03` / `_05a` を正本とする
- 関連scope ref
- target refまたはtarget draft key（element対象の場合）
- state description（説明用。identityには使わない）
- state basis refs。既存immutable action / evidence / sample / variation refsをcanonical sortして保持
- current document identity（live documentに依存する場合）
- canonical observation field key
- fixed predicate key / payload（必要な場合）
- 必要な観測内容の説明
- 観測が必要な理由
- current evidence refs

canonical observation field / predicate keyの選択はsemantic layerの責務です。必要な観測内容の説明はLLMの判断理由として保持しますが、scriptがその自然言語からfield / probeを推論しません。field keyは `browser-observation-catalog.json` の ``provided_observation_fields`` に存在し、一意なprobe ownerへ解決できる必要があります。

browser ownerは宣言済みtarget / origin / role / side-effect scopeの中でuser-facing interactionを使って必要stateへ到達できます。LLMが任意CSS selector、XPath、test id、JavaScript式、hidden implementation stateを追加観測の実行方法として指定する契約にはしません。

`observation_contract.py materialize-additional` はusability-inspectionがcurrent browser/session ownerの場合だけartifact-local `OBSREQ-001` 等を採番します。request identityはcanonical requester identity / scope / target / canonical sort済みstate basis refs / current document identity / canonical observation field / canonical predicate payloadから導出し、state descriptionの自由記述は含めません。current evidence refsはcanonical sortしてinput evidence fingerprintを導出します。ref採番、field → probe mapping、required field、schema、capability、currentnessはscriptが検証します。

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
- canonical observation field inventory全16 key → exactly-one probe mapping
- `document.location` は `page.url()`、`element.rendered-text` は `locator.innerText()`、`element.control-value` は `locator.inputValue()`、`element.selected-values` はselectedOptions `{value,label}` を使用
- semantic additional observation draft → OBSREQ ref / requester kind / field → probe mapping / state basis identity / evidence fingerprint
- same request identity + same evidence fingerprint → no-progress
- unknown observation field → unsupported。自然言語からprobeを推論しない
- geometry machine calculation
- media / container size conditionのbrowser evaluationとnumeric transition
- `px / em / rem / viewport-relative / container-relative / calc()` を含むsize queryを独自換算せずbrowser match transitionで評価
- `var()` 等を含むconditionはsource textから展開せず、browserが有効に評価できる場合だけ採用
- media compound condition / comma branch identityを保持
- container query container identity / geometryとtransitionの対応
- style / scroll-state queryを非数値responsive conditionとして保持
- browser capability不足 → unsupported、safe state作成不能 → not-executable / incomplete
- boundary normalizedだがstateを実現できない → not-executable / incomplete
- complete responsive condition inventory → numeric boundaryまたはstate別closure
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
- semantic追加観測用canonical observation field inventoryを本ファイルの16 keyへ固定し、catalogでexactly-one fixed probeへ解決する。semantic layerはfield keyを選べるがscriptは自然言語からprobeを推論しない。formal WCAG machine procedureの固定browser入力は `_05j` を正本とする
- semantic additional observation requestをOBSREQ ref / identity / evidence fingerprint付きでmaterializeし、no-progressを機械判定する
- final artifactに `planned` requestを残さず、completed / unsupported / no-progress / blockedのいずれかへ閉じる
- document location / rendered text / control value / selected value等、business flowの意味判断に必要でmachine取得可能な値をfixed probeで取得する
- raw browser valueの算術・enum・closureをLLMへ戻さない
- general / scoped / formal-handoff scope row生成が決定論化
- rule / measurementから必要probe集合をscript導出
- arbitrary JavaScript / generic probe DSLなし
- responsive condition inventoryとnumeric size transitionを分離し、browserが評価可能な標準構文をPlan都合のsupported subsetへ落とさない
- size queryのlength / math functionを独自換算せずbrowser evaluationを正本にし、style / scroll-state queryは数値boundaryへ偽装しない
- condition detectionとexecution feasibilityを分離し、実現不能stateをcomplete扱いしない
- responsive completenessをunreadable / unsupported / not-executable source込みで扱う
- 8種fixed end predicateのrequest schema / required fieldが固定
- interaction timing start / end / predicate / clock domainが固定
- fixed predicateで表せないmeasurementを捏造しない
- PR #12のbrowser ownership / side-effect / cleanup / evidence safety契約を再利用
- browser runner / wrapperを二重実装しない

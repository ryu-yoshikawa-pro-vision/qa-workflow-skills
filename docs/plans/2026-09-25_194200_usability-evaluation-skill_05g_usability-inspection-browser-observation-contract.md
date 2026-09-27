# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `usability-inspection` で、live browserからmachine-readable observationを取得する前後の契約を固定します。

目的は、bounding box、viewport、focus、accessible semantics、computed style、responsive boundary、PerformanceEntry、interaction timing等の取得方法・result schema・取得不能状態をAgentのその場判断へ残さないことです。

browser I/OそのものはPR #12のcurrent browser execution pathが所有します。今回新しいbrowser runner / wrapper / accessibility engineは作りません。決定論化できるrequest生成、fixed probe payload、result schema、normalization、required field / capability検証はSkill-local scriptへ移します。

## 1. 既存browser経路との関係

実装開始時はPR #12 merge後current `test-execution` の実行手段選択を再確認し、利用可能な経路をそのまま使います。

- Playwright MCP
- Playwright CLI
- 独立した今回run用Playwright Libraryコード

`usability-inspection` のために新しいrunner selection frameworkを追加しません。

browser ownerは `observation_contract.py` がmaterializeしたobservation requestを実行します。Agentが観測値の単位、enum、派生値、required field、probe result statusを手で決めません。

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
- required request fields
- required result fields
- result value type / unit
- clock domain（applicableな場合）
- required browser capability
- sensitive-data handling
- fixed implementation dispatch key

`observation_contract.py` は明示dispatchでrequest / fixed payload / result validationを処理します。任意式、任意JavaScript、plugin registryを入力として受けません。

## 3. observation lifecycle

処理順を固定します。

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
  - resolver schema / currentness / uniqueness contract
        ↓
observation_contract.py plan
  - scope / selected rule / measurementからrequired observation field / probe key集合
  - PROBE-001等のrequest ref
  - required result schema
        ↓
browser owner
  - target resolverをcurrent sessionで再解決
  - current PR #12 browser経路でrequestを直列実行
        ↓
observation_contract.py normalize
  - target resolution / schema / enum / unit / capability検証
  - canonical machine observation
        ↓
criterion_checks.py / measurement.py / inspection_structure.py
```

LLMはraw tool resultからbounding box算術、viewport内外、elapsed、threshold、required field closure等を再計算しません。

## 3.1 browser target registry

element単位のprobeは、自然言語labelやPlaywright locator文字列を直接requestへ埋めません。

user-facing情報から対象を識別した後、semantic / browser ownerはtarget draftを返し、`observation_contract.py materialize-targets` がartifact-local target registryを生成します。

target row:

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

resolver kindは次に固定します。

- `role-name`
- `label`
- `visible-text`
- `machine-population-index`
- `current-session-ref`

任意CSS selector、XPath、JavaScript式、source code path、test idをtarget registryの汎用入力として受けません。

`machine-population-index` はDOM / accessibility populationをmachine-readableに列挙した後で、そのpopulation内のcanonical orderとindexから対象を再解決する場合だけ使います。discoverabilityの証拠にはしません。

`current-session-ref` はcurrent browser ownerが返すopaque refです。同じdocument / session内だけ有効で、navigation、document replacement、session変更後は `stale` とします。永続identityとして再利用しません。

各element probe直前にbrowser ownerがresolverを再解決し、match count / current document identityを返します。`observation_contract.py normalize` は次へ閉じます。

- `unique`: current targetを1件に解決
- `missing`
- `ambiguous`
- `stale`

`unique` 以外ではelement probeを成功扱いせず `unavailable / blocked` へ閉じます。DOM replacement後も同じresolverが一意に同じ意味対象へ解決できる場合だけ同じ `target_ref` を継続できます。

target ref採番、一意性、resolver enum、session currentness、probeとのcross-referenceはscriptが検証します。LLMは `TARGET-001` 等を手採番しません。

## 4. fixed probe key

current scopeで少なくとも次を固定probeとして実装します。

### `viewport-state`

- viewport width / height
- scroll x / y
- document scroll width / height
- device scale factor等、current execution pathから取得できるenvironment値

### `element-geometry`

- target ref
- bounding box x / y / width / height
- box取得不能理由

viewport内外、target size、overlap候補等の数値導出はraw boxとviewportを入力にscriptが行います。

### `element-state`

- visible
- enabled / disabled
- checked / selected / expanded等、current pathでmachine-readableに取得できるstate

### `accessibility-semantics`

- role
- accessible name
- accessible description（取得可能な場合）
- relevant state / property
- host element / role applicabilityの判定に必要なmachine-readable field

browserが返すaccessible name等は観測事実です。値を取得できたことだけでWCAG / ARIA requirementを `satisfied` にしません。

### `focus-state`

- active/focused target identity
- focusable / focus-visible判定に必要なmachine-readable値
- before / after request ref

視覚上focus indicatorが認識可能かはscreenshot等のvisual evidenceを別に扱います。

### `computed-style`

criterion / visual checkで必要と確定したpropertyだけ取得します。全computed styleを無条件保存しません。

allowlistはcurrent implemented checkから導出し、LLMが任意property集合を成果物用に作りません。

### `responsive-boundaries`

current documentから取得可能なwidth / height関連のmedia query / container query条件を列挙し、正規化可能なboundary valueを返します。

- same-origin / readable CSSOMを対象にする
- inaccessible cross-origin stylesheet等は `unreadable_source_count` とsource refを返す
- unreadable sourceが存在し、project / Design System Authority等の別sourceでもboundary completenessを閉じられない場合はcurrent target boundary inventoryをcomplete扱いしない
- duplicate boundary / sort / before-boundary-afterの数値集合はscriptがcanonicalizeする
- project / Design System Authorityから得るboundaryは、CSS pxとして明示済み、またはAuthority側に明示的なCSS px変換根拠がある値だけmachine boundaryとして受ける。LLMがrelative unitを換算しない

browser probeが直接parseするCSSOMのsupported subsetを固定します。

- media query / size container queryの `width / min-width / max-width / height / min-height / max-height`
- legacy min/max syntax
- Media Queries Level 4の単純range syntax
- length unitは `px` のみ
- `and` で結合されたqueryはsupported size conditionごとにboundaryを抽出し、他conditionをcontextとして保持
- comma-separated queryはbranchごとに処理

次は推測変換せず `incomplete` とします。

- `em / rem / vw / vh / vmin / vmax / cqw / cqh` 等のrelative unit
- `calc()` / `var()`
- `not` を含み単純なsize boundaryへ分解できない条件
- style query等のsize query以外のcontainer query
- parse不能なnested condition
- unreadable stylesheet

unsupported queryのraw全文を成果物へ無条件保存せず、source ref / query kind / unsupported reasonだけを保持します。

CSS本文をraw evidenceとして無条件保存しません。

### `navigation-timing`

Navigation Timingの必要fieldをcurrent page/sessionから取得します。

### `paint-timing`

Paint TimingからFCP等、Planで対象にしたentryだけを取得します。

### `interaction-timing`

actual user-facing input eventから固定したuser-facing end predicateまでの時刻を、同一pageの`performance.now()` clockで取得します。詳細は§7を正本とします。

### `screenshot`

visual judgmentが必要なstate / viewportのevidence refを取得します。画像の意味判断はdeterministic runtimeへ押し込みません。

## 5. target discoveryとの境界

probeはUI発見shortcutになりません。

- visual / pointer inspectionでtargetを発見する前にtest id / hidden selector / source code情報を使わない
- user-facing情報から対象と判断した後、browser ownerがrole / accessible name等のlocatorをautomation手段として使える
- `element-geometry` 等はtarget ref確定後の観測に使う
- off-viewport targetのdiscoverability確認はuser-facing scrollとbefore / after evidenceで行う

`observation_contract.py` は自然言語UIからtargetを選びません。targetの意味的同一性・発見はsemantic/browser owner境界、request schemaとmachine observation closureはscript境界です。

## 6. scopeからprobe集合を導出する

`inspection_structure.py` はraw user requestから完成scope rowをLLMへ作らせません。required observation field集合とprobe集合の導出ownerは `observation_contract.py` に一元化し、`inspection_structure.py` はその集合を再計算しません。

inspection mode:

- `general`: `_05c` の固定上位観点7件をrowとして生成する
- `scoped`: semantic layerが明示要求を正規のaspect key集合へmappingし、scriptがその集合だけをrowへ生成する
- `formal-handoff`: handoffのrequired sample / requirement / observation request集合を正本として必要rowを生成する

`task-flow` rowはtask / flowが明示された場合だけscriptが追加します。

semantic layerへ残すのは、対象UIにpopulationが存在するか、意味上のapplicability / exception、visual interpretation等です。

scope rowとselected supported rule / measurement kindから必要probe key集合を `observation_contract.py plan` が導出します。Agentがruleごとに必要probeを手で列挙しません。

## 7. interaction timing

`actual input event → first visible feedback`、`actual input event → task-ready state` 等をPlaywright action呼び出しwall-clockで測りません。

### start

- action前にfixed probeをarmする
- browser page内で対象eventを観測した時点に `performance.now()` を記録する
- `event.timeStamp` と別clockを混ぜず、start / endとも同じpage `performance.now()` domainへ固定する
- input eventを観測できなければstart未取得として `measurement-unavailable`

### end predicate

semantic layerは「何をuser-facing feedback / ready stateとみなすか」を判断できますが、browserへ渡すpredicateは次のfixed vocabularyへ正規化します。

- `element-visible`
- `element-hidden`
- `text-present`
- `attribute-equals`
- `aria-state-equals`
- `element-enabled`
- `element-disabled`
- `url-changed`

predicateはtarget refとexpected valueを持ち、action前にmaterializeします。

任意JavaScript式、任意CSS selector式、LLM生成predicate functionをmeasurement inputとして受けません。必要なend conditionをfixed vocabularyで表現できず、project既存instrumentationもない場合はそのmeasurementを `measurement-unavailable` とします。

end predicateがaction前から成立している場合は `preexisting-end-state` issueを返し、0ms成功として扱いません。

fixed probeはMutationObserver / animation frame等、current browserで必要な監視をpackage-owned dispatchとして実装し、end成立時の `performance.now()` を返します。timeout時はtimeout reasonを返し、任意の値を補完しません。

### task-ready

`task-ready state` という自然言語labelだけでは測定を開始しません。今回のtargetでreadyを表すfixed predicateをaction前に確定できる場合だけ測定します。

## 8. unavailable / partial result

probe result statusは少なくとも次へ閉じます。

- `ok`
- `unsupported`
- `unavailable`
- `incomplete`
- `blocked`

`unsupported` はcurrent browser/tool capabilityに機能がない場合、`unavailable` は対象状態や必要eventを取得できない場合、`incomplete` は一部sourceを読めずpopulation completenessを閉じられない場合です。

tool failureやprobe unavailableをproduct defect / usability issueへ自動変換しません。

## 9. sensitive data

probeは必要最小fieldだけ返します。

- full DOM / accessibility tree / CSS全文を既定で保存しない
- screenshotはPR #12のevidence safety契約を再利用する
- password、token、cookie、storageState、secret値をresultへ含めない
- user textやaccessible nameに個人情報が含まれ得る場合は成果物へ必要最小限だけ残す

## 10. deterministic fixture

少なくとも次を検証します。

- general mode → 固定7 aspect
- scoped mode → normalized requested aspectだけ
- formal-handoff mode → handoff required scopeだけ
- task / flow未指定でtask-flow rowを作らない
- selected rule / measurementからrequired probe集合を導出
- unknown probe key拒否
- target draft → `TARGET-001` 等の決定論的採番 / resolver enum / unique resolution
- missing / ambiguous / stale targetを成功扱いしない
- probe request refの決定論的採番
- viewport / element geometryのschema
- geometryからのmachine calculationをLLMへ戻さない
- readable / unreadable stylesheetを含むresponsive boundary closure
- supported px media / container size queryとunsupported relative unit / calc / style queryの分離
- accessible semanticsをobservationとして保持しrequirement resultへ自動昇格しない
- interaction timing start / endを同一clock domainで取得
- end predicate preexisting → measurement-unavailable
- unsupported custom predicate拒否
- timeout → measurement-unavailable
- screenshotはsemantic resultを自動生成しない
- secret / full raw snapshotを必須resultにしない

## 11. 完了条件

- browser target registry / resolver / currentness / uniquenessとbrowser observation request / result schemaが固定されている
- fixed probe payload / normalizationをSkill-local scriptが所有する
- raw browser valueの算術・enum・closureをLLMへ戻していない
- general / scoped / formal-handoffのscope row生成が決定論化されている
- rule / measurementから必要probe集合をscriptが導出する
- arbitrary JavaScript / generic probe DSLを導入していない
- responsive boundary completenessをunreadable source込みで扱える
- interaction timingのstart / end / predicate / clock domainが固定されている
- fixed predicateで表せないmeasurementを捏造しない
- PR #12のbrowser ownership / side-effect / cleanup / evidence safety契約を再利用する
- browser runner / wrapperを二重実装しない


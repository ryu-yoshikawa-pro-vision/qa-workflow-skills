# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` のmachine procedureがbrowserから必要とする固定観測を、`usability-inspection` が実行できる有限contractとして定義します。

`_05g_usability-inspection-browser-observation-contract.md` の16 canonical observation fieldはsemantic layerが追加evidenceを必要とした場合に選択できるinterfaceです。本ファイルのmachine probeはformal WCAG machine procedure専用です。

- `wcag-conformance-evaluation` の `wcag_criterion_plan.py` が自packageのprocedure catalogからrequired machine probe keyを導出し、typed observation requestをmaterializeする
- LLMはmachine probe keyを選択・省略・追加しない
- `usability-inspection` はtyped requestを自packageの `wcag-machine-probe-catalog.json` と照合し、current browser ownerとして固定dispatchだけを実行する
- `usability-inspection` はformal procedure catalogを読まず、procedure key → probe keyを再解決しない
- machine probe resultから意味判断を行わない
- fixed probeで閉じない意味・例外・visual interpretationはsemantic / manual procedureへ残す
- 任意JavaScript、任意selector、generic rule DSL、plugin registryは追加しない

formal Skillからsibling Skillのscript / assetを直接import・readしません。cross-packageのformal required machine probe key集合と `wcag-machine-probe-catalog` key集合の一致はrepository-level contract test / CIで検証し、runtimeではformal handoff requestとreturned inspection runtime evidenceで接続します。

## 1. package / ownership

`skills/usability-inspection/assets/wcag-machine-probe-catalog.json` を追加します。新しい `wcag_machine_observation.py` は作りません。既存Planで追加予定の `skills/usability-inspection/scripts/observation_contract.py` が、semantic追加観測とformal WCAG machine probe requestのrequest / result validationを同じbrowser I/O境界で担当します。

`wcag-conformance-evaluation` 側は `wcag_criterion_plan.py` が次のtyped requestをmaterializeします。

- `request_kind`: `wcag-machine-probe`
- `observation_request_ref`
- `request_signature`
- `criterion_evaluation_ref`
- `procedure_execution_ref`
- `machine_probe_key`
- sample / variation / process / requirement refs
- target / population identity input
- required browser capability
- currentness dependency

`usability-inspection` は `procedure_execution_ref` の意味を再解釈せず、`request_kind` と `machine_probe_key` からlocal catalogのfixed dispatchへ一意に解決します。formal側 `request_signature` とcurrent target / population identityを検証し、resultはrequest ref / request signature / machine probe key / currentness / runtime evidenceを保持してformal Skillへ返します。

## 2. machine probe catalog

各rowは次を持ちます。

- `machine_probe_key`
- `execution_kind`: `playwright-native / fixed-page-evaluate / fixed-interaction / evidence-capture`
- required request fields / result fields
- value type / unit
- required browser capability
- target kind / currentness dependency
- sensitive-data handling
- fixed implementation dispatch key

catalogに任意expression、自然言語instruction、JavaScript本文、selector文字列を保存しません。

catalogのcanonical JSON SHA-256は、`request_kind=wcag-machine-probe` を1件以上処理した `usability-inspection` runtime unitだけ `static_data_versions.wcag_machine_probes` へ保持し、inspection runtime freshness / validatorでcurrent assetとapproved hashを照合します。formal machine requestを扱っていないgeneral / scoped inspectionへこのkeyを無条件追加しません。formal Skillはこのsibling assetを直接読まず、returned inspection artifact / evidence refsに加えてinspection Machine Runtimeの `runtime_unit_key / generation_fingerprint` を受け取り、formal consumerの `metadata.upstream_runtime_units` からcurrentnessを検証します。inspection static data hashをformal `static_data_versions` へ複製しません。

## 3. finite machine probe inventory

### document / metadata

| machine probe key | 固定取得内容 |
| --- | --- |
| `mp-document-title` | document title raw value、存在、current document identity |
| `mp-document-language` | document elementのlanguage metadata |
| `mp-part-language-inventory` | current scope内のpart-level language metadata、target ref |
| `mp-purpose-metadata` | autocomplete、role、purpose関連のallowlisted programmatic metadata |

### structure / population

| machine probe key | 固定取得内容 |
| --- | --- |
| `mp-nontext-content-inventory` | image / icon / canvas / embedded non-text candidateのtarget ref、type、programmatic metadata |
| `mp-media-inventory` | audio / video / synchronized media candidate、track / caption / autoplay等のmachine-readable metadata |
| `mp-moving-updating-inventory` | moving / blinking / scrolling / auto-updating candidate、control state |
| `mp-timer-inventory` | time limit / timeout / countdown candidate、duration / notification state |
| `mp-shortcut-inventory` | single printable character shortcut candidate / declared shortcut metadata |
| `mp-form-control-inventory` | input control、label association、required / invalid / constraint / autocomplete metadata |
| `mp-heading-label-inventory` | heading / label candidate、level、association、rendered / accessibility text |
| `mp-link-inventory` | link target、rendered text、accessible name、programmatic context ref |
| `mp-structure-inventory` | heading / list / table / landmark / form relationshipの必要最小projection |
| `mp-sequence-inventory` | relevant DOM / accessibility orderのtarget sequence |
| `mp-component-semantics` | name / role / value / state / propertyの必要最小projection |
| `mp-status-candidate-inventory` | focus移動なしで表示されるstatus candidate、role / live / property |

### geometry / presentation

| machine probe key | 固定取得内容 |
| --- | --- |
| `mp-target-geometry` | target x / y / width / height CSS px |
| `mp-neighbor-geometry` | 周辺interactive target geometry / spacing計算用ref |
| `mp-focus-obscuring-geometry` | focused targetとauthor-created overlay / viewport geometry |
| `mp-computed-color-context` | foreground / background / border / outline等のallowlisted computed color値 |
| `mp-text-presentation-values` | line height / spacing / width / alignment等のmachine-readable presentation値 |
| `mp-focus-appearance-evidence` | focused / unfocused screenshot refs、target geometry、author-defined outline / border / background / box-shadow等のtechnology-defined値、user-agent-owned flag |
| `mp-viewport-state` | viewport / document scroll metrics |

`mp-focus-appearance-evidence` はscreenshotのpixel意味解析を行いません。CSS / SVG等のtechnology-defined colorとgeometryから一意に計算できる部分だけmachine計算へ渡し、複雑なshape、gradient、image background、anti-aliasing等はsemantic / manualへ残します。

### interaction

| machine probe key | 固定取得内容 |
| --- | --- |
| `mp-focus-sequence-run` | fixed keyboard navigationによるfocus sequence、visible state、before / after refs |
| `mp-keyboard-functionality-run` | 宣言済みfunctionality / flowのkeyboard-only trace、unreachable / trap evidence |
| `mp-pointer-interaction-run` | down / up / drag / path / alternative action trace |
| `mp-hover-focus-content-run` | hover / focus before / after、追加content visible / dismiss / persist state |
| `mp-change-trigger-run` | focus / input / request等のfixed trigger前後のURL / focus / rendered state |
| `mp-error-scenario-run` | declared error scenario後のinvalid target、error text、association、focus / state |
| `mp-orientation-run` | portrait / landscape環境とcontent / functionality evidence |
| `mp-reflow-run` | required viewport条件、overflow / clipping / geometry evidence |
| `mp-resize-text-run` | valid text scaling mechanism、baseline / intermediate / target state、mechanism scale、rendered text candidateのbaseline / current used font size、rendered scale ratio、overflow / clipping / obscuring / functionality evidence、mechanism capability / cleanup |
| `mp-text-spacing-run` | WCAG text spacing fixed override条件、clipping / overlap / scroll / functionality evidence |
| `mp-control-value-history` | flow内のcurrent / previous control value ref |
| `mp-multipage-signature` | selected page setのcontrol / help / navigation structure signature |
| `mp-audio-autoplay-run` | page load後の自動再生audio candidate、開始条件、継続時間 |

### Resize Text mechanism contract

`mp-resize-text-run` の `resize_mechanism` は次の有限enumだけを許可します。

- `user-agent-full-page-zoom`
- `user-agent-text-only-resize`
- `author-provided-resize-control`

mechanism candidateはcurrent browser / user agent capabilityと、current pageで確認できるauthor-provided controlからmaterializeします。LLM supplied arbitrary mechanism名を受け付けません。

- baselineでin-scope rendered text candidateごとのused font sizeとapplicable variation identityを取得する。caption / image-of-text等のnormative exception判定はsemanticへ残す
- user agentがfull-page zoomを提供しbrowser ownerが実際にそのUI / session mechanismを安全に操作できる場合、browserが提供する実際のzoom stateをbaselineから順に実行する
- user agentがtext-only resizeを提供しbrowser ownerが安全に操作できる場合、その実際のresize stateをbaselineから順に実行する
- author-provided resize controlはcurrent UI上のcontrol identityと作用が確認できる場合だけ実行する
- `user-agent-full-page-zoom` はbrowser ownerがdocumentedに取得したzoom scale ratioとcurrent / baseline computed font sizeから `rendered_scale_ratio = zoom_scale_ratio × current_font_size_css_px / baseline_font_size_css_px` をscript計算する
- `user-agent-text-only-resize` はbrowser ownerがdocumentedに取得できるtext scale / rendered font metricを正本にする。computed styleへscaleが反映されることを確認できる場合だけcurrent / baseline font size比を使い、scale factorとの二重計算をしない。機構のscaleをmachine-readableに確定できない場合はそのprobeを `unsupported` とする
- `author-provided-resize-control` はcurrent / baseline used font size比を正本とし、control操作が対象textへ作用した結果を取得する
- responsive breakpoint等でcomputed text sizeが変わることを許容し、mechanism control値が200%という理由だけでtarget到達としない。machine stageはcurrent mechanismが提供する有限state列をbaselineから順に取得し、全machine-observed text candidateが2.0xへ到達するか、documented / machine-readableなmechanism最大stateへ到達するまで記録する。semantic exception未確定を理由にstate列を途中でsuccess closureしない
- machine resultはtext candidateごとのrendered scale ratio、state別loss evidence、population completeness、mechanism state sequence completenessを返し、caption / image-of-text等のexceptionを自動判定しない
- semantic procedureがexception target refsを確定した後、scriptがrecorded state列から残るapplicable text集合の全targetが初めて2.0xへ到達するstateを導出する。incremental mechanismではbaselineからそのtarget stateまでに通過するstateのcontent / functionality loss evidenceをrequired coverageとする
- 1つのvalid mechanismでsemantic exception除外後の全applicable text candidateが2.0xへ到達し、そこまでのstateでcontent / functionality lossなしを確認できれば、そのmechanismをsatisfied candidateへできる。あるmechanismの失敗だけでSC全体をfailedへ固定せず、他のvalid mechanism / semantic evidenceのclosureを待つ
- executableなvalid mechanismをすべて確認してもapplicable textが2.0xへ到達できない、または到達前後でcontent / functionality lossがある場合だけnot-satisfied candidateへ進める。未確認mechanism / text population / exception closureが残る場合は `incomplete / blocked` とする
- Playwright `deviceScaleFactor` はDPR emulationでありtext scaling mechanismとして扱わない
- viewport resize、CSS `transform: scale()`、test専用font-size / zoom style注入を1.4.4のtext scaling mechanismとして扱わない
- browser / toolが存在するuser-agent mechanismを操作できない場合は `unsupported + text-scaling-mechanism-not-machine-executable`、mechanism state / scaleをmachine-readableに取得できない場合は `unavailable + text-scaling-state-not-machine-readable` とする。author-provided mechanismも含めmachine-executable candidateが残らない場合でも、このmachine limitationだけでcriterionをblockedへ短絡せず、formal側 `_05i` のconditional manual fallbackをapplicable化する。manual fallbackも閉じられない場合だけcriterionを `blocked / undetermined` とする。擬似的なstyle変更へfallbackしない

W3C Technique G142等の評価で必要なuser-agent zoomは、current browser経路が実際のuser-agent zoom capabilityとscale stateを安全に提供する場合だけfixed dispatchへ登録します。responsive breakpointによりCSS font sizeが変わるcaseでもbaseline比2.0x enlargementを確認し、特定browserのprivate protocolやundocumented shortcutをgeneric fallbackとして追加しません。

Text Spacing等、W3Cの評価手順自体がauthor style overrideを要求するprocedureだけ、Techniqueで定義された固定overrideをdispatchします。Resize Textは上記valid text scaling mechanism contractを使用し、style overrideで代替しません。固定overrideを使うprocedureでも任意style injection interfaceにはせず、元状態、適用したoverride、cleanup結果を保持します。

## 4. machine procedure → probe mapping

次を `wcag-evaluation-procedure-catalog.json` の正本mappingとし、実装時に増減しません。

| machine procedure | required machine probe keys |
| --- | --- |
| `m-accessible-name` | `mp-nontext-content-inventory`, `mp-component-semantics` |
| `m-audio-autoplay` | `mp-media-inventory`, `mp-audio-autoplay-run` |
| `m-change-trigger-run` | `mp-change-trigger-run` |
| `m-control-value-compare` | `mp-control-value-history` |
| `m-dom-sequence` | `mp-sequence-inventory` |
| `m-error-state` | `mp-form-control-inventory`, `mp-error-scenario-run` |
| `m-focus-appearance` | `mp-focus-appearance-evidence`, `mp-target-geometry`, `mp-computed-color-context` |
| `m-focus-obscured` | `mp-focus-obscuring-geometry` |
| `m-focus-order` | `mp-focus-sequence-run` |
| `m-form-labels` | `mp-form-control-inventory` |
| `m-form-purpose-metadata` | `mp-form-control-inventory`, `mp-purpose-metadata` |
| `m-heading-label-inventory` | `mp-heading-label-inventory` |
| `m-hover-focus-content` | `mp-hover-focus-content-run` |
| `m-image-text-inventory` | `mp-nontext-content-inventory` |
| `m-keyboard-run` | `mp-keyboard-functionality-run`, `mp-focus-sequence-run` |
| `m-label-name` | `mp-form-control-inventory`, `mp-component-semantics` |
| `m-language-page` | `mp-document-language` |
| `m-language-parts` | `mp-part-language-inventory` |
| `m-link-inventory` | `mp-link-inventory` |
| `m-media-inventory` | `mp-media-inventory` |
| `m-moving-content-inventory` | `mp-moving-updating-inventory` |
| `m-multipage-controls` | `mp-multipage-signature` |
| `m-multipage-help` | `mp-multipage-signature` |
| `m-multipage-structure` | `mp-multipage-signature` |
| `m-name-role-value` | `mp-component-semantics` |
| `m-nontext-contrast` | `mp-target-geometry`, `mp-computed-color-context` |
| `m-nontext-inventory` | `mp-nontext-content-inventory` |
| `m-orientation-run` | `mp-orientation-run` |
| `m-page-title` | `mp-document-title` |
| `m-parsing-version-rule` | なし。target WCAG version / content technology metadataだけで実行 |
| `m-pointer-run` | `mp-pointer-interaction-run` |
| `m-reflow` | `mp-reflow-run`, `mp-viewport-state` |
| `m-resize-text` | `mp-resize-text-run` |
| `m-shortcut-inventory` | `mp-shortcut-inventory` |
| `m-status-semantics` | `mp-status-candidate-inventory`, `mp-component-semantics` |
| `m-structure-snapshot` | `mp-structure-inventory` |
| `m-target-size` | `mp-target-geometry`, `mp-neighbor-geometry` |
| `m-text-contrast` | `mp-computed-color-context` |
| `m-text-presentation` | `mp-text-presentation-values`, `mp-computed-color-context` |
| `m-text-spacing` | `mp-text-spacing-run` |
| `m-timer-inventory` | `mp-timer-inventory` |
| `m-ui-purpose-metadata` | `mp-purpose-metadata`, `mp-component-semantics` |

`m-parsing-version-rule` はbrowser observationを要求しません。content technology metadataはformal exploration / sample metadataを正本にします。

## 5. identity / status

formal Skillがmaterializeするmachine probe requestは対象に応じて `target_ref`、`population_ref + population_revision + identity_fingerprint`、`sample_ref + variation_ref + current document identity`、process / action refのいずれかを持ちます。LLM supplied selectorを受けません。inspection側はこのidentity inputをlocal target registry / current browser stateへ解決し、requestに存在しないprocedure意味を補完しません。

result statusは `ok / unsupported / unavailable / incomplete / blocked` です。`unsupported` はcurrent browser / tool capabilityがrequired operationを提供しない場合だけに使い、既知標準の未実装を隠す用途には使いません。

manual fallback activationへ使う `limitation_code` は次の有限値だけを許可します。

- `background-not-machine-resolvable`: gradient / image background / blend / anti-aliasing等によりrequired contrast値をmachineで一意に閉じられない
- `focus-indicator-not-machine-resolvable`: focus indicatorのshape / area / visual stateをCSS / SVG等のmachine-readable値だけで一意に閉じられない
- `text-scaling-mechanism-not-machine-executable`: valid text scaling mechanismは候補として存在するがcurrent browser ownerが安全に操作できない
- `text-scaling-state-not-machine-readable`: valid mechanismを操作できてもscale / rendered stateをmachine-readableに確定できない

上記codeは `_05i` に明示したconditional manual fallbackだけを起動します。probe resultやmachine procedureがこのcodeからcriterion resultを直接決定しません。fixed probeを契約どおり完了してlimitationを正しく取得した場合、formal側source machine procedureは `_05h` に従い `complete + limitation_code` として閉じます。browser action未開始、request不正、cleanup未完了等のblockedとは混同しません。

- `m-text-contrast / m-nontext-contrast` はcomputed color contextから一意にcontrastを算出できない場合、statusを `unavailable`、limitation codeを `background-not-machine-resolvable` とする
- `m-focus-appearance` はsimple machine pathで閉じないcomplex shape / gradient / image background / anti-aliasing等の場合、statusを `incomplete`、limitation codeを `focus-indicator-not-machine-resolvable` とする
- `m-resize-text` は上記Resize Text contractの2 codeだけを使う
- unknown limitation code、自然言語だけのfallback理由、LLM supplied limitation codeをrejectする

## 6. sensitive data

- full DOM / full accessibility treeを保存しない
- input valueはcriterion上必要なtargetだけに限定する
- password / token / cookie / storageState / secretを保存しない
- screenshotはPR #12 evidence safety契約を再利用する
- DOM / media metadataに個人情報が含まれる場合は必要最小fieldだけを保持する

## 7. deterministic validator / fixture

validatorを2層に分けます。

- formal Skill validator: `_05i` のmachine procedure全件、procedure catalog内のrequired machine probe key、typed request schema、duplicateを検証する。`m-parsing-version-rule` だけbrowser probe 0件を許可する
- usability-inspection validator: local machine probe catalog、request / result schema、fixed dispatch、target / population currentness、duplicate、status / limitation code整合、unsupported理由、`static_data_versions.wcag_machine_probes` を検証する
- repository-level contract test: formal procedure catalogが参照するmachine probe key集合とinspectionのmachine probe catalog key集合を比較し、missing / extra / unusedを0件にする

fixtureにはdocument metadata、non-text / media / link / heading / form / structure population、keyboard / focus / pointer / hover-focus、error scenario、target size / spacing、text / non-text contrast、simple / complex focus appearance、responsive condition、orientation / reflow / text spacing、moving / timer / shortcut、multipage signature、stale population、missing capabilityを含めます。gradient / image / blend背景のcontrast unavailable、complex focus indicator limitation codeとmanual fallback activationも含めます。Resize Textはfull-page zoom、text-only resize、author-provided control、incremental step、responsive breakpointでzoom control値とrendered text scaleが一致しないcase、2.0x到達、text population incomplete、valid mechanism実行不能、`deviceScaleFactor` / viewport / CSS injection rejectを個別fixtureで持ちます。

## 8. 完了条件

- `_05i` の全machine procedureにformal procedure catalog上の固定probe mappingがある
- formal Skillがtyped `wcag-machine-probe` requestをmaterializeし、inspection側がprocedure catalogを再読込しない
- machine probe catalogの全keyにfixed dispatch / request / result schemaがある
- fallback対象machine limitationは有限 `limitation_code` へ正規化され、unknown codeを許可しない
- formal machine probeを処理したinspection runtimeではmachine probe catalogのcanonical hashを `static_data_versions.wcag_machine_probes` へ固定し、変更時はreturned inspection runtime evidenceのfingerprint変化としてformal評価へ伝播する。formal machine probe未使用のinspection runtimeへは含めない
- repository-level contract testでformal required probe keyとinspection catalog keyのmissing / extra / unusedが0件
- LLMがmachine probe集合を入力しない
- browser ownerがmaterialize済みrequestだけを実行する
- machine化できる列挙・値取得・固定操作・数値計算をsemanticへ逃がさない
- visual meaning / exception / equivalenceをmachineへ押し込まない
- generic browser DSL / arbitrary JavaScript interfaceを作らない
- deterministic validator / fixtureが全mappingを閉じる

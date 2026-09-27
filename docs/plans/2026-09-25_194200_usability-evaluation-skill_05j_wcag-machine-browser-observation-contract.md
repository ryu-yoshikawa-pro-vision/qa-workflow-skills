# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` のmachine procedureがbrowserから必要とする固定観測を、`usability-inspection` が実行できる有限contractとして定義します。

`_05g_usability-inspection-browser-observation-contract.md` の16 canonical observation fieldはsemantic layerが追加evidenceを必要とした場合に選択できるinterfaceです。本ファイルのmachine probeは別用途です。

- required machine probe keyは `wcag_criterion_plan.py` がprocedure catalogから導出する
- LLMはmachine probe keyを選択・省略・追加しない
- browser ownerはmaterialize済みrequestだけを実行する
- machine probe resultから意味判断を行わない
- fixed probeで閉じない意味・例外・visual interpretationはsemantic / manual procedureへ残す
- 任意JavaScript、任意selector、generic rule DSL、plugin registryは追加しない

## 1. package

`skills/usability-inspection/` へ次を追加します。

```text
scripts/
└── wcag_machine_observation.py
assets/
└── wcag-machine-probe-catalog.json
```

`wcag_machine_observation.py` はbrowserを直接起動しません。procedure key → required machine probe key集合、fixed request payload、result schema / enum / unit / currentness、target / population ref、duplicate request / resultを検証し、machine-owned resultをmaterializeします。実browser操作はcurrent `usability-inspection` browser ownerが行います。

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

## 3. finite machine probe inventory

### document / metadata

| machine probe key | 固定取得内容 |
| --- | --- |
| `mp-document-title` | document title raw value、存在、current document identity |
| `mp-document-language` | document elementのlanguage metadata |
| `mp-part-language-inventory` | current scope内のpart-level language metadata、target ref |
| `mp-document-location` | safe current URL / limitation |
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
| `mp-responsive-condition-inventory` | `_05g` のresponsive condition / numeric transition result |
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
| `mp-resize-text-run` | required text resize条件、overflow / clipping / functionality evidence |
| `mp-text-spacing-run` | WCAG text spacing fixed override条件、clipping / overlap / scroll / functionality evidence |
| `mp-control-value-history` | flow内のcurrent / previous control value ref |
| `mp-multipage-signature` | selected page setのcontrol / help / navigation structure signature |
| `mp-audio-autoplay-run` | page load後の自動再生audio candidate、開始条件、継続時間 |

text resize / text spacing等で評価用stateを作る場合は、WCAG Techniqueで定義された固定overrideだけをdispatchします。任意style injection interfaceにはせず、元状態、適用したoverride、cleanup結果を保持します。

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

machine probe requestは対象に応じて `target_ref`、`population_ref + population_revision + identity_fingerprint`、`sample_ref + variation_ref + current document identity`、process / action refのいずれかを持ちます。LLM supplied selectorを受けません。

result statusは `ok / unsupported / unavailable / incomplete / blocked` です。`unsupported` はcurrent browser / tool capabilityがrequired operationを提供しない場合だけに使い、既知標準の未実装を隠す用途には使いません。

## 6. sensitive data

- full DOM / full accessibility treeを保存しない
- input valueはcriterion上必要なtargetだけに限定する
- password / token / cookie / storageState / secretを保存しない
- screenshotはPR #12 evidence safety契約を再利用する
- DOM / media metadataに個人情報が含まれる場合は必要最小fieldだけを保持する

## 7. deterministic validator / fixture

validatorは `_05i` のmachine procedure全件、required machine probe mapping、probe catalog存在、request / result schema、target / population currentness、duplicate、unsupported理由を独立確認します。`m-parsing-version-rule` だけbrowser probe 0件を許可します。

fixtureにはdocument metadata、non-text / media / link / heading / form / structure population、keyboard / focus / pointer / hover-focus、error scenario、target size / spacing、text / non-text contrast、simple / complex focus appearance、responsive condition、orientation / reflow / resize text / text spacing、moving / timer / shortcut、multipage signature、stale population、missing capabilityを含めます。

## 8. 完了条件

- `_05i` の全machine procedureに固定probe mappingがある
- machine probe catalogの全keyにfixed dispatch / request / result schemaがある
- LLMがmachine probe集合を入力しない
- browser ownerがmaterialize済みrequestだけを実行する
- machine化できる列挙・値取得・固定操作・数値計算をsemanticへ逃がさない
- visual meaning / exception / equivalenceをmachineへ押し込まない
- generic browser DSL / arbitrary JavaScript interfaceを作らない
- deterministic validator / fixtureが全mappingを閉じる

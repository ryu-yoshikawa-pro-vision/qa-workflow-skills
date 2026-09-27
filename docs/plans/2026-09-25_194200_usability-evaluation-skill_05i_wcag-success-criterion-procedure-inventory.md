# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `wcag-conformance-evaluation` の全Success Criterion procedure inventoryを固定します。

`_05h_wcag-criterion-evaluation-contract.md` がcriterion evaluation runtimeの正本、本ファイルが `criterion_ref → procedure_keys` の正本です。実装時に各Success Criterionのprocedure構成を再設計しません。

対象はWCAG 2.0 / 2.1 / 2.2です。version別required Success Criterion集合はversioned requirements assetを正本とします。WCAG 2.2では4.1.1を含めません。

## 1. version別Success Criterion集合

WCAG 2.0の61件は次です。

- 1.1.1
- 1.2.1–1.2.9
- 1.3.1–1.3.3
- 1.4.1–1.4.9
- 2.1.1–2.1.3
- 2.2.1–2.2.5
- 2.3.1–2.3.2
- 2.4.1–2.4.10
- 3.1.1–3.1.6
- 3.2.1–3.2.5
- 3.3.1–3.3.6
- 4.1.1–4.1.2

WCAG 2.1はWCAG 2.0へ次の17件を追加した78件です。

- 1.3.4, 1.3.5, 1.3.6
- 1.4.10, 1.4.11, 1.4.12, 1.4.13
- 2.1.4
- 2.2.6
- 2.3.3
- 2.5.1, 2.5.2, 2.5.3, 2.5.4, 2.5.5, 2.5.6
- 4.1.3

WCAG 2.2はWCAG 2.1から4.1.1を除外し、次の9件を追加した86件です。

- 2.4.11, 2.4.12, 2.4.13
- 2.5.7, 2.5.8
- 3.2.6
- 3.3.7, 3.3.8, 3.3.9

validatorはこの集合とrequirements assetのcriterion集合をversion別に比較し、missing / extraを0件にします。

## 2. procedure key生成規則

selected versionの全required Success Criterionへ、必ず1件のcriterion-specific semantic procedure `s-wcag-<criterion-ref>` を割り当てます。例: 2.4.2なら `s-wcag-2.4.2` です。

`s-wcag-*` は共通schemaを使いますが、入力するnormative requirement / definitions / exceptionは各criterion refに固定します。LLMが別criterionの要求へ置き換えたり、criterionを省略したりしません。

共通semantic procedure Input:

- criterion ref / target WCAG version / level
- normative requirement source item refs / definition refs
- sample / presentation variation / process refs
- sibling machine / manual / AT / external procedure execution refs
- current evidence refs
- accessibility support baseline

共通semantic procedure Output:

- applicability: `applicable / not-applicable / unknown`
- exception decision / exception refs
- semantic decision: `satisfied / not-satisfied / undetermined`
- judgment reason
- evidence refs
- uncertainty / limitation
- additional observation draft（必要な場合）

このsemantic procedureはmachine値を再計算しません。数値、集合、固定enum、browser field取得、machine比較は後述のmachine procedureへ移します。

## 3. machine procedure割当

下表のmachine procedureを、該当Success Criterionの `procedure_keys` へ追加します。表にないmachine keyを実装時判断で追加しません。

| procedure key | 対象SC | 固定処理 |
|---|---|---|
| `m-accessible-name` | 1.1.1 | targetのaccessible name / role / relevant label sourceをfixed browser observationから取得する。 |
| `m-audio-autoplay` | 1.4.2 | page load後の自動再生audio candidate、開始条件、継続時間を取得する。 |
| `m-change-trigger-run` | 3.2.1, 3.2.2, 3.2.5 | focus / input / request等のfixed trigger前後でURL、focus、rendered state等のcontext change evidenceを取得する。 |
| `m-control-value-compare` | 3.3.7 | flow内の既取得control valueをcanonical valueとして比較し、同値 / 差分だけを返す。 |
| `m-dom-sequence` | 1.3.2 | relevant content sequence / DOM order / accessibility orderのmachine-readable sequence refを生成する。 |
| `m-error-state` | 3.3.1, 3.3.3 | declared input error scenario後のinvalid target、error text、association、focus / stateを取得する。 |
| `m-focus-appearance` | 2.4.13 | focus indicatorのbefore / after pixel・geometry・contrastのmachine計測可能部分を取得・計算する。 |
| `m-focus-obscured` | 2.4.11, 2.4.12 | focused target geometryとauthor-created overlay / viewport geometryを取得し、obscured areaを計算する。 |
| `m-focus-order` | 2.4.3, 2.4.7 | keyboard navigationでfocus target sequence、visible state、before / after refsを取得する。 |
| `m-form-labels` | 3.3.2 | user input controlとlabel / instruction association、required / constraint metadataを取得する。 |
| `m-form-purpose-metadata` | 1.3.5 | 対象inputのautocomplete等、input purposeを示すprogrammatic metadataを取得する。 |
| `m-heading-label-inventory` | 2.4.6, 2.4.10 | heading / label candidate、level / association、rendered / accessibility textを列挙する。 |
| `m-hover-focus-content` | 1.4.13 | hover / focusのbefore / after stateを固定操作で取得し、追加contentのvisible / dismiss / persist stateを返す。 |
| `m-image-text-inventory` | 1.4.5, 1.4.9 | textを含むimage candidateを列挙し、target / evidence refを返す。画像内textの意味判定はsemantic / manual。 |
| `m-keyboard-run` | 2.1.1, 2.1.2, 2.1.3 | 宣言済みfunctionality / flowをkeyboard-onlyで実行し、focus / action trace、unreachable / trap evidenceを返す。 |
| `m-label-name` | 2.5.3 | visible label textとaccessible nameをtarget単位で取得し、normalized containment比較用valueを返す。 |
| `m-language-page` | 3.1.1 | page default human language metadataを取得する。 |
| `m-language-parts` | 3.1.2 | part-level language metadataとtarget refを取得する。 |
| `m-link-inventory` | 2.4.4, 2.4.9 | link target ref、rendered text、accessible name、programmatic context refを列挙する。 |
| `m-media-inventory` | 1.2.1–1.2.9, 1.4.7 | audio / video / synchronized media candidateを列挙し、media kind、track / caption metadata、autoplay等のmachine-readable metadataを返す。 |
| `m-moving-content-inventory` | 2.2.2 | moving / blinking / scrolling / auto-updating content candidateとcontrol stateを列挙する。 |
| `m-multipage-controls` | 3.2.4 | selected page setで同一functionality candidateのname / role / label等のsignatureを生成する。 |
| `m-multipage-help` | 3.2.6 | selected page setでhelp mechanism candidateとrelative order signatureを生成する。 |
| `m-multipage-structure` | 3.2.3 | selected page setでnavigation structure / orderのmachine-readable signatureを生成する。 |
| `m-name-role-value` | 4.1.2 | UI componentのname / role / value / state / propertyと変更後のmachine-readable exposureを取得する。 |
| `m-nontext-contrast` | 1.4.11 | UI component / state indicator / graphical objectの対象領域についてcontrast計算可能な色を取得しratioを計算する。 |
| `m-nontext-inventory` | 1.1.1 | current scopeの非テキストcontent candidateをmachine-readable sourceから列挙し、target refとtypeを返す。 |
| `m-orientation-run` | 1.3.4 | portrait / landscapeの2条件をfixed viewportで実行し、content / functionality loss evidenceを取得する。 |
| `m-page-title` | 2.4.2 | document titleの存在とnormalized valueを取得する。 |
| `m-parsing-version-rule` | 4.1.1 | target WCAG versionとcontent technologyから4.1.1のapplicability / version ruleを決定論的に導出する。 |
| `m-pointer-run` | 2.5.1, 2.5.2, 2.5.7 | 宣言済みpointer interactionをfixed browser actionで実行し、down / up / drag / path / alternative action traceを返す。 |
| `m-reflow` | 1.4.10 | required viewport条件を実行し、horizontal / vertical overflow、clipping、target geometryを取得する。 |
| `m-resize-text` | 1.4.4 | browser zoomとは分離したrequired text resize条件を適用し、overflow / clipping / functionality evidenceを取得する。 |
| `m-shortcut-inventory` | 2.1.4 | single printable character shortcut candidateをmachine-readable metadataまたはdeclared inventoryから列挙する。 |
| `m-status-semantics` | 4.1.3 | focusを移さず表示されるstatus candidateとrole / live / property等のaccessibility semanticsを取得する。 |
| `m-structure-snapshot` | 1.3.1, 2.4.1 | heading / list / table / landmark / form relationship等のprogrammatic structureを必要fieldだけ取得する。 |
| `m-target-size` | 2.5.5, 2.5.8 | target bounding boxと隣接target spacingを取得し、CSS px size / spacingを計算する。 |
| `m-text-contrast` | 1.4.3, 1.4.6 | text foreground / backgroundを取得し、解決可能な背景についてcontrast ratioを計算する。 |
| `m-text-presentation` | 1.4.8 | foreground / background selection、line width、alignment、line / paragraph spacing、text resize等のmachine-observable presentation値を取得する。 |
| `m-text-spacing` | 1.4.12 | WCAG text spacing overrideをfixed値で適用し、clipping / overlap / scroll / functionality evidenceを取得する。 |
| `m-timer-inventory` | 2.2.1, 2.2.3, 2.2.6 | UIに現れるtime limit / timeout / countdown candidateとcurrent machine-readable duration / notification stateを取得する。 |
| `m-ui-purpose-metadata` | 1.3.6 | UI component / icon / regionのprogrammatic purpose関連metadataを取得する。 |

machine procedureが必要とするbrowser値は `_05g_usability-inspection-browser-observation-contract.md` のcanonical observation fieldだけを使います。machine keyごとのfield mappingは `wcag-evaluation-procedure-catalog.json` に固定し、LLMがprocedureごとに手で列挙しません。

## 4. manual / assistive technology / external evidence割当

次のprocedure keyを該当criterionへ追加します。

### manual

- 1.2.1–1.2.9 → 各 `manual-wcag-<SC>`
- 1.4.7 → `manual-wcag-1.4.7`
- 2.3.1 → `manual-wcag-2.3.1`
- 2.3.2 → `manual-wcag-2.3.2`
- 2.5.6 → `manual-wcag-2.5.6`
- 3.3.8 → `manual-wcag-3.3.8`
- 3.3.9 → `manual-wcag-3.3.9`

### assistive technology

- 1.3.1 → `at-wcag-1.3.1`
- 1.3.2 → `at-wcag-1.3.2`
- 4.1.2 → `at-wcag-4.1.2`
- 4.1.3 → `at-wcag-4.1.3`

AT procedureはSuccess Criterion固定で常に実行するという意味ではありません。`_05h` の契約どおり、selected technology / content / accessibility support baselineから実行applicabilityを閉じ、requiredなのに環境がない場合は `blocked` とします。

### external evidence

- 2.3.1 → `external-wcag-2.3.1`
- 2.3.2 → `external-wcag-2.3.2`
- 3.1.5 → `external-wcag-3.1.5`

manual / AT / external procedureはrequired evidence kind、result contract、不足時statusをcatalogで固定し、証拠をLLM推測で補いません。

## 5. criterion別procedure_keysの決定方法

各criterionの最終 `procedure_keys` は次の集合演算だけで生成します。

1. `s-wcag-<criterion-ref>` を必ず追加
2. §3のmachine tableでcriterionに一致するmachine keyをすべて追加
3. §4のmanual / AT / external mappingでcriterionに一致するkeyをすべて追加
4. canonical sortして保存

この4段階以外でprocedure keyを増減しません。requirements assetにhand-authoredな別procedure集合を持たせず、本inventoryから生成したexpected集合との一致をvalidatorで確認します。

## 6. criterion-specific semantic contract

`s-wcag-*` はgenericな自然言語rule engineではありません。criterion refごとにversioned requirements assetのnormative requirement / definitions / exceptionsをInputへ固定し、共通Output schemaで意味判断します。

semantic layerへ残すもの:

- applicability / exception
- purpose / meaning / equivalence
- sequenceやrelationshipの意味
- user-facing instruction / feedbackの意味
- machine evidenceをcriterion全体へ適用できるか
- manual / AT / external evidenceを含めた最終semantic closure

scriptへ残すもの:

- required criterion集合 / procedure key集合
- population / target inventoryで機械的に閉じられる部分
- browser値取得
- 数値計算 / fixed comparison
- execution status / missing evidence集合
- final row / count / summary / cross-reference

criterion固有の判断で追加evidenceが必要なら `_05g` のcanonical observation fieldを選んだadditional observation draftを返せます。procedure集合自体は変更しません。

## 7. implementation contract

実装では次を同時に満たします。

1. `wcag-2.0-requirements.json` / `wcag-2.1-requirements.json` / `wcag-2.2-requirements.json` の各SCへ本inventoryから導出した `procedure_keys` を設定する
2. 本inventoryに現れる全procedure keyを `wcag-evaluation-procedure-catalog.json` へ登録する
3. `m-` keyは全件 `machine_dispatch_key` とproduction implementation / fixtureを持つ
4. `s-wcag-*` はcriterion ref、normative source refs、共通semantic schemaを持つ
5. `manual-* / at-* / external-*` はrequired evidence kindと不足時statusを固定する
6. requirements assetのprocedure key集合と本inventoryのexpected集合をcontract testで比較する
7. procedure catalogのcanonical hashを `static_data_versions.wcag_evaluation_procedures` へ保持する

## 8. deterministic / semantic eval

deterministic eval:

- 2.0=61 / 2.1=78 / 2.2=86件
- 2.2に4.1.1が存在しない
- 全required SCに `s-wcag-<SC>` が1件ある
- §3 / §4 mappingから導出したexpected procedure集合とrequirements assetが一致
- inventoryにないprocedure key / catalogにないprocedure key / unused catalog keyをreject
- machine procedure dispatch欠落をreject
- machine化可能な値をsemantic resultとして自己申告してもfinal resultへ採用しない

semantic eval:

- machine evidenceとsemantic judgmentを分離できる
- criterionごとのapplicability / exception / purpose / equivalenceを判断できる
- required manual / AT / external evidenceを推測で埋めない
- additional observationが必要な場合にcanonical observation fieldを選び、procedure集合は変更しない
- WCAG criterion外の複合的なusability concernを別routingできる

## 9. 完了条件

- WCAG 2.0 / 2.1 / 2.2の全required Success Criterionが本inventoryからprocedure集合へ一意に解決する
- 実装者がcriterionごとのprocedure構成を実装時に決める余地がない
- machine procedureは全件scriptへ移り、semantic layerは意味判断に集中する
- semantic / manual / AT / external procedureの不足evidenceを推測で補わない
- requirements asset / procedure catalog / validator / semantic eval / canonical E2Eが同じinventoryを参照する

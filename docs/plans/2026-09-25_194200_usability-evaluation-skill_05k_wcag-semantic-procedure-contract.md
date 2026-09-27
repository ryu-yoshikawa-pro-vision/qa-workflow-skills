# UI/UX評価・ユーザビリティ検査Skill追加Plan

## 0. 本ファイルの対象

本ファイルは `s-wcag-<criterion-ref>` のcriterion固有semantic契約を固定します。目的は、実装時またはruntime時にLLMが「このSuccess Criterionで何を意味判断するか」を再設計しないようにすることです。

一方、LLMがevidence間の関係、目的、意味、equivalence、例外の成立、判断理由、uncertaintyを柔軟に評価する責務は維持します。semantic contractは自然言語rule engineや回答テンプレートではありません。

## 1. 正本とasset

`skills/wcag-conformance-evaluation/assets/wcag-semantic-contracts.json` を追加します。

supported target versionごとに、そのversionに存在する全Success Criterionへ1件のcontract rowを持ちます。

- WCAG 2.0: 61 rows
- WCAG 2.1: 78 rows
- WCAG 2.2: 86 rows。4.1.1 rowは存在しない

同じcriterion refでもversionごとに別rowとします。normative wording、definition、exception、conformance noteの差を別versionへ暗黙継承しません。

## 2. contract row

各rowは次を持ちます。

- `semantic_contract_key`: `s-wcag-<criterion-ref>@<version>`
- `criterion_ref`
- `target_wcag_version`
- `level`
- `normative_source_item_refs`
- `normative_clause_refs`
- `definition_refs`
- `exception_refs`
- `semantic_evaluation_points`
- `required_evidence_roles`
- `allowed_additional_observation_fields`
- `forbidden_shortcuts`
- `missing_evidence_behavior`
- `procedure_applicability_contracts[]`。該当criterionに`applicability_mode=semantic` procedureがある場合だけ非空

`normative_clause_refs` はSuccess Criterion本文の意味上独立した要求、例外、conditionへ一意に戻れるsource item locatorです。単にSuccess Criterion全体のURLだけを持って「実装時に本文を読んで分解する」構造にしません。

`semantic_evaluation_points` は次のfieldだけを持つ有限rowです。

- `point_key`
- `source_clause_refs`
- `decision_kind`: `applicability / exception / purpose / meaning / equivalence / relationship / sequence / instruction-feedback / accessibility-support / other-normative-semantic`
- `required_evidence_roles`
- `completion_required`: boolean

`other-normative-semantic` は自由なcatch-allではありません。W3C本文上の意味判断が上記kindへ自然に分類できない場合だけ使用し、`source_clause_refs` を必須にします。実装時にsource clauseなしで独自観点を追加しません。

`procedure_applicability_contracts[]` は次のfieldだけを持ちます。

- `procedure_key`
- `decision_key`
- `source_clause_refs`
- `required_evidence_roles`
- `allowed_additional_observation_fields`
- `missing_evidence_behavior`

PR #14では `_05i` の4 AT procedureだけがこのrowを持ち、decision keyも `_05i` の固定値と一致させます。required evidence roleは `population-completeness / machine-procedure-result / current-browser-observation / presentation-variation / accessibility-support-baseline / technology-context / authority-context` の部分集合だけを許可します。`assistive-technology-result`、`manual-procedure-result`、`external-evidence-result`、final `s-wcag-*` semantic resultはAT applicability decisionのInputにしません。

applicability decision Outputは `procedure_key / applicability(applicable|not-applicable|unknown) / reason / evidence_refs / uncertainty` だけです。criterion result、procedure result、final semantic decisionをここで生成しません。

## 3. required evidence role

evidence roleはprocedure catalogから決定論的に導出できるものを優先し、semantic contractがsibling procedureを省略する経路を作りません。

許可role:

- `population-completeness`
- `machine-procedure-result`
- `manual-procedure-result`
- `assistive-technology-result`
- `external-evidence-result`
- `current-browser-observation`
- `visual-evidence`
- `process-context`
- `presentation-variation`
- `accessibility-support-baseline`
- `technology-context`
- `authority-context`

`wcag_criterion_plan.py` はAT等のsemantic applicability decisionを先に閉じた後、current applicable procedure keysとsemantic contractを突合し、final `s-wcag-*` evaluationでrequiredなprocedure result roleをmaterializeします。`not-applicable` procedureのresult roleは要求せず、applicability basis refだけを保持します。LLMがrequired evidence role集合を完成集合として入力しません。

## 4. semantic procedure Input / Output

Input:

- semantic contract row
- sample / variation / process refs
- current population result
- current applicableかつclosure済みのsibling machine / manual / AT / external procedure result refs
- not-applicable sibling procedureのapplicability basis refs
- current evidence refs
- accessibility support baseline
- technology context
- project Authority / Step 1.4 additional requirement refs（applicableな場合）

Output:

- `applicability`: `applicable / not-applicable / unknown`
- `evaluation_point_decisions[]`: point key、`satisfied / not-satisfied / undetermined / not-applicable`、reason、evidence refs
- exception decision / source clause refs
- overall semantic decision: `satisfied / not-satisfied / undetermined`
- judgment reason
- evidence refs
- uncertainty / limitation
- additional observation draft（必要な場合）

scriptはoverall decision本文を生成しません。validatorはrequired point coverage、enum、source / evidence refs、procedure closureとの整合だけを検証します。

AT procedureを持つcriterionでは、`procedure_applicability_contracts[]` のdecisionをfinal semantic evaluationより前に実行します。final semantic evaluationはAT applicability `unknown` のまま開始せず、ATが `applicable` ならAT result closure後、`not-applicable` ならそのbasis確認後に開始します。final semantic evaluationのInputをAT applicability decisionのInputへ戻さないため、循環依存を作りません。

## 5. LLMへ残す判断

LLMは次を判断できます。

- criterionがcurrent contentへ意味的に適用されるか
- normative exceptionが現在のevidenceで成立するか
- text / image / control / relationship / sequence / feedback等のpurposeや意味
- alternativeが同等の情報・機能・結果を提供するか
- machine / manual / AT evidenceをcriterion全体へどう適用するか
- conflicting evidenceや不確実性
- fixed evidenceだけで閉じない場合に追加観測が必要か

LLMは次を変更しません。

- required criterion集合
- procedure key集合
- semantic evaluation point集合
- required machine probe集合
- source clause
- required evidence role
- completion status / summary count

## 6. 追加観測

追加観測が必要な場合、semantic procedureは `_05g` の16 canonical observation fieldとfixed predicateから表現できるdraftだけを返します。

- existing fieldで取得可能 → observation requestへmaterialize
- same request identity + same evidence fingerprint → `no-progress`
- fixed observation contractで表現不能 → ad hoc probeを作らず `undetermined / blocked`

追加観測によってcriterion / procedure / semantic evaluation point集合を増減しません。取得したnew evidenceで同じsemantic procedureを再評価します。

## 7. 4.1.1特別契約

WCAG 2.2には4.1.1 rowを作りません。

WCAG 2.0 / 2.1では `m-parsing-version-rule` を先に実行します。

- content technologyがHTMLまたはXML → W3C current conformance noteに従い `always-satisfied-html-xml`。`s-wcag-4.1.1` のsemantic実行を不要としてscriptがclosureする
- HTML / XML以外 → `evaluate-normative-rule`。versioned `s-wcag-4.1.1` contractを通常実行する
- technology不明 → shortcutせず `undetermined / blocked`

project独自のHTML validity / parsing quality gateが存在しても、WCAG 4.1.1 conformance resultとは別Authority / requirementとして扱います。

## 7.1 criterion-specific semantic inventory

次の87 unique Success CriterionをPlan上のsemantic inventoryとして固定します。実装時はこのrowをsupported versionへ展開し、`normative_source_item_refs / clause refs / definition refs / exception refs` だけを各versionのW3C正本へbindingします。semantic focus自体を実装者が再設計しません。

`required_evidence_roles` は本表のsemantic focusに加え、`_05i` procedure keysと `_05j` machine probe mappingからscriptが導出するsibling evidenceを必ず含みます。本表にmachine値の再計算指示は含めません。

| SC | version | semantic focus / special evidence guard |
| --- | --- | --- |
| 1.1.1 | 2.0 / 2.1 / 2.2 | non-text contentのpurpose / meaningとtext alternativeのequivalence、normative exception。machine population / accessible-name evidenceだけで意味の同等性を確定しない |
| 1.2.1 | 2.0 / 2.1 / 2.2 | prerecorded audio-only / video-onlyのmedia kind、equivalent alternative、normative exception。manual media evidence必須 |
| 1.2.2 | 2.0 / 2.1 / 2.2 | prerecorded synchronized mediaのcaptionがspoken / non-speech informationを同等に伝えるか。manual media evidence必須 |
| 1.2.3 | 2.0 / 2.1 / 2.2 | prerecorded synchronized mediaのaudio descriptionまたはmedia alternativeがvisual informationを同等に伝えるか |
| 1.2.4 | 2.0 / 2.1 / 2.2 | live synchronized mediaのcaption coverage / equivalence。manual evidence必須 |
| 1.2.5 | 2.0 / 2.1 / 2.2 | prerecorded synchronized mediaのaudio descriptionが必要visual informationを伝えるか |
| 1.2.6 | 2.0 / 2.1 / 2.2 | prerecorded audio contentのsign language interpretation coverage / equivalence |
| 1.2.7 | 2.0 / 2.1 / 2.2 | 通常pauseで収まらないvisual informationにextended audio descriptionが必要か、そのcoverage |
| 1.2.8 | 2.0 / 2.1 / 2.2 | prerecorded synchronized mediaのmedia alternativeが必要情報を同等に伝えるか |
| 1.2.9 | 2.0 / 2.1 / 2.2 | live audio-only contentのequivalent alternativeが必要情報を伝えるか |
| 1.3.1 | 2.0 / 2.1 / 2.2 | visual / structural information and relationshipsの意味とprogrammatic determinability / text availability。structure / AT evidenceを総合 |
| 1.3.2 | 2.0 / 2.1 / 2.2 | content sequenceがmeaningへ影響するか、programmatic sequenceがintended meaningを保持するか |
| 1.3.3 | 2.0 / 2.1 / 2.2 | instructionがshape / color / size / visual location / orientation / sound等のsensory characteristicだけに依存するか |
| 1.3.4 | 2.1 / 2.2 | portrait / landscape restrictionが存在するか、specific display orientationがessentialか |
| 1.3.5 | 2.1 / 2.2 | user informationを収集するinputか、purpose metadataがnormative taxonomyの意味と一致するか |
| 1.3.6 | 2.1 / 2.2 | UI component / icon / regionのpurposeをprogrammatically determineする必要がある対象か、metadataの意味がpurposeと一致するか |
| 1.4.1 | 2.0 / 2.1 / 2.2 | colorがinformation / action / response / visual element distinctionの唯一の手段になっていないか |
| 1.4.2 | 2.0 / 2.1 / 2.2 | auto-play audioの適用条件、pause / stop / independent volume controlが要求を満たすか |
| 1.4.3 | 2.0 / 2.1 / 2.2 | text / image-of-textの対象分類、large text条件、incidental / logo等のexception。ratioはmachine result、`background-not-machine-resolvable` 時は `_05i` のmanual fallback evidenceを使用し、LLMが画像から数値を推測しない |
| 1.4.4 | 2.0 / 2.1 / 2.2 | caption / image-of-text等のexception applicabilityと、current environmentで確認したvalid text scaling mechanismのevidenceをSCへ適用できるか。少なくとも1つのvalid mechanismで全applicable textがbaseline比2.0xのrendered enlargementへ到達し、到達までcontent / functionality lossなしならsatisfied候補。machine ownerがvalid mechanismを操作・scale取得できない場合は `_05i` のmanual fallback evidenceを使用でき、browser capability不足だけでfailureへ短絡しない。browser zoom control値だけで2.0x到達を推測せず、未確認mechanism / text populationが残る状態をfailureへ短絡しない |
| 1.4.5 | 2.0 / 2.1 / 2.2 | image candidateにtextが含まれるか、customizable / essential image-of-text exceptionが成立するか |
| 1.4.6 | 2.0 / 2.1 / 2.2 | enhanced contrast対象分類、large text / incidental / logo等のexception。ratioはmachine result、`background-not-machine-resolvable` 時はmanual fallback evidenceを使用 |
| 1.4.7 | 2.0 / 2.1 / 2.2 | speechを主とするprerecorded audioか、background sound条件 / audio-only exceptionを満たすか |
| 1.4.8 | 2.0 / 2.1 / 2.2 | blocks of textへのapplicabilityと、color selection / width / alignment / spacing / resize等のmachine valuesがsemantic requirementを満たすか |
| 1.4.9 | 2.0 / 2.1 / 2.2 | image candidateにtextが含まれるか、decoration / essential exceptionが成立するか |
| 1.4.10 | 2.1 / 2.2 | required reflow conditionでinformation / functionality lossがあるか、two-dimensional layout等のnormative exceptionが成立するか |
| 1.4.11 | 2.1 / 2.2 | UI component / state / graphical objectを識別するためrequiredなvisual informationか、inactive / UA-controlled等のexception。contrast値はmachine result、`background-not-machine-resolvable` 時はmanual fallback evidenceを使用 |
| 1.4.12 | 2.1 / 2.2 | required text-spacing override後にcontent / functionality lossがあるか。固定overrideの適用結果を意味的に評価 |
| 1.4.13 | 2.1 / 2.2 | hover / focusで追加contentが出るcaseか、dismissible / hoverable / persistent各条件とnormative exception |
| 2.1.1 | 2.0 / 2.1 / 2.2 | functionalityがkeyboard interfaceでoperableか、underlying functionがpath-dependent inputを必要とするexceptionが成立するか |
| 2.1.2 | 2.0 / 2.1 / 2.2 | keyboard focusがcomponent内にtrapされるか、standard exitまたはuser adviceで離脱可能か |
| 2.1.3 | 2.0 / 2.1 / 2.2 | all functionalityがkeyboard interfaceでoperableか。2.1.1のpath-dependent exceptionを適用しない |
| 2.1.4 | 2.1 / 2.2 | single printable character shortcutが存在するか、off / remap / focus時だけactiveのいずれかを満たすか |
| 2.2.1 | 2.0 / 2.1 / 2.2 | time limitへのapplicability、turn off / adjust / extend条件、real-time / essential / 20-hour exception |
| 2.2.2 | 2.0 / 2.1 / 2.2 | moving / blinking / scrolling / auto-updating contentの適用条件とpause / stop / hide / frequency control、essential exception |
| 2.2.3 | 2.0 / 2.1 / 2.2 | content / eventにtimingがessentialか、normative exceptionを除きtiming requirementが存在しないか |
| 2.2.4 | 2.0 / 2.1 / 2.2 | interruptionsをpostpone / suppressできるか、emergency exceptionが成立するか |
| 2.2.5 | 2.0 / 2.1 / 2.2 | authenticated session expiry後のre-authenticationでuser dataをlossせずactivity継続できるか |
| 2.2.6 | 2.1 / 2.2 | inactivityによるdata loss timeoutがあるか、duration warning / preservation exceptionを満たすか |
| 2.3.1 | 2.0 / 2.1 / 2.2 | flash contentがthreshold対象か、three flashes / below-threshold条件を満たすか。manual / external evidence必須 |
| 2.3.2 | 2.0 / 2.1 / 2.2 | flash contentのfrequencyがnormative upper boundを超えないか。manual / external evidence必須 |
| 2.3.3 | 2.1 / 2.2 | interaction-triggered motion animationか、disable mechanismがあるか、animationがfunction / informationにessentialか |
| 2.4.1 | 2.0 / 2.1 / 2.2 | repeated blocksが存在するか、それをbypassするmechanismが意味上成立するか |
| 2.4.2 | 2.0 / 2.1 / 2.2 | page titleが存在するだけでなく、page topic / purposeをdescribeしているか |
| 2.4.3 | 2.0 / 2.1 / 2.2 | sequential navigationがmeaning / operationへ影響する場合、focus orderがそれをpreserveしているか |
| 2.4.4 | 2.0 / 2.1 / 2.2 | link purposeをlink text単独またはprogrammatically determined contextから判断できるか、normative ambiguity exception |
| 2.4.5 | 2.0 / 2.1 / 2.2 | set of pages内のWeb pageをlocateする複数手段があるか、process step exceptionが成立するか |
| 2.4.6 | 2.0 / 2.1 / 2.2 | heading / labelがtopic / purposeをdescribeしているか |
| 2.4.7 | 2.0 / 2.1 / 2.2 | keyboard-operable UIでfocus indicatorが視覚的に認識可能か |
| 2.4.8 | 2.0 / 2.1 / 2.2 | set of pages内でuser locationを示すinformationが利用可能か |
| 2.4.9 | 2.0 / 2.1 / 2.2 | link textだけからpurposeを識別できるか、users generallyへのambiguity exception |
| 2.4.10 | 2.0 / 2.1 / 2.2 | section headingがcontent organizationに使用されているか、content自体がsectionを必要とするか |
| 2.4.11 | 2.2 | keyboard focusを受けるcomponentがauthor-created contentでentirely hiddenになっていないか。geometry evidenceの意味上のownershipを確認 |
| 2.4.12 | 2.2 | keyboard focusを受けるcomponentのどの部分もauthor-created contentでhiddenになっていないか |
| 2.4.13 | 2.2 | focus indicatorがrequired area / contrast changeを満たすか。CSS / SVG等から一意に閉じないshape / visual stateでは `focus-indicator-not-machine-resolvable` によりmanual fallbackを有効化し、manual測定evidenceとscreenshotの意味評価を組み合わせる。LLMがarea / contrast数値を推測しない |
| 2.5.1 | 2.1 / 2.2 | multipoint / path-based gestureでoperableなfunctionalityにsingle-pointer alternativeがあるか、gestureがessentialか |
| 2.5.2 | 2.1 / 2.2 | single-pointer operationのdown-event execution / abort / undo / up-event reversal条件、essential exception |
| 2.5.3 | 2.1 / 2.2 | visible text / image-of-textとして提示されたlabelを特定し、そのtextがaccessible nameへ含まれるというmachine comparisonを当該label / controlへ適用できるか |
| 2.5.4 | 2.1 / 2.2 | device / user motionでoperableなfunctionalityか、UI alternative / motion disableがあるか、motionがessentialか |
| 2.5.5 | 2.1 / 2.2 | pointer target size requirementの対象か、equivalent / inline / UA-controlled / essential exceptionが成立するか |
| 2.5.6 | 2.1 / 2.2 | platform-supported input modalitiesをrestrictしているか、security / essential / user setting等のnormative exception |
| 2.5.7 | 2.2 | dragging movementを使うfunctionalityにdragなしsingle-pointer alternativeがあるか、draggingがessentialか |
| 2.5.8 | 2.2 | minimum target size / spacing条件の対象か、equivalent / inline / UA-controlled / essential exceptionが成立するか |
| 3.1.1 | 2.0 / 2.1 / 2.2 | page default human languageのactual languageとprogrammatic metadataが一致するか |
| 3.1.2 | 2.0 / 2.1 / 2.2 | part-level language changeが存在するか、metadataがactual languageと一致するか、proper name / technical term等のexception |
| 3.1.3 | 2.0 / 2.1 / 2.2 | unusual / restricted usageのwordやphraseが存在する場合、そのspecific meaningをidentifyするmechanismがあるか |
| 3.1.4 | 2.0 / 2.1 / 2.2 | abbreviationのexpanded form / meaningをidentifyするmechanismがあるか |
| 3.1.5 | 2.0 / 2.1 / 2.2 | textがadvanced reading abilityを要求する範囲か、supplemental content / lower-secondary reading versionがあるか。external evidenceを含む |
| 3.1.6 | 2.0 / 2.1 / 2.2 | pronunciationなしではmeaningがambiguousなwordがあるか、specific pronunciationをidentifyするmechanismがあるか |
| 3.2.1 | 2.0 / 2.1 / 2.2 | focus取得だけでchange of contextが発生するか |
| 3.2.2 | 2.0 / 2.1 / 2.2 | user input setting変更だけでchange of contextが発生するか、事前にbehaviorがadvisedされているか |
| 3.2.3 | 2.0 / 2.1 / 2.2 | set of pagesでrepeated navigation mechanismのrelative orderがconsistentか、userによる変更を除外 |
| 3.2.4 | 2.0 / 2.1 / 2.2 | set of pagesでsame functionalityを持つcomponentがconsistently identifiedされているか |
| 3.2.5 | 2.0 / 2.1 / 2.2 | change of contextがuser requestだけで開始されるか、automatic changeをoffにするmechanismがあるか |
| 3.2.6 | 2.2 | help mechanismが複数pageに現れる場合、relative orderがconsistentか、user-initiated changeを除外 |
| 3.3.1 | 2.0 / 2.1 / 2.2 | input errorがautomatically detectedされた場合、error itemがidentifiedされerrorがtextでdescribedされているか |
| 3.3.2 | 2.0 / 2.1 / 2.2 | contentがuser inputを要求する場合、必要なlabel / instructionが提供されているか |
| 3.3.3 | 2.0 / 2.1 / 2.2 | input errorがdetectedされsuggestionがknownな場合、security / purposeを害さずsuggestionを提供できるか |
| 3.3.4 | 2.0 / 2.1 / 2.2 | legal / financial commitment、user-controlled data modification / deletion、test response submissionに該当するか、reversible / checked / confirmedのいずれかを満たすか |
| 3.3.5 | 2.0 / 2.1 / 2.2 | userがtaskを完了するためのcontext-sensitive helpが利用可能か |
| 3.3.6 | 2.0 / 2.1 / 2.2 | user submission一般についてreversible / checked / confirmedのいずれかを満たすか |
| 3.3.7 | 2.2 | 同一processで以前入力 / 提供した情報を再要求しているか、auto-populate / selection alternativeがあるか、essential / security / invalidated information等のexception |
| 3.3.8 | 2.2 | authentication processのcognitive function testへのapplicabilityと、alternative / assistance / normative exceptionが成立するか |
| 3.3.9 | 2.2 | enhanced authentication requirementのcognitive function testへのapplicabilityと、許可されたalternative / exceptionが成立するか |
| 4.1.1 | 2.0 / 2.1 | `m-parsing-version-rule` がHTML / XMLならsemantic実行不要。その他markup technologyだけversioned normative parsing requirementを評価 |
| 4.1.2 | 2.0 / 2.1 / 2.2 | UI componentのname / role / value / user-settable stateがprogrammatically determinableで、変更通知が利用可能か。custom component等のapplicabilityを含む |
| 4.1.3 | 2.1 / 2.2 | focusを受けず提示されるstatus informationか、appropriate role / propertyでATへprogrammatically determinedできるか |

## 8. asset作成契約

実装時はW3C正本から各version / Success Criterionを全件確認し、rowを生成・レビューします。

1. normative Success Criterion本文をsource item化する
2. requirementの意味上独立したclause / exception / conditionへlocatorを付ける
3. meaning judgmentが必要なclauseだけsemantic evaluation pointへする
4. 数値、集合、fixed state / attribute comparison等はmachine procedureへ残し、semantic pointへ重複させない
5. procedure catalogからrequired evidence roleを照合する
6. shortcut禁止条件を明記する
7. source原文とのsemantic validationを全row実施する
8. canonical JSON hashを `static_data_versions.wcag_semantic_contracts` へ固定する

「86件あるため一部だけ先に実装する」は許可しません。supported versionの全rowを同じ実装範囲で閉じます。

## 9. forbidden shortcuts

少なくとも次を全row共通で禁止します。

- 単一ACT Rule PASSだけでSuccess Criterion全体を `satisfied` にする
- 単一element 0件だけでapplicable population `none` にする
- machine procedure一部PASSだけでsemantic requirementを閉じる
- screenshotなしでvisual meaningを観測済みとする
- required manual / AT / external evidenceをLLM推測で補う
- exceptionを根拠なしで適用する
- neighboring Success Criterionの判断をそのまま流用する
- version違いのnormative wordingを暗黙利用する

criterion固有で追加の禁止shortcutがある場合はrowへ固定します。

## 10. deterministic validator

validatorは次を独立確認します。

- version別criterion集合とsemantic contract row集合の差分0
- duplicate contract key / duplicate point key 0
- source / clause / definition / exception refs全解決
- semantic evaluation pointのsource clause coverage
- required evidence roleが許可enumで、current applicable procedure集合とprocedure catalogとの整合がある
- `_05i` の4 AT procedureと `procedure_applicability_contracts[]` のdecision key / source clause / allowed evidence roleが1対1で一致
- AT applicability contractが `assistive-technology-result` またはfinal semantic resultへ依存していない
- machine-only decisionをsemantic pointへ重複させていない
- allowed additional observation fieldが `_05g` の16 keyの部分集合
- forbidden shortcutがrequired common guardを含む
- 4.1.1 version / technology rule
- asset canonical hash / approved hash一致

## 11. semantic eval

semantic evalは代表SCだけの品質確認ではなく、asset全件のcontract completenessをdeterministicに確認したうえで、meaning判断の代表caseを実Judgeで確認します。

少なくとも次を含めます。

- applicable / not-applicable / unknown
- normative exception成立 / 不成立 / evidence不足
- machine resultとsemantic meaningが一致しないcase
- visual evidenceが必要なcase
- AT applicability applicable / not-applicable / unknownをAT resultなしで判定するcase
- applicable判定後にAT evidenceを取得してfinal semantic evaluationへ渡すcase
- manual / AT evidenceが必要なcase
- additional observationで解決するcase
- no-progressでundeterminedへ残るcase
- conflicting evidence
- WCAG 2.0 / 2.1 4.1.1 HTML/XML shortcutとnon-HTML/XML path

## 12. 完了条件

- supported versionの全Success Criterionにversioned semantic contract rowがある
- 各rowのnormative clause / definition / exception / semantic evaluation point / required evidence roleがsourceへ追跡可能
- machine化できる処理をsemanticへ逃がしていない
- LLMの判断理由・uncertainty・evidence関係・追加観測の柔軟性を維持する
- criterion / procedure / point集合をLLMが変更できない
- 4.1.1特別契約がversion / technology別に固定される
- deterministic validator / semantic evalがPASSする
